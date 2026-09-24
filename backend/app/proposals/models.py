"""AI-proposed work orders (RF-013, RF-114).

A proposal is **not** a work order. RF-013 says «al aprobarla pasa a Planificada; al rechazarla
guarda el motivo», and both halves argue for a separate table:

* A rejected proposal must not be a work order that was never work. Creating one in `borrador` and
  cancelling it would leave the boards, the audit trail and the dashboards counting work that never
  existed — and the counts of RF-130 are the ones a unit reports upwards.
* A proposal carries things a work order does not: the findings that produced it, the model that saw
  them, and the arithmetic of Annex C. A work order carries none of that, and it should not: it is
  the record of work, not of a suggestion.

Every AI value here arrives with its origin, the model version and the confidence (rule 8), and
nothing leaves this table for the work-order tables without a person's decision (RF-013, RF-114).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
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
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base
from app.workorders.models import STORAGE_SRID


class ProposalState(StrEnum):
    """The four states RF-114's tray has actions for."""

    OPEN = "propuesta"
    #: A work order was created from it. `work_order_id` says which.
    APPROVED = "aprobada"
    #: Its findings were attached to a work order that already existed.
    MERGED = "fusionada"
    #: Refused with a catalogued reason, which is a training label (RF-114).
    REJECTED = "rechazada"


class ProposalOrigin(StrEnum):
    """Where the finding came from. Kept apart because their error modes differ: a technician's
    finding is wrong about the world, a detection is wrong about the photograph."""

    FIELD_FINDING = "hallazgo_campo"
    VISION = "deteccion_visual"


class WorkOrderProposal(Base):
    """One suggested work order, waiting for a supervisor."""

    __tablename__ = "work_order_proposal"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )

    #: The work order whose capture produced the finding. Not the one it becomes: that is
    #: `work_order_id`, set on approval.
    source_work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="SET NULL")
    )

    origin: Mapped[str] = mapped_column(String(24), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default=ProposalState.OPEN)

    asset_code: Mapped[str | None] = mapped_column(String(128))
    asset_type_key: Mapped[str | None] = mapped_column(String(64))
    feeder_code: Mapped[str | None] = mapped_column(String(32))
    zone: Mapped[str | None] = mapped_column(String(64))
    location: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=STORAGE_SRID, spatial_index=False)
    )

    #: The defect that justifies the work. One proposal per asset and defect, so the tray does not
    #: fill with one row per photograph of the same broken crossarm.
    defect_code: Mapped[str] = mapped_column(String(64), nullable=False)
    work_type: Mapped[str] = mapped_column(String(32), nullable=False)
    form_code: Mapped[str | None] = mapped_column(String(16))

    #: The computed priority and the whole arithmetic behind it (Annex C), including what the
    #: computation could not know. Stored rather than recomputed on read: the catalogues move, and a
    #: supervisor looking at a decision from March has to see the numbers of March.
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    criticality: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    #: The annex's «plazo sugerido», in hours, or null for P4 — which is «plan de mantenimiento» and
    #: not a deadline.
    suggested_deadline_hours: Mapped[int | None] = mapped_column(Integer)

    #: Why this work is proposed, in words a supervisor reads. Assembled from the findings.
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    #: The findings behind it, as they were when the proposal was made.
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    #: Evidence ids, so the tray can show the photographs without reopening the capture.
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    #: Rule 8: every AI value with its origin, model version and confidence. Null for a proposal
    #: raised from a technician's own finding, which is a person's observation and not a model's.
    model_name: Mapped[str | None] = mapped_column(String(64))
    model_version: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column(Float)

    #: Set when approved: the work order this became.
    work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="SET NULL")
    )
    #: Set when merged: the work order its findings were attached to.
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="SET NULL")
    )

    #: The catalogued reason (RF-114). A code and not free text, because «el motivo de rechazo se
    #: usa como señal negativa en el entrenamiento» and free text cannot be a label.
    reject_reason_code: Mapped[str | None] = mapped_column(String(64))
    reject_note: Mapped[str | None] = mapped_column(Text)

    decided_by: Mapped[str | None] = mapped_column(String(255))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        #: One open proposal per asset and defect. The partial index is what stops the tray from
        #: filling with a row per inspection of the same broken crossarm, while still allowing a
        #: new proposal after one was rejected — a defect somebody dismissed can come back.
        Index(
            "uq_proposal_open_per_asset_defect",
            "business_unit_id",
            "asset_code",
            "defect_code",
            unique=True,
            postgresql_where="state = 'propuesta'",
        ),
        Index("ix_proposal_tray", "business_unit_id", "state"),
        UniqueConstraint("work_order_id", name="uq_proposal_work_order"),
    )

    @property
    def is_open(self) -> bool:
        return self.state == ProposalState.OPEN
