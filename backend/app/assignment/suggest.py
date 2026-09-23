"""Assisted assignment: the top three crews, with a score somebody can argue with (RF-021).

«La sugerencia devuelve el top 3 de cuadrillas con puntaje explicable» is the acceptance criterion,
and *explicable* is the whole design. A planner who cannot see why a crew came first will either
follow the number blindly or ignore it, and both are worse than no suggestion.

So the shape is:

* **Hard requirements exclude; soft factors score.** A crew without the competency the form demands
  never appears, however close it is. Folding safety into a weighted sum would let proximity
  outvote «no está habilitada para trabajar en tensión», and the day that happens somebody is hurt.
* **Every excluded crew comes back with its reason.** Silently omitting it leaves the planner
  wondering whether the platform forgot C-03 or ruled it out; the first invites them to assign it
  by hand.
* **Every point carries a sentence.** Not a weight table in a docstring: the reason travels in the
  payload, so the screen shows «+40: la OT cae en la zona NORTE, que es la de esta cuadrilla».
* **Unknown is said, not scored as zero.** The platform holds no crew GPS (RF-020's «último GPS
  reportado» is not captured yet), so proximity falls back to where the crew's open work is, and
  when there is none it says so instead of quietly awarding nothing and looking like a bad fit.

Nothing here assigns anything. It answers a question; the planner clicks (RF-021 is a suggestion,
and ADR-013's rule that a decision needs a person holds here too).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.forms.catalog import load_definitions
from app.org.models import BusinessUnit
from app.workorders.models import STORAGE_SRID, Crew, WorkOrder, WorkOrderState
from app.zones.models import Zone

#: How many suggestions come back. The requirement's number.
TOP_N = 3

#: States that mean a crew is still carrying the order. Same set the workload board uses, so the
#: two screens cannot disagree about what «carga abierta» means.
OPEN_STATES = (
    WorkOrderState.ASSIGNED,
    WorkOrderState.DOWNLOADED,
    WorkOrderState.EN_ROUTE,
    WorkOrderState.ON_SITE,
    WorkOrderState.IN_EXECUTION,
    WorkOrderState.SUSPENDED,
)

#: Points for each factor. Deliberately whole numbers that add to 100: a planner comparing 72 with
#: 68 should be able to see which factor made the difference without a calculator.
POINTS_ZONE = 40
POINTS_DISTANCE = 30
POINTS_LOAD = 20
POINTS_SLA = 10

#: Beyond this, distance stops earning anything. Twenty kilometres is roughly a service area's own
#: size — past it, «closer» stops meaning «can get there sooner» in city traffic.
DISTANCE_CEILING_KM = 20.0

#: An order due within this window is urgent, and a crew already holding urgent work has less room
#: for more. The same window the operational board calls «por vencer» (RF-130).
DUE_SOON = timedelta(hours=8)

#: Load above this many open orders earns nothing. Not a hard cap: a planner may well want to give a
#: tenth order to the crew that is already in that street, and the score should let them see the
#: cost rather than forbid it.
LOAD_CEILING = 8


@dataclass(frozen=True)
class Reason:
    """One factor's contribution, with the sentence that explains it."""

    factor: str
    points: int
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"factor": self.factor, "points": self.points, "detail": self.detail}


@dataclass
class Candidate:
    """A crew that may take the order, and why it scored what it scored."""

    crew_id: uuid.UUID
    code: str
    name: str
    score: int = 0
    reasons: list[Reason] = field(default_factory=list)

    def add(self, factor: str, points: int, detail: str) -> None:
        self.reasons.append(Reason(factor, points, detail))
        self.score += points

    def as_dict(self) -> dict[str, Any]:
        return {
            "crew_id": str(self.crew_id),
            "code": self.code,
            "name": self.name,
            "score": self.score,
            "reasons": [reason.as_dict() for reason in self.reasons],
        }


@dataclass(frozen=True)
class Exclusion:
    """A crew that was ruled out, and why. Returned, never silently dropped."""

    crew_id: uuid.UUID
    code: str
    name: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "crew_id": str(self.crew_id),
            "code": self.code,
            "name": self.name,
            "reason": self.reason,
        }


@dataclass
class Suggestion:
    """The answer: the top few, everything that was ruled out, and what could not be measured."""

    work_order_id: uuid.UUID
    required_competencies: list[str]
    candidates: list[Candidate] = field(default_factory=list)
    excluded: list[Exclusion] = field(default_factory=list)
    #: What the score could not take into account, in Spanish. Shown, not paraphrased: a suggestion
    #: computed without knowing where the order is should say so rather than look confident.
    caveats: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": str(self.work_order_id),
            "required_competencies": self.required_competencies,
            "candidates": [item.as_dict() for item in self.candidates],
            "excluded": [item.as_dict() for item in self.excluded],
            "caveats": self.caveats,
        }


