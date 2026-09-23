"""Catalogos operativos administrables, con revision para el delta (RF-034).

Los formularios ya los referenciaban: `b11-hallazgos.yaml` dice `x-catalog-ref: defect` y
`b06-actividades.yaml` dice `x-catalog-ref: activity`, y **nada servia ninguna de las dos listas**.
Un telefono que renderizaba esos bloques tenia un campo de codigo y ningun valor de donde elegir. La
referencia existia; el catalogo no.

Tres cosas que no viven aqui: los catalogos del SIG (`feeder`, `substation`), que llegan por
sincronizacion y difieren por unidad (RF-304); los enums del perfil (`voltage_level`), que son del
descriptor del modelo de activos; y los parametros regulatorios, que tienen su propia tabla con
vigencia y cita (ADR-007).

**La revision la pone un disparador**, no el servicio. Es lo que hace posible la descarga
incremental: el dispositivo pide todo lo que este por encima de la revision que tiene. Una marca de
tiempo no serviria —el `now()` de PostgreSQL es el reloj de la transaccion, asi que un lote editado
junto compartiria un valor— y el disparador, en vez de una funcion del servicio, porque una entrada
escrita por el conector del ERP tambien necesita revision, y una regla que vive en una sola funcion
es una regla que el siguiente escritor olvida. Dispara en INSERT **y** en UPDATE: una etiqueta
corregida tiene que llegar al telefono igual que un valor nuevo.

**Desactivar es la forma de borrar.** Un valor retirado tiene que viajar al dispositivo como lapida,
o el telefono sigue ofreciendo un codigo que la distribuidora retiro hace dos anos.

El indice unico parcial cubre las filas nacionales: la restriccion unica sobre
(catalogo, unidad, codigo) no alcanza, porque PostgreSQL considera los nulos distintos entre si y
dos `defect/cruceta_podrida` sin unidad entrarian las dos.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVISION_TRIGGER = """
CREATE OR REPLACE FUNCTION catalog_entry_stamp_revision() RETURNS trigger AS $$
BEGIN
    NEW.revision := nextval('catalog_entry_revision_seq');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER catalog_entry_revision
    BEFORE INSERT OR UPDATE ON catalog_entry
    FOR EACH ROW EXECUTE FUNCTION catalog_entry_stamp_revision();
"""


def upgrade() -> None:
    op.create_table(
        "catalog",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("note", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.execute("CREATE SEQUENCE IF NOT EXISTS catalog_entry_revision_seq")
    op.create_table(
        "catalog_entry",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "revision",
            sa.BigInteger(),
            nullable=False,
            unique=True,
            server_default=sa.text("nextval('catalog_entry_revision_seq')"),
        ),
        sa.Column(
            "catalog_code",
            sa.String(64),
            sa.ForeignKey("catalog.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_unit.id", ondelete="CASCADE"),
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column(
            "synonyms",
            postgresql.ARRAY(sa.String(64)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("parent_code", sa.String(64)),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", sa.String(255)),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "catalog_code", "business_unit_id", "code", name="uq_catalog_entry_identity"
        ),
    )
    op.create_index(
        "uq_catalog_entry_national",
        "catalog_entry",
        ["catalog_code", "code"],
        unique=True,
        postgresql_where=sa.text("business_unit_id IS NULL"),
    )
    op.create_index("ix_catalog_entry_delta", "catalog_entry", ["revision"])
    op.create_index(
        "ix_catalog_entry_catalog", "catalog_entry", ["catalog_code", "business_unit_id"]
    )
    op.execute(REVISION_TRIGGER)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS catalog_entry_revision ON catalog_entry")
    op.execute("DROP FUNCTION IF EXISTS catalog_entry_stamp_revision()")
    op.drop_index("ix_catalog_entry_catalog", table_name="catalog_entry")
    op.drop_index("ix_catalog_entry_delta", table_name="catalog_entry")
    op.drop_index("uq_catalog_entry_national", table_name="catalog_entry")
    op.drop_table("catalog_entry")
    op.execute("DROP SEQUENCE IF EXISTS catalog_entry_revision_seq")
    op.drop_table("catalog")
