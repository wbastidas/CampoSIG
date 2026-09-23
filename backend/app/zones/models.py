"""Zones as polygons (RF-152).

Until now a zone was a string. `work_order.zone` and `crew.zone` hold text, which is enough to
filter a list and not enough for anything a zone is actually for: deciding which crew covers a
point, naming the offline package a device downloads, or scoping a supervisor to the north of the
city. All three need geometry.

Three decisions are load-bearing:

* **The code stays the string it always was.** Existing rows carry `zone = "NORTE"`, and the
  polygon arrives as a second source of truth for the same idea. So a zone's identity is its code,
  unique per business unit, and the geometry hangs off it. Nothing has to be migrated on the day
  the polygons land, and a unit that has not drawn its zones yet keeps working exactly as before.

* **A zone belongs to one business unit** (ADR-009), and so does the question "which zone is this
  point in". Two units may have a `NORTE` and their polygons may even overlap on a map — they are
  different zones and no query may see both.

* **Geometry is stored in EPSG:4326**, like every other geometry the platform holds (see
  `workorders.models`). GeoJSON is defined in WGS84, MapLibre draws WGS84, and a zone whose
  polygon sat in the unit's UTM zone could not be compared with a work order's point.

The geometry is MULTIPOLYGON rather than POLYGON because real operating zones are not always
connected: an island, a detached parish, a service area split by a river that belongs to somebody
else. Forcing POLYGON would make the importer reject a boundary the utility actually uses, and the
usual workaround — importing it as two zones — invents a distinction the operation does not have.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base
from app.workorders.models import STORAGE_SRID


class ZoneOrigin(StrEnum):
    """Where the polygon came from. Kept because the two have different failure modes.

    A drawn polygon is somebody's reading of a map and is expected to be approximate. An imported
    one came from a file that exists somewhere else, and when it disagrees with the operation the
    answer is to fix the file and import again, not to nudge the vertices here.
    """

    DRAWN = "dibujada"
    IMPORTED = "importada"


class Zone(Base):
    """One operating zone of a business unit."""

    __tablename__ = "zone"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )

    #: The same string `work_order.zone` and `crew.zone` already carry. Unique per unit, not
    #: globally: two units may both operate a `NORTE` (ADR-009).
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=STORAGE_SRID, spatial_index=False),
        nullable=False,
    )

    origin: Mapped[str] = mapped_column(String(16), nullable=False, default=ZoneOrigin.DRAWN)
    #: For an imported zone: the file and the feature it came from, so a wrong boundary can be
    #: traced back to its source instead of being argued about.
    imported_from: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    #: Deactivated rather than deleted. A zone that named ten thousand closed work orders is part
    #: of their history, and deleting it would leave that history pointing at nothing.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    #: Who last touched the boundary, which is the question asked when a zone stops matching the
    #: operation (RF-150's «usuario que modificó», applied to the same module's other objects).
    updated_by: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("business_unit_id", "code", name="uq_zone_code_per_unit"),
        Index("ix_zone_unit_active", "business_unit_id", "active"),
        #: The index that makes «which zone is this point in» a lookup instead of a scan over
        #: every polygon of the unit.
        Index("ix_zone_geom", "geom", postgresql_using="gist"),
    )