def required_competencies(form_code: str) -> list[str]:
    """What the order's form demands of a crew. Data, from `forms/definitions/` (rule 3)."""
    definition = load_definitions().get(form_code)
    if definition is None:
        # An unknown form is not a reason to suggest nobody: the order exists and somebody has to
        # do it. The caveat says the requirements could not be read.
        return []
    return list(definition.form.requires_competencies)


def _zones_of(session: Session, unit: BusinessUnit, order: WorkOrder) -> list[str]:
    """The active zones whose polygon contains the order's point (RF-152)."""
    if order.location is None:
        return []
    rows = session.execute(
        select(Zone.code)
        .where(
            Zone.business_unit_id == unit.id,
            Zone.active.is_(True),
            func.ST_Intersects(Zone.geom, order.location),
        )
        .order_by(Zone.code)
    ).all()
    return [row[0] for row in rows]


@dataclass(frozen=True)
class Workload:
    """What a crew is already carrying."""

    open_orders: int
    due_soon: int
    #: Kilometres from the centroid of the crew's open work to this order, or None when the crew
    #: has no open work with a location to compute it from.
    distance_km: float | None


def _order_point(session: Session, order: WorkOrder) -> tuple[float, float] | None:
    """The order's coordinates, read back as numbers.

    Read rather than used directly: `order.location` comes off the row as a WKB element, which is a
    value and not a SQL expression, so it cannot be cast inside a query. Two floats can.
    """
    if order.location is None:
        return None
    row = session.execute(
        select(func.ST_X(WorkOrder.location), func.ST_Y(WorkOrder.location)).where(
            WorkOrder.id == order.id
        )
    ).first()
    if row is None or row[0] is None or row[1] is None:
        return None
    return float(row[0]), float(row[1])


def _workloads(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    now: datetime,
    point: tuple[float, float] | None,
) -> dict[uuid.UUID, Workload]:
    """One query for the three things every candidate needs.

    The distance is from the **centroid of the crew's open work**, not from a reported position: the
    platform holds no crew GPS yet. It is a proxy, and it is a defensible one — a crew with six
    orders in the north is in the north — but it is a proxy, and the caveats say so.
    """
    horizon = now + DUE_SOON
    centroid = func.ST_Centroid(func.ST_Collect(WorkOrder.location))
    here = (
        func.ST_SetSRID(func.ST_MakePoint(point[0], point[1]), STORAGE_SRID)
        if point is not None
        else None
    )
    distance = (
        func.ST_Distance(centroid.cast(Geography), here.cast(Geography)) / 1000.0
        if here is not None
        else None
    )
    # Typed loosely on purpose: the distance column is a float expression among UUID and int
    # ones, and narrowing the list to their common type is what the annotation would have to do.
    columns: list[Any] = [
        WorkOrder.assigned_crew_id,
        func.count(WorkOrder.id),
        func.count(WorkOrder.sla_due_at).filter(WorkOrder.sla_due_at <= horizon),
    ]
    if distance is not None:
        columns.append(distance)
    rows = session.execute(
        select(*columns)
        .where(
            WorkOrder.business_unit_id == unit.id,
            WorkOrder.state.in_([state.value for state in OPEN_STATES]),
            WorkOrder.assigned_crew_id.is_not(None),
            WorkOrder.id != order.id,
        )
        .group_by(WorkOrder.assigned_crew_id)
    ).all()
    found: dict[uuid.UUID, Workload] = {}
    for row in rows:
        crew_id = row[0]
        km = float(row[3]) if distance is not None and row[3] is not None else None
        found[crew_id] = Workload(open_orders=int(row[1]), due_soon=int(row[2]), distance_km=km)
    return found


def _score_zone(candidate: Candidate, crew: Crew, order_zones: list[str]) -> None:
    if not order_zones:
        return
    if crew.zone and crew.zone in order_zones:
        candidate.add(
            "zona",
            POINTS_ZONE,
            f"la OT cae en la zona {crew.zone}, que es la de esta cuadrilla",
        )
    elif crew.zone:
        named = " o ".join(order_zones)
        candidate.add(
            "zona",
            0,
            f"la cuadrilla es de {crew.zone} y la OT cae en {named}",
        )


