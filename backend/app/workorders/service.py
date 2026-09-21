"""Work order lifecycle, assignment and graphical selection (M02, M03; RF-310..RF-324).

Two properties every function here protects:

* **Nothing crosses business units.** Every query takes a unit and filters by it (ADR-009).
* **Reassignment never destroys captured work.** A technician working offline can have a
  work order taken from them; what they already captured must survive that (RF-322).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from geoalchemy2.functions import ST_MakeEnvelope, ST_Within
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import Case

from app.forms.catalog import get_definition
from app.org.models import BusinessUnit
from app.workorders.models import (
    STORAGE_SRID,
    Crew,
    DeviceCustody,
    Priority,
    WorkOrder,
    WorkOrderSource,
    WorkOrderState,
)

#: Allowed state transitions (SRS 3.3). Anything absent here is refused, so an invalid
#: sequence fails at the boundary rather than leaving an order in a state nothing handles.
TRANSITIONS: dict[str, set[str]] = {
    WorkOrderState.DRAFT: {WorkOrderState.PLANNED, WorkOrderState.CANCELLED},
    WorkOrderState.PLANNED: {WorkOrderState.ASSIGNED, WorkOrderState.CANCELLED},
    WorkOrderState.ASSIGNED: {
        WorkOrderState.DOWNLOADED,
        WorkOrderState.PLANNED,
        WorkOrderState.CANCELLED,
    },
    WorkOrderState.DOWNLOADED: {WorkOrderState.EN_ROUTE, WorkOrderState.ASSIGNED},
    WorkOrderState.EN_ROUTE: {WorkOrderState.ON_SITE, WorkOrderState.SUSPENDED},
    WorkOrderState.ON_SITE: {WorkOrderState.IN_EXECUTION, WorkOrderState.SUSPENDED},
    WorkOrderState.IN_EXECUTION: {WorkOrderState.SUSPENDED, WorkOrderState.CLOSED_FIELD},
    WorkOrderState.SUSPENDED: {WorkOrderState.IN_EXECUTION, WorkOrderState.CANCELLED},
    WorkOrderState.CLOSED_FIELD: {WorkOrderState.SYNCED},
    WorkOrderState.SYNCED: {WorkOrderState.IN_REVIEW},
    WorkOrderState.IN_REVIEW: {
        WorkOrderState.APPROVED,
        WorkOrderState.RETURNED,
        WorkOrderState.CANCELLED,
    },
    WorkOrderState.RETURNED: {WorkOrderState.IN_EXECUTION},
    WorkOrderState.APPROVED: {WorkOrderState.CLOSED},
    WorkOrderState.CLOSED: set(),
    WorkOrderState.CANCELLED: set(),
}

#: Transitions that cannot happen without a stated reason (SRS 3.3).
REASON_REQUIRED = {WorkOrderState.SUSPENDED, WorkOrderState.RETURNED, WorkOrderState.CANCELLED}

#: Sort weight per priority. Needed because ordering by the stored string is alphabetical
#: ('alta' < 'baja' < 'critica' < 'media'), which would put low priority above critical on
#: the planner's board — exactly backwards.
#:
#: Keys are the plain string values, not the enum members: StrEnum members subclass str, but
#: SQLAlchemy infers NULL as their type and then cannot render them, which fails at compile
#: time. Verified by compiling the query against the PostgreSQL dialect.
_PRIORITY_RANK: dict[str, int] = {
    Priority.CRITICAL.value: 0,
    Priority.HIGH.value: 1,
    Priority.MEDIUM.value: 2,
    Priority.LOW.value: 3,
}


def _priority_order() -> Case[int]:
    """SQL ordering expression that sorts critical first."""
    return case(_PRIORITY_RANK, value=WorkOrder.priority, else_=99)


class InvalidTransitionError(Exception):
    """Raised when a state change is not allowed from the current state."""


class ReasonRequiredError(Exception):
    """Raised when a transition that demands a reason is attempted without one."""


class ConcurrentEditError(Exception):
    """Raised when a planner's change is based on a stale version (RF-311)."""


class NotAssignableError(Exception):
    """Raised when a work order cannot be assigned in its current state."""


class CrossUnitError(Exception):
    """Raised when an operation would move work between business units."""


