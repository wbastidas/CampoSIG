"""Autor y bitacora de ediciones de los parametros regulatorios (RF-150).

RF-150 pide «vigencia, referencia normativa y usuario que modifico». Lo primero y lo segundo ya
estaban; el autor faltaba. Se anaden `created_by` y `updated_by`, que son distintos de
`verified_by`: ese ultimo es una afirmacion mas fuerte —que alguien leyo el texto oficial— y una
persona puede corregir una descripcion sin certificar la cifra.

Y se anade `regulatory_revision`, porque «usuario que modifico» solo sirve al lado de **desde que
valor**. Los periodos son la historia de los valores que publico el regulador; esta tabla es la
historia de las ediciones, y existe porque la unica mutacion que el modelo permite —corregir un
periodo abierto— sobrescribiria una cifra sin dejar rastro.

No comparte la cadena de hashes de M16 y no es esa bitacora: la de M16 es por unidad de negocio y
trata del trabajo de campo, mientras un parametro regulatorio es nacional (ADR-009 no mete nada
corporativo dentro de la bitacora de una unidad).

`updated_at` se llena con `created_at` en las filas existentes y no con `now()`: decir que todas se
tocaron el dia de la migracion seria inventar una fecha de edicion.

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("regulatory_parameter", sa.Column("created_by", sa.String(255)))
    op.add_column("regulatory_parameter", sa.Column("updated_by", sa.String(255)))
    op.add_column(
        "regulatory_parameter",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    # Las filas que ya existian no se editaron hoy.
    op.execute("UPDATE regulatory_parameter SET updated_at = created_at")

    op.create_table(
        "regulatory_revision",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "parameter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("regulatory_parameter.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # El orden de insercion, de la base. `at` no puede llevarlo: el `now()` de PostgreSQL es el
        # reloj de la *transaccion*, asi que todas las revisiones de una misma peticion comparten la
        # marca al microsegundo y ordenar por ella devuelve lo que el indice quiera.
        sa.Column(
            "sequence", sa.BigInteger(), sa.Identity(always=False), nullable=False, unique=True
        ),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("changed", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("note", sa.Text()),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_regulatory_revision_code", "regulatory_revision", ["code", "sequence"])


def downgrade() -> None:
    op.drop_index("ix_regulatory_revision_code", table_name="regulatory_revision")
    op.drop_table("regulatory_revision")
    op.drop_column("regulatory_parameter", "updated_at")
    op.drop_column("regulatory_parameter", "updated_by")
    op.drop_column("regulatory_parameter", "created_by")
