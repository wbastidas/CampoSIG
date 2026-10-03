"""Devices, the sync ledger and offline packages.

RF-004 (enrolment, remote block and wipe), RF-101 (idempotent push), RF-102 (delta pull),
RF-360 (per-zone offline packages).

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device",
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
        sa.Column("device_key", sa.String(128), nullable=False, unique=True),
        sa.Column("user_sub", sa.String(255), nullable=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("android_version", sa.String(32), nullable=True),
        sa.Column("app_version", sa.String(32), nullable=True),
        sa.Column("model_package_version", sa.String(32), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="activo"),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_reason", sa.String(500), nullable=True),
        sa.Column("wipe_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('activo', 'bloqueado', 'retirado')", name="ck_device_status"
        ),
    )
    op.create_index("ix_device_unit_status", "device", ["business_unit_id", "status"])
    op.create_index("ix_device_user", "device", ["user_sub"])

    op.create_table(
        "sync_operation_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("device.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("operation_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("accepted", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("result", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Device clock kept separately: field devices work offline and their clocks drift.
        sa.Column("device_created_at", sa.DateTime(timezone=True), nullable=True),
        # The idempotency guarantee, enforced by the database rather than by application luck.
        sa.UniqueConstraint("device_id", "operation_id", name="uq_sync_operation_identity"),
    )
    op.create_index("ix_sync_operation_work_order", "sync_operation_log", ["work_order_id"])

    op.create_table(
        "offline_package",
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
        sa.Column("zone", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("manifest", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "built_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "business_unit_id", "zone", "version", name="uq_offline_package_version"
        ),
    )
    op.create_index(
        "ix_offline_package_current",
        "offline_package",
        ["business_unit_id", "zone"],
        postgresql_where=sa.text("superseded_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("offline_package")
    op.drop_table("sync_operation_log")
    op.drop_table("device")
