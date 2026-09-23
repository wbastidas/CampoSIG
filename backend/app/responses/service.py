"""Validate and store form responses, evidence and provenance (RF-043 to RF-048, M07).

Validation runs on the server as well as on the device, deliberately. The device validates so
a technician is told immediately; the server validates because the device is not trusted —
an old app version, a corrupted local database or a replayed payload must not be able to store
answers that violate the form.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

import jsonschema
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.models import ActorKind, EventKind
from app.forms.composer import ComposedForm, FormComposer
from app.forms.rules import missing_requirements
from app.org.models import BusinessUnit
from app.org.service import context_for_unit
from app.policy import service as policy
from app.responses.models import (
    Evidence,
    EvidenceKind,
    EvidenceStage,
    FieldProvenance,
    FormResponse,
    ResponseState,
    ValueOrigin,
)
from app.workorders.models import WorkOrder


class AudioNotAllowedError(Exception):
    """Raised when a device sends audio into an area whose policy does not keep it (RF-058).

    Refused rather than accepted and quietly dropped. The area decided not to keep recordings, and
    an evidence row pointing at a file nobody is going to store would be worse than either: it
    would read as kept audio in an audit, and read as missing audio to whoever went looking for it.

    Checked on the server and not only on the phone for the same reason answers are validated
    twice: an old build, a corrupted local database or a replayed payload must not be able to make
    the platform keep a customer's voice against the area's decision.
    """


class AnswerValidationError(Exception):
    """Raised when answers do not satisfy the form they claim to answer."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


class NotEditableError(Exception):
    """Raised when a response is edited after it stopped being the device's to change."""


class IntegrityError(Exception):
    """Raised when an uploaded file does not match the hash the device recorded."""


def compose_for(session: Session, unit: BusinessUnit, order: WorkOrder) -> ComposedForm:
    """The form a work order executes with, for its business unit."""
    resolver, metadata = context_for_unit(session, unit)
    return FormComposer(resolver, metadata).compose(order.form_code, order.asset_type_key)


# --- validation --------------------------------------------------------------------
def validate_answers(form: ComposedForm, answers: dict[str, Any]) -> list[str]:
    """Check answers against the composed schema and the form's rules.

    Returns problems in Spanish, phrased for the person who has to fix them rather than for a
    developer reading a stack trace.
    """
    problems: list[str] = []

    validator = jsonschema.Draft202012Validator(form.schema)
    for error in sorted(validator.iter_errors(answers), key=lambda e: list(e.path)):
        location = ".".join(str(part) for part in error.path) or "(raíz)"
        problems.append(f"{location}: {error.message}")

    problems.extend(_evaluate_rules(form, answers))
    return problems


def _evaluate_rules(form: ComposedForm, answers: dict[str, Any]) -> list[str]:
    """The form's conditional requirements, as messages for the person who has to fix them.

    The judgement lives in `app/forms/rules.py`, which the web and the phone mirror against a
    shared corpus (`forms/contract/validation-cases.json`). Only the wording is here: a rule
    that behaves differently on the phone than on the server is a rule nobody can trust, and the
    way to prevent that is one contract rather than three careful implementations.
    """
    return [
        missing.message or f"{missing.field}: es obligatorio en este caso"
        for missing in missing_requirements(form.rules, answers)
    ]


# --- responses ---------------------------------------------------------------------
def save_answers(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    answers: dict[str, Any],
    device_key: str | None = None,
    captured_by: str | None = None,
    captured_at: datetime | None = None,
    submit: bool = False,
) -> FormResponse:
    """Store answers, validating them against the form the work order executes with.

    :param submit: True when the technician closed the form in the field. A submitted
        response stops being the device's to change.
    :raises AnswerValidationError: if the answers do not satisfy the form.
    :raises NotEditableError: if the response is no longer editable.
    """
    response = session.scalars(
        select(FormResponse).where(
            FormResponse.work_order_id == order.id, FormResponse.form_code == order.form_code
        )
    ).first()

    if response is not None and not response.is_editable:
        raise NotEditableError(
            f"la respuesta está en estado '{response.state}' y ya no se puede modificar "
            "desde el dispositivo"
        )

    form = compose_for(session, unit, order)
    if submit:
        # Drafts are saved as they are: a technician halfway through a form must not be
        # blocked by a field they have not reached yet. Submission is where it must hold.
        problems = validate_answers(form, answers)
        if problems:
            raise AnswerValidationError(problems)

    if response is None:
        response = FormResponse(
            business_unit_id=unit.id,
            work_order_id=order.id,
            form_code=order.form_code,
            form_version=order.form_version or form.version,
            answers=answers,
            device_key=device_key,
            captured_by=captured_by,
            captured_at=captured_at,
        )
        session.add(response)
    else:
        response.answers = answers
        response.device_key = device_key or response.device_key
        response.captured_by = captured_by or response.captured_by
        response.captured_at = captured_at or response.captured_at

    if submit:
        response.state = ResponseState.SUBMITTED
        response.submitted_at = datetime.now(UTC)

    session.flush()
    return response


