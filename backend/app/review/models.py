"""Supervisor review and its outcome (M11: RF-110 to RF-115)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


class Decision(StrEnum):
    APPROVED = "aprobada"
    #: Returned with observations. The work order goes back to the device, with each
    #: observation attached to the exact field it concerns (RF-112).
    RETURNED = "devuelta"
    CANCELLED = "anulada"


class ReviewDecision(Base):
    """One supervisor decision on one work order."""

    __tablename__ = "review_decision"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False
    )
    response_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("form_response.id", ondelete="SET NULL")
    )

    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reviewer_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    #: Set when the reviewer's own decision was recorded before the agent report was shown,
    #: for the anchoring-bias sample (RF-111a). Null when no agent report existed.
    blind_sample: Mapped[bool | None] = mapped_column()

    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    observations: Mapped[list[FieldObservation]] = relationship(
        back_populates="decision_row", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_review_decision_unit", "business_unit_id", "decided_at"),
        Index("ix_review_decision_work_order", "work_order_id"),
    )


class FieldObservation(Base):
    """An observation attached to one field (RF-112).

    Per field rather than one free-text note on the whole work order, because a technician
    reading "faltan datos" has to guess, and guessing is how a work order gets returned twice.
    """

    __tablename__ = "field_observation"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("review_decision.id", ondelete="CASCADE"), nullable=False
    )
    #: Canonical field key, or an evidence id when the observation is about a photograph.
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    #: What the reviewer believes the value should be, when they know.
    suggested_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    decision_row: Mapped[ReviewDecision] = relationship(back_populates="observations")

    __table_args__ = (Index("ix_field_observation_decision", "decision_id"),)


class BlindReview(Base):
    """One work order drawn for the anchoring-bias sample (RF-111a).

    A row per draw, written when the report is stored and closed when the supervisor decides. Stored
    rather than recomputed from a rate, because the rate is configurable and a metric whose
    denominator changes when somebody edits a setting is a metric nobody can defend in a review
    meeting.

    `agent_verdict` is nullable on purpose: an order the agents never rated closes the draw with no
    pair. Counting it as agreement would flatter the agent; counting it as disagreement would
    punish it for a night batch that had not run.
    """

    __tablename__ = "blind_review"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False
    )
    #: The rate in force when this order was drawn, so a changed setting does not rewrite history.
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    drawn_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    #: When the supervisor's own decision released the report. Null while it is still withheld.
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: 'sin_problema' or 'con_problema' — two categories, because a button and a risk level are not
    #: the same scale.
    supervisor_verdict: Mapped[str | None] = mapped_column(String(16))
    agent_verdict: Mapped[str | None] = mapped_column(String(16))

    __table_args__ = (
        # One draw per work order: a re-run of the pre-review must not give it a second chance at
        # being measured, nor release a report that was meant to be withheld.
        UniqueConstraint("work_order_id", name="uq_blind_review_work_order"),
        Index("ix_blind_review_unit", "business_unit_id", "revealed_at"),
    )
