"""Vision proposals into the response, under the same rule as voice (SRS rule 0.5, ADR-011).

Everything a model sees is stored as an unconfirmed AI value and nothing else. The approval
gate built in I6 already refuses a response carrying unconfirmed proposals, so a photograph
analysed and never reviewed cannot become a record.

Confirmation reuses the voice path deliberately: a technician confirming a field should not
have to care whether the suggestion came from their voice or from the camera, and a single
confirmation path means a single place where the rule can be got wrong.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.forms.composer import ComposedForm
from app.responses.models import FieldProvenance, FormResponse, ValueOrigin
from app.responses.service import record_provenance
from app.vision.contracts import ImageAnalysis
from app.vision.prefill import PrefillResult, prefill_from_analysis
from app.vision.taxonomy import VisionTaxonomy


def propose_from_photograph(
    session: Session,
    response: FormResponse,
    form: ComposedForm,
    analysis: ImageAnalysis,
    *,
    taxonomy: VisionTaxonomy | None = None,
) -> PrefillResult:
    """Analyse one photograph's predictions and store every proposal, unconfirmed.

    The findings are returned rather than stored as provenance: a finding is not a value of
    any field, it is something to report, and the form's findings block is where a person
    decides whether it belongs in the record.
    """
    result = prefill_from_analysis(analysis, form.schema, taxonomy=taxonomy)

    for proposal in result.proposals:
        record_provenance(
            session,
            response,
            field_key=proposal.field_key,
            origin=ValueOrigin.VISION,
            # Not a final value: nobody has confirmed it.
            final_value=None,
            proposed_value=proposal.value,
            model_name=proposal.model_name[:64],
            model_version=proposal.model_version[:32],
            confidence=proposal.confidence,
            # The evidence and the box, so the review screen can show the person the crop
            # the model was looking at. A proposal nobody can look at is not reviewable.
            source_transcript=_evidence_reference(proposal.evidence_key, proposal.box),
        )
    return result


def pending_proposals(response: FormResponse) -> list[FieldProvenance]:
    """Vision proposals still waiting for a person."""
    return [
        entry
        for entry in response.provenance
        if entry.origin == ValueOrigin.VISION and entry.confirmed_by is None
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
    """Confirm or correct one vision proposal, writing the value into the answers.

    :raises UnknownProposalError: if no vision proposal exists for that field.
    """
    from app.voice.service import UnknownProposalError

    entry = next(
        (
            p
            for p in response.provenance
            if p.field_key == field_key and p.origin == ValueOrigin.VISION
        ),
        None,
    )
    if entry is None:
        raise UnknownProposalError(
            f"no hay una propuesta de visión para el campo '{field_key}' en esta respuesta"
        )

    updated = dict(response.answers or {})
    updated[field_key] = final_value
    response.answers = updated

    proposed = entry.proposed_value
    return record_provenance(
        session,
        response,
        field_key=field_key,
        origin=ValueOrigin.VISION,
        final_value=final_value,
        proposed_value=proposed["v"]
        if isinstance(proposed, dict) and "v" in proposed
        else proposed,
        confirmed_by=confirmed_by,
        reviewer_level=reviewer_level,
    )


def _evidence_reference(evidence_key: str, box: Any) -> str:
    """A stable, readable pointer to the crop a proposal came from."""
    if box is None:
        return f"evidencia:{evidence_key}"
    return f"evidencia:{evidence_key}@{box.x:.3f},{box.y:.3f},{box.width:.3f},{box.height:.3f}"
