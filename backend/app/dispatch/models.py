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

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
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
