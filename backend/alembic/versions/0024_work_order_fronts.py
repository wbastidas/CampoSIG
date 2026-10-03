"""OT hijas: una obra con multiples frentes (RF-015).

`parent_id` es autorreferencial y de **un solo nivel**, que el servicio hace cumplir: un frente no
puede tener frentes. «Una obra con multiples frentes» es un arbol de profundidad uno, y permitir
nietos volveria «el avance» una pregunta sobre cual nivel se queria — ademas de abrir la puerta a un
ciclo que nadie nota hasta que una consulta se cuelga.

`ondelete="RESTRICT"` y no CASCADE: borrar una obra no puede llevarse por delante el trabajo de sus
frentes, que es trabajo real con capturas, evidencias y bitacora. La plataforma tampoco borra OT —se
anulan— asi que la restriccion es una segunda linea contra un borrado directo en la base.

Revision ID: 0024
Revises: 0023
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "work_order", sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_work_order_parent",
        "work_order",
        "work_order",
        ["parent_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_work_order_parent", "work_order", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_work_order_parent", table_name="work_order")
    op.drop_constraint("fk_work_order_parent", "work_order", type_="foreignkey")
    op.drop_column("work_order", "parent_id")
