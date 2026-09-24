"""Politica de captura por area (RF-151).

Todas las columnas son anulables y un nulo significa **sin opinion**. Una zona que solo difiere de
su unidad en que no sube por datos moviles declara eso y nada mas; si tuviera que repetir los otros
nueve valores, el dia que la unidad cambie uno la zona se quedaria callada con el viejo. Esa es la
falla que esta forma vuelve imposible.

Dos niveles: la unidad (la fila con `zone_code` nulo) y la zona. El indice unico parcial es lo que
garantiza que haya **una sola** fila de unidad: PostgreSQL considera los nulos distintos entre si,
asi que la restriccion unica sobre (unidad, zona) no alcanza para eso.

No hay indice adicional por unidad: la tabla tiene una fila por unidad y una por zona configurada,
y el indice unico ya sirve para la busqueda.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "capture_policy",
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
        sa.Column("zone_code", sa.String(64)),
        sa.Column("store_audio", sa.Boolean()),
        sa.Column("require_audio_consent", sa.Boolean()),
        sa.Column("audio_retention_days", sa.Integer()),
        sa.Column("min_photos", sa.Integer()),
        sa.Column("photo_max_edge_px", sa.Integer()),
        sa.Column("photo_quality", sa.Integer()),
        sa.Column("evidence_retention_days", sa.Integer()),
        sa.Column("upload_on_metered", sa.Boolean()),
        sa.Column("metered_upload_limit_mb", sa.Integer()),
        sa.Column("downscale_on_metered", sa.Boolean()),
        sa.Column("note", sa.Text()),
        sa.Column("updated_by", sa.String(255)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("business_unit_id", "zone_code", name="uq_capture_policy_scope"),
    )
    op.create_index(
        "uq_capture_policy_unit_row",
        "capture_policy",
        ["business_unit_id"],
        unique=True,
        postgresql_where=sa.text("zone_code IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_capture_policy_unit_row", table_name="capture_policy")
    op.drop_table("capture_policy")
