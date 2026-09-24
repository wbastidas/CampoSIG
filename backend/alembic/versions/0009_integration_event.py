"""The integration ledger: every exchange with a corporate system.

RF-120 (work-order platform), RF-124 (call centre), RF-125 (consultable log with retry).

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_event",
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
        sa.Column("connector", sa.String(32), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pendiente"),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("response", postgresql.JSONB, nullable=True),
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_ref", sa.String(64), nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "connector", "direction", "idempotency_key", name="uq_integration_identity"
        ),
    )
    op.create_index(
        "ix_integration_unit_status", "integration_event", ["business_unit_id", "status"]
    )
    op.create_index("ix_integration_due", "integration_event", ["status", "next_attempt_at"])
    op.create_index("ix_integration_order", "integration_event", ["work_order_id"])


def downgrade() -> None:
    op.drop_table("integration_event")
