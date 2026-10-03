"""Reporte de posicion con horario laboral y consentimiento (RF-107).

La politica de captura gana el intervalo de reporte, la jornada (inicio, fin y dias) y si se exige
consentimiento; el dispositivo gana quien consintio y cuando. Columnas nulas: en la politica, nulo
es «sin opinion» y se hereda, igual que el resto de sus campos.

Revision ID: 0031
Revises: 0030
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("capture_policy", sa.Column("position_report_minutes", sa.Integer()))
    op.add_column("capture_policy", sa.Column("workday_start", sa.String(5)))
    op.add_column("capture_policy", sa.Column("workday_end", sa.String(5)))
    op.add_column("capture_policy", sa.Column("workdays", sa.String(16)))
    op.add_column("capture_policy", sa.Column("require_position_consent", sa.Boolean()))
    op.add_column("device", sa.Column("position_consent_sub", sa.String(255)))
    op.add_column("device", sa.Column("position_consent_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("device", "position_consent_at")
    op.drop_column("device", "position_consent_sub")
    op.drop_column("capture_policy", "require_position_consent")
    op.drop_column("capture_policy", "workdays")
    op.drop_column("capture_policy", "workday_end")
    op.drop_column("capture_policy", "workday_start")
    op.drop_column("capture_policy", "position_report_minutes")
