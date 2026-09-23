"""Zone management: import, resolution, and the two numbers that say whether it worked (RF-152).

The requirement is one line — «gestión de zonas (polígonos) para la asignación y la descarga de
mapas» — and its acceptance criterion is «dibujar o importar polígonos GeoJSON». What makes it
useful, though, is not the import: it is the three questions the import makes answerable.

1. **Which zone is this work order in?** Used to pick a crew and to name the offline package.
2. **Which work orders are in no zone at all?** This is the number that matters. Zones that cover
   90 % of the territory look correct on a map and quietly leave one parish unassignable, and
   nobody finds out until a technician is standing in it.
3. **Which zones overlap?** Because a point in two zones has no answer, and the platform must say
   so rather than pick the first row the planner happens to see.

Two deliberate refusals:

* **An invalid polygon is rejected, not repaired.** PostGIS can fix a self-intersecting ring with
  `ST_MakeValid`, and the result is a *different boundary* than the one in the file. Silently
  redrawing somebody's operating zone and reporting success is how a zone ends up covering a street
  it does not cover. So the feature is refused with the reason PostGIS gave, and the fix belongs in
  the source file.
* **An existing `work_order.zone` is never overwritten.** A zone on an order may have come from the
  corporate system, from an integration, or from a planner who knows something the polygon does not.
  Backfilling only fills what is empty.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.audit.models import EventKind
from app.audit.service import record
from app.org.models import BusinessUnit
from app.workorders.models import STORAGE_SRID, WorkOrder, WorkOrderState
from app.zones.models import Zone, ZoneOrigin

#: Property names an importer will look at for the zone's code, in order, when the caller does not
#: name one. Generic words on purpose: a GeoJSON exported from any desktop GIS uses one of these,
#: and nothing here may carry a name from the CNEL data model (rule 4).
CODE_PROPERTIES = ("code", "codigo", "zone", "zona", "id")

#: And for its display name.
NAME_PROPERTIES = ("name", "nombre", "label", "etiqueta", "descripcion")

#: The geometry types a zone accepts. A zone is an area; a point or a line is a different mistake
#: and saying which one it was saves the importer's user a round trip.
POLYGONAL = ("Polygon", "MultiPolygon")

#: States whose work orders still have somewhere to go, and therefore whose coverage matters. A
#: closed order in no zone is history; an assigned one in no zone is a technician without a map.
OPEN_STATES = (
    WorkOrderState.DRAFT,
    WorkOrderState.PLANNED,
    WorkOrderState.ASSIGNED,
    WorkOrderState.DOWNLOADED,
    WorkOrderState.EN_ROUTE,
    WorkOrderState.ON_SITE,
    WorkOrderState.IN_EXECUTION,
    WorkOrderState.SUSPENDED,
)


class ZoneError(Exception):
    """A request that cannot be served at all, as opposed to one feature that cannot be read."""


class UnknownZoneError(ZoneError):
    pass


class DuplicateZoneError(ZoneError):
    pass


@dataclass(frozen=True)
class Rejection:
    """One feature the importer would not take, and why.

    Carried per feature rather than raised, because a file of forty parishes with one broken ring
    should import thirty-nine. Refusing the file would leave the user editing GeoJSON by hand to
    find out which feature it was.
    """

    #: Position in the file, 0-based, so the user can find it in an editor.
    index: int
    code: str | None
    reason: str


@dataclass
class ImportReport:
    """What an import did. Both halves, always."""

    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)

    @property
    def accepted(self) -> int:
        return len(self.created) + len(self.updated)

    def as_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "updated": self.updated,
            "accepted": self.accepted,
            "rejected": [
                {"index": item.index, "code": item.code, "reason": item.reason}
                for item in self.rejected
            ],
        }


@dataclass(frozen=True)
class Overlap:
    """Two zones of the same unit whose interiors meet."""

    left: str
    right: str
    #: Square metres, computed on the geography so the number means something at this latitude.
    area_m2: float

    def describe(self) -> str:
        return f"{self.left} y {self.right} se solapan en {self.area_m2:,.0f} m²".replace(",", ".")


@dataclass(frozen=True)
class Coverage:
    """Whether the zones actually cover the work (question 2 of the module docstring)."""

    open_orders: int
    #: Orders whose point falls in exactly one active zone.
    inside_one: int
    #: Orders whose point falls in two or more. These have no answer, which is why they are counted
    #: apart from the ones that are simply outside.
    ambiguous: int
    #: Orders with a point that no zone contains. The number a planner has to act on.
    outside: int
    #: Orders with no point at all. Not a zone problem, but it would otherwise hide inside
    #: `outside` and make the zones look worse than they are.
    without_location: int

    @property
    def covered_share(self) -> float | None:
        """Share of *locatable* open orders that resolve to one zone, or None when there are none.

        The denominator excludes orders without a point deliberately: a unit that has not started
        capturing coordinates would otherwise read as 0 % zone coverage, which is true of the
        coordinates and false of the zones.
        """
        locatable = self.open_orders - self.without_location
        if locatable <= 0:
            return None
        return self.inside_one / locatable

    def as_dict(self) -> dict[str, Any]:
        return {
            "open_orders": self.open_orders,
            "inside_one": self.inside_one,
            "ambiguous": self.ambiguous,
            "outside": self.outside,
            "without_location": self.without_location,
            "covered_share": self.covered_share,
        }


@dataclass
class BackfillReport:
    """Result of filling `work_order.zone` from the polygons."""

    filled: dict[str, str] = field(default_factory=dict)
    ambiguous: dict[str, list[str]] = field(default_factory=dict)
    outside: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "filled": self.filled,
            "ambiguous": self.ambiguous,
            "outside": self.outside,
        }


def _scoped(unit: BusinessUnit) -> Select[tuple[Zone]]:
    return select(Zone).where(Zone.business_unit_id == unit.id)


def list_zones(
    session: Session, unit: BusinessUnit, *, include_inactive: bool = False
) -> list[Zone]:
    statement = _scoped(unit)
    if not include_inactive:
        statement = statement.where(Zone.active.is_(True))
    return list(session.execute(statement.order_by(Zone.code)).scalars())


def get_zone(session: Session, unit: BusinessUnit, code: str) -> Zone:
    zone = session.execute(_scoped(unit).where(Zone.code == code)).scalar_one_or_none()
    if zone is None:
        raise UnknownZoneError(f"la zona «{code}» no existe en esta unidad")
    return zone


def _multipolygon_sql(geometry: dict[str, Any]) -> Any:
    """A SQL expression that turns one GeoJSON geometry into a validated MULTIPOLYGON.

    `ST_Multi` rather than a cast: a Polygon and a MultiPolygon must land in the same column, and
    promoting the first is lossless while narrowing the second is not.
    """
    literal = json.dumps(geometry)
    return func.ST_Multi(func.ST_SetSRID(func.ST_GeomFromGeoJSON(literal), STORAGE_SRID))


def _validate_geometry(session: Session, geometry: dict[str, Any]) -> str | None:
    """None when PostGIS accepts the ring; otherwise the reason it gave.

    Asking the database rather than reimplementing OGC validity: the same engine that will answer
    «is this point in this zone» decides whether the zone is answerable at all.
    """
    kind = geometry.get("type")
    if kind not in POLYGONAL:
        seen = kind or "desconocida"
        return f"la geometría es {seen} y una zona es un área (Polygon o MultiPolygon)"
    # A malformed GeoJSON body is the caller's mistake, not a bug here, so the error becomes a
    # rejection reason. The SAVEPOINT is what makes that possible: PostGIS aborts the whole
    # transaction on a literal it cannot parse, and a plain `session.rollback()` here would throw
    # away the features of the same file that had already been accepted. This probe rolls back only
    # itself.
    try:
        with session.begin_nested():
            reason = session.execute(
                select(func.ST_IsValidReason(_multipolygon_sql(geometry)))
            ).scalar_one()
    except Exception as exc:
        return f"PostGIS no pudo leer la geometría: {type(exc).__name__}"
    if reason and reason != "Valid Geometry":
        return f"geometría inválida: {reason}"
    return None


def _first_property(properties: dict[str, Any], names: tuple[str, ...]) -> str | None:
    for name in names:
        for key, value in properties.items():
            if key.lower() == name and value not in (None, ""):
                return str(value).strip()
    return None


def import_geojson(
    session: Session,
    unit: BusinessUnit,
    document: dict[str, Any],
    *,
    actor: str,
    code_property: str | None = None,
    name_property: str | None = None,
    replace_existing: bool = True,
) -> ImportReport:
    """Import a FeatureCollection (or one Feature) as zones.

    :param replace_existing: when True a feature whose code already exists replaces that zone's
        boundary — re-importing a corrected file is the normal way to fix a zone. When False an
        existing code is rejected, which is what an operator wants the first time they import a
        file they are not sure about.
    """
    if document.get("type") == "Feature":
        features: list[Any] = [document]
    elif document.get("type") == "FeatureCollection":
        features = list(document.get("features") or [])
    else:
        raise ZoneError(
            "el documento debe ser un FeatureCollection o un Feature de GeoJSON; "
            f"llegó «{document.get('type') or 'sin type'}»"
        )
    if not features:
        raise ZoneError("el GeoJSON no trae ningún rasgo")

    report = ImportReport()
    seen: set[str] = set()
    source_name = str(document.get("name") or "").strip() or None

    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            report.rejected.append(
                Rejection(index, None, "el elemento no es un Feature de GeoJSON")
            )
            continue
        properties = feature.get("properties") or {}
        if not isinstance(properties, dict):
            properties = {}
        code = (
            str(properties.get(code_property) or "").strip()
            if code_property
            else _first_property(properties, CODE_PROPERTIES)
        )
        if not code:
            wanted = code_property or "/".join(CODE_PROPERTIES)
            report.rejected.append(
                Rejection(
                    index, None, f"el rasgo no trae el código de la zona (se buscó en {wanted})"
                )
            )
            continue
        if code in seen:
            report.rejected.append(
                Rejection(index, code, "el código viene repetido en el mismo archivo")
            )
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            report.rejected.append(Rejection(index, code, "el rasgo no trae geometría"))
            continue
        problem = _validate_geometry(session, geometry)
        if problem is not None:
            report.rejected.append(Rejection(index, code, problem))
            continue

        name = (
            str(properties.get(name_property) or "").strip()
            if name_property
            else _first_property(properties, NAME_PROPERTIES)
        ) or code
        existing = session.execute(_scoped(unit).where(Zone.code == code)).scalar_one_or_none()
        provenance = {
            "file": source_name,
            "feature_index": index,
            "properties": {
                str(k): v for k, v in properties.items() if isinstance(v, str | int | float | bool)
            },
        }
        if existing is not None:
            if not replace_existing:
                report.rejected.append(
                    Rejection(index, code, "la zona ya existe y no se pidió reemplazarla")
                )
                continue
            existing.name = name
            existing.geom = _multipolygon_sql(geometry)
            existing.origin = ZoneOrigin.IMPORTED
            existing.imported_from = provenance
            existing.updated_by = actor
            session.flush()
            _audit(session, unit, existing, actor=actor, created=False)
            report.updated.append(code)
        else:
            zone = Zone(
                business_unit_id=unit.id,
                code=code,
                name=name,
                geom=_multipolygon_sql(geometry),
                origin=ZoneOrigin.IMPORTED,
                imported_from=provenance,
                created_by=actor,
                updated_by=actor,
            )
            session.add(zone)
            session.flush()
            _audit(session, unit, zone, actor=actor, created=True)
            report.created.append(code)
        seen.add(code)

    return report


def save_drawn(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str,
    name: str,
    geometry: dict[str, Any],
    actor: str,
    description: str | None = None,
) -> Zone:
    """Create or replace one zone from a polygon drawn in the browser."""
    problem = _validate_geometry(session, geometry)
    if problem is not None:
        raise ZoneError(problem)
    zone = session.execute(_scoped(unit).where(Zone.code == code)).scalar_one_or_none()
    if zone is None:
        zone = Zone(
            business_unit_id=unit.id,
            code=code,
            name=name,
            description=description,
            geom=_multipolygon_sql(geometry),
            origin=ZoneOrigin.DRAWN,
            created_by=actor,
            updated_by=actor,
        )
        session.add(zone)
        session.flush()
        _audit(session, unit, zone, actor=actor, created=True)
        return zone
    zone.name = name
    zone.description = description
    zone.geom = _multipolygon_sql(geometry)
    zone.origin = ZoneOrigin.DRAWN
    zone.imported_from = None
    zone.updated_by = actor
    session.flush()
    _audit(session, unit, zone, actor=actor, created=False)
    return zone


def set_active(
    session: Session, unit: BusinessUnit, code: str, *, active: bool, actor: str
) -> Zone:
    """Deactivate or reactivate a zone. There is no delete, on purpose (see the model)."""
    zone = get_zone(session, unit, code)
    if zone.active != active:
        zone.active = active
        zone.updated_by = actor
        session.flush()
        record(
            session,
            unit.id,
            kind=EventKind.FIELD_CHANGED,
            subject_type="zone",
            subject_id=str(zone.id),
            actor=actor,
            payload={"code": zone.code, "field": "active", "to": active},
        )
    return zone


def _audit(session: Session, unit: BusinessUnit, zone: Zone, *, actor: str, created: bool) -> None:
    record(
        session,
        unit.id,
        kind=EventKind.CREATED if created else EventKind.FIELD_CHANGED,
        subject_type="zone",
        subject_id=str(zone.id),
        actor=actor,
        payload={"code": zone.code, "name": zone.name, "origin": zone.origin},
        reason=None if created else "se reemplazó el polígono de la zona",
    )


def zones_at(session: Session, unit: BusinessUnit, longitude: float, latitude: float) -> list[str]:
    """The active zones whose polygon contains the point, ordered by code.

    Plural because zones can overlap and a point can therefore have no single answer. Boundary
    contact counts as inside (`ST_Intersects`, not `ST_Contains`): a point exactly on a shared edge
    is then reported as ambiguous, which is the truth, instead of belonging to nowhere.
    """
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), STORAGE_SRID)
    rows = session.execute(
        select(Zone.code)
        .where(
            Zone.business_unit_id == unit.id,
            Zone.active.is_(True),
            func.ST_Intersects(Zone.geom, point),
        )
        .order_by(Zone.code)
    ).all()
    return [row[0] for row in rows]


def overlaps(session: Session, unit: BusinessUnit) -> list[Overlap]:
    """Pairs of active zones whose interiors meet.

    Zones that merely share a border are *not* an overlap — adjacent zones are the normal case and
    reporting every neighbour would bury the one pair that is actually wrong. So touching is
    excluded and containment is not: a zone entirely inside another is a real problem.
    """
    left = Zone.__table__.alias("l")
    right = Zone.__table__.alias("r")
    rows = session.execute(
        select(
            left.c.code,
            right.c.code,
            # Cast to geography so the area comes out in square metres. On `geometry` at this
            # latitude it would come out in square degrees, which is a number nobody can read.
            func.ST_Area(func.ST_Intersection(left.c.geom, right.c.geom).cast(Geography)),
        )
        .where(
            left.c.business_unit_id == unit.id,
            right.c.business_unit_id == unit.id,
            left.c.active.is_(True),
            right.c.active.is_(True),
            left.c.code < right.c.code,
            func.ST_Intersects(left.c.geom, right.c.geom),
            ~func.ST_Touches(left.c.geom, right.c.geom),
        )
        .order_by(left.c.code, right.c.code)
    ).all()
    return [Overlap(str(a), str(b), float(area or 0.0)) for a, b, area in rows]


def _open_orders_with_location(unit: BusinessUnit) -> Select[tuple[uuid.UUID, Any]]:
    return select(WorkOrder.id, WorkOrder.location).where(
        WorkOrder.business_unit_id == unit.id,
        WorkOrder.state.in_([state.value for state in OPEN_STATES]),
    )


def coverage(session: Session, unit: BusinessUnit) -> Coverage:
    """How many open work orders the zones actually place."""
    matches = (
        select(
            WorkOrder.id.label("order_id"),
            func.count(Zone.id).label("zones"),
        )
        .select_from(WorkOrder)
        .outerjoin(
            Zone,
            (Zone.business_unit_id == unit.id)
            & Zone.active.is_(True)
            & func.ST_Intersects(Zone.geom, WorkOrder.location),
        )
        .where(
            WorkOrder.business_unit_id == unit.id,
            WorkOrder.state.in_([state.value for state in OPEN_STATES]),
            WorkOrder.location.is_not(None),
        )
        .group_by(WorkOrder.id)
        .subquery()
    )
    counted = session.execute(select(matches.c.zones, func.count()).group_by(matches.c.zones)).all()
    inside_one = 0
    ambiguous = 0
    outside = 0
    for zones, total in counted:
        if zones == 0:
            outside += int(total)
        elif zones == 1:
            inside_one += int(total)
        else:
            ambiguous += int(total)

    without_location = int(
        session.execute(
            select(func.count())
            .select_from(WorkOrder)
            .where(
                WorkOrder.business_unit_id == unit.id,
                WorkOrder.state.in_([state.value for state in OPEN_STATES]),
                WorkOrder.location.is_(None),
            )
        ).scalar_one()
    )
    return Coverage(
        open_orders=inside_one + ambiguous + outside + without_location,
        inside_one=inside_one,
        ambiguous=ambiguous,
        outside=outside,
        without_location=without_location,
    )


def backfill_zones(
    session: Session, unit: BusinessUnit, *, actor: str, dry_run: bool = False
) -> BackfillReport:
    """Fill `work_order.zone` on open orders that have none, from the polygons.

    Only the empty ones, and only the unambiguous ones. An order already carrying a zone keeps it:
    the string may have come from the corporate system or from a planner, and a polygon drawn last
    Tuesday is not authority enough to contradict either. The ambiguous and the uncovered are
    returned rather than guessed — a batch that quietly picked one of two zones would be
    unreviewable.
    """
    report = BackfillReport()
    rows = session.execute(
        select(WorkOrder)
        .where(
            WorkOrder.business_unit_id == unit.id,
            WorkOrder.state.in_([state.value for state in OPEN_STATES]),
            WorkOrder.location.is_not(None),
            (WorkOrder.zone.is_(None)) | (WorkOrder.zone == ""),
        )
        .order_by(WorkOrder.created_at)
    ).scalars()
    for order in rows:
        found = session.execute(
            select(Zone.code)
            .where(
                Zone.business_unit_id == unit.id,
                Zone.active.is_(True),
                func.ST_Intersects(Zone.geom, order.location),
            )
            .order_by(Zone.code)
        ).all()
        codes = [row[0] for row in found]
        key = str(order.id)
        if len(codes) == 1:
            report.filled[key] = codes[0]
            if not dry_run:
                previous = order.zone
                order.zone = codes[0]
                session.flush()
                record(
                    session,
                    unit.id,
                    kind=EventKind.FIELD_CHANGED,
                    subject_type="work_order",
                    subject_id=key,
                    work_order_id=order.id,
                    actor=actor,
                    payload={"field": "zone", "from": previous, "to": codes[0]},
                    reason="zona asignada desde el polígono (RF-152)",
                )
        elif codes:
            report.ambiguous[key] = codes
        else:
            report.outside.append(key)
    return report


def as_feature(session: Session, zone: Zone) -> dict[str, Any]:
    """One zone as a GeoJSON Feature, which is what MapLibre draws and what an export returns."""
    geometry = session.execute(select(func.ST_AsGeoJSON(zone.geom))).scalar_one()
    return {
        "type": "Feature",
        "geometry": json.loads(geometry),
        "properties": {
            "code": zone.code,
            "name": zone.name,
            "description": zone.description,
            "origin": zone.origin,
            "active": zone.active,
            "updated_by": zone.updated_by,
            "updated_at": zone.updated_at.isoformat() if zone.updated_at else None,
        },
    }


def as_collection(session: Session, zones: list[Zone]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [as_feature(session, zone) for zone in zones],
    }
