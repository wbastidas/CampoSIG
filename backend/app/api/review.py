"""Supervisor review endpoints (M11, RF-110 to RF-112, RF-342).

The screen these serve is where field data becomes authoritative, so the endpoint gives the
supervisor everything the decision depends on in one call: the answers, what the AI proposed
and whether anybody confirmed it, the evidence before and after, what the deterministic
compliance rules found — with their citations — and the reasons the approval is blocked, if it
is.

Assembling it server-side is deliberate. A screen that had to make six calls and combine them
would be a screen where one failed call silently removes a blocker from view.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.gis_gateway.models import AsBuiltBatch
from app.gis_gateway.staging_table import asbuilt_proposal
from app.inference.service import pre_review_degradations
from app.infra.database import get_session
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.prereview.service import latest_report, latest_run
from app.responses.models import FormResponse, ValueOrigin
from app.responses.service import compose_for, missing_photos, photo_counts
from app.review.models import Decision
from app.review.service import (
    ApprovalBlockedError,
    NotReviewableError,
    approval_blockers,
    compliance_findings,
    decide,
    decision_history,
    observations_for,
    queue_size,
    review_queue,
)
from app.workorders.models import WorkOrder

# `unit_scope` as a router dependency, not per endpoint: an endpoint cannot forget it, and
# ADR-009 holds at the door instead of inside each handler.
router = APIRouter(prefix="/api/v1/review", tags=["review"], dependencies=[Depends(unit_scope)])

SessionDep = Annotated[Session, Depends(get_session)]


def _unit(session: Session, code: str):  # type: ignore[no-untyped-def]
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _order(session: Session, unit_id: uuid.UUID, order_id: uuid.UUID) -> WorkOrder:
    order = session.get(WorkOrder, order_id)
    if order is None or order.business_unit_id != unit_id:
        # Same answer for "not yours" as for "does not exist" (ADR-009).
        raise HTTPException(status.HTTP_404_NOT_FOUND, "la orden de trabajo no existe")
    return order


def _response_for(session: Session, order: WorkOrder) -> FormResponse | None:
    return session.scalars(
        select(FormResponse)
        .options(selectinload(FormResponse.provenance), selectinload(FormResponse.evidence))
        .where(FormResponse.work_order_id == order.id)
    ).first()


@router.get("/units/{unit_code}/queue")
def queue(
    session: SessionDep,
    unit_code: str,
    area: Annotated[str | None, Query()] = None,
    crew_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Work orders awaiting a decision, worst SLA first (RF-110)."""
    unit = _unit(session, unit_code)
    orders = review_queue(session, unit, area=area, crew_id=crew_id, limit=limit, offset=offset)
    return {
        "total": queue_size(session, unit),
        "items": [
            {
                "work_order_id": str(order.id),
                "code": order.code,
                "work_type": order.work_type,
                "form_code": order.form_code,
                "state": order.state,
                "priority": order.priority,
                "asset_code": order.asset_code,
                "crew_id": str(order.assigned_crew_id) if order.assigned_crew_id else None,
                "sla_due_at": order.sla_due_at.isoformat() if order.sla_due_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            }
            for order in orders
        ],
    }


@router.get("/units/{unit_code}/work-orders/{order_id}")
def detail(session: SessionDep, unit_code: str, order_id: uuid.UUID) -> dict[str, Any]:
    """Everything the decision depends on, in one call."""
    unit = _unit(session, unit_code)
    order = _order(session, unit.id, order_id)
    response = _response_for(session, order)
    form = compose_for(session, unit, order)

    evidence = sorted(
        (response.evidence if response else []),
        key=lambda item: (item.stage, item.storage_key),
    )

    return {
        "work_order": {
            "work_order_id": str(order.id),
            "code": order.code,
            "work_type": order.work_type,
            "state": order.state,
            "priority": order.priority,
            "asset_type_key": order.asset_type_key,
            "asset_code": order.asset_code,
            "feeder_code": order.feeder_code,
            "zone": order.zone,
            "external_ref": order.external_ref,
        },
        "form": {
            "code": form.code,
            "version": form.version,
            "title": form.definition.form.title,
            "schema": form.schema,
            "ui_schema": form.ui_schema,
            # The conditional rules travel too, so the form view can mark what the answers still
            # owe with the same evaluator the phone runs (I5, shared corpus).
            "rules": form.rules,
            "warnings": form.warnings,
        },
        "response": None
        if response is None
        else {
            "response_id": str(response.id),
            "state": response.state,
            "answers": response.answers,
            "captured_by": response.captured_by,
            "captured_at": response.captured_at.isoformat() if response.captured_at else None,
            "submitted_at": response.submitted_at.isoformat() if response.submitted_at else None,
        },
        # What the machine proposed and what a person did with it. The supervisor's main job
        # on an AI-assisted capture is auditing this list (SRS rule 0.5).
        "provenance": [
            {
                "field_key": entry.field_key,
                "origin": entry.origin,
                "proposed_value": (entry.proposed_value or {}).get("v"),
                "final_value": (entry.final_value or {}).get("v"),
                "confidence": entry.confidence,
                "model_name": entry.model_name,
                "model_version": entry.model_version,
                "accepted_unchanged": entry.accepted_unchanged,
                "confirmed_by": entry.confirmed_by,
                "source": entry.source_transcript,
                "is_ai": entry.origin in (ValueOrigin.VOICE, ValueOrigin.VISION),
            }
            for entry in (response.provenance if response else [])
        ],
        "evidence": [
            {
                "evidence_id": str(item.id),
                "kind": item.kind,
                "stage": item.stage,
                "storage_key": item.storage_key,
                "content_hash": item.content_hash,
                "integrity_verified": item.integrity_verified,
                "vision_result": item.vision_result,
            }
            for item in evidence
        ],
        "photo_counts": photo_counts(response) if response else {},
        "missing_photos": missing_photos(form, response) if response else [],
        # Deterministic, cited, and reproducible from stored data (ADR-007).
        "compliance": [
            finding.as_dict() for finding in compliance_findings(session, order, response)
        ],
        "blockers": approval_blockers(session, unit, order, response),
        # RF-204: what the AI layer will not do on this deployment, and why. Said out loud rather
        # than left as a missing section — a report with a gap looks complete, which is worse than
        # no report. Computed from configuration, with no call to the model service: a review
        # screen must never wait on a model, and the approval below does not either.
        "degradations": [entry.as_dict() for entry in pre_review_degradations()],
        # The pre-review report (RF-111, RF-175), or null when there is none yet. Null is an
        # ordinary answer: the order may be waiting for the night batch, or this deployment may have
        # no model service at all. The degradations above say which.
        "agent_report": _agent_report(session, order.id),
        "observations": [
            {
                "field_key": observation.field_key,
                "message": observation.message,
                "suggested_value": observation.suggested_value,
            }
            for observation in observations_for(session, order)
        ],
        "history": [
            {
                "decision": row.decision,
                "reviewer_sub": row.reviewer_sub,
                "note": row.note,
                "decided_at": row.decided_at.isoformat() if row.decided_at else None,
                "blind_sample": row.blind_sample,
            }
            for row in decision_history(session, order)
        ],
    }


