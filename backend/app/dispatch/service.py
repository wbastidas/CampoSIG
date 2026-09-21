"""The dispatch board: what was sent, what arrived, and what is coming back (RF-104, RF-360).

Assignment and delivery are different facts. A planner assigns work on the map; the work
reaches a crew only when that crew's phone pulls it, which may be minutes later, or never —
the phone was flat, the technician never opened the app, the order was edited after the last
sync. A board that shows assignment and calls it dispatch tells the dispatcher what they
intended rather than what happened.

So everything here is measured from the server's own record of hand-overs, and the one
number that matters most is the gap between the two.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dispatch.models import WorkOrderDelivery
from app.org.models import BusinessUnit

# SYNCABLE_STATES is imported, never repeated: the board must report on exactly the states
# the sync endpoint actually sends.
from app.sync.models import (
    SYNCABLE_STATES,
    Device,
    DeviceStatus,
    OfflinePackage,
    SyncOperationLog,
)
from app.workorders.models import Crew, WorkOrder, WorkOrderState

#: States that mean the crew is working the order right now.
IN_PROGRESS_STATES = (
    WorkOrderState.EN_ROUTE,
    WorkOrderState.ON_SITE,
    WorkOrderState.IN_EXECUTION,
)

#: States that mean the work came back and is the office's problem now.
RETURNED_STATES = (
    WorkOrderState.CLOSED_FIELD,
    WorkOrderState.SYNCED,
    WorkOrderState.IN_REVIEW,
)


def record_delivery(
    session: Session, device: Device, orders: list[WorkOrder]
) -> list[WorkOrderDelivery]:
    """Record that these orders were handed to this device.

    Called by the pull endpoint, because the hand-over *is* the delivery: recording it
    anywhere else leaves a window in which the server believes something it did not do.

    Idempotent per (order, device): a device that re-pulls updates the row and increments
    the counter rather than creating a second one. The counter is not decoration — a number
    that keeps climbing means the phone is re-downloading instead of storing, which is a
    real failure that is otherwise invisible from the server.
    """
    if not orders:
        return []

    existing = {
        row.work_order_id: row
        for row in session.scalars(
            select(WorkOrderDelivery).where(
                WorkOrderDelivery.device_id == device.id,
                WorkOrderDelivery.work_order_id.in_([order.id for order in orders]),
            )
        )
    }

    now = datetime.now(UTC)
    recorded: list[WorkOrderDelivery] = []
    for order in orders:
        row = existing.get(order.id)
        if row is None:
            row = WorkOrderDelivery(
                business_unit_id=device.business_unit_id,
                work_order_id=order.id,
                device_id=device.id,
                delivered_version=order.version,
                form_version=order.form_version,
                first_delivered_at=now,
                last_delivered_at=now,
                delivery_count=1,
            )
            session.add(row)
        else:
            row.delivered_version = order.version
            row.form_version = order.form_version
            row.last_delivered_at = now
            row.delivery_count += 1
        recorded.append(row)
    session.flush()
    return recorded


@dataclass
class CrewDispatch:
    """One row of the dispatch board."""

    crew_id: uuid.UUID
    code: str
    name: str
    zone: str | None
    assigned: int = 0
    #: Of the assigned, how many reached a device at all.
    delivered: int = 0
    #: Delivered, but the planner has edited the order since. The crew holds an old copy.
    stale_on_device: int = 0
    in_progress: int = 0
    returned: int = 0
    overdue: int = 0
    devices: list[str] = field(default_factory=list)
    last_sync_at: datetime | None = None

    @property
    def undelivered(self) -> int:
        """Assigned work no device has received. The number that ruins a morning."""
        return max(self.assigned - self.delivered, 0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "crew_id": str(self.crew_id),
            "code": self.code,
            "name": self.name,
            "zone": self.zone,
            "assigned": self.assigned,
            "delivered": self.delivered,
            "undelivered": self.undelivered,
            "stale_on_device": self.stale_on_device,
            "in_progress": self.in_progress,
            "returned": self.returned,
            "overdue": self.overdue,
            "devices": self.devices,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
        }


def dispatch_board(session: Session, unit: BusinessUnit) -> list[CrewDispatch]:
    """Per-crew dispatch state for one business unit.

    Scoped to the unit at every step (ADR-009): a dispatcher in one unit cannot see, or
    count, another unit's crews or devices.
    """
    crews = list(
        session.scalars(
            select(Crew)
            .where(Crew.business_unit_id == unit.id, Crew.active.is_(True))
            .order_by(Crew.code)
        )
    )
    board = {
        crew.id: CrewDispatch(crew_id=crew.id, code=crew.code, name=crew.name, zone=crew.zone)
        for crew in crews
    }
    if not board:
        return []

    now = datetime.now(UTC)
    orders = list(
        session.scalars(
            select(WorkOrder).where(
                WorkOrder.business_unit_id == unit.id,
                WorkOrder.assigned_crew_id.in_(board),
                WorkOrder.state.in_(tuple(SYNCABLE_STATES) + RETURNED_STATES),
            )
        )
    )
    deliveries = _deliveries_by_order(session, [order.id for order in orders])

    for order in orders:
        row = board[order.assigned_crew_id]  # type: ignore[index]
        if order.state in RETURNED_STATES:
            row.returned += 1
            continue
        row.assigned += 1
        delivered = deliveries.get(order.id)
        if delivered is not None:
            row.delivered += 1
            if delivered < order.version:
                # The planner changed the order after the crew downloaded it. The crew is
                # working from an old copy and nothing on the phone can tell them so.
                row.stale_on_device += 1
        if order.state in IN_PROGRESS_STATES:
            row.in_progress += 1
        if order.sla_due_at is not None and order.sla_due_at < now:
            row.overdue += 1

    _attach_devices(session, unit, board)
    return [board[crew.id] for crew in crews]


def _deliveries_by_order(session: Session, order_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Highest delivered version per order, across every device that received it."""
    if not order_ids:
        return {}
    rows = session.execute(
        select(
            WorkOrderDelivery.work_order_id,
            func.max(WorkOrderDelivery.delivered_version),
        )
        .where(WorkOrderDelivery.work_order_id.in_(order_ids))
        .group_by(WorkOrderDelivery.work_order_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def _attach_devices(
    session: Session, unit: BusinessUnit, board: dict[uuid.UUID, CrewDispatch]
) -> None:
    """Attach each crew's devices, found through the work they currently hold.

    A device belongs to a person, not to a crew, and people move between crews. Deriving the
    link from the work actually delivered means the board shows the phone that has the work,
    which is the one a dispatcher needs to call.
    """
    rows = session.execute(
        select(WorkOrder.assigned_crew_id, Device.device_key, Device.last_sync_at)
        .join(WorkOrderDelivery, WorkOrderDelivery.work_order_id == WorkOrder.id)
        .join(Device, Device.id == WorkOrderDelivery.device_id)
        .where(
            WorkOrder.business_unit_id == unit.id,
            WorkOrder.assigned_crew_id.in_(board),
            WorkOrder.state.in_(SYNCABLE_STATES),
        )
        .distinct()
    ).all()
    for crew_id, device_key, last_sync_at in rows:
        row = board[crew_id]
        if device_key not in row.devices:
            row.devices.append(device_key)
        if last_sync_at is not None and (
            row.last_sync_at is None or last_sync_at > row.last_sync_at
        ):
            row.last_sync_at = last_sync_at
    for row in board.values():
        row.devices.sort()


@dataclass
class DeviceReadiness:
    """Whether one phone is ready to leave for a zone with no coverage."""

    device_key: str
    user_sub: str | None
    status: str
    app_version: str | None
    model_package_version: str | None
    last_sync_at: datetime | None
    held_orders: int
    stale_orders: int
    pending_uploads: int
    package_zone: str | None = None
    package_version: int | None = None
    package_current: bool = True

    @property
    def blockers(self) -> list[str]:
        """Why this device should not leave yet, phrased for the dispatcher."""
        reasons: list[str] = []
        if self.status != DeviceStatus.ACTIVE:
            reasons.append(f"el dispositivo está en estado '{self.status}'")
        if self.last_sync_at is None:
            reasons.append("nunca ha sincronizado")
        if self.stale_orders:
            reasons.append(
                f"tiene {self.stale_orders} OT con cambios posteriores que todavía no bajó"
            )
        if not self.package_current:
            reasons.append("el paquete offline de su zona cambió y aún no lo descargó")
        if self.pending_uploads:
            reasons.append(f"le quedan {self.pending_uploads} operaciones por subir")
        return reasons

    def as_dict(self) -> dict[str, Any]:
        return {
            "device_key": self.device_key,
            "user_sub": self.user_sub,
            "status": self.status,
            "app_version": self.app_version,
            "model_package_version": self.model_package_version,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "held_orders": self.held_orders,
            "stale_orders": self.stale_orders,
            "pending_uploads": self.pending_uploads,
            "package_zone": self.package_zone,
            "package_version": self.package_version,
            "package_current": self.package_current,
            "blockers": self.blockers,
        }


def device_readiness(session: Session, unit: BusinessUnit) -> list[DeviceReadiness]:
    """Per-device readiness for one business unit.

    "Ready" is not "enrolled". A phone that synced last Tuesday, holds four orders the
    planner has edited since and never downloaded the new zone package is enrolled, active,
    and useless in the field.
    """
    devices = list(
        session.scalars(
            select(Device).where(Device.business_unit_id == unit.id).order_by(Device.device_key)
        )
    )
    if not devices:
        return []

    held = _held_orders(session, [device.id for device in devices])
    pending = _pending_uploads(session, [device.id for device in devices])
    packages = {
        package.zone: package
        for package in session.scalars(
            select(OfflinePackage).where(
                OfflinePackage.business_unit_id == unit.id,
                OfflinePackage.superseded_at.is_(None),
            )
        )
    }

    readiness: list[DeviceReadiness] = []
    for device in devices:
        counts = held.get(device.id, (0, 0))
        zone, version, current = _package_state(session, device, packages)
        readiness.append(
            DeviceReadiness(
                device_key=device.device_key,
                user_sub=device.user_sub,
                status=device.status,
                app_version=device.app_version,
                model_package_version=device.model_package_version,
                last_sync_at=device.last_sync_at,
                held_orders=counts[0],
                stale_orders=counts[1],
                pending_uploads=pending.get(device.id, 0),
                package_zone=zone,
                package_version=version,
                package_current=current,
            )
        )
    return readiness


def _held_orders(session: Session, device_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, int]]:
    """Per device: (orders held, of those how many are behind the server's version)."""
    rows = session.execute(
        select(
            WorkOrderDelivery.device_id,
            func.count(WorkOrderDelivery.id),
            func.count(WorkOrderDelivery.id).filter(
                WorkOrderDelivery.delivered_version < WorkOrder.version
            ),
        )
        .join(WorkOrder, WorkOrder.id == WorkOrderDelivery.work_order_id)
        .where(
            WorkOrderDelivery.device_id.in_(device_ids),
            WorkOrder.state.in_(SYNCABLE_STATES),
        )
        .group_by(WorkOrderDelivery.device_id)
    ).all()
    return {row[0]: (row[1], row[2]) for row in rows}


def _pending_uploads(session: Session, device_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Operations the device sent that the server rejected and nobody resolved.

    The server cannot see what a phone has not sent — that is the device's own outbox. What
    it can see is what it refused, and a rejected operation is captured work that is not in
    the system yet.
    """
    rows = session.execute(
        select(SyncOperationLog.device_id, func.count(SyncOperationLog.id))
        .where(
            SyncOperationLog.device_id.in_(device_ids),
            SyncOperationLog.accepted.is_(False),
        )
        .group_by(SyncOperationLog.device_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def _package_state(
    session: Session, device: Device, packages: dict[str, OfflinePackage]
) -> tuple[str | None, int | None, bool]:
    """The zone package this device should hold, and whether it holds the current one.

    The zone is taken from the work it actually holds rather than from a field on the device,
    because a phone follows the work: the same technician covers a different zone tomorrow.
    """
    zone = session.scalars(
        select(WorkOrder.zone)
        .join(WorkOrderDelivery, WorkOrderDelivery.work_order_id == WorkOrder.id)
        .where(
            WorkOrderDelivery.device_id == device.id,
            WorkOrder.state.in_(SYNCABLE_STATES),
            WorkOrder.zone.is_not(None),
        )
        .limit(1)
    ).first()
    if zone is None:
        return None, None, True
    package = packages.get(zone)
    if package is None:
        return zone, None, True
    # A device that never synced after the package was built does not have it. This is a
    # conservative reading of an honest limit: the server knows when it published, and when
    # the phone last spoke to it, and nothing else.
    #
    # `built_at` is PostgreSQL's now(), which is the *transaction* time. A package published
    # in the same transaction as a device's sync would therefore look already-held. That
    # cannot happen in production — publishing and syncing are different requests — but it
    # is why the test for this sets the sync time relative to the package.
    current = device.last_sync_at is not None and device.last_sync_at >= package.built_at
    return zone, package.version, current