# --- creation ---------------------------------------------------------------------
def create_work_order(
    session: Session,
    unit: BusinessUnit,
    *,
    work_type: str,
    form_code: str,
    priority: str = Priority.MEDIUM,
    source: str = WorkOrderSource.MANUAL,
    external_ref: str | None = None,
    description: str | None = None,
    asset_type_key: str | None = None,
    asset_code: str | None = None,
    longitude: float | None = None,
    latitude: float | None = None,
    feeder_code: str | None = None,
    zone: str | None = None,
    planner_id: str | None = None,
) -> WorkOrder:
    """Create a work order for one business unit.

    The form code is validated against the catalogue here, because a work order pointing at
    a form that does not exist would only fail later, on a phone, in the field.
    """
    get_definition(form_code)  # raises CatalogError if unknown

    order = WorkOrder(
        business_unit_id=unit.id,
        work_type=work_type,
        form_code=form_code,
        priority=priority,
        source=source,
        external_ref=external_ref,
        description=description,
        asset_type_key=asset_type_key,
        asset_code=asset_code,
        feeder_code=feeder_code,
        zone=zone,
        planner_id=planner_id,
        state=WorkOrderState.PLANNED if planner_id else WorkOrderState.DRAFT,
    )
    if longitude is not None and latitude is not None:
        order.location = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), STORAGE_SRID)
    session.add(order)
    session.flush()
    return order


def import_external(
    session: Session, unit: BusinessUnit, *, external_ref: str, **kwargs: Any
) -> tuple[WorkOrder, bool]:
    """Import from the corporate system, idempotently (RF-011, RF-120 satellite mode).

    :returns: (order, created). Re-importing the same reference returns the existing order
        rather than a duplicate, because the external system owns the number and may resend.
    """
    existing = session.scalars(
        select(WorkOrder).where(
            WorkOrder.business_unit_id == unit.id, WorkOrder.external_ref == external_ref
        )
    ).first()
    if existing is not None:
        return existing, False
    kwargs.setdefault("source", WorkOrderSource.EXTERNAL_SYSTEM)
    created = create_work_order(session, unit, external_ref=external_ref, **kwargs)
    return created, True


# --- state ------------------------------------------------------------------------
def transition(
    session: Session,
    order: WorkOrder,
    target: str,
    *,
    reason: str | None = None,
    actor: str | None = None,
) -> WorkOrder:
    """Move a work order to a new state, validating the transition (SRS 3.3)."""
    allowed = TRANSITIONS.get(order.state, set())
    if target not in allowed:
        readable = ", ".join(sorted(allowed)) or "ninguno"
        raise InvalidTransitionError(
            f"no se puede pasar de '{order.state}' a '{target}'; permitidos: {readable}"
        )
    if target in REASON_REQUIRED and not reason:
        raise ReasonRequiredError(f"el paso a '{target}' exige un motivo")

    order.state = target
    order.version += 1
    session.flush()
    return order


# --- assignment -------------------------------------------------------------------
def assign(
    session: Session,
    order: WorkOrder,
    *,
    crew: Crew | None = None,
    user_sub: str | None = None,
    device_id: str | None = None,
    expected_version: int | None = None,
    reason: str | None = None,
    granted_by: str | None = None,
) -> WorkOrder:
    """Assign or reassign a work order (RF-320, RF-321, RF-324).

    Reassignment closes the current custody row and opens a new one, so the chain survives.
    If the previous holder had unsynced captured data, that is recorded on the closed row:
    the platform must not free the order until what they captured has arrived (RF-322).

    :param expected_version: the version the planner was looking at. When given and stale,
        the change is refused so two planners never silently overwrite each other (RF-311).
    :raises CrossUnitError: if the crew belongs to a different business unit.
    """
    if expected_version is not None and order.version != expected_version:
        raise ConcurrentEditError(
            f"la OT cambió mientras la editaba (versión {order.version}, usted vio "
            f"{expected_version}); recargue antes de reasignar"
        )
    if not order.is_assignable:
        raise NotAssignableError(
            f"una OT en estado '{order.state}' no se puede asignar; "
            f"asignables: {WorkOrderState.PLANNED}, {WorkOrderState.ASSIGNED}"
        )
    if crew is not None and crew.business_unit_id != order.business_unit_id:
        raise CrossUnitError("no se puede asignar una OT a una cuadrilla de otra unidad de negocio")

    now = datetime.now(UTC)
    previous = current_custody(session, order)
    if previous is not None:
        previous.until = now
        if reason:
            previous.reason = reason

    order.assigned_crew_id = crew.id if crew else None
    order.assigned_user_sub = user_sub
    order.state = WorkOrderState.ASSIGNED
    order.version += 1

    # Pin the form version at assignment time: the order executes with the version current
    # now, not whatever is current when it closes (SRS 4.1.6).
    if order.form_version is None:
        order.form_version = get_definition(order.form_code).version

    session.add(
        DeviceCustody(
            work_order_id=order.id,
            device_id=device_id,
            user_sub=user_sub,
            crew_id=crew.id if crew else None,
            since=now,
            reason=reason,
            granted_by=granted_by,
        )
    )
    session.flush()
    return order


def current_custody(session: Session, order: WorkOrder) -> DeviceCustody | None:
    """The open custody row, if any."""
    return session.scalars(
        select(DeviceCustody).where(
            DeviceCustody.work_order_id == order.id, DeviceCustody.until.is_(None)
        )
    ).first()


