"""Muestra ciega para medir la concordancia supervisor-agente (RF-111a).

Una fila por sorteo, escrita cuando se guarda el informe y cerrada cuando el supervisor decide. Se
guarda el sorteo en vez de recalcularlo desde un porcentaje: la tasa es configurable, y una metrica
cuyo denominador cambia cuando alguien edita un ajuste no se puede defender en una reunion.

`agent_verdict` admite nulo a proposito. Una OT que los agentes nunca calificaron cierra el sorteo
sin par: contarla como concordancia halagaria al agente, y contarla como discrepancia lo castigaria
por un lote nocturno que no habia corrido.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blind_review",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
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
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column(
            "drawn_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("revealed_at", sa.DateTime(timezone=True)),
        sa.Column("supervisor_verdict", sa.String(16)),
        sa.Column("agent_verdict", sa.String(16)),
        # Un solo sorteo por OT: una nueva ejecucion de la pre-revision no puede darle otra
        # oportunidad de ser medida, ni liberar un informe que estaba retenido.
        sa.UniqueConstraint("work_order_id", name="uq_blind_review_work_order"),
    )
    op.create_index("ix_blind_review_unit", "blind_review", ["business_unit_id", "revealed_at"])


def downgrade() -> None:
    op.drop_index("ix_blind_review_unit", table_name="blind_review")
    op.drop_table("blind_review")
