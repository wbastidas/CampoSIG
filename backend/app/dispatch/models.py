"""What each device was actually handed (RF-104, RF-324).

Until this table existed, the platform could answer "who is this work order assigned to?"
but not "does that phone have it?". Those are different questions and only the second one
matters at six in the morning, when a crew leaves for a zone with no coverage: an order that
was assigned but never reached the device is a crew that arrives with nothing.

One row per work order and device, updated on every hand-over. Append-only history lives in
``device_custody``; this is the current delivery state, which is what a dispatcher looks at.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


class WorkOrderDelivery(Base):
    """A work order as handed to one device by the sync endpoint."""

    __tablename__ = "work_order_delivery"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )

    #: The order's optimistic-lock version at the moment it was handed over. A device holding
    #: version 3 of an order the planner has since edited to version 4 is stale, and the
    #: dispatcher can see that without asking the phone.
    delivered_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    #: The form version pinned when it was delivered, for the same reason.
    form_version: Mapped[str | None] = mapped_column(String(16))

    first_delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    #: How many times the device pulled it. A number that keeps climbing means the phone is
    #: re-downloading instead of storing, which is a real failure and an invisible one.
    delivery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint("work_order_id", "device_id", name="uq_delivery_order_device"),
        Index("ix_delivery_unit", "business_unit_id"),
        Index("ix_delivery_device", "device_id"),
    )


class DevicePosition(Base):
    """Where a phone last reported itself to be (RF-020).

    **One row per device, and the device is the primary key.** That is the whole privacy design,
    written into the schema rather than into a policy note: the platform holds the *last* position a
    phone reported and cannot hold a history of where a technician went, because there is nowhere to
    put one. RF-020 asks for «la ubicación de cuadrillas según el último GPS reportado» so a
    dispatcher can decide who is closest to a fault; a movement log would answer a different
    question that nobody asked and that a works council would be right to object to.

    Reported at sync, not continuously: the phone says where it is when it talks to the server
    anyway. So a position is always as old as the last sync, and `reported_at` travels with it —
    a position without its age is a position that lies.
    """

    __tablename__ = "device_position"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device.id", ondelete="CASCADE"), primary_key=True
    )
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    #: EPSG:4326, like everything else the platform stores (see `workorders.models`).
    location: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    #: What the phone said about its own fix. A 2 km accuracy is not a position, and the map has to
    #: be able to say so instead of drawing a confident dot.
    accuracy_m: Mapped[float | None] = mapped_column(Float)
    #: The device clock, kept because it is the age of the fix; `received_at` is the server's.
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_device_position_unit", "business_unit_id", "reported_at"),
        Index("ix_device_position_geom", "location", postgresql_using="gist"),
    )
