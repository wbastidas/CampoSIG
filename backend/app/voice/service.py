"""Dictation as a proposal, never as an answer (I7, SRS rule 0.5, RF-140).

The rule this module exists to enforce: a value the machine heard is a *proposal* until a
person confirms it. So a dictation writes rows in ``field_provenance`` with no
``confirmed_by``, and leaves ``form_response.answers`` alone. The approval gate built in I6
already refuses to let a response through with unconfirmed AI values, which means a
technician who dictates and never reviews cannot accidentally submit the machine's guesses.

Confirmation is the other half: :func:`confirm` writes the value into the answers and
records whether the person accepted the proposal or corrected it — the pair that training
consumes and the acceptance rate the dashboards report.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.forms.composer import ComposedForm
from app.model_profile.metadata import GisMetadata
from app.model_profile.resolver import ModelResolver
from app.org.models import BusinessUnit
from app.org.service import context_for_unit
from app.responses.models import FieldProvenance, FormResponse, ValueOrigin
from app.responses.service import compose_for, record_provenance
from app.voice.extractor import ExtractionResult, FormExtractor, RuleBasedExtractor
from app.voice.lexicon import OrderContext, VoiceLexicon, build_lexicon
from app.workorders.models import WorkOrder


class UnknownProposalError(Exception):
    """Raised when a confirmation names a field nothing proposed."""


def order_context(order: WorkOrder) -> OrderContext:
    """The work order's own words, for the lexicon (RF-331).

    Read from the order's canonical columns, never from the GIS: the platform's own record
    of what this crew was sent to do is the thing most likely to be said out loud next.
    The zone stands in for the address — it is the geographic name the order actually
    carries, and it is what a technician says when locating themselves.
    """
    return OrderContext(
        asset_code=order.asset_code,
        feeder_code=order.feeder_code,
        address=order.zone,
        asset_type_key=order.asset_type_key,
    )


def lexicon_for_order(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    form: ComposedForm | None = None,
) -> VoiceLexicon:
    """The lexicon a device needs to dictate this work order's form."""
    resolver, metadata = context_for_unit(session, unit)
    composed = form or compose_for(session, unit, order)
    return build_lexicon_for(resolver, metadata, composed, order_context(order))


def build_lexicon_for(
    resolver: ModelResolver,
    metadata: GisMetadata | None,
    form: ComposedForm,
    context: OrderContext | None = None,
) -> VoiceLexicon:
    """Lexicon for a composed form, without touching the database.

    Separate from :func:`lexicon_for_order` so the offline package builder and the mobile
    tests can build a lexicon from a form alone.
    """
    return build_lexicon(
        resolver,
        metadata,
        form_code=form.code,
        form_version=form.version,
        schema=form.schema,
        asset_type_key=form.schema.get("x-asset-type"),
        context=context,
    )


def propose_from_dictation(
    session: Session,
    response: FormResponse,
    form: ComposedForm,
    lexicon: VoiceLexicon,
    transcript: str,
    *,
    extractor: FormExtractor | None = None,
    fields: list[str] | None = None,
    asr_model: str | None = None,
    asr_version: str | None = None,
) -> ExtractionResult:
    """Run extraction and store every proposal as an unconfirmed AI value.

    :param fields: restrict extraction to one section of the form, which is how a long form
        is really dictated.
    :param asr_model: the speech model that produced the transcript. Recorded next to the
        extractor's own version because a bad proposal may be the transcript's fault, and
        telling the two apart is the whole point of keeping both (RF-052).
    """
    engine = extractor or RuleBasedExtractor()
    result = engine.extract(transcript, lexicon, form.schema, fields=fields)

    model_name = getattr(engine, "model_name", None) or "unknown"
    model_version = getattr(engine, "model_version", None) or "0"
    if asr_model:
        # One string, because a proposal is only ever as good as the weaker of the two
        # models that produced it and they must be read together.
        model_name = f"{asr_model}+{model_name}"
        model_version = f"{asr_version or '0'}+{model_version}"

    for proposal in result.proposals:
        record_provenance(
            session,
            response,
            field_key=proposal.field_key,
            origin=ValueOrigin.VOICE,
            # Deliberately not the final value: nobody has confirmed it yet, and a row
            # with a final value is a row that looks decided.
            final_value=None,
            proposed_value=proposal.value,
            model_name=model_name[:64],
            model_version=model_version[:32],
            confidence=proposal.confidence,
            source_transcript=proposal.transcript_span,
        )
    return result


def pending_proposals(response: FormResponse) -> list[FieldProvenance]:
    """Voice proposals still waiting for a person."""
    return [
        entry
        for entry in response.provenance
        if entry.origin == ValueOrigin.VOICE and entry.confirmed_by is None
    ]


def confirm(
    session: Session,
    response: FormResponse,
    *,
    field_key: str,
    final_value: Any,
    confirmed_by: str,
    reviewer_level: str = "tecnico",
) -> FieldProvenance:
    """Confirm or correct one proposal, and write the value into the answers.

    Passing a ``final_value`` different from the proposal is a correction, and that is the
    normal case — the acceptance rate is a metric, not a target. Either way the value
    reaches the response only through here, so an unreviewed proposal can never be an
    answer.

    :raises UnknownProposalError: if no proposal exists for that field.
    """
    entry = next(
        (
            p
            for p in response.provenance
            if p.field_key == field_key and p.origin == ValueOrigin.VOICE
        ),
        None,
    )
    if entry is None:
        raise UnknownProposalError(
            f"no hay una propuesta de voz para el campo '{field_key}' en esta respuesta"
        )

    updated = dict(response.answers or {})
    updated[field_key] = final_value
    response.answers = updated

    return record_provenance(
        session,
        response,
        field_key=field_key,
        origin=ValueOrigin.VOICE,
        final_value=final_value,
        proposed_value=_proposed_value(entry),
        confirmed_by=confirmed_by,
        reviewer_level=reviewer_level,
    )


def discard(session: Session, response: FormResponse, *, field_key: str, discarded_by: str) -> None:
    """Reject a proposal outright.

    Deleted rather than kept with a null value: a rejected proposal is a training example,
    but one recorded as a rejection, and the accepted-unchanged comparison has no meaning
    for a value nobody chose. The rejection itself is kept in the review decision.
    """
    for entry in list(response.provenance):
        if entry.field_key == field_key and entry.origin == ValueOrigin.VOICE:
            session.delete(entry)
    session.flush()


def _proposed_value(entry: FieldProvenance) -> Any:
    """Unwrap what was stored, so the acceptance comparison sees the value itself."""
    stored = entry.proposed_value
    if isinstance(stored, dict) and "v" in stored:
        return stored["v"]
    return stored
