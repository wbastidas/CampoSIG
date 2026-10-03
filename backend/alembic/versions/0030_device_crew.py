"""El telefono compartido de una cuadrilla (RF-320).

RF-320 dice que una OT asignada a una cuadrilla «aparece en el proximo sync/pull de los
dispositivos de esa cuadrilla». No habia ningun lugar donde un dispositivo perteneciera a una
cuadrilla: la asignacion por lazo del mapa (solo cuadrilla, sin dispositivo) no llegaba a ningun
telefono. `device.crew_id` es ese lugar, y lo fija la web, nunca el telefono.

Revision ID: 0030
Revises: 0029
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "device",
        sa.Column(
            "crew_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="SET NULL"),
        ),
    )
    op.create_index("ix_device_crew", "device", ["crew_id"])


def downgrade() -> None:
    op.drop_index("ix_device_crew", table_name="device")
    op.drop_column("device", "crew_id")
