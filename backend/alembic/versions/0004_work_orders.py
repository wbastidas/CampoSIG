"""Work orders, crews and chain of custody.

M02/M03 of the SRS; RF-310 to RF-324. Scoped by business unit throughout (ADR-009).

Geometry is stored in EPSG:4326: the phone's GPS produces WGS84, MapLibre consumes WGS84,
and business units may sit in different UTM zones. Projection happens at the GIS boundary.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crew",
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
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("leader_name", sa.String(255), nullable=True),
        sa.Column("vehicle", sa.String(64), nullable=True),
        sa.Column(
            "competencies",
            postgresql.ARRAY(sa.String(32)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("zone", sa.String(64), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("business_unit_id", "code", name="uq_crew_code"),
    )
    op.create_index("ix_crew_unit_active", "crew", ["business_unit_id", "active"])

    op.create_table(
        "work_order",
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
        sa.Column("code", sa.String(32), nullable=True),
        sa.Column("source", sa.String(24), nullable=False, server_default="manual"),
        sa.Column("external_ref", sa.String(64), nullable=True),
        sa.Column("work_type", sa.String(32), nullable=False),
        sa.Column("form_code", sa.String(16), nullable=False),
        sa.Column("form_version", sa.String(16), nullable=True),
        sa.Column("state", sa.String(24), nullable=False, server_default="borrador"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="media"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("asset_type_key", sa.String(64), nullable=True),
        sa.Column("asset_code", sa.String(128), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("feeder_code", sa.String(32), nullable=True),
        sa.Column("zone", sa.String(64), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planner_id", sa.String(255), nullable=True),
        sa.Column(
            "assigned_crew_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("assigned_user_sub", sa.String(255), nullable=True),
        # Optimistic lock between concurrent planners (RF-311).
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Idempotent import: the same external reference cannot enter a unit twice.
        sa.UniqueConstraint("business_unit_id", "external_ref", name="uq_work_order_external_ref"),
        sa.UniqueConstraint("business_unit_id", "code", name="uq_work_order_code"),
    )
    op.create_index("ix_work_order_unit_state", "work_order", ["business_unit_id", "state"])
    op.create_index(
        "ix_work_order_unit_crew", "work_order", ["business_unit_id", "assigned_crew_id"]
    )
    op.create_index("ix_work_order_sla", "work_order", ["sla_due_at"])
    # GiST index for the map's bbox and lasso selection: the hot query of the graphical
    # assignment screen.
    op.create_index("ix_work_order_location", "work_order", ["location"], postgresql_using="gist")

    op.create_table(
        "device_custody",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device_id", sa.String(128), nullable=True),
        sa.Column("user_sub", sa.String(255), nullable=True),
        sa.Column(
            "crew_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "since", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        # True when the previous holder still had unsynced captured data (RF-322).
        sa.Column("had_unsynced_data", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("granted_by", sa.String(255), nullable=True),
        sa.Column("context", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_device_custody_order", "device_custody", ["work_order_id"])
    op.create_index(
        "ix_device_custody_current",
        "device_custody",
        ["work_order_id"],
        postgresql_where=sa.text("until IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("device_custody")
    op.drop_index("ix_work_order_location", table_name="work_order")
    op.drop_table("work_order")
    op.drop_table("crew")
