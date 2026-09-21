"""Delivery of work orders to devices: what the crew actually holds.

RF-104 (offline package and delivery), RF-324 (custody), RF-360.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_order_delivery",
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
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("device.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("delivered_version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("form_version", sa.String(16), nullable=True),
        sa.Column(
            "first_delivered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_delivered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("delivery_count", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.UniqueConstraint("work_order_id", "device_id", name="uq_delivery_order_device"),
    )
    op.create_index("ix_delivery_unit", "work_order_delivery", ["business_unit_id"])
    op.create_index("ix_delivery_device", "work_order_delivery", ["device_id"])


def downgrade() -> None:
    op.drop_table("work_order_delivery")
