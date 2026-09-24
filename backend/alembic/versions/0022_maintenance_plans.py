"""Planes de mantenimiento preventivo (RF-012).

El criterio de aceptacion es un conteo —«un plan mensual genera N OT en la fecha programada»— y de
ahi sale la forma de estas tres tablas.

`plan_issue` es la mas importante y la menos obvia: guarda **una fila por plan, activo y periodo**,
tanto si se emitio la OT como si no, con el motivo. Dos indices unicos parciales y no uno, porque
PostgreSQL trata los NULL como distintos: un plan que emite una sola OT para todo el alcance tiene
`asset_code` nulo, y con un solo indice podria emitir el mismo periodo dos veces, que es exactamente
lo que esta tabla existe para impedir.

El periodo es una etiqueta (`2026-09`, `2026-T3`) y no una marca de tiempo. Dos corridas el 3 y el
27 de septiembre son el mismo periodo y la segunda no emite nada; una comparacion contra la fecha
de la ultima corrida habria hecho legal la segunda.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "maintenance_plan",
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
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("work_type", sa.String(32), nullable=False),
        sa.Column("form_code", sa.String(16), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("asset_type_key", sa.String(64)),
        sa.Column("cadence", sa.String(16), nullable=False),
        sa.Column("cadence_days", sa.Integer()),
        sa.Column("day_of_month", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("scope_value", sa.String(64)),
        sa.Column("skip_if_attended_within_days", sa.Integer()),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(255)),
        sa.Column("updated_by", sa.String(255)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("business_unit_id", "code", name="uq_maintenance_plan_code"),
    )
    op.create_index(
        "ix_maintenance_plan_active", "maintenance_plan", ["business_unit_id", "active"]
    )

    op.create_table(
        "plan_target",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("maintenance_plan.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset_code", sa.String(128), nullable=False),
        sa.Column("asset_type_key", sa.String(64)),
        sa.Column("feeder_code", sa.String(32)),
        sa.Column("zone", sa.String(64)),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("plan_id", "asset_code", name="uq_plan_target_asset"),
    )
    op.create_index("ix_plan_target_order", "plan_target", ["plan_id", "sort_order"])

    op.create_table(
        "plan_issue",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("maintenance_plan.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period", sa.String(16), nullable=False),
        sa.Column("asset_code", sa.String(128)),
        sa.Column("outcome", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="SET NULL"),
        ),
        sa.Column("caveats", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "uq_plan_issue_asset_period",
        "plan_issue",
        ["plan_id", "asset_code", "period"],
        unique=True,
        postgresql_where=sa.text("asset_code IS NOT NULL"),
    )
    op.create_index(
        "uq_plan_issue_scope_period",
        "plan_issue",
        ["plan_id", "period"],
        unique=True,
        postgresql_where=sa.text("asset_code IS NULL"),
    )
    op.create_index("ix_plan_issue_history", "plan_issue", ["plan_id", "period"])


def downgrade() -> None:
    op.drop_index("ix_plan_issue_history", table_name="plan_issue")
    op.drop_index("uq_plan_issue_scope_period", table_name="plan_issue")
    op.drop_index("uq_plan_issue_asset_period", table_name="plan_issue")
    op.drop_table("plan_issue")
    op.drop_index("ix_plan_target_order", table_name="plan_target")
    op.drop_table("plan_target")
    op.drop_index("ix_maintenance_plan_active", table_name="maintenance_plan")
    op.drop_table("maintenance_plan")
