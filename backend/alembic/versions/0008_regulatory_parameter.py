"""Regulatory parameters with period of force and reference to the norm.

SRS 1.4 (values are parameterised, never coded), ADR-007 (no RAG in v1), RF-350, RF-351.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "regulatory_parameter",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("value", postgresql.JSONB, nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("norm_ref", sa.String(255), nullable=False),
        sa.Column("article_ref", sa.String(64), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("verified_by", sa.String(255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        # text("false"), never func.false(): the latter renders the invalid SQL `false()`.
        sa.Column("strict", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("code", "effective_from", name="uq_regulatory_code_from"),
    )
    op.create_index("ix_regulatory_code", "regulatory_parameter", ["code"])
    op.create_index(
        "ix_regulatory_in_force",
        "regulatory_parameter",
        ["code", "effective_from", "effective_to"],
    )


def downgrade() -> None:
    op.drop_table("regulatory_parameter")
