"""Versionado de formularios: la forma publicada se congela (RF-032).

El criterio de RF-032 es «publicar la v2 no altera las OT asignadas con la v1», y la plataforma no
lo cumplia: los formularios viven como archivos bajo `forms/` y el catalogo los indexaba solo por
codigo, asi que editar `F-AP-01.yaml` cambiaba la forma de **todas** las OT, incluidas las que un
tecnico ya llevaba en el telefono.

Los archivos son el borrador. Publicar congela aqui la definicion **y los bloques que usa**:
congelar solo la definicion dejaria la forma a merced de una edicion de bloque, que es el mismo
error un nivel mas abajo.

Una sola fila `publicado` por codigo. Dos dejarian «que version recibe una OT nueva» a la fila que
la consulta viera primero, asi que lo garantiza un indice unico parcial en la base y no una
comprobacion en el servicio que un segundo escritor pueda correr en paralelo.

Lo que **no** se congela son los catalogos de la unidad: una OT ejecutada hoy tiene que nombrar un
alimentador que exista hoy (RF-304).

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "published_form",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        # El orden de publicacion, de la base. `published_at` no puede llevarlo: el `now()` de
        # PostgreSQL es el reloj de la *transaccion*, asi que dos publicaciones de una misma
        # peticion comparten la marca y «la mas nueva primero» queda al azar del recorrido.
        sa.Column(
            "sequence", sa.BigInteger(), sa.Identity(always=False), nullable=False, unique=True
        ),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("blocks", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("published_by", sa.String(255)),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("obsoleted_by", sa.String(255)),
        sa.Column("obsoleted_at", sa.DateTime(timezone=True)),
        sa.Column("note", sa.Text()),
        sa.UniqueConstraint("code", "version", name="uq_published_form_version"),
    )
    op.create_index(
        "uq_published_form_current",
        "published_form",
        ["code"],
        unique=True,
        postgresql_where=sa.text("state = 'publicado'"),
    )


def downgrade() -> None:
    op.drop_index("uq_published_form_current", table_name="published_form")
    op.drop_table("published_form")
