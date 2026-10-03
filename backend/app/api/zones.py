"""Zone administration (RF-152, M15).

Read for planners and dispatchers — they need the polygons to draw the board — and write for the
functional administrator alone. A zone boundary decides which crew covers which street, so moving
one is an administrative act and not a planning convenience.

The read endpoints speak GeoJSON because that is what MapLibre consumes directly and what the
operator's desktop GIS produces, so the same document round-trips: export, correct it in QGIS,
import it back.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.zones import service as zones

router = APIRouter(prefix="/api/v1/zones", tags=["zones"], dependencies=[Depends(unit_scope)])

SessionDep = Annotated[Session, Depends(get_session)]

#: Who may look. The dispatcher and the planner assign by zone, and the supervisor's boards are
#: filtered by it.
READERS = (Role.PLANNER, Role.SUPERVISOR, Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN)

#: Who may move a boundary. One role, deliberately (see the module docstring).
EDITORS = (Role.FUNCTIONAL_ADMIN,)


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


class ZoneIn(BaseModel):
    """One zone drawn in the browser. The geometry arrives as GeoJSON, like everything else."""

    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    geometry: dict[str, Any]
    # No `created_by`: the author is whoever the token says they are.


class ImportIn(BaseModel):
    document: dict[str, Any]
    #: Which property carries the code. Left unset the importer tries the usual generic names.
    code_property: str | None = Field(default=None, max_length=64)
    name_property: str | None = Field(default=None, max_length=64)
    #: False the first time an operator imports a file they are unsure about: an existing code is
    #: then reported instead of silently replacing a boundary somebody is working against.
    replace_existing: bool = True


@router.get("/units/{unit_code}", summary="Las zonas de la unidad, como GeoJSON (RF-152)")
def list_zones(
    unit_code: str,
    session: SessionDep,
    include_inactive: Annotated[bool, Query()] = False,
    _: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    rows = zones.list_zones(session, unit, include_inactive=include_inactive)
    return zones.as_collection(session, rows)


@router.get(
    "/units/{unit_code}/coverage",
    summary="Cuántas OT abiertas caen en una zona, en varias o en ninguna (RF-152)",
)
def coverage(
    unit_code: str,
    session: SessionDep,
    _: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> dict[str, Any]:
    """The number that says whether the zones work: how much open work they fail to place."""
    unit = _unit(session, unit_code)
    return {
        "coverage": zones.coverage(session, unit).as_dict(),
        "overlaps": [
            {
                "left": item.left,
                "right": item.right,
                "area_m2": item.area_m2,
                "text": item.describe(),
            }
            for item in zones.overlaps(session, unit)
        ],
    }


@router.get("/units/{unit_code}/at", summary="En qué zonas cae un punto (RF-152)")
def zones_at(
    unit_code: str,
    session: SessionDep,
    longitude: Annotated[float, Query(ge=-180, le=180)],
    latitude: Annotated[float, Query(ge=-90, le=90)],
    _: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> dict[str, Any]:
    """Plural, because overlapping zones give a point more than one answer and the caller has to
    see that rather than receive the first row."""
    unit = _unit(session, unit_code)
    found = zones.zones_at(session, unit, longitude, latitude)
    return {"zones": found, "ambiguous": len(found) > 1}


@router.put("/units/{unit_code}/{code}", summary="Crear o reemplazar una zona dibujada (RF-152)")
def save_zone(
    unit_code: str,
    code: str,
    payload: ZoneIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*EDITORS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    if payload.code != code:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"el código de la ruta («{code}») y el del cuerpo («{payload.code}») no coinciden",
        )
    try:
        zone = zones.save_drawn(
            session,
            unit,
            code=code,
            name=payload.name,
            geometry=payload.geometry,
            description=payload.description,
            actor=principal.subject,
        )
    except zones.ZoneError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return zones.as_feature(session, zone)


@router.post("/units/{unit_code}/import", summary="Importar un GeoJSON de zonas (RF-152)")
def import_zones(
    unit_code: str,
    payload: ImportIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*EDITORS))] = None,
) -> dict[str, Any]:
    """A file of forty parishes with one broken ring imports thirty-nine, and names the one."""
    unit = _unit(session, unit_code)
    try:
        report = zones.import_geojson(
            session,
            unit,
            payload.document,
            actor=principal.subject,
            code_property=payload.code_property,
            name_property=payload.name_property,
            replace_existing=payload.replace_existing,
        )
    except zones.ZoneError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return report.as_dict()


@router.post("/units/{unit_code}/{code}/active", summary="Activar o desactivar una zona (RF-152)")
def set_active(
    unit_code: str,
    code: str,
    session: SessionDep,
    active: Annotated[bool, Body(embed=True)],
    principal: Annotated[Any, Depends(require_roles(*EDITORS))] = None,
) -> dict[str, Any]:
    """There is no delete: a zone that named ten thousand closed orders is part of their history."""
    unit = _unit(session, unit_code)
    try:
        zone = zones.set_active(session, unit, code, active=active, actor=principal.subject)
    except zones.UnknownZoneError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    session.commit()
    return zones.as_feature(session, zone)


@router.post(
    "/units/{unit_code}/backfill",
    summary="Rellenar la zona de las OT abiertas que no la tienen (RF-152)",
)
def backfill(
    unit_code: str,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*EDITORS))] = None,
    dry_run: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """Only the empty ones and only the unambiguous ones; the rest come back for a person to see."""
    unit = _unit(session, unit_code)
    report = zones.backfill_zones(session, unit, actor=principal.subject, dry_run=dry_run)
    # No rollback on the dry run: `backfill_zones` writes nothing when asked not to, and a rollback
    # here would be a second place that has to stay true about that. One place is enough.
    if not dry_run:
        session.commit()
    return {"dry_run": dry_run, **report.as_dict()}
