"""Registro de documentos emitidos, para que el QR del acta verifique algo (RF-115).

Un QR que solo abre una página mostrando el mismo hash que está impreso al lado no verifica
nada: la página estaría repitiendo el papel. Lo que convierte eso en verificación es que la
plataforma reconozca el código —y que pueda decir **no consta** de uno que nunca emitió—.

Reimprimir crea una fila nueva, no edita la anterior: la OT puede haberse corregido en medio, y
entonces dos personas tendrían dos papeles distintos afirmando ser el mismo documento.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issued_document",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("verification_code", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("state_at_issue", sa.String(length=32), nullable=False),
        sa.Column("form_code", sa.String(length=32), nullable=True),
        sa.Column("form_version", sa.String(length=16), nullable=True),
        sa.Column("issued_by", sa.String(length=255), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_unit.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["response_id"], ["form_response.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        # El código de verificación es la identidad pública del documento: único, y por eso
        # también el índice por el que la página de verificación lo busca.
        sa.UniqueConstraint("verification_code", name="uq_issued_document_code"),
    )
    op.create_index("ix_issued_document_order", "issued_document", ["work_order_id"])
    op.create_index("ix_issued_document_unit", "issued_document", ["business_unit_id"])


def downgrade() -> None:
    op.drop_index("ix_issued_document_unit", table_name="issued_document")
    op.drop_index("ix_issued_document_order", table_name="issued_document")
    op.drop_table("issued_document")
