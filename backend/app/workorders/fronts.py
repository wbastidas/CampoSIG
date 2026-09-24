"""Work with several fronts: parent orders and their children (RF-015).

«OT multi-actividad y OT hijas (p. ej., una obra con múltiples frentes)», and the acceptance is one
sentence: «una OT padre muestra el avance agregado de sus hijas». Everything here exists to make
that aggregate honest.

**The parent is a container, not a second place to do the work.** The fronts are where crews are
assigned and captures happen; a parent that could also be assigned would make «¿está hecho?» a
question with two answers. So attaching a front refuses a parent already out with a crew, and the
parent's own progress is nothing but the sum of its fronts.

**A parent cannot close while a front is open.** Without that rule the aggregate lies at exactly the
moment somebody relies on it — the day the work is reported as finished.

**Depth is one.** A front cannot itself have fronts. «Una obra con múltiples frentes» is a tree of
depth one; grandchildren would make «el avance» a question about which level you meant, and would
open the door to a cycle that nobody notices until a query hangs.

**Progress is a fraction with its denominator**, like every other rate in this platform. «6 de 11
frentes cerrados» says what «55 %» does not, which is how much is left and of what.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.models import EventKind
from app.audit.service import record
from app.org.models import BusinessUnit
from app.workorders.models import WorkOrder, WorkOrderState

#: States in which a front still owes work. A front in review is not finished either: the office is
#: still deciding, and a parent closed over it would be closed over work that may come back.
OPEN_FRONT_STATES = tuple(
    state
    for state in WorkOrderState
    if state not in (WorkOrderState.CLOSED, WorkOrderState.CANCELLED)
)

#: States in which a parent may still take on fronts. Once the work is out with a crew or being
#: reviewed, adding a front silently changes what «hecho» meant when somebody looked at it.
ATTACHABLE_PARENT_STATES = (WorkOrderState.DRAFT, WorkOrderState.PLANNED)


class FrontError(Exception):
    pass


@dataclass
class Progress:
    """How a parent's work is going, counted over its fronts."""

    total: int = 0
    closed: int = 0
    cancelled: int = 0
    in_field: int = 0
    in_review: int = 0
    pending: int = 0
    #: The fronts that are still owed, worst first, for the screen.
    open_codes: list[str] = field(default_factory=list)

    @property
    def done(self) -> int:
        """Fronts that will not come back: closed, plus the ones somebody cancelled.

        Cancelled counts as settled and **not** as achieved, which is why it is also reported on its
        own: a work whose four fronts were all cancelled is finished and nothing was built, and a
        single «4 de 4» would say the opposite.
        """
        return self.closed + self.cancelled

    @property
    def is_complete(self) -> bool:
        return self.total > 0 and self.done == self.total

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "closed": self.closed,
            "cancelled": self.cancelled,
            "in_field": self.in_field,
            "in_review": self.in_review,
            "pending": self.pending,
            "done": self.done,
            "is_complete": self.is_complete,
            "open_codes": self.open_codes,
            # The sentence the screen shows. Written here so the web and the acta cannot phrase the
            # same fraction differently — and never a bare percentage.
            "summary": self.summary(),
        }

    def summary(self) -> str:
        if self.total == 0:
            return "sin frentes"
        parts = [f"{self.done} de {self.total} frentes resueltos"]
        if self.cancelled:
            parts.append(f"{self.cancelled} anulado(s)")
        if self.in_field:
            parts.append(f"{self.in_field} en campo")
        if self.in_review:
            parts.append(f"{self.in_review} en revisión")
        return "; ".join(parts)


def attach(
    session: Session,
    unit: BusinessUnit,
    parent: WorkOrder,
    child: WorkOrder,
    *,
    actor: str,
) -> WorkOrder:
    """Make `child` a front of `parent` (RF-015).

    :raises FrontError: when the link would make the aggregate meaningless — a different business
        unit, a second level, a cycle, or a parent whose work is already under way.
    """
    if parent.id == child.id:
        raise FrontError("una OT no puede ser frente de sí misma")
    if parent.business_unit_id != unit.id or child.business_unit_id != unit.id:
        # ADR-009. A front in another unit would put one unit's crews inside another's work, and
        # the parent's progress would count work its planner cannot even see.
        raise FrontError("el padre y el frente tienen que ser de la misma unidad de negocio")
    if parent.parent_id is not None:
        raise FrontError(
            "esa OT ya es un frente de otra: las obras tienen un nivel, no un árbol. "
            "Cuelgue el frente de la OT padre"
        )
    if child.parent_id is not None and child.parent_id != parent.id:
        raise FrontError("el frente ya pertenece a otra obra; sepárelo primero")
    if children_of(session, child):
        raise FrontError("esa OT ya tiene frentes propios: no puede ser a la vez padre y frente")
    if parent.state not in ATTACHABLE_PARENT_STATES:
        raise FrontError(
            f"la obra está «{parent.state}» y ya no admite frentes nuevos: añadir uno cambiaría "
            "en silencio lo que significaba «hecho» para quien ya la miró"
        )

    child.parent_id = parent.id
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.FIELD_CHANGED,
        subject_type="orden_trabajo",
        subject_id=str(child.id),
        work_order_id=child.id,
        asset_code=child.asset_code,
        actor=actor,
        payload={
            "field": "parent_id",
            "to": str(parent.id),
            "parent_code": parent.code,
        },
    )
    return child


