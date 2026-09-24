"""OT propuestas por IA y la exposicion de la zona (RF-013, RF-114).

Una propuesta **no** es una OT. RF-013 dice «al aprobarla pasa a Planificada; al rechazarla guarda
el motivo», y las dos mitades piden una tabla aparte: una propuesta rechazada no puede ser una OT
que nunca fue trabajo —los tableros de RF-130 y la bitacora contarian trabajo inexistente, y esos
numeros son los que una unidad reporta hacia arriba— y una propuesta lleva cosas que una OT no
lleva: los hallazgos que la originaron, el modelo que los vio y la aritmetica del anexo C.

El indice unico parcial sobre el estado abierto es lo que impide que la bandeja se llene con una
fila por inspeccion de la misma cruceta rota, y a la vez permite una propuesta nueva despues de un
rechazo: un defecto que alguien descarto puede volver.

`zone.exposure` es el ajuste por exposicion del anexo C («zona urbana o escolar, via principal: +1
nivel»). Vive en la zona porque es lo que el anexo describe, y en falso por omision: subir un nivel
a todas las propuestas porque nadie marco la casilla seria peor que no aplicar el ajuste.

Revision ID: 0021
Revises: 0020
"""

from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "zone",
        sa.Column("exposure", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "work_order_proposal",
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
            "source_work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="SET NULL"),
        ),
        sa.Column("origin", sa.String(24), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="propuesta"),
        sa.Column("asset_code", sa.String(128)),
        sa.Column("asset_type_key", sa.String(64)),
        sa.Column("feeder_code", sa.String(32)),
        sa.Column("zone", sa.String(64)),
        sa.Column("location", Geometry(geometry_type="POINT", srid=4326, spatial_index=False)),
        sa.Column("defect_code", sa.String(64), nullable=False),
        sa.Column("work_type", sa.String(32), nullable=False),
        sa.Column("form_code", sa.String(16)),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column(
            "criticality", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("suggested_deadline_hours", sa.Integer()),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("findings", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "evidence_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("model_name", sa.String(64)),
        sa.Column("model_version", sa.String(32)),
        sa.Column("confidence", sa.Float()),
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "merged_into_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="SET NULL"),
        ),
        sa.Column("reject_reason_code", sa.String(64)),
        sa.Column("reject_note", sa.Text()),
        sa.Column("decided_by", sa.String(255)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("work_order_id", name="uq_proposal_work_order"),
    )
    op.create_index(
        "uq_proposal_open_per_asset_defect",
        "work_order_proposal",
        ["business_unit_id", "asset_code", "defect_code"],
        unique=True,
        postgresql_where=sa.text("state = 'propuesta'"),
    )
    op.create_index("ix_proposal_tray", "work_order_proposal", ["business_unit_id", "state"])


def downgrade() -> None:
    op.drop_index("ix_proposal_tray", table_name="work_order_proposal")
    op.drop_index("uq_proposal_open_per_asset_defect", table_name="work_order_proposal")
    op.drop_table("work_order_proposal")
    op.drop_column("zone", "exposure")