def record_provenance(
    session: Session,
    response: FormResponse,
    *,
    field_key: str,
    origin: str,
    final_value: Any,
    proposed_value: Any = None,
    model_name: str | None = None,
    model_version: str | None = None,
    confidence: float | None = None,
    confirmed_by: str | None = None,
    reviewer_level: str = "tecnico",
    source_transcript: str | None = None,
) -> FieldProvenance:
    """Record where a field's value came from (RF-052, RF-140).

    The comparison between proposal and final value is the training signal, so it is computed
    here rather than left for an analyst to reconstruct later.
    """
    accepted_unchanged = proposed_value is not None and proposed_value == final_value

    existing = session.scalars(
        select(FieldProvenance).where(
            FieldProvenance.response_id == response.id, FieldProvenance.field_key == field_key
        )
    ).first()

    if existing is not None:
        was = _value(existing.final_value)
        existing.origin = origin
        existing.final_value = _wrap(final_value)
        existing.proposed_value = _wrap(proposed_value)
        existing.accepted_unchanged = accepted_unchanged
        existing.confirmed_by = confirmed_by or existing.confirmed_by
        existing.confirmed_at = datetime.now(UTC) if confirmed_by else existing.confirmed_at
        existing.reviewer_level = reviewer_level
        session.flush()
        _log_field_change(
            session,
            response,
            field_key=field_key,
            origin=origin,
            before=was,
            after=final_value,
            proposed=proposed_value,
            actor=confirmed_by,
            model_name=model_name,
            model_version=model_version,
            confidence=confidence,
        )
        return existing

    entry = FieldProvenance(
        response_id=response.id,
        field_key=field_key,
        origin=origin,
        proposed_value=_wrap(proposed_value),
        final_value=_wrap(final_value),
        model_name=model_name,
        model_version=model_version,
        confidence=confidence,
        accepted_unchanged=accepted_unchanged,
        confirmed_by=confirmed_by,
        confirmed_at=datetime.now(UTC) if confirmed_by else None,
        reviewer_level=reviewer_level,
        source_transcript=source_transcript,
    )
    session.add(entry)
    session.flush()
    _log_field_change(
        session,
        response,
        field_key=field_key,
        origin=origin,
        before=None,
        after=final_value,
        proposed=proposed_value,
        actor=confirmed_by,
        model_name=model_name,
        model_version=model_version,
        confidence=confidence,
    )
    return entry


def _log_field_change(
    session: Session,
    response: FormResponse,
    *,
    field_key: str,
    origin: str,
    before: Any,
    after: Any,
    proposed: Any,
    actor: str | None,
    model_name: str | None,
    model_version: str | None,
    confidence: float | None,
) -> None:
    """Record a field change in the trail, with the value before and after (RF-160).

    The origin travels because RF-160 asks for it by name — «origen humano o IA» — and because the
    two are answers to different questions. A value a model proposed and a person confirmed has two
    actors, and the trail records the person as the actor and the model in the payload: the person
    is who answered for it (regla 8), and the model is where it came from.
    """
    if before == after and proposed is None:
        # Re-saving the same manual value is not a change. Logging it would bury the changes that
        # matter under every autosave the device makes.
        return
    audit.record(
        session,
        response.business_unit_id,
        kind=EventKind.FIELD_CHANGED,
        subject_type="respuesta",
        subject_id=str(response.id),
        work_order_id=response.work_order_id,
        actor=actor or response.captured_by or "sistema:captura",
        actor_kind=ActorKind.PERSON if (actor or response.captured_by) else ActorKind.SYSTEM,
        device_key=response.device_key,
        payload={
            "field_key": field_key,
            "before": before,
            "after": after,
            "proposed": proposed,
            "origin": origin,
            "model": (
                {"name": model_name, "version": model_version, "confidence": confidence}
                if model_name
                else None
            ),
        },
    )


