"""Bitacora inmutable de eventos, con cadena de hashes (RF-160, RF-161).

El criterio de aceptacion de RF-160 son dos cosas: que no exista endpoint que edite ni borre la
bitacora, y una cadena de hashes que demuestre que nadie la edito por detras de la aplicacion. Lo
segundo se sostiene en los datos; lo primero, aqui, en la base.

El disparador rechaza UPDATE y DELETE sobre la tabla. No es una comodidad: una guarda que vive solo
en el codigo de la aplicacion la salta cualquiera con un psql y buenas intenciones, y la buena
intencion —«arreglo este registro que quedo mal»— es exactamente como una bitacora deja de servir
como prueba.

Las claves foraneas van con ON DELETE RESTRICT y no CASCADE: borrar una unidad de negocio o una OT
no puede llevarse su historia por delante. Si hay que retirar una unidad, primero hay que decidir
que se hace con su bitacora, y eso es una decision de una persona y no un efecto colateral.

## Reemplaza la tabla de la baseline

La migracion 0001 declaro una tabla `audit_event` con otra forma (entity_type, action, actor_sub) y
**ningun codigo llego a escribir en ella jamas**: no tenia modelo, no aparecia en la metadata y por
eso las pruebas, que construyen el esquema desde la metadata, nunca la tuvieron. Fue la tabla
declarada la que hizo creer que M16 estaba hecho.

Se reemplaza en vez de convivir con ella, porque dos bitacoras son ninguna. Y no se borra a ciegas:
si en algun despliegue llegara a tener filas, la migracion se detiene con un mensaje en lugar de
destruirlas. Que una tabla este vacia en el repositorio no es prueba de que lo este en produccion.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GUARD = """
CREATE OR REPLACE FUNCTION audit_event_is_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_event es append-only (RF-160): % rechazado', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_event_no_update
    BEFORE UPDATE ON audit_event
    FOR EACH ROW EXECUTE FUNCTION audit_event_is_append_only();

CREATE TRIGGER audit_event_no_delete
    BEFORE DELETE ON audit_event
    FOR EACH ROW EXECUTE FUNCTION audit_event_is_append_only();
"""


#: La baseline declaro una `audit_event` de otra forma que nunca se uso. Se retira aqui, y solo si
#: esta vacia: una tabla vacia en el repositorio no prueba que lo este en produccion.
REPLACE_THE_STUB = """
DO $$
DECLARE
    filas bigint;
BEGIN
    IF to_regclass('public.audit_event') IS NULL THEN
        RETURN;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audit_event' AND column_name = 'sequence'
    ) THEN
        RETURN;  -- ya es la tabla nueva
    END IF;
    EXECUTE 'SELECT count(*) FROM audit_event' INTO filas;
    IF filas > 0 THEN
        RAISE EXCEPTION
            'la audit_event de la baseline tiene % fila(s): decida que hacer con ellas',
            filas;
    END IF;
    DROP TABLE audit_event;
END
$$;
"""


def upgrade() -> None:
    op.execute(REPLACE_THE_STUB)
    op.create_table(
        "audit_event",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_unit.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("subject_id", sa.String(128), nullable=False),
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="RESTRICT"),
        ),
        sa.Column("asset_code", sa.String(64)),
        sa.Column("actor_kind", sa.String(16), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("device_key", sa.String(128)),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reason", sa.Text()),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
        # Un hueco en la secuencia delata el evento que alguien quito del final, que es lo unico que
        # los enlaces solos no ven.
        sa.UniqueConstraint("business_unit_id", "sequence", name="uq_audit_event_sequence"),
    )
    # Las cuatro preguntas de RF-161 —por OT, por activo, por usuario, por dispositivo— cada una con
    # su indice: un auditor que pide la historia de una OT no deberia esperar el recorrido completo.
    op.create_index("ix_audit_event_work_order", "audit_event", ["work_order_id", "sequence"])
    op.create_index("ix_audit_event_asset", "audit_event", ["business_unit_id", "asset_code"])
    op.create_index("ix_audit_event_actor", "audit_event", ["business_unit_id", "actor"])
    op.create_index("ix_audit_event_device", "audit_event", ["business_unit_id", "device_key"])
    op.create_index("ix_audit_event_unit_time", "audit_event", ["business_unit_id", "occurred_at"])
    op.execute(GUARD)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_event_no_delete ON audit_event")
    op.execute("DROP TRIGGER IF EXISTS audit_event_no_update ON audit_event")
    op.execute("DROP FUNCTION IF EXISTS audit_event_is_append_only()")
    for name in (
        "ix_audit_event_unit_time",
        "ix_audit_event_device",
        "ix_audit_event_actor",
        "ix_audit_event_asset",
        "ix_audit_event_work_order",
    ):
        op.drop_index(name, table_name="audit_event")
    op.drop_table("audit_event")