def mark_pending_handover(
    session: Session, order: WorkOrder, *, device_id: str
) -> DeviceCustody | None:
    """Record that a device still holds unsynced data for this order (RF-322).

    Called when a reassignment reaches a device that captured work offline. The order is not
    freed until that data arrives, which is the difference between a reassignment and losing
    a technician's afternoon.
    """
    rows = session.scalars(
        select(DeviceCustody)
        .where(DeviceCustody.work_order_id == order.id, DeviceCustody.device_id == device_id)
        .order_by(DeviceCustody.since.desc())
    ).all()
    if not rows:
        return None
    rows[0].had_unsynced_data = True
    session.flush()
    return rows[0]


def custody_history(session: Session, order: WorkOrder) -> list[DeviceCustody]:
    """Full chain of custody, oldest first (RF-324)."""
    return list(
        session.scalars(
            select(DeviceCustody)
            .where(DeviceCustody.work_order_id == order.id)
            .order_by(DeviceCustody.since)
        )
    )


# --- graphical selection ----------------------------------------------------------
def in_bounding_box(
    session: Session,
    unit: BusinessUnit,
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    states: list[str] | None = None,
    unassigned_only: bool = False,
    limit: int = 1000,
) -> list[WorkOrder]:
    """Work orders inside a map viewport — the planner's map query (RF-310, RF-313).

    Coordinates are WGS84 degrees, matching what MapLibre sends. The result is capped:
    a planner zoomed out to the whole country must not pull every order ever created.
    """
    envelope = ST_MakeEnvelope(west, south, east, north, STORAGE_SRID)
    statement = (
        select(WorkOrder)
        .where(
            WorkOrder.business_unit_id == unit.id,
            WorkOrder.location.is_not(None),
            ST_Within(WorkOrder.location, envelope),
        )
        .order_by(_priority_order(), WorkOrder.sla_due_at.nulls_last())
        .limit(limit)
    )
    if states:
        statement = statement.where(WorkOrder.state.in_(states))
    if unassigned_only:
        statement = statement.where(WorkOrder.assigned_crew_id.is_(None))
    return list(session.scalars(statement))


def assignable_in_box(
    session: Session, unit: BusinessUnit, *, west: float, south: float, east: float, north: float
) -> list[WorkOrder]:
    """What the planner may lasso and assign in one gesture."""
    return in_bounding_box(
        session,
        unit,
        west=west,
        south=south,
        east=east,
        north=north,
        states=[WorkOrderState.PLANNED, WorkOrderState.ASSIGNED],
    )


def assign_many(
    session: Session,
    unit: BusinessUnit,
    order_ids: list[uuid.UUID],
    *,
    crew: Crew,
    reason: str | None = None,
    granted_by: str | None = None,
) -> tuple[list[WorkOrder], list[tuple[uuid.UUID, str]]]:
    """Assign a lasso selection to one crew.

    Partial success by design: one order in a state that cannot be assigned must not lose
    the planner the other nineteen. Failures come back with their reason so the map can
    show exactly which pins were refused and why.

    :returns: (assigned, failures) where each failure is (order_id, message).
    """
    if crew.business_unit_id != unit.id:
        raise CrossUnitError("la cuadrilla no pertenece a esta unidad de negocio")

    orders = session.scalars(
        select(WorkOrder).where(WorkOrder.business_unit_id == unit.id, WorkOrder.id.in_(order_ids))
    ).all()
    found = {order.id for order in orders}

    assigned: list[WorkOrder] = []
    failures: list[tuple[uuid.UUID, str]] = [
        (missing, "no existe en esta unidad de negocio")
        for missing in order_ids
        if missing not in found
    ]
    for order in orders:
        try:
            assign(session, order, crew=crew, reason=reason, granted_by=granted_by)
            assigned.append(order)
        except (NotAssignableError, CrossUnitError) as exc:
            failures.append((order.id, str(exc)))
    return assigned, failures


def crew_workload(session: Session, unit: BusinessUnit) -> list[dict[str, Any]]:
    """Open work per crew — the shared board several planners work against (RF-313)."""
    open_states = [
        WorkOrderState.ASSIGNED,
        WorkOrderState.DOWNLOADED,
        WorkOrderState.EN_ROUTE,
        WorkOrderState.ON_SITE,
        WorkOrderState.IN_EXECUTION,
        WorkOrderState.SUSPENDED,
    ]
    rows = session.execute(
        select(Crew.id, Crew.code, Crew.name, func.count(WorkOrder.id))
        .outerjoin(
            WorkOrder,
            (WorkOrder.assigned_crew_id == Crew.id) & WorkOrder.state.in_(open_states),
        )
        .where(Crew.business_unit_id == unit.id, Crew.active.is_(True))
        .group_by(Crew.id, Crew.code, Crew.name)
        .order_by(Crew.code)
    ).all()
    return [
        {"crew_id": row[0], "code": row[1], "name": row[2], "open_work_orders": row[3]}
        for row in rows
    ]
