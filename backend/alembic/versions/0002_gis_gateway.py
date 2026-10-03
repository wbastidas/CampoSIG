"""GIS gateway: metadata snapshots and as-built batch results.

RF-349 (metadata export), RF-343/RF-344 (batches), RF-353 (result per proposal).

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gis_metadata_snapshot",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("profile_id", sa.String(64), nullable=False),
        sa.Column("agent_version", sa.String(32), nullable=True),
        sa.Column("contract_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("domain_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("layer_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("relationship_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("problems", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Null while current. Snapshots are superseded, never deleted, so a generated
        # form stays traceable to the metadata it came from.
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_metadata_snapshot_profile", "gis_metadata_snapshot", ["profile_id"])
    # Partial index: looking up the current snapshot happens on every form generation.
    op.create_index(
        "ix_metadata_snapshot_current",
        "gis_metadata_snapshot",
        ["profile_id"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )

    op.create_table(
        "asbuilt_batch",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("profile_id", sa.String(64), nullable=False),
        sa.Column("asset_type_key", sa.String(64), nullable=False),
        sa.Column("zone", sa.String(64), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="ready"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by", sa.String(128), nullable=True),
        sa.CheckConstraint(
            "status IN ('ready', 'dispatched', 'completed', 'failed')",
            name="ck_asbuilt_batch_status",
        ),
    )
    op.create_index("ix_asbuilt_batch_status", "asbuilt_batch", ["status"])

    op.create_table(
        "asbuilt_proposal_result",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asbuilt_batch.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proposal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("message", sa.String(2000), nullable=True),
        sa.Column(
            "reported_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # The agent may retry a batch; a retry must update the outcome, not duplicate it.
        sa.UniqueConstraint("batch_id", "proposal_id", name="uq_proposal_result_identity"),
        sa.CheckConstraint(
            "status IN ('applied', 'rejected', 'error', 'requires_arcfm')",
            name="ck_proposal_result_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("asbuilt_proposal_result")
    op.drop_table("asbuilt_batch")
    op.drop_table("gis_metadata_snapshot")
