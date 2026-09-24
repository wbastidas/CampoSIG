"""Consignaciones y su ventana horaria (RF-024).

El criterio de aceptacion es una negativa —«no se habilita el formulario F-TR-02 sin un N.º de
consignacion»— y de ahi sale la forma de esta tabla: el **numero** es la autoridad, no el estado. Es
lo que la cuadrilla repite por radio antes de tocar nada y lo que se pide despues si algo sale mal,
asi que la plataforma exige el numero y no solo una solicitud marcada como aprobada.

La ventana lleva los dos extremos obligatorios: una consignacion sin fin no es una ventana, y
registrarla existe precisamente para poder decir si el trabajo ocurrio dentro. Trabajar fuera de la
ventana **no se rechaza**: se registra, porque rechazar la captura perderia el registro de lo que
realmente paso, que es lo unico que una investigacion necesita.

`work_order.outage_request_id` es de muchos a uno a proposito: «consignacion del alimentador sur,
sabado de 06:00 a 12:00» cubre todos los frentes que trabajan bajo ella, y una solicitud por OT
tendria al Centro de Control otorgando seis descargos para un solo corte.

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outage_request",
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
        sa.Column("number", sa.String(32)),
        sa.Column("state", sa.String(16), nullable=False, server_default="solicitada"),
        sa.Column("equipment", sa.String(255), nullable=False),
        sa.Column("feeder_code", sa.String(32)),
        sa.Column("substation_code", sa.String(32)),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("decided_by", sa.String(255)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("note", sa.Text()),
        sa.Column("returned_at", sa.DateTime(timezone=True)),
        sa.Column("returned_by", sa.String(255)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("business_unit_id", "number", name="uq_outage_request_number"),
    )
    op.create_index("ix_outage_request_state", "outage_request", ["business_unit_id", "state"])
    op.create_index(
        "ix_outage_request_window",
        "outage_request",
        ["business_unit_id", "window_start", "window_end"],
    )

    op.add_column(
        "work_order",
        sa.Column("outage_request_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_work_order_outage",
        "work_order",
        "outage_request",
        ["outage_request_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_work_order_outage", "work_order", ["outage_request_id"])


def downgrade() -> None:
    op.drop_index("ix_work_order_outage", table_name="work_order")
    op.drop_constraint("fk_work_order_outage", "work_order", type_="foreignkey")
    op.drop_column("work_order", "outage_request_id")
    op.drop_index("ix_outage_request_window", table_name="outage_request")
    op.drop_index("ix_outage_request_state", table_name="outage_request")
    op.drop_table("outage_request")
