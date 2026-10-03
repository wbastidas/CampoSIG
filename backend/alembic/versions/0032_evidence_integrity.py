"""Metadatos, origen, marca de agua e integridad de la evidencia (RF-071 a RF-074).

Revision ID: 0032
Revises: 0031
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("altitude_m", sa.Float()))
    op.add_column("evidence", sa.Column("heading_deg", sa.Float()))
    op.add_column("evidence", sa.Column("captured_by", sa.String(255)))
    op.add_column("evidence", sa.Column("device_model", sa.String(128)))
    op.add_column("evidence", sa.Column("source", sa.String(16)))
    op.add_column("evidence", sa.Column("watermarked_storage_key", sa.String(512)))
    op.add_column(
        "evidence",
        sa.Column("integrity_status", sa.String(16), nullable=False, server_default="pendiente"),
    )
    # Lo ya verificado no vuelve a «pendiente».
    op.execute("UPDATE evidence SET integrity_status = 'verificada' WHERE integrity_verified")


def downgrade() -> None:
    for column in (
        "integrity_status",
        "watermarked_storage_key",
        "source",
        "device_model",
        "captured_by",
        "heading_deg",
        "altitude_m",
    ):
        op.drop_column("evidence", column)
