"""Voice endpoints: the lexicon a device downloads, and dictation as proposals (I7).

Three routes, and the split between them is the design:

* ``GET .../lexicon`` is what makes recognition of *this* utility's vocabulary possible at
  all. It answers 304-style with the hash the device already holds, because the stable part
  of a lexicon is most of it and the volatile catalogues are the part that moves.
* ``POST .../dictation`` stores proposals. It never writes an answer.
* ``POST .../confirm`` is the only way a dictated value becomes an answer, and it always
  carries who confirmed it (SRS rule 0.5).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infra.database import get_session
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.responses.models import FormResponse
from app.responses.service import compose_for
from app.voice.grammar import GrammarError, build_grammar
from app.voice.lexicon import VoiceLexicon
from app.voice.service import (
    UnknownProposalError,
    confirm,
    discard,
    lexicon_for_order,
    pending_proposals,
    propose_from_dictation,
)
from app.workorders.models import WorkOrder

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

SessionDep = Annotated[Session, Depends(get_session)]

#: A dictation longer than this is not a form entry, it is a monologue. The bound exists so
#: a stuck recorder cannot post a megabyte of text into an extraction.
MAX_TRANSCRIPT_CHARS = 8000


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


def _response(session: Session, unit_id: uuid.UUID, response_id: uuid.UUID) -> FormResponse:
    response = session.get(FormResponse, response_id)
    if response is None or response.business_unit_id != unit_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "la respuesta no existe")
    return response


class LexiconOut(BaseModel):
    """The lexicon, or a statement that the one the device holds is still current."""

    unchanged: bool = False
    lexicon: VoiceLexicon | None = None
    grammar: str | None = None


@router.get("/units/{unit_code}/orders/{order_id}/lexicon", response_model=LexiconOut)
def order_lexicon(
    session: SessionDep,
    unit_code: str,
    order_id: uuid.UUID,
    known_hash: Annotated[str | None, Query(alias="known-hash")] = None,
) -> LexiconOut:
    """The lexicon and grammar for a work order's form (RF-331, RF-332)."""
    unit = _unit(session, unit_code)
    order = _order(session, unit.id, order_id)
    form = compose_for(session, unit, order)
    lexicon = lexicon_for_order(session, unit, order, form=form)
    if known_hash and known_hash == lexicon.content_hash:
        return LexiconOut(unchanged=True)
    try:
        grammar = build_grammar(form.schema)
    except GrammarError:
        # A form with nothing dictable is a real case (a pure evidence form). The lexicon
        # still travels, because its hotwords help the free-text note.
        grammar = None
    return LexiconOut(lexicon=lexicon, grammar=grammar)


class DictationIn(BaseModel):
    transcript: str = Field(min_length=1, max_length=MAX_TRANSCRIPT_CHARS)
    #: Restrict extraction to one section, which is how a long form is really dictated.
    fields: list[str] | None = None
    asr_model: str | None = None
    asr_version: str | None = None


class ProposalOut(BaseModel):
    field_key: str
    value: Any
    confidence: float
    transcript_span: str
    rationale: str


class DictationOut(BaseModel):
    normalized_transcript: str
    proposals: list[ProposalOut]
    unfilled: list[str]
    warnings: list[str]
    model_name: str
    model_version: str


@router.post(
    "/units/{unit_code}/responses/{response_id}/dictation",
    response_model=DictationOut,
    status_code=status.HTTP_201_CREATED,
)
def dictate(
    session: SessionDep, unit_code: str, response_id: uuid.UUID, payload: DictationIn
) -> DictationOut:
    """Extract proposals from a transcript and store them unconfirmed (RF-140)."""
    unit = _unit(session, unit_code)
    response = _response(session, unit.id, response_id)
    order = session.get(WorkOrder, response.work_order_id)
    if order is None:  # pragma: no cover - a response always has its order
        raise HTTPException(status.HTTP_404_NOT_FOUND, "la orden de trabajo no existe")

    form = compose_for(session, unit, order)
    lexicon = lexicon_for_order(session, unit, order, form=form)
    result = propose_from_dictation(
        session,
        response,
        form,
        lexicon,
        payload.transcript,
        fields=payload.fields,
        asr_model=payload.asr_model,
        asr_version=payload.asr_version,
    )
    session.commit()
    return DictationOut(
        normalized_transcript=result.normalized.text if result.normalized else "",
        proposals=[
            ProposalOut(
                field_key=p.field_key,
                value=p.value,
                confidence=p.confidence,
                transcript_span=p.transcript_span,
                rationale=p.rationale,
            )
            for p in result.proposals
        ],
        unfilled=result.unfilled,
        warnings=result.warnings,
        model_name=result.model_name,
        model_version=result.model_version,
    )


class ConfirmIn(BaseModel):
    field_key: str
    #: Absent means "reject this proposal". A correction sends the corrected value.
    final_value: Any = None
    accept: bool = True
    confirmed_by: str
    reviewer_level: str = "tecnico"


class PendingOut(BaseModel):
    field_key: str
    proposed_value: Any
    confidence: float | None
    model_name: str | None
    transcript_span: str | None


@router.get("/units/{unit_code}/responses/{response_id}/pending", response_model=list[PendingOut])
def pending(session: SessionDep, unit_code: str, response_id: uuid.UUID) -> list[PendingOut]:
    """Proposals still waiting for a person — what the review UI renders."""
    unit = _unit(session, unit_code)
    response = _response(session, unit.id, response_id)
    return [
        PendingOut(
            field_key=entry.field_key,
            proposed_value=(entry.proposed_value or {}).get("v"),
            confidence=entry.confidence,
            model_name=entry.model_name,
            transcript_span=entry.source_transcript,
        )
        for entry in pending_proposals(response)
    ]


@router.post("/units/{unit_code}/responses/{response_id}/confirm")
def confirm_proposal(
    session: SessionDep, unit_code: str, response_id: uuid.UUID, payload: ConfirmIn
) -> dict[str, Any]:
    """Confirm, correct or reject one proposal. The only path from proposal to answer."""
    unit = _unit(session, unit_code)
    response = _response(session, unit.id, response_id)
    try:
        if not payload.accept:
            discard(
                session, response, field_key=payload.field_key, discarded_by=payload.confirmed_by
            )
            session.commit()
            return {"field_key": payload.field_key, "state": "descartada"}
        entry = confirm(
            session,
            response,
            field_key=payload.field_key,
            final_value=payload.final_value,
            confirmed_by=payload.confirmed_by,
            reviewer_level=payload.reviewer_level,
        )
    except UnknownProposalError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    session.commit()
    return {
        "field_key": entry.field_key,
        "state": "confirmada",
        "accepted_unchanged": entry.accepted_unchanged,
    }
