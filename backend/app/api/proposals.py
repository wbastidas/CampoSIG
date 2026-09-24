"""The proposal tray (RF-013, RF-114).

«La propuesta aparece en la bandeja del supervisor; al aprobarla pasa a Planificada; al rechazarla
guarda el motivo.» So the tray is the supervisor's, the three actions are POSTs that each take a
person from a token, and generation is a separate endpoint an administrator or a scheduled worker
calls — never a side effect of reading the tray.

Every proposal carries the arithmetic of Annex C and what the computation could not know. That is
not decoration: a priority presented as a computation when half its inputs were defaults is how a
supervisor learns to ignore the whole tray.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.proposals import service as proposals
from app.proposals.models import ProposalState, WorkOrderProposal
from app.workorders.models import Priority, WorkOrder

router = APIRouter(
    prefix="/api/v1/proposals", tags=["proposals"], dependencies=[Depends(unit_scope)]
)

SessionDep = Annotated[Session, Depends(get_session)]

#: Who decides. The supervisor, as RF-013 says, and the planner because the tray feeds their board.
DECIDERS = (Role.SUPERVISOR, Role.PLANNER)

#: Who may run a generation pass by hand. Not the supervisor: raising proposals is not a decision,
#: and a button that filled somebody's own tray would be an odd thing to put in front of them.
GENERATORS = (Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN, Role.PLANNER)

#: How far back a generation pass looks when nobody says. Thirty days, the same window the
#: maintenance board defaults to, so the two screens talk about the same findings.
DEFAULT_WINDOW = timedelta(days=30)


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _proposal(session: Session, unit: BusinessUnit, proposal_id: uuid.UUID) -> WorkOrderProposal:
    row = session.get(WorkOrderProposal, proposal_id)
    if row is None or row.business_unit_id != unit.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "la propuesta no existe en esta unidad de negocio"
        )
    return row


def _as_dict(row: WorkOrderProposal) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "state": row.state,
        "origin": row.origin,
        "asset_code": row.asset_code,
        "asset_type_key": row.asset_type_key,
        "feeder_code": row.feeder_code,
        "zone": row.zone,
        "defect_code": row.defect_code,
        "work_type": row.work_type,
        "form_code": row.form_code,
        "priority": row.priority,
        "criticality": row.criticality,
        "suggested_deadline_hours": row.suggested_deadline_hours,
        "justification": row.justification,
        "findings": row.findings,
        "source_work_order_id": (
            str(row.source_work_order_id) if row.source_work_order_id else None
        ),
        "work_order_id": str(row.work_order_id) if row.work_order_id else None,
        "merged_into_id": str(row.merged_into_id) if row.merged_into_id else None,
        "reject_reason_code": row.reject_reason_code,
        "reject_note": row.reject_note,
        "decided_by": row.decided_by,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        # Rule 8: an AI value travels with its origin, model version and confidence.
        "model_name": row.model_name,
        "model_version": row.model_version,
        "confidence": row.confidence,
    }


class GenerateIn(BaseModel):
    since: datetime | None = None
    until: datetime | None = None
    #: False proposes from every finding, not only the ones a crew flagged. What a supervisor
    #: reviewing a backlog wants; the default is the crew's flag, which is the cheapest reliable
    #: signal there is.
    only_wanted: bool = True


class ApproveIn(BaseModel):
    """The supervisor's own call on the priority, and why.

    No `decided_by`: the decider is whoever the token says they are. A decision whose author the
    caller could type is a decision nobody signed.
    """

    priority: Priority | None = None
    note: str | None = Field(default=None, max_length=2000)


class MergeIn(BaseModel):
    work_order_id: uuid.UUID
    note: str | None = Field(default=None, max_length=2000)


class RejectIn(BaseModel):
    """The catalogued reason, and free text for the human reader.

    The code is the training label (RF-114); the note never is — free text cannot be one.
    """

    reason_code: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=2000)


@router.get("/units/{unit_code}", summary="La bandeja de OT propuestas (RF-114)")
def tray(
    unit_code: str,
    session: SessionDep,
    state: Annotated[str, Query()] = ProposalState.OPEN.value,
    _: Annotated[Any, Depends(require_roles(*DECIDERS, *GENERATORS))] = None,
) -> dict[str, Any]:
    """Worst first, then oldest first: a P1 under twenty P4s is the failure this order prevents."""
    unit = _unit(session, unit_code)
    rows = proposals.tray(session, unit, state=state)
    return {
        "state": state,
        "counts": proposals.counts(session, unit),
        "reject_reasons": [
            {
                "code": entry.code,
                "label": entry.label,
                "signal": entry.attributes.get("signal"),
            }
            for entry in proposals.reject_reasons(session)
        ],
        "proposals": [_as_dict(row) for row in rows],
    }


@router.get(
    "/units/{unit_code}/training-signals",
    summary="Los rechazos agrupados por la señal que llevan (RF-114)",
)
def training_signals(
    unit_code: str,
    session: SessionDep,
    _: Annotated[Any, Depends(require_roles(*DECIDERS, Role.ML_ANALYST))] = None,
) -> dict[str, int]:
    """«No es un defecto» y «ya está resuelto» son ambos un rechazo para la bandeja y cosas
    opuestas para un conjunto de entrenamiento."""
    unit = _unit(session, unit_code)
    return proposals.training_signals(session, unit)


@router.post(
    "/units/{unit_code}/generate",
    dependencies=[Depends(require_roles(*GENERATORS))],
    summary="Levantar propuestas desde los hallazgos de un periodo (RF-013)",
)
def generate(
    unit_code: str,
    payload: GenerateIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*GENERATORS))] = None,
) -> dict[str, Any]:
    """What it refused to do comes back too: an asset with open work, a duplicate, a finding with no
    asset. A pass that silently dropped them would look like one that missed them."""
    unit = _unit(session, unit_code)
    until = payload.until or datetime.now(UTC)
    since = payload.since or (until - DEFAULT_WINDOW)
    if since > until:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "el inicio del periodo es posterior al fin"
        )
    report = proposals.generate_from_findings(
        session,
        unit,
        since=since,
        until=until,
        only_wanted=payload.only_wanted,
        actor=principal.subject,
    )
    session.commit()
    return {"since": since.isoformat(), "until": until.isoformat(), **report.as_dict()}


@router.post(
    "/units/{unit_code}/{proposal_id}/approve",
    summary="Aprobar: la propuesta pasa a una OT planificada (RF-013)",
)
def approve(
    unit_code: str,
    proposal_id: uuid.UUID,
    payload: ApproveIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*DECIDERS))] = None,
) -> dict[str, Any]:
    """The only path from a proposal to a work order, and it needs a person (RF-013)."""
    unit = _unit(session, unit_code)
    row = _proposal(session, unit, proposal_id)
    try:
        order = proposals.approve(
            session,
            unit,
            row,
            actor=principal.subject,
            priority=payload.priority.value if payload.priority else None,
            note=payload.note,
        )
    except proposals.NotOpenError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    session.commit()
    return {"proposal": _as_dict(row), "work_order_id": str(order.id), "state": order.state}


@router.post(
    "/units/{unit_code}/{proposal_id}/merge",
    summary="Fusionar: los hallazgos se adjuntan a una OT existente (RF-114)",
)
def merge(
    unit_code: str,
    proposal_id: uuid.UUID,
    payload: MergeIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*DECIDERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    row = _proposal(session, unit, proposal_id)
    target = session.get(WorkOrder, payload.work_order_id)
    if target is None or target.business_unit_id != unit.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "la OT de destino no existe en esta unidad de negocio"
        )
    try:
        proposals.merge(session, unit, row, into=target, actor=principal.subject, note=payload.note)
    except proposals.NotOpenError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except proposals.ProposalError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return _as_dict(row)


@router.post(
    "/units/{unit_code}/{proposal_id}/reject",
    summary="Rechazar con un motivo de catálogo, que es una etiqueta (RF-114)",
)
def reject(
    unit_code: str,
    proposal_id: uuid.UUID,
    payload: RejectIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*DECIDERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    row = _proposal(session, unit, proposal_id)
    try:
        proposals.reject(
            session,
            unit,
            row,
            reason_code=payload.reason_code,
            actor=principal.subject,
            note=payload.note,
        )
    except proposals.NotOpenError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except proposals.UnknownReasonError as exc:
        # 422 with the available codes in the message: the screen shows the list, and a supervisor
        # should not have to guess which reason the platform knows.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return _as_dict(row)
