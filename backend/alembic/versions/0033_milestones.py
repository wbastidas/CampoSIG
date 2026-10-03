"""Hitos de tiempo de la OT con corrección justificada (RF-047).

Revision ID: 0033
Revises: 0032
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_order_milestone",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
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
        sa.Column("milestone", sa.String(16), nullable=False),
        sa.Column("device_time", sa.DateTime(timezone=True)),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("recorded_by", sa.String(255)),
        sa.Column("corrected_time", sa.DateTime(timezone=True)),
        sa.Column("correction_reason", sa.String(500)),
        sa.Column("corrected_by", sa.String(255)),
        sa.Column("corrected_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("work_order_id", "milestone", name="uq_work_order_milestone"),
    )
    op.create_index("ix_work_order_milestone_unit", "work_order_milestone", ["business_unit_id"])


def downgrade() -> None:
    op.drop_index("ix_work_order_milestone_unit", table_name="work_order_milestone")
    op.drop_table("work_order_milestone")
