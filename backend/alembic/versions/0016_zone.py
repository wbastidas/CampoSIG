"""Zonas como poligonos (RF-152).

Hasta aqui una zona era una cadena: `work_order.zone` y `crew.zone` guardan texto. Esta migracion
no la cambia. Anade una tabla cuya identidad es **ese mismo codigo** y que le cuelga el poligono,
de modo que una unidad que todavia no dibujo sus zonas sigue funcionando igual que ayer y nada hay
que migrar el dia que los poligonos llegan.

MULTIPOLYGON y no POLYGON porque las zonas de operacion reales no siempre son conexas: una isla,
una parroquia separada, un area partida por un rio que es de otro. Exigir POLYGON obligaria a
partir en dos una zona que la operacion trata como una.

El indice GiST es lo que vuelve «en que zona cae este punto» una busqueda y no un recorrido por
todos los poligonos de la unidad. Se declara aqui y no en el modelo con `spatial_index=True`
porque asi lo hace el resto del esquema: los indices espaciales viven en la migracion, donde se
pueden nombrar.

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "zone",
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
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "geom",
            Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("origin", sa.String(16), nullable=False, server_default="dibujada"),
        sa.Column("imported_from", postgresql.JSONB()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", sa.String(255)),
        sa.Column("created_by", sa.String(255)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("business_unit_id", "code", name="uq_zone_code_per_unit"),
    )
    op.create_index("ix_zone_unit_active", "zone", ["business_unit_id", "active"])
    op.create_index("ix_zone_geom", "zone", ["geom"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_zone_geom", table_name="zone")
    op.drop_index("ix_zone_unit_active", table_name="zone")
    op.drop_table("zone")