def detach(session: Session, unit: BusinessUnit, child: WorkOrder, *, actor: str) -> WorkOrder:
    """Separate a front from its work, leaving it an ordinary order."""
    if child.parent_id is None:
        raise FrontError("esa OT no es frente de ninguna obra")
    previous = child.parent_id
    child.parent_id = None
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.FIELD_CHANGED,
        subject_type="orden_trabajo",
        subject_id=str(child.id),
        work_order_id=child.id,
        asset_code=child.asset_code,
        actor=actor,
        payload={"field": "parent_id", "from": str(previous), "to": None},
    )
    return child


def children_of(session: Session, parent: WorkOrder) -> list[WorkOrder]:
    """This work's fronts, in a stable order so two readings agree.

    By code first, which is what a planner reads and refers to on the phone. **Not** by
    `created_at`: PostgreSQL's `now()` is the transaction clock, so fronts created in one
    transaction share it to the microsecond and the tiebreak would be a random UUID — a list that
    shuffles between two readings of the same work. That is the fourth time this platform has met
    that trap (the revision log, the published form, the catalogue entry), and the first time it was
    caught by a test asserting an order rather than by a number coming out wrong.

    The order a front was *attached* in is not recorded at all, which is why it is not the order
    used: inventing it from `created_at` would be inventing it from the wrong column.
    """
    return list(
        session.execute(
            select(WorkOrder)
            .where(WorkOrder.parent_id == parent.id)
            .order_by(WorkOrder.code.nulls_last(), WorkOrder.created_at, WorkOrder.id)
        ).scalars()
    )


def progress_of(session: Session, parent: WorkOrder) -> Progress:
    """The aggregate the acceptance criterion asks for: what the fronts add up to."""
    progress = Progress()
    for child in children_of(session, parent):
        progress.total += 1
        if child.state == WorkOrderState.CLOSED:
            progress.closed += 1
        elif child.state == WorkOrderState.CANCELLED:
            progress.cancelled += 1
        elif child.state in (
            WorkOrderState.SYNCED,
            WorkOrderState.IN_REVIEW,
            WorkOrderState.APPROVED,
            WorkOrderState.RETURNED,
        ):
            progress.in_review += 1
        elif child.state in (
            WorkOrderState.DOWNLOADED,
            WorkOrderState.EN_ROUTE,
            WorkOrderState.ON_SITE,
            WorkOrderState.IN_EXECUTION,
            WorkOrderState.SUSPENDED,
            WorkOrderState.CLOSED_FIELD,
        ):
            progress.in_field += 1
        else:
            progress.pending += 1
        if child.state in OPEN_FRONT_STATES and child.code:
            progress.open_codes.append(child.code)
    return progress


def open_fronts(session: Session, parent: WorkOrder) -> list[WorkOrder]:
    return [child for child in children_of(session, parent) if child.state in OPEN_FRONT_STATES]


def blocking_fronts(session: Session, order: WorkOrder, target: str) -> list[str]:
    """Front codes that stop this order reaching `target`, or an empty list.

    A parent closes when its fronts are settled, and not before: an aggregate that could say «hecho»
    over an open front would lie on the one day somebody relies on it, which is the day the work is
    reported finished.

    Cancelling a parent is refused the same way rather than cascading. A cascade would cancel work a
    crew may already be doing, from a screen where nobody is looking at those fronts.
    """
    if target not in (WorkOrderState.CLOSED, WorkOrderState.CANCELLED):
        return []
    return [child.code or str(child.id) for child in open_fronts(session, order)]


def parents_with_fronts(session: Session, unit: BusinessUnit) -> list[tuple[WorkOrder, Progress]]:
    """Every work that has fronts in this unit, with its aggregate."""
    parent_ids = set(
        session.execute(
            select(WorkOrder.parent_id).where(
                WorkOrder.business_unit_id == unit.id, WorkOrder.parent_id.is_not(None)
            )
        )
        .scalars()
        .all()
    )
    if not parent_ids:
        return []
    parents = list(
        session.execute(
            select(WorkOrder)
            .where(WorkOrder.id.in_(parent_ids))
            .order_by(WorkOrder.code.nulls_last(), WorkOrder.created_at, WorkOrder.id)
        ).scalars()
    )
    return [(parent, progress_of(session, parent)) for parent in parents]


def front_counts(session: Session, unit: BusinessUnit) -> dict[uuid.UUID, int]:
    """How many fronts each work has, in one query, for a list screen."""
    rows = session.execute(
        select(WorkOrder.parent_id, func.count())
        .where(WorkOrder.business_unit_id == unit.id, WorkOrder.parent_id.is_not(None))
        .group_by(WorkOrder.parent_id)
    ).all()
    return {parent_id: int(total) for parent_id, total in rows if parent_id is not None}
