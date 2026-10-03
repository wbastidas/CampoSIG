"""Form responses, evidence and the provenance of every AI-proposed value.

RF-043 to RF-048 (responses), M07 (evidence), RF-052 and RF-140 (provenance).

The provenance table is the quiet centrepiece of the whole learning story. Every value an AI
model proposes is stored next to what the technician finally confirmed, with the model version
and the confidence that produced it. A confirmation is a positive example; a correction is a
better one. Without this table the platform has AI features; with it, it has a data flywheel.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


class ResponseState(StrEnum):
    DRAFT = "borrador"
    #: Closed in the field and delivered. Immutable from the device onwards.
    SUBMITTED = "enviada"
    #: A supervisor returned it; the device may edit and resubmit.
    RETURNED = "devuelta"
    APPROVED = "aprobada"


class ValueOrigin(StrEnum):
    """Where a field's value came from (SRS rule 0.5)."""

    MANUAL = "manual"
    VOICE = "voz"
    VISION = "vision"
    #: Computed by the form itself, e.g. a restoration time.
    COMPUTED = "calculado"
    #: Carried over from the asset's record in the GIS.
    PREFILLED = "precargado"


class EvidenceKind(StrEnum):
    PHOTO = "foto"
    AUDIO = "audio"
    SIGNATURE = "firma"
    SKETCH = "croquis"
    DOCUMENT = "documento"


class EvidenceSource(StrEnum):
    """Where a photograph came from (RF-074). Only the live camera makes evidence; a picture from
    the gallery may be attached, but it was not taken there and then, and nothing proves it was."""

    CAMERA = "camara"
    GALLERY = "galeria"


class IntegrityStatus(StrEnum):
    """What the server found when it hashed the uploaded file (RF-073)."""

    #: Registered, not uploaded yet, or uploaded and not checked yet.
    PENDING = "pendiente"
    VERIFIED = "verificada"
    #: The file in storage is not the one the device hashed at capture.
    ALTERED = "alterada"


class EvidenceStage(StrEnum):
    BEFORE = "antes"
    AFTER = "despues"
    DURING = "durante"
    NOT_APPLICABLE = "no_aplica"


class FormResponse(Base):
    """What a technician filled in for one work order."""

    __tablename__ = "form_response"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False
    )

    form_code: Mapped[str] = mapped_column(String(16), nullable=False)
    #: The version the work order was assigned with, not whatever is current now (SRS 4.1.6).
    form_version: Mapped[str] = mapped_column(String(16), nullable=False)

    #: Canonical keys to confirmed values. Never real field names (ADR-004).
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default=ResponseState.DRAFT)

    #: The AI's summary and the technician's edit of it, kept apart: the difference between
    #: them is a training signal (RF-091).
    summary_ai: Mapped[str | None] = mapped_column(Text)
    summary_final: Mapped[str | None] = mapped_column(Text)

    device_key: Mapped[str | None] = mapped_column(String(128))
    captured_by: Mapped[str | None] = mapped_column(String(255))
    #: Device clock and server clock kept separately: phones work offline and drift.
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    provenance: Mapped[list[FieldProvenance]] = relationship(
        back_populates="response", cascade="all, delete-orphan"
    )
    evidence: Mapped[list[Evidence]] = relationship(
        back_populates="response", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # One response per work order and form: a second one would make "the answers" ambiguous.
        UniqueConstraint("work_order_id", "form_code", name="uq_form_response_identity"),
        Index("ix_form_response_unit_state", "business_unit_id", "state"),
    )

    @property
    def is_editable(self) -> bool:
        return self.state in (ResponseState.DRAFT, ResponseState.RETURNED)


class FieldProvenance(Base):
    """Where one field's value came from, and what a human did with it (RF-052, RF-140).

    One row per field the AI proposed. `proposed_value` is what the model said,
    `final_value` is what was submitted, and comparing them gives the acceptance rate the
    dashboards report and the corrected examples that training consumes.
    """

    __tablename__ = "field_provenance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("form_response.id", ondelete="CASCADE"), nullable=False
    )
    #: Canonical attribute key, dotted for nested fields.
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)

    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    #: What the model proposed. JSONB because a field may be a scalar, a list or an object.
    proposed_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    final_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    model_name: Mapped[str | None] = mapped_column(String(64))
    model_version: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column(Float)

    #: True when a human accepted the proposal unchanged, false when they corrected it.
    accepted_unchanged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Who confirmed it. Never null for an AI value on a submitted response: the SRS requires
    #: human confirmation before any AI value is definitive (rule 0.5).
    confirmed_by: Mapped[str | None] = mapped_column(String(255))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: 'tecnico' or 'supervisor'. A supervisor's correction carries more weight in training.
    reviewer_level: Mapped[str | None] = mapped_column(String(16))

    #: The transcript fragment a voice value came from, for the ASR training pair.
    source_transcript: Mapped[str | None] = mapped_column(Text)

    response: Mapped[FormResponse] = relationship(back_populates="provenance")

    __table_args__ = (
        UniqueConstraint("response_id", "field_key", name="uq_field_provenance_identity"),
        Index("ix_field_provenance_origin", "origin"),
        # The active-learning query: low-confidence proposals are labelled first.
        Index("ix_field_provenance_confidence", "confidence"),
    )


class Evidence(Base):
    """A photograph, audio note, signature or sketch (M07).

    `content_hash` is what makes a photograph evidence rather than a picture: it is computed
    on the device at capture, travels with the file, and is verified on arrival. A photograph
    whose hash does not match what the device recorded is not the photograph that was taken.
    """

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("form_response.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    stage: Mapped[str] = mapped_column(
        String(16), nullable=False, default=EvidenceStage.NOT_APPLICABLE
    )

    #: Key in object storage. The file itself never touches the database.
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(64))

    #: Capture position and time, from the device.
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: The rest of RF-071's metadata. Altitude and heading come from the phone with the fix; the
    #: person and the model are taken from the enrolled device on the server, never from the payload
    #: — a capture cannot be signed with somebody else's name by writing it in a field.
    altitude_m: Mapped[float | None] = mapped_column(Float)
    heading_deg: Mapped[float | None] = mapped_column(Float)
    captured_by: Mapped[str | None] = mapped_column(String(255))
    device_model: Mapped[str | None] = mapped_column(String(128))

    #: Live camera or gallery (RF-074). Null for captures from before the field existed, read as
    #: camera: those phones had no gallery option.
    source: Mapped[str | None] = mapped_column(String(16))
    #: The copy with the visible watermark (RF-072). The original, without it, is `storage_key` and
    #: is the one hashed: the watermark is for people, the hash is for evidence.
    watermarked_storage_key: Mapped[str | None] = mapped_column(String(512))

    #: The guided framing this photograph was taken for, so a reviewer knows what it should
    #: show and the before/after comparison can pair them (RF-070).
    framing: Mapped[str | None] = mapped_column(String(64))

    #: Verified on arrival. False means not verified: not uploaded yet, or altered — which of the
    #: two is `integrity_status`.
    integrity_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    integrity_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=IntegrityStatus.PENDING, server_default="pendiente"
    )

    #: Detections the on-device vision model produced, kept as proposals until confirmed.
    vision_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    response: Mapped[FormResponse] = relationship(back_populates="evidence")

    __table_args__ = (
        Index("ix_evidence_response_stage", "response_id", "stage"),
        # Deduplication: the same file uploaded twice is stored once.
        Index("ix_evidence_hash", "content_hash"),
    )
