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

from app.audit import service as audit
from app.audit.models import EventKind
from app.integrations.callcentre_adapter import enqueue_claim_closure
from app.integrations.workorder_adapter import enqueue_result_push, enqueue_status_push
from app.org.models import BusinessUnit
from app.regulatory import rules as compliance
from app.regulatory.facts import facts_from
from app.responses.models import FormResponse, ResponseState
from app.responses.service import compose_for, missing_photos, unconfirmed_ai_values
from app.review import blind
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

    # Regulatory breaches, evaluated deterministically against the limit in force (ADR-007).
    # Only a confirmed high-severity breach against a *verified* limit blocks: a parameter
    # nobody loaded is the office's omission, and blocking the crew's approval over it would
    # put the cost on the wrong person. The rest travel as findings for the supervisor.
    for finding in compliance_findings(session, order, response):
        if finding.blocking:
            citation = (
                f" ({finding.norm_ref}{f', {finding.article_ref}' if finding.article_ref else ''})"
            )
            reasons.append(f"incumplimiento normativo: {finding.message}{citation}")

    return reasons


def compliance_findings(
    session: Session, order: WorkOrder, response: FormResponse | None
) -> list[compliance.Finding]:
    """What the deterministic rules say about this capture (ADR-007, RF-350, RF-351).

    Derived rather than stored, and that is deliberate: the facts live in the response and the
    limit lives in `regulatory_parameter` with its period of force, so re-running this on an
    order approved in March reproduces March's verdict exactly. A snapshot would be a second
    copy of the truth, free to drift from the rule that produced it.
    """
    if response is None:
        return []
    return compliance.evaluate(session, facts_from(order, response.answers))


def decide(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    decision: str,
    reviewer_sub: str,
    note: str | None = None,
    observations: list[dict[str, Any]] | None = None,
    agent_risk: str | None = None,
) -> ReviewDecision:
    """Record a supervisor's decision and move the work order (RF-112).

    :param agent_risk: the risk the pre-review assigned, when there is a report. Used to close a
        blind draw (RF-111a); passed in rather than read here because `app.prereview` reads this
        module and the import would close a cycle.
    :raises NotReviewableError: if the work order is not awaiting a decision.
    :raises ApprovalBlockedError: on approval, when preconditions are unmet.

    Whether this decision was a blind one is **not** a parameter: it is read from the draw. A
    caller-supplied flag would let the thing being measured fill in its own scorecard (RF-111a).
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

    # The draw decides, and it is read before the reveal closes it: after `blind.reveal` there is
    # nothing pending to find, and this decision would look like an ordinary one.
    was_blind = blind.pending_for(session, order.id) is not None

    row = ReviewDecision(
        business_unit_id=unit.id,
        work_order_id=order.id,
        response_id=response.id if response else None,
        decision=decision,
        reviewer_sub=reviewer_sub,
        note=note,
        blind_sample=was_blind or None,
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
        # The outbound events are written here, in the approval's own transaction (RF-120,
        # RF-124). That ordering is the point: a crew fixes the lamp, a supervisor approves,
        # and the customer's claim stays open — that is what happens when telling the other
        # system is a side effect nobody guaranteed. Delivery happens later and may fail,
        # retry, or wait for a person; it cannot be lost.
        enqueue_status_push(session, unit, order, state=WorkOrderState.APPROVED.value)
        enqueue_result_push(
            session,
            unit,
            order,
            summary=(response.answers or {}).get("summary") if response else None,
            evidence_keys=[item.storage_key for item in response.evidence] if response else [],
        )
        enqueue_claim_closure(session, unit, order)
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

    # The agreement is written in the decision's own transaction (RF-111a): a pair with one half
    # missing is a row that would quietly bias the kappa.
    blind.reveal(session, order.id, decision=decision, risk=agent_risk)

    # The trail records the decision itself, beside the transition the decision caused. Both,
    # because they answer different questions: the transition says the order moved, the decision
    # says who signed for it and what they saw when they signed (RF-160, RF-161).
    audit.record(
        session,
        unit.id,
        kind=EventKind.DECIDED,
        subject_type="orden_trabajo",
        subject_id=str(order.id),
        work_order_id=order.id,
        asset_code=order.asset_code,
        actor=reviewer_sub,
        payload={
            "decision": decision,
            "response_id": str(response.id) if response else None,
            "observations": len(observations or []),
            # Whether the decision was taken without seeing the agent's report (RF-111a). It is part
            # of the decision's context and an auditor reading the trail should see it.
            "blind_sample": bool(was_blind),
            "state": order.state,
        },
        reason=note,
    )

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
