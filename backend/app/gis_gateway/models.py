"""Persistence for what the arcpy agent uploads (RF-349, RF-353).

The backend never touches ArcSDE (ADR-006, ADR-008); everything it knows about the
geodatabase arrives through this gateway and is stored here. Snapshots are versioned
rather than overwritten so a form generated last month can be explained: the metadata it
was derived from is still on record.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Importado por su efecto: `asbuilt_proposal` es una tabla Core en un módulo que no se llama
# `models.py`, así que `import_all_models()` —que descubre por nombre de módulo— no la
# alcanzaba. El resultado era un `create_all` que construía el esquema sin la tabla de staging
# salvo que algún otro import la arrastrara por casualidad; es decir, un fallo que dependía del
# orden de los tests. Importarla aquí la pone en `Base.metadata` siempre que el gateway se
# cargue, que es siempre.
from app.gis_gateway.staging_table import asbuilt_proposal as _asbuilt_proposal  # noqa: F401
from app.infra.database import Base


class MetadataSnapshot(Base):
    """One metadata export from the agent.

    Kept append-only: superseding a snapshot marks the previous one stale instead of
    deleting it, because a generated form must remain traceable to its source.
    """

    __tablename__ = "gis_metadata_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    #: Snapshots are keyed by business unit, not by profile. Units normally share one
    #: profile because the schema is national, but each has its own domain contents:
    #: its own feeder and substation codes. Keying by profile would let one unit's
    #: catalogues overwrite another's.
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_version: Mapped[str | None] = mapped_column(String(32))
    contract_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    #: The whole GisMetadata payload, validated before storage.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    #: Counts, so the admin screen need not parse the payload to show a summary.
    domain_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    layer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relationship_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    #: Completeness diagnostic at ingest time (RF-302).
    problems: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    #: Null while current; set when a newer snapshot for the same profile arrives.
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_metadata_snapshot_unit", "business_unit_id"),
        # Partial index: the "current snapshot" lookup happens on every form generation.
        Index(
            "ix_metadata_snapshot_current",
            "business_unit_id",
            postgresql_where="superseded_at IS NULL",
        ),
    )

    @property
    def is_current(self) -> bool:
        return self.superseded_at is None


class AsBuiltBatch(Base):
    """A batch of approved as-built proposals handed to the agent (RF-343, RF-344)."""

    __tablename__ = "asbuilt_batch"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    #: The unit whose geodatabase this batch is destined for. An agent only ever
    #: receives and reports on batches of its own unit, which is a routing rule and a
    #: security boundary at once (ADR-009).
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_type_key: Mapped[str] = mapped_column(String(64), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(64))

    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ready")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: Which agent took it, so a stuck batch can be traced to a machine.
    claimed_by: Mapped[str | None] = mapped_column(String(128))

    results: Mapped[list[ProposalResult]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_asbuilt_batch_status", "status"),
        # An agent polls for its own unit's ready batches; this is that query.
        Index("ix_asbuilt_batch_unit_status", "business_unit_id", "status"),
    )


class ProposalResult(Base):
    """What the agent reported back for one proposal (RF-353).

    Unique on (batch, proposal) so replaying a batch reports idempotently rather than
    accumulating duplicate rows — the agent is explicitly allowed to retry.
    """

    __tablename__ = "asbuilt_proposal_result"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asbuilt_batch.id", ondelete="CASCADE"), nullable=False
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    message: Mapped[str | None] = mapped_column(String(2000))
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    batch: Mapped[AsBuiltBatch] = relationship(back_populates="results")

    __table_args__ = (
        UniqueConstraint("batch_id", "proposal_id", name="uq_proposal_result_identity"),
    )
