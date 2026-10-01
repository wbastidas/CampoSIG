"""Agencia y contratista, para que el ambito de RF-002 tenga donde apoyarse.

RF-002 pide ambito por area, zona, agencia y contratista. Area ya resuelve contra el catalogo de
formularios (`forms.catalog.codes_for_area`) y zona ya existe en `work_order.zone`; faltaban las
columnas para las otras dos: `agency` en `crew` y `work_order` (texto libre, igual que `zone`), y
`contractor` en `crew` (null para una cuadrilla propia).

Revision ID: 0029
Revises: 0028
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("crew", sa.Column("agency", sa.String(length=64)))
    op.add_column("crew", sa.Column("contractor", sa.String(length=64)))
    op.add_column("work_order", sa.Column("agency", sa.String(length=64)))


def downgrade() -> None:
    op.drop_column("work_order", "agency")
    op.drop_column("crew", "contractor")
    op.drop_column("crew", "agency")
