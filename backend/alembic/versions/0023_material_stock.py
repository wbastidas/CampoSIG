"""Existencias de material por bodega o vehiculo (RF-122).

Una **instantanea**, no un libro mayor: el ERP es el sistema de registro del inventario y esta tabla
guarda lo que el ERP dijo la ultima vez. De ahi la unicidad por unidad, tipo de ubicacion, ubicacion
y material: cada lote reemplaza las lineas de su ubicacion en vez de sumarlas, porque una linea que
desaparecio significa que el material se acabo y dejarla tendria a alguien planificando contra algo
que no esta.

`material_code` no es clave ajena a `catalog_entry` a proposito: el lote de existencias y el del
catalogo llegan por separado y cualquiera puede ser primero, y una restriccion entre los dos
rechazaria datos buenos por llegar en el orden equivocado. Lo que el adaptador hace en su lugar es
reportar los codigos con existencia que el catalogo no conoce.

`as_of` es del ERP y se muestra junto al numero: una existencia de un lote nocturno tiene horas, y
un numero presentado como actual cuando tiene doce horas es como una cuadrilla maneja hasta una
bodega por algo que ya no esta.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "material_stock",
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
        sa.Column("material_code", sa.String(64), nullable=False),
        sa.Column("location_kind", sa.String(16), nullable=False),
        sa.Column("location_code", sa.String(64), nullable=False),
        sa.Column("location_name", sa.String(255)),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(16)),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "business_unit_id",
            "location_kind",
            "location_code",
            "material_code",
            name="uq_material_stock_line",
        ),
    )
    op.create_index(
        "ix_material_stock_location",
        "material_stock",
        ["business_unit_id", "location_kind", "location_code"],
    )
    op.create_index(
        "ix_material_stock_material", "material_stock", ["business_unit_id", "material_code"]
    )


def downgrade() -> None:
    op.drop_index("ix_material_stock_material", table_name="material_stock")
    op.drop_index("ix_material_stock_location", table_name="material_stock")
    op.drop_table("material_stock")
