"""Adjuntos de oficina de la OT (RF-017).

El criterio de aceptacion es «un PDF adjunto se abre en modo avion», y de ahi salen las columnas: el
`content_hash` y el `size_bytes` no son metadatos decorativos, son lo que el manifiesto del paquete
offline lleva para que el telefono sepa si ya tiene el archivo y cuanto le falta por descargar.

El archivo no vive aqui: `storage_key` apunta al almacenamiento de objetos, igual que las
evidencias. La unica constraint que importa es la de contenido: el mismo archivo dos veces en una OT
es la oficina reenviandolo, no dos adjuntos, asi que se actualiza la fila en lugar de duplicarla.

El retiro es un marcado, no un DELETE: la cuadrilla pudo ejecutar el trabajo con el plano viejo y un
adjunto desaparecido dejaria la revision de ese trabajo sin respuesta.

Revision ID: 0026
Revises: 0025
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_order_attachment",
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
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False, server_default="documento"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("offline", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("uploaded_by", sa.String(255), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.Column("withdrawn_by", sa.String(255)),
        sa.Column("withdrawn_reason", sa.Text()),
        sa.UniqueConstraint(
            "work_order_id", "content_hash", name="uq_work_order_attachment_content"
        ),
    )
    op.create_index("ix_work_order_attachment_order", "work_order_attachment", ["work_order_id"])
    # El paquete offline pregunta por unidad y por si el archivo viaja, en ese orden.
    op.create_index(
        "ix_work_order_attachment_unit",
        "work_order_attachment",
        ["business_unit_id", "offline"],
    )


def downgrade() -> None:
    op.drop_index("ix_work_order_attachment_unit", table_name="work_order_attachment")
    op.drop_index("ix_work_order_attachment_order", table_name="work_order_attachment")
    op.drop_table("work_order_attachment")