def _score_distance(candidate: Candidate, load: Workload | None) -> None:
    if load is None or load.distance_km is None:
        candidate.add(
            "cercanía",
            0,
            "no se puede medir: la cuadrilla no tiene trabajo abierto con ubicación desde donde "
            "estimar dónde está",
        )
        return
    km = load.distance_km
    if km >= DISTANCE_CEILING_KM:
        candidate.add(
            "cercanía",
            0,
            f"su trabajo abierto está a {km:.1f} km, más allá de los {DISTANCE_CEILING_KM:.0f} km "
            "desde donde la cercanía deja de contar".replace(".", ",", 1),
        )
        return
    points = round(POINTS_DISTANCE * (1 - km / DISTANCE_CEILING_KM))
    candidate.add(
        "cercanía",
        points,
        f"su trabajo abierto está a {km:.1f} km de esta OT".replace(".", ","),
    )


def _score_load(candidate: Candidate, load: Workload | None) -> None:
    open_orders = load.open_orders if load else 0
    if open_orders == 0:
        candidate.add("carga", POINTS_LOAD, "no tiene OT abiertas")
        return
    if open_orders >= LOAD_CEILING:
        candidate.add(
            "carga",
            0,
            f"ya lleva {open_orders} OT abiertas, {LOAD_CEILING} o más",
        )
        return
    points = round(POINTS_LOAD * (1 - open_orders / LOAD_CEILING))
    candidate.add("carga", points, f"lleva {open_orders} OT abierta(s)")


def _score_sla(candidate: Candidate, load: Workload | None) -> None:
    urgent = load.due_soon if load else 0
    if urgent == 0:
        candidate.add("presión de SLA", POINTS_SLA, "no tiene OT por vencer en las próximas 8 h")
        return
    candidate.add(
        "presión de SLA",
        0,
        f"tiene {urgent} OT por vencer en las próximas 8 h, así que le queda menos margen",
    )


def suggest_crews(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    top: int = TOP_N,
    now: datetime | None = None,
) -> Suggestion:
    """Rank the crews that may take this order, with the reason for every point.

    The ranking is deterministic: two runs over the same data return the same order, because a
    suggestion that reshuffles on refresh is one a planner stops trusting. That holds twice over —
    the crews are read `ORDER BY code` and Python's sort is stable — and the explicit code
    tie-break below is deliberately redundant, so the property survives somebody changing the
    query. A test cannot tell the two mechanisms apart; this comment is the record that the
    redundancy is on purpose.
    """
    moment = now or datetime.now(UTC)
    wanted = required_competencies(order.form_code)
    result = Suggestion(work_order_id=order.id, required_competencies=wanted)

    if load_definitions().get(order.form_code) is None:
        result.caveats.append(
            f"no se pudo leer el formulario {order.form_code}, así que no se comprobó ninguna "
            "competencia: revise la sugerencia antes de asignar"
        )
    if order.location is None:
        result.caveats.append(
            "la OT no tiene ubicación, así que ni la zona ni la cercanía cuentan en el puntaje"
        )

    order_zones = _zones_of(session, unit, order)
    if order.location is not None and not order_zones:
        result.caveats.append(
            "la ubicación de la OT no cae en ninguna zona dibujada, así que la zona no cuenta"
        )
    point = _order_point(session, order)
    loads = _workloads(session, unit, order, now=moment, point=point)

    crews = list(
        session.execute(
            select(Crew)
            .where(Crew.business_unit_id == unit.id, Crew.active.is_(True))
            .order_by(Crew.code)
        ).scalars()
    )
    if not crews:
        result.caveats.append("esta unidad no tiene cuadrillas activas")
        return result

    for crew in crews:
        held = set(crew.competencies or [])
        missing = [item for item in wanted if item not in held]
        if missing:
            # A hard requirement. Never a penalty: proximity must not be able to outvote it.
            result.excluded.append(
                Exclusion(
                    crew.id,
                    crew.code,
                    crew.name,
                    f"no tiene la(s) competencia(s) {', '.join(missing)} que exige "
                    f"{order.form_code}",
                )
            )
            continue
        candidate = Candidate(crew_id=crew.id, code=crew.code, name=crew.name)
        load = loads.get(crew.id)
        _score_zone(candidate, crew, order_zones)
        _score_distance(candidate, load)
        _score_load(candidate, load)
        _score_sla(candidate, load)
        result.candidates.append(candidate)

    result.candidates.sort(key=lambda item: (-item.score, item.code))
    result.candidates = result.candidates[:top]
    if not result.candidates and result.excluded:
        result.caveats.append(
            "ninguna cuadrilla activa tiene las competencias que exige este formulario"
        )
    return result