def _agent_report(session: Session, order_id: uuid.UUID) -> dict[str, Any] | None:
    """The stored report plus the state of its run.

    The run's state travels with it because "there is no report" has two very different
    meanings — it failed, or it has not run — and a supervisor deciding without one should know
    which.
    """
    report = latest_report(session, order_id)
    if report is None:
        run = latest_run(session, order_id)
        if run is None:
            return None
        return {"run_state": run.state, "error": run.error, "report": None}
    run = latest_run(session, order_id)
    return {
        "run_state": run.state if run else None,
        "error": run.error if run else None,
        "report": report.model_dump(mode="json"),
    }


class ObservationIn(BaseModel):
    field_key: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=1000)
    suggested_value: Any = None


class DecisionIn(BaseModel):
    decision: Decision
    # No `reviewer_sub`: the reviewer is whoever the token says they are. A decision whose
    # author the caller could type is a decision nobody signed.
    note: str | None = Field(default=None, max_length=2000)
    observations: list[ObservationIn] = Field(default_factory=list)
    #: True when this order was drawn for the blind sample that measures agreement between
    #: the supervisor and the agents (SRS 10.4).
    blind_sample: bool | None = None


@router.post("/units/{unit_code}/work-orders/{order_id}/decision")
def submit_decision(
    session: SessionDep,
    unit_code: str,
    order_id: uuid.UUID,
    payload: DecisionIn,
    principal: Annotated[Any, Depends(require_roles(Role.SUPERVISOR, Role.INSPECTOR))] = None,
) -> dict[str, Any]:
    """Record a decision (RF-112). Approval is refused when its preconditions are unmet."""
    unit = _unit(session, unit_code)
    order = _order(session, unit.id, order_id)
    try:
        row = decide(
            session,
            unit,
            order,
            decision=payload.decision.value,
            reviewer_sub=principal.subject,
            note=payload.note,
            observations=[item.model_dump() for item in payload.observations],
            blind_sample=payload.blind_sample,
        )
    except NotReviewableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except ApprovalBlockedError as exc:
        # 422 with the reasons, not a bare 400: the screen shows the list, and a supervisor
        # should not have to guess which precondition failed.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"message": "la aprobación tiene condiciones pendientes", "blockers": exc.reasons},
        ) from exc
    session.commit()
    return {
        "decision": row.decision,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "work_order_state": order.state,
    }


@router.get("/units/{unit_code}/gis-tray")
def gis_tray(session: SessionDep, unit_code: str) -> dict[str, Any]:
    """As-built proposals staged for the GIS, and the batches already dispatched (RF-342).

    The tray is the last human checkpoint before anything reaches the corporate geodatabase,
    which is why it is part of the review screen and not an admin corner: the person who
    approved the work is the person who should see what it is about to change.
    """
    unit = _unit(session, unit_code)
    rows = session.execute(
        select(
            asbuilt_proposal.c.proposal_id,
            asbuilt_proposal.c.work_order_ref,
            asbuilt_proposal.c.asset_type_key,
            asbuilt_proposal.c.action,
            asbuilt_proposal.c.status,
            asbuilt_proposal.c.requires_arcfm,
            asbuilt_proposal.c.created_at,
        )
        .where(asbuilt_proposal.c.business_unit_id == unit.id)
        .order_by(asbuilt_proposal.c.created_at.desc())
        .limit(200)
    ).all()

    batches = list(
        session.scalars(
            select(AsBuiltBatch)
            .where(AsBuiltBatch.business_unit_id == unit.id)
            .order_by(AsBuiltBatch.created_at.desc())
            .limit(50)
        )
    )

    return {
        "proposals": [
            {
                "proposal_id": str(row[0]),
                "work_order_id": row[1],
                "asset_type_key": row[2],
                "action": row[3],
                "status": row[4],
                # Lo que ArcFM tiene que aplicar a mano: la plataforma nunca escribe
                # conectividad (ADR-001), así que esto es lo que el editor GIS debe ver.
                "requires_arcfm": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
            }
            for row in rows
        ],
        "batches": [
            {
                "batch_id": str(batch.id),
                "status": batch.status,
                "created_at": batch.created_at.isoformat() if batch.created_at else None,
                "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
                "results": len(batch.results),
            }
            for batch in batches
        ],
    }
