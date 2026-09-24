"""Devices and the sync ledger (RF-004, RF-101, RF-102).

The mobile side promises that re-sending is safe: every operation carries an id generated on
the device, and a reply lost on the way back costs a duplicate request rather than duplicate
data (ADR-010). This module is the server half of that promise — the ledger is what makes it
true instead of aspirational.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base
from app.workorders.models import WorkOrderState

#: States whose work a device should hold. Anything else is not the device's business, and
#: sending it would put closed work back on a technician's list.
#:
#: It lives with the models rather than with the sync service because two modules need it —
#: the endpoint that sends the work and the board that reports on it — and a board that
#: disagreed with the endpoint would be worse than no board.
SYNCABLE_STATES = (
    WorkOrderState.ASSIGNED,
    WorkOrderState.DOWNLOADED,
    WorkOrderState.EN_ROUTE,
    WorkOrderState.ON_SITE,
    WorkOrderState.IN_EXECUTION,
    WorkOrderState.SUSPENDED,
    WorkOrderState.RETURNED,
)


class DeviceStatus(StrEnum):
    ACTIVE = "activo"
    #: Blocked by an administrator. The app closes on next sync and wipes its local database.
    BLOCKED = "bloqueado"
    RETIRED = "retirado"


class Device(Base):
    """An enrolled field device (RF-004).

    Belongs to exactly one business unit: what it captures is routed to that unit's
    geodatabase, and the device never learns this happens (ADR-009).
    """

    __tablename__ = "device"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    #: Stable identifier the app presents; unique across the platform.
    device_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    user_sub: Mapped[str | None] = mapped_column(String(255))

    model: Mapped[str | None] = mapped_column(String(128))
    android_version: Mapped[str | None] = mapped_column(String(32))
    app_version: Mapped[str | None] = mapped_column(String(32))
    model_package_version: Mapped[str | None] = mapped_column(String(32))

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=DeviceStatus.ACTIVE)
    #: Set when an administrator blocks the device, so the wipe can be audited.
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_reason: Mapped[str | None] = mapped_column(String(500))
    wipe_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    operations: Mapped[list[SyncOperationLog]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_device_unit_status", "business_unit_id", "status"),
        Index("ix_device_user", "user_sub"),
    )

    @property
    def may_sync(self) -> bool:
        return self.status == DeviceStatus.ACTIVE


class SyncOperationLog(Base):
    """One operation the device delivered, and what the server did with it.

    The idempotency ledger. Keyed by (device, operation id) so replaying an operation returns
    the recorded outcome rather than applying it twice. Kept rather than deleted: it is also
    the evidence trail for "the technician says they sent it".
    """

    __tablename__ = "sync_operation_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    #: The id generated on the device. Stable across retries.
    operation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="SET NULL")
    )

    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Why it was rejected, when it was. The device parks it and shows this to a human.
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    #: Recorded so a replay returns the same answer without re-applying anything.
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    #: Device clock, kept separately: field devices work offline and their clocks drift.
    device_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped[Device] = relationship(back_populates="operations")

    __table_args__ = (
        # The idempotency guarantee, enforced by the database rather than by application luck.
        UniqueConstraint("device_id", "operation_id", name="uq_sync_operation_identity"),
        Index("ix_sync_operation_work_order", "work_order_id"),
    )


class OfflinePackage(Base):
    """A downloadable per-zone package (RF-360).

    Immutable once built and identified by a content hash, so a device can verify what it
    received and two devices on the same zone share one artifact.
    """

    __tablename__ = "offline_package"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    zone: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    #: What the package contains and where each part lives, so the device can fetch parts
    #: independently and resume (RF-104).
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    built_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("business_unit_id", "zone", "version", name="uq_offline_package_version"),
        Index(
            "ix_offline_package_current",
            "business_unit_id",
            "zone",
            postgresql_where="superseded_at IS NULL",
        ),
    )
