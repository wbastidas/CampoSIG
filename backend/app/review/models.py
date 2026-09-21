"""Supervisor review and its outcome (M11: RF-110 to RF-115)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
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
