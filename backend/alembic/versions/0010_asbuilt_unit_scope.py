"""Acotar la tabla de staging as-built a la unidad de negocio.

ADR-009. Sin esta columna, `create_batch` agrupaba toda propuesta aprobada de un tipo de activo
sin importar de qué unidad era, y la despachaba al agente de la unidad que pidió el lote: los
datos de campo de una unidad escritos en la geodatabase de otra. No es una fuga de lectura, es
una escritura cruzada, que es peor.

La columna se añade nullable, se rellena, y solo entonces se hace obligatoria — el orden que
permite aplicar esto sobre una base que ya tiene propuestas.

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "asbuilt_proposal",
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Las propuestas existentes se atribuyen por su OT, que sí está acotada. Una propuesta
    # huérfana —sin OT que la explique— no se adivina: se deja nula y la restricción de abajo
    # falla, que es la señal correcta para revisarla a mano antes de migrar.
    op.execute(
        """
        UPDATE asbuilt_proposal AS p
        SET business_unit_id = w.business_unit_id
        FROM work_order AS w
        WHERE p.work_order_ref = w.id::text
        """
    )
    op.alter_column("asbuilt_proposal", "business_unit_id", nullable=False)
    op.create_index(
        "ix_asbuilt_unit_status",
        "asbuilt_proposal",
        ["business_unit_id", "status", "asset_type_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_asbuilt_unit_status", table_name="asbuilt_proposal")
    op.drop_column("asbuilt_proposal", "business_unit_id")
