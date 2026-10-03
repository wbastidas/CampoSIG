"""Organisational hierarchy and business-unit scoping.

RF-002 (scope), and the multi-tenant routing of ADR-009: one platform, one headquarters,
several business units, each with its own geodatabase and its own arcpy agent.

Also re-keys metadata snapshots and as-built batches from profile to business unit.
Business units normally share one profile because the schema is national; what differs is
each unit's domain contents, so keying by profile would let one unit's catalogues
overwrite another's.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False, server_default="EC"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "business_unit",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organization.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("profile_id", sa.String(64), nullable=False),
        sa.Column("spatial_reference", sa.Integer, nullable=False, server_default="32717"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("organization_id", "code", name="uq_business_unit_code"),
    )
    op.create_index("ix_business_unit_active", "business_unit", ["active"])

    op.create_table(
        "agent_registration",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_unit.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_key", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_agent_registration_unit", "agent_registration", ["business_unit_id"])

    # --- re-key snapshots and batches to the business unit --------------------------
    # No data migration branch: revision 0002 shipped in the same unreleased increment as
    # this one, so no deployment can hold rows here yet. A later re-key would need one.
    op.drop_index("ix_metadata_snapshot_profile", table_name="gis_metadata_snapshot")
    op.drop_index("ix_metadata_snapshot_current", table_name="gis_metadata_snapshot")
    op.add_column(
        "gis_metadata_snapshot",
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_metadata_snapshot_unit",
        "gis_metadata_snapshot",
        "business_unit",
        ["business_unit_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_metadata_snapshot_unit", "gis_metadata_snapshot", ["business_unit_id"])
    op.create_index(
        "ix_metadata_snapshot_current",
        "gis_metadata_snapshot",
        ["business_unit_id"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )

    op.add_column(
        "asbuilt_batch",
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_asbuilt_batch_unit",
        "asbuilt_batch",
        "business_unit",
        ["business_unit_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_asbuilt_batch_unit_status", "asbuilt_batch", ["business_unit_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_asbuilt_batch_unit_status", table_name="asbuilt_batch")
    op.drop_constraint("fk_asbuilt_batch_unit", "asbuilt_batch", type_="foreignkey")
    op.drop_column("asbuilt_batch", "business_unit_id")

    op.drop_index("ix_metadata_snapshot_current", table_name="gis_metadata_snapshot")
    op.drop_index("ix_metadata_snapshot_unit", table_name="gis_metadata_snapshot")
    op.drop_constraint("fk_metadata_snapshot_unit", "gis_metadata_snapshot", type_="foreignkey")
    op.drop_column("gis_metadata_snapshot", "business_unit_id")
    op.create_index("ix_metadata_snapshot_profile", "gis_metadata_snapshot", ["profile_id"])
    op.create_index(
        "ix_metadata_snapshot_current",
        "gis_metadata_snapshot",
        ["profile_id"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )

    op.drop_table("agent_registration")
    op.drop_table("business_unit")
    op.drop_table("organization")
