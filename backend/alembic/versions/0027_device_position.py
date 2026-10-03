"""La ultima posicion reportada por cada telefono (RF-020).

La clave primaria es el dispositivo, y eso es todo el diseno de privacidad escrito en el esquema en
vez de en una nota: la plataforma guarda la **ultima** posicion que reporto un telefono y no puede
guardar un historial de por donde anduvo un tecnico, porque no hay donde ponerlo. RF-020 pide la
ubicacion para decidir quien esta mas cerca de una falla; un registro de movimientos contestaria
otra pregunta que nadie hizo.

`reported_at` es el reloj del telefono y `received_at` el del servidor. Viajan los dos porque la
posicion se captura cuando el telefono sincroniza: es tan vieja como el ultimo sync, y una posicion
sin su edad miente.

Revision ID: 0027
Revises: 0026
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device_position",
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("device.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_unit.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "location",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("accuracy_m", sa.Float()),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_device_position_unit", "device_position", ["business_unit_id", "reported_at"]
    )
    op.create_index(
        "ix_device_position_geom", "device_position", ["location"], postgresql_using="gist"
    )


def downgrade() -> None:
    op.drop_index("ix_device_position_geom", table_name="device_position")
    op.drop_index("ix_device_position_unit", table_name="device_position")
    op.drop_table("device_position")
