"""Baseline schema: extensions, audit log and the as-built staging table.

RF-342 (as-built proposals with idempotency), RNF audit trail (SRS M16).

Deliberately small: I0 only lays the foundations that later increments build on.
Work orders, forms and assignments arrive in I3 and I5.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # --- Audit trail (SRS M16) -------------------------------------------------
    op.create_table(
        "audit_event",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor_sub", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        # Device time and server time are recorded separately on purpose: field devices
        # work offline and their clocks drift (SRS 3.3).
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_audit_event_entity", "audit_event", ["entity_type", "entity_id"])
    op.create_index("ix_audit_event_recorded_at", "audit_event", ["recorded_at"])

    # --- As-built staging (RF-342, ADR-001, ADR-008) ---------------------------
    op.create_table(
        "asbuilt_proposal",
        # proposal_id comes from the mobile device and is the idempotency key: the
        # agent may replay a batch without duplicating anything (RF-353).
        sa.Column("proposal_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_type_key", sa.String(64), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        # Null for new elements; carries the geodatabase GLOBALID otherwise.
        sa.Column("gis_global_id", sa.String(64), nullable=True),
        sa.Column("work_order_ref", sa.String(64), nullable=True),
        # Canonical attribute keys (AMD), never real field names — ADR-004.
        sa.Column("attributes", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("geometry", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("requires_arcfm", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("apply_result", postgresql.JSONB, nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("action IN ('create', 'update', 'retire')", name="ck_asbuilt_action"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'dispatched', 'applied', 'rejected', 'error')",
            name="ck_asbuilt_status",
        ),
    )
    op.create_index("ix_asbuilt_status", "asbuilt_proposal", ["status"])
    op.create_index("ix_asbuilt_batch", "asbuilt_proposal", ["batch_id"])
    # GIN index so attribute lookups inside JSONB stay usable as the table grows.
    op.create_index(
        "ix_asbuilt_attributes",
        "asbuilt_proposal",
        ["attributes"],
        postgresql_using="gin",
    )

    # PostGIS geometry column for the network cache, proving the extension works
    # end to end in I0 rather than at the first spatial query in I4.
    op.create_table(
        "network_asset_cache",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("asset_type_key", sa.String(64), nullable=False),
        sa.Column("gis_global_id", sa.String(64), nullable=False),
        sa.Column("business_key", sa.String(128), nullable=True),
        sa.Column("attributes", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "gis_modified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Source modification timestamp; drives incremental extraction (RF-352)",
        ),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("asset_type_key", "gis_global_id", name="uq_network_asset_identity"),
    )
    # SRID 32717 = UTM 17S WGS84, the geodatabase's spatial reference.
    op.execute(
        "SELECT AddGeometryColumn('public', 'network_asset_cache', 'geom', 32717, 'GEOMETRY', 2)"
    )
    op.create_index(
        "ix_network_asset_geom", "network_asset_cache", ["geom"], postgresql_using="gist"
    )


def downgrade() -> None:
    op.drop_table("network_asset_cache")
    op.drop_table("asbuilt_proposal")
    op.drop_table("audit_event")
