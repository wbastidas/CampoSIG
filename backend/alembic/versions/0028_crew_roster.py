"""La cuadrilla gana integrantes y quien la edito (RF-005).

El modelo ya tenia jefe (`leader_name`, texto libre), vehiculo, competencias y zona; le faltaba la
lista de integrantes que el requerimiento pide y el rastro de quien creo o edito el registro, que es
lo que responde «historial de cambios» junto con la bitacora (RF-160) que `crews.py` ya escribe en
cada alta o cambio.

Revision ID: 0028
Revises: 0027
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crew",
        sa.Column("members", sa.ARRAY(sa.String(length=255)), nullable=False, server_default="{}"),
    )
    op.add_column("crew", sa.Column("created_by", sa.String(length=255)))
    op.add_column("crew", sa.Column("updated_by", sa.String(length=255)))
    op.add_column(
        "crew",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.add_column(
        "crew",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_column("crew", "updated_at")
    op.drop_column("crew", "created_at")
    op.drop_column("crew", "updated_by")
    op.drop_column("crew", "created_by")
    op.drop_column("crew", "members")
