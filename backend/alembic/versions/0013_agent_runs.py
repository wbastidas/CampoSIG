"""Ejecuciones, informes y trazas de la pre-revisión (RF-170, RF-175, RF-180).

Tres tablas porque RF-180 pide que se puedan responder tres preguntas distintas: si una OT recibió
pre-revisión y cómo terminó, qué dice el informe que el supervisor leyó, y qué hizo cada nodo —
incluido el que no corrió y por qué. Lo último es lo que convierte «¿por qué no hay sección visual?»
en algo con respuesta en el registro en vez de en la memoria de alguien sobre el despliegue.

El informe se guarda entero, con la forma del Anexo D, y no normalizado en filas de observación: es
un artefacto que una persona leyó en una fecha, y repartirlo en tablas dejaría al esquema como
fuente de verdad sin forma de reconstruir lo que alguien vio.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("graph_version", sa.String(length=32), nullable=False),
        sa.Column("hardware_profile", sa.String(length=8), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False),
        sa.Column("compute_seconds", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_unit.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_run_order", "agent_run", ["work_order_id"])
    op.create_index("ix_agent_run_pending", "agent_run", ["business_unit_id", "state"])

    op.create_table(
        "agent_report",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_level", sa.String(length=8), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("document", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("discarded", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_run.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Un informe por ejecución: con dos, nadie puede decir cuál leyó el supervisor.
        sa.UniqueConstraint("agent_run_id", name="uq_agent_report_run"),
    )

    op.create_table(
        "agent_step_trace",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node", sa.String(length=48), nullable=False),
        sa.Column("model_alias", sa.String(length=32), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("skipped_reason", sa.Text(), nullable=True),
        sa.Column("tools", postgresql.ARRAY(sa.String(length=64)), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_run.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_step_trace_run", "agent_step_trace", ["agent_run_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_step_trace_run", table_name="agent_step_trace")
    op.drop_table("agent_step_trace")
    op.drop_table("agent_report")
    op.drop_index("ix_agent_run_pending", table_name="agent_run")
    op.drop_index("ix_agent_run_order", table_name="agent_run")
    op.drop_table("agent_run")
