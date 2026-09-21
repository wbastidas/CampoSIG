"""Review queue and decisions (M11), and what an approval sets in motion (RF-342).

Approving a work order is the moment field data becomes authoritative: it is what releases
as-built proposals towards the GIS and what closes the loop the whole platform exists to close.
So approval has preconditions, and they are checked here rather than trusted from the UI.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.org.models import BusinessUnit
from app.responses.models import FormResponse, ResponseState
from app.responses.service import compose_for, missing_photos, unconfirmed_ai_values
from app.review.models import Decision, FieldObservation, ReviewDecision
from app.workorders.models import WorkOrder, WorkOrderState
from app.workorders.service import transition


class NotReviewableError(Exception):
    """Raised when a work order is not in a state a supervisor can decide on."""


class ApprovalBlockedError(Exception):
    """Raised when a work order cannot be approved yet, with the reasons."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


def review_queue(
    session: Session,
    unit: BusinessUnit,
    *,
    area: str | None = None,
    crew_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[WorkOrder]:
    """Work orders waiting for a decision (RF-110).

    Paginated on the server: the SRS requires this to stay under two seconds with ten thousand
    work orders, which rules out loading the queue and filtering in the browser.
    """
    statement = (
        select(WorkOrder)
        .where(
            WorkOrder.business_unit_id == unit.id,
            WorkOrder.state.in_([WorkOrderState.SYNCED, WorkOrderState.IN_REVIEW]),
        )
        .order_by(WorkOrder.sla_due_at.nulls_last(), WorkOrder.updated_at)
        .limit(limit)
        .offset(offset)
    )
    if crew_id is not None:
        statement = statement.where(WorkOrder.assigned_crew_id == crew_id)
    if area is not None:
        statement = statement.where(WorkOrder.work_type.startswith(area))
    return list(session.scalars(statement))


def queue_size(session: Session, unit: BusinessUnit) -> int:
    return int(
        session.scalar(
            select(func.count(WorkOrder.id)).where(
                WorkOrder.business_unit_id == unit.id,
                WorkOrder.state.in_([WorkOrderState.SYNCED, WorkOrderState.IN_REVIEW]),
            )
        )
        or 0
    )


def approval_blockers(
    session: Session, unit: BusinessUnit, order: WorkOrder, response: FormResponse | None
) -> list[str]:
    """Why a work order cannot be approved yet.

    Checked on the server because approval is what sends data to the corporate GIS. A UI that
    forgot a check would let incomplete work through, and nobody would notice until an editor
    found a pole with no material recorded.
    """
    reasons: list[str] = []
    if response is None:
        reasons.append("no hay respuesta de formulario para esta OT")
        return reasons

    form = compose_for(session, unit, order)

    problems = missing_photos(form, response)
    reasons.extend(problems)

    # SRS rule 0.5: no AI value is definitive until a human confirmed it. Approving over
    # unconfirmed proposals would quietly make the model the author of the record.
    unconfirmed = unconfirmed_ai_values(session, response)
    if unconfirmed:
        fields = ", ".join(sorted(entry.field_key for entry in unconfirmed))
        reasons.append(f"hay valores propuestos por IA sin confirmar: {fields}")

    if response.state == ResponseState.DRAFT:
        reasons.append("la respuesta sigue en borrador; el técnico no la ha cerrado")

    return reasons


def decide(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    decision: str,
    reviewer_sub: str,
    note: str | None = None,
    observations: list[dict[str, Any]] | None = None,
    blind_sample: bool | None = None,
) -> ReviewDecision:
    """Record a supervisor's decision and move the work order (RF-112).

    :raises NotReviewableError: if the work order is not awaiting a decision.
    :raises ApprovalBlockedError: on approval, when preconditions are unmet.
    """
    if order.state not in (WorkOrderState.SYNCED, WorkOrderState.IN_REVIEW):
        raise NotReviewableError(f"una OT en estado '{order.state}' no está esperando revisión")

    response = session.scalars(
        select(FormResponse)
        .options(selectinload(FormResponse.provenance), selectinload(FormResponse.evidence))
        .where(FormResponse.work_order_id == order.id)
    ).first()

    if decision == Decision.APPROVED:
        blockers = approval_blockers(session, unit, order, response)
        if blockers:
            raise ApprovalBlockedError(blockers)

    if order.state == WorkOrderState.SYNCED:
        transition(session, order, WorkOrderState.IN_REVIEW)

    row = ReviewDecision(
        business_unit_id=unit.id,
        work_order_id=order.id,
        response_id=response.id if response else None,
        decision=decision,
        reviewer_sub=reviewer_sub,
        note=note,
        blind_sample=blind_sample,
    )
    session.add(row)
    session.flush()

    for observation in observations or []:
        session.add(
            FieldObservation(
                decision_id=row.id,
                field_key=observation["field_key"],
                message=observation["message"],
                suggested_value=observation.get("suggested_value"),
            )
        )

    if decision == Decision.APPROVED:
        transition(session, order, WorkOrderState.APPROVED)
        if response is not None:
            response.state = ResponseState.APPROVED
    elif decision == Decision.RETURNED:
        transition(
            session,
            order,
            WorkOrderState.RETURNED,
            reason=note or "devuelta con observaciones",
        )
        if response is not None:
            # Editable again: the technician has to act on the observations.
            response.state = ResponseState.RETURNED
    elif decision == Decision.CANCELLED:
        transition(session, order, WorkOrderState.CANCELLED, reason=note or "anulada en revisión")

    session.flush()
    return row


def observations_for(session: Session, order: WorkOrder) -> list[FieldObservation]:
    """Observations from the most recent decision, for the device to show by field."""
    latest = session.scalars(
        select(ReviewDecision)
        .options(selectinload(ReviewDecision.observations))
        .where(ReviewDecision.work_order_id == order.id)
        .order_by(ReviewDecision.decided_at.desc())
    ).first()
    return list(latest.observations) if latest else []


def decision_history(session: Session, order: WorkOrder) -> list[ReviewDecision]:
    """Every decision made on a work order, oldest first (M16)."""
    return list(
        session.scalars(
            select(ReviewDecision)
            .options(selectinload(ReviewDecision.observations))
            .where(ReviewDecision.work_order_id == order.id)
            .order_by(ReviewDecision.decided_at)
        )
    )
