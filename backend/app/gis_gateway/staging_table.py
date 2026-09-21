"""The as-built staging table, defined as Core rather than as a mapped class.

`asbuilt_proposal` is a queue between two processes — the platform writes approved proposals,
the arcpy agent drains them — not a domain entity. Giving it a mapped class would invite code
to treat it as one, load it into sessions and attach behaviour to it.

It still lives in ``Base.metadata`` so that ``create_all`` builds it and the schema-parity
guard sees it. Mirrors migration 0001 exactly; the parity test is what keeps them in step.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.infra.database import Base

asbuilt_proposal = Table(
    "asbuilt_proposal",
    Base.metadata,
    # Generated on the device; the idempotency key that stops a replay from creating a second
    # pole in the geodatabase (RF-353).
    Column("proposal_id", UUID(as_uuid=True), primary_key=True),
    Column("asset_type_key", String(64), nullable=False),
    Column("action", String(16), nullable=False),
    # Null for new elements; carries the geodatabase GLOBALID otherwise.
    Column("gis_global_id", String(64), nullable=True),
    Column("work_order_ref", String(64), nullable=True),
    # Canonical attribute keys (AMD), never real field names — ADR-004.
    Column("attributes", JSONB, nullable=False, server_default=text("'{}'")),
    Column("geometry", Text(), nullable=True),
    Column("status", String(24), nullable=False, server_default="pending"),
    Column("requires_arcfm", Boolean(), nullable=False, server_default=text("false")),
    Column("apply_result", JSONB, nullable=True),
    Column("batch_id", UUID(as_uuid=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    CheckConstraint("action IN ('create', 'update', 'retire')", name="ck_asbuilt_action"),
    CheckConstraint(
        "status IN ('pending', 'approved', 'dispatched', 'applied', 'rejected', 'error')",
        name="ck_asbuilt_status",
    ),
    Index("ix_asbuilt_status", "status"),
    Index("ix_asbuilt_batch", "batch_id"),
    Index("ix_asbuilt_attributes", "attributes", postgresql_using="gin"),
)