def _value(payload: dict[str, Any] | None) -> Any:
    return None if payload is None else payload.get("v")


def _wrap(value: Any) -> dict[str, Any] | None:
    """Wrap a value for JSONB storage.

    Wrapped in an object because a field may hold a scalar, a list or an object, and a JSONB
    column holding bare scalars is awkward to query consistently.
    """
    return None if value is None else {"v": value}


def unconfirmed_ai_values(session: Session, response: FormResponse) -> list[FieldProvenance]:
    """AI proposals nobody confirmed yet.

    The SRS is explicit that no AI value is definitive without human confirmation (rule 0.5),
    so this is what stands between a proposal and a submitted response.
    """
    return [
        entry
        for entry in response.provenance
        if entry.origin in (ValueOrigin.VOICE, ValueOrigin.VISION) and entry.confirmed_by is None
    ]


# --- evidence ----------------------------------------------------------------------
def register_evidence(
    session: Session,
    response: FormResponse,
    *,
    kind: str,
    storage_key: str,
    content_hash: str,
    stage: str = EvidenceStage.NOT_APPLICABLE,
    size_bytes: int = 0,
    mime_type: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    gps_accuracy_m: float | None = None,
    captured_at: datetime | None = None,
    framing: str | None = None,
    vision_result: dict[str, Any] | None = None,
) -> Evidence:
    """Register a piece of evidence against a response.

    :raises AudioNotAllowedError: for audio when the area's policy does not keep it (RF-151).
    """
    if kind == EvidenceKind.AUDIO:
        zone = session.execute(
            select(WorkOrder.zone).where(WorkOrder.id == response.work_order_id)
        ).scalar_one_or_none()
        allowed = policy.resolve_field(session, response.business_unit_id, "store_audio", zone)
        if not allowed.value:
            raise AudioNotAllowedError(
                "la política de esta área no guarda el audio original "
                f"(store_audio, {allowed.source}); solo se conserva la transcripción"
            )
    evidence = Evidence(
        response_id=response.id,
        kind=kind,
        stage=stage,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=size_bytes,
        mime_type=mime_type,
        latitude=latitude,
        longitude=longitude,
        gps_accuracy_m=gps_accuracy_m,
        captured_at=captured_at,
        framing=framing,
        vision_result=vision_result,
    )
    session.add(evidence)
    session.flush()
    return evidence


def verify_integrity(evidence: Evidence, content: bytes) -> bool:
    """Confirm an uploaded file is the one the device recorded.

    A photograph whose hash does not match is not the photograph that was taken, and marking
    it verified would turn a picture into evidence it is not.
    """
    digest = hashlib.sha256(content).hexdigest()
    evidence.integrity_verified = digest == evidence.content_hash
    return evidence.integrity_verified


def photo_counts(response: FormResponse) -> dict[str, int]:
    """Photographs per stage, for checking a form's minimums (SRS 4.8)."""
    counts = {EvidenceStage.BEFORE.value: 0, EvidenceStage.AFTER.value: 0}
    for item in response.evidence:
        if item.kind == "foto" and item.stage in counts:
            counts[item.stage] += 1
    return counts


def missing_photos(form: ComposedForm, response: FormResponse) -> list[str]:
    """Which photo minimums a response still fails (SRS 4.8)."""
    counts = photo_counts(response)
    required = form.definition.form.min_photos
    problems: list[str] = []
    if counts[EvidenceStage.BEFORE.value] < required.before:
        problems.append(
            f"faltan fotos ANTES: {counts[EvidenceStage.BEFORE.value]} de {required.before}"
        )
    if counts[EvidenceStage.AFTER.value] < required.after:
        problems.append(
            f"faltan fotos DESPUÉS: {counts[EvidenceStage.AFTER.value]} de {required.after}"
        )
    return problems


def duplicate_of(session: Session, content_hash: str) -> uuid.UUID | None:
    """Whether this exact file already exists, so it is stored once."""
    existing = session.scalars(
        select(Evidence).where(Evidence.content_hash == content_hash)
    ).first()
    return existing.id if existing else None
