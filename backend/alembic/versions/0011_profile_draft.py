"""Borradores versionados del perfil de modelo de datos (RF-301).

Hasta ahora el perfil solo existía como archivo en `profiles/`, así que instalar la
plataforma en otra unidad de negocio exigía que alguien escribiera un YAML a mano. Esta
tabla es donde el importador guarda lo que una persona decidió, versión por versión.

Publicar no edita: supersede. Un formulario generado en marzo tiene que seguir
explicándose en septiembre, y solo lo explica el perfil que lo generó.

Los dos índices parciales son la parte que importa: uno solo borrador abierto y una sola
versión publicada por unidad y perfil. Dos administradores editando el mismo perfil en
paralelo es cómo se pierde la mitad del trabajo de uno de ellos, y eso lo tiene que
rechazar la base, no esperar que la pantalla se dé cuenta.

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profile_draft",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decisions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("document", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("problems", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("published_by", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_unit.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["gis_metadata_snapshot.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "business_unit_id", "profile_id", "version", name="uq_profile_draft_version"
        ),
    )
    op.create_index(
        "ix_profile_draft_unit", "profile_draft", ["business_unit_id", "status"], unique=False
    )
    op.create_index(
        "uq_profile_draft_open",
        "profile_draft",
        ["business_unit_id", "profile_id"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )
    op.create_index(
        "uq_profile_draft_published",
        "profile_draft",
        ["business_unit_id", "profile_id"],
        unique=True,
        postgresql_where=sa.text("status = 'published'"),
    )


def downgrade() -> None:
    op.drop_index("uq_profile_draft_published", table_name="profile_draft")
    op.drop_index("uq_profile_draft_open", table_name="profile_draft")
    op.drop_index("ix_profile_draft_unit", table_name="profile_draft")
    op.drop_table("profile_draft")
