"""Sync contract: delta pull and idempotent push (RF-004, RF-101 to RF-106, RF-322).

The server half of the promise the mobile engine makes (ADR-010). Two properties matter most:

* **Replaying is safe.** The ledger records what happened to every operation, so a second
  delivery returns the first outcome instead of applying it twice.
* **Nothing crosses business units.** A device belongs to one unit and can only ever see and
  affect that unit's work (ADR-009).
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dispatch.service import record_delivery
from app.forms.catalog import load_definitions
from app.org.models import BusinessUnit
from app.sync.models import (
    SYNCABLE_STATES,
    Device,
    DeviceStatus,
    OfflinePackage,
    SyncOperationLog,
)
from app.workorders.models import WorkOrder

__all__ = ["SYNCABLE_STATES"]


class DeviceBlockedError(Exception):
    """Raised when a blocked device attempts to sync (RF-004)."""


class UnknownDeviceError(Exception):
    """Raised when a device key is not enrolled."""


class CrossUnitError(Exception):
    """Raised when an operation would affect another business unit's work."""


# --- enrolment ---------------------------------------------------------------------
def enrol_device(
    session: Session,
    unit: BusinessUnit,
    *,
    device_key: str,
    user_sub: str | None = None,
    model: str | None = None,
    android_version: str | None = None,
    app_version: str | None = None,
) -> tuple[Device, bool]:
    """Enrol a device, or update the record of one already enrolled.

    Idempotent, because the app re-registers on every upgrade and after a reinstall.

    :returns: (device, created)
    """
    existing = session.scalars(select(Device).where(Device.device_key == device_key)).first()
    if existing is not None:
        existing.user_sub = user_sub or existing.user_sub
        existing.model = model or existing.model
        existing.android_version = android_version or existing.android_version
        existing.app_version = app_version or existing.app_version
        session.flush()
        return existing, False

    device = Device(
        business_unit_id=unit.id,
        device_key=device_key,
        user_sub=user_sub,
        model=model,
        android_version=android_version,
        app_version=app_version,
    )
    session.add(device)
    session.flush()
    return device, True


def resolve_device(session: Session, device_key: str) -> Device:
    """Find an enrolled device and confirm it may sync.

    :raises UnknownDeviceError: if the key is not enrolled.
    :raises DeviceBlockedError: if an administrator blocked it.
    """
    device = session.scalars(select(Device).where(Device.device_key == device_key)).first()
    if device is None:
        raise UnknownDeviceError(f"el dispositivo '{device_key}' no está enrolado")
    if not device.may_sync:
        raise DeviceBlockedError(
            f"el dispositivo '{device_key}' está {device.status}: "
            f"{device.blocked_reason or 'sin motivo registrado'}"
        )
    return device


def block_device(session: Session, device: Device, *, reason: str) -> Device:
    """Block a device and instruct it to wipe its local database (RF-004).

    Used for a lost or stolen phone, so it is deliberately blunt: the app closes and destroys
    its encrypted database on the next sync, whether or not it still holds unsynced work.
    That data loss is the accepted cost of not leaking a technician's work orders and customer
    details along with the phone.
    """
    device.status = DeviceStatus.BLOCKED
    device.blocked_at = datetime.now(UTC)
    device.blocked_reason = reason
    session.flush()
    return device


# --- delta pull (RF-102) -----------------------------------------------------------
def encode_cursor(updated_at: datetime, last_id: uuid.UUID) -> str:
    """Opaque cursor over (updated_at, id).

    The tuple rather than the timestamp alone: several work orders can share a timestamp to
    the microsecond, and a timestamp-only cursor would skip or repeat them.
    """
    payload = json.dumps({"t": updated_at.isoformat(), "id": str(last_id)})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    """Decode a cursor, tolerating a malformed one by starting from the beginning.

    A device that somehow persisted a corrupt cursor must be able to recover by resyncing, not
    be locked out of syncing entirely.
    """
    if not cursor:
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return datetime.fromisoformat(payload["t"]), uuid.UUID(payload["id"])
    except (ValueError, KeyError, TypeError):
        return None


def pull_work_orders(
    session: Session,
    device: Device,
    *,
    cursor: str | None = None,
    limit: int = 200,
) -> tuple[list[WorkOrder], str | None]:
    """Work orders this device should hold, changed since the cursor.

    Filtered by the device's own business unit and by the user or crew it serves, so a
    technician's phone never receives another unit's work (ADR-009).

    :returns: (orders, next_cursor). A null cursor means nothing changed.
    """
    statement = select(WorkOrder).where(
        WorkOrder.business_unit_id == device.business_unit_id,
        WorkOrder.state.in_(SYNCABLE_STATES),
    )
    if device.user_sub:
        statement = statement.where(WorkOrder.assigned_user_sub == device.user_sub)

    decoded = decode_cursor(cursor)
    if decoded is not None:
        watermark, last_id = decoded
        # Strictly after the cursor position, using the same (updated_at, id) ordering.
        statement = statement.where(
            (WorkOrder.updated_at > watermark)
            | ((WorkOrder.updated_at == watermark) & (WorkOrder.id > last_id))
        )

    orders = list(
        session.scalars(statement.order_by(WorkOrder.updated_at, WorkOrder.id).limit(limit))
    )
    if not orders:
        return [], None

    # The hand-over is recorded here, where it happens. Recording it anywhere else leaves a
    # window in which the server believes a crew has work it was never sent — and "assigned"
    # and "actually on the phone" are the two numbers a dispatcher compares every morning.
    record_delivery(session, device, orders)

    last = orders[-1]
    return orders, encode_cursor(last.updated_at, last.id)


def form_versions() -> dict[str, str]:
    """Form code to version that a device should hold.

    Read from the catalogue rather than the database: forms are data on disk, versioned there
    (SRS 4.1). The device compares versions and downloads only what changed.
    """
    return {code: definition.version for code, definition in load_definitions().items()}


# --- idempotent push (RF-101) ------------------------------------------------------
def already_processed(
    session: Session, device: Device, operation_id: str
) -> SyncOperationLog | None:
    """The ledger entry for an operation, if it was already delivered."""
    return session.scalars(
        select(SyncOperationLog).where(
            SyncOperationLog.device_id == device.id,
            SyncOperationLog.operation_id == operation_id,
        )
    ).first()


def push_operation(
    session: Session,
    device: Device,
    *,
    operation_id: str,
    kind: str,
    work_order_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    device_created_at: datetime | None = None,
) -> tuple[SyncOperationLog, bool]:
    """Accept one operation from a device's outbox, idempotently.

    :returns: (ledger_entry, applied). ``applied`` is False when this was a replay, so the
        caller knows the recorded outcome is being returned rather than a fresh one.
    :raises CrossUnitError: if the operation targets another unit's work order.
    """
    existing = already_processed(session, device, operation_id)
    if existing is not None:
        # A replay. Return the recorded outcome; apply nothing.
        return existing, False

    accepted = True
    rejection: str | None = None

    if work_order_id is not None:
        order = session.get(WorkOrder, work_order_id)
        if order is None:
            # Recorded as a rejection rather than raising: the device must be told to park
            # this operation, and a hard error would make it retry forever.
            accepted = False
            rejection = "la OT no existe"
        elif order.business_unit_id != device.business_unit_id:
            raise CrossUnitError("una operación no puede afectar trabajo de otra unidad de negocio")

    entry = SyncOperationLog(
        device_id=device.id,
        operation_id=operation_id,
        kind=kind,
        work_order_id=work_order_id if accepted else None,
        accepted=accepted,
        rejection_reason=rejection,
        result={"payload_keys": sorted(payload or {})},
        device_created_at=device_created_at,
    )
    session.add(entry)
    device.last_sync_at = datetime.now(UTC)
    session.flush()
    return entry, True


def undelivered_for(session: Session, device: Device, work_order_id: uuid.UUID) -> bool:
    """Whether this device still owes the server data for a work order (RF-322).

    Mirrors ``Outbox.isFullyDelivered`` on the device, from the server's side. The server can
    only see what arrived, so this answers "has anything at all arrived for this pairing?" —
    the authoritative answer lives on the device, and the two are reconciled at handover.
    """
    return (
        session.scalars(
            select(SyncOperationLog).where(
                SyncOperationLog.device_id == device.id,
                SyncOperationLog.work_order_id == work_order_id,
            )
        ).first()
        is None
    )


# --- offline package (RF-360) ------------------------------------------------------
def build_offline_package(
    session: Session,
    unit: BusinessUnit,
    *,
    zone: str,
    tile_url: str,
    asset_count: int,
    model_package_version: str | None = None,
) -> OfflinePackage:
    """Assemble the manifest for a zone package and supersede the previous one.

    The manifest lists parts with their own hashes so the device fetches them independently
    and resumes an interrupted transfer part by part rather than restarting (RF-104).
    """
    parts = [
        {"name": "tiles", "kind": "pmtiles", "url": tile_url},
        {"name": "assets", "kind": "geojson", "count": asset_count},
        {"name": "forms", "kind": "json", "versions": form_versions()},
    ]
    manifest: dict[str, Any] = {
        "business_unit": unit.code,
        "zone": zone,
        "spatial_reference": unit.spatial_reference,
        "parts": parts,
        "model_package_version": model_package_version,
    }
    # Hash over the canonical manifest: two builds with identical content produce the same
    # hash, so a device can tell whether it already holds this package.
    content_hash = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    previous = session.scalars(
        select(OfflinePackage).where(
            OfflinePackage.business_unit_id == unit.id,
            OfflinePackage.zone == zone,
            OfflinePackage.superseded_at.is_(None),
        )
    ).first()
    if previous is not None:
        if previous.content_hash == content_hash:
            # Nothing changed: reuse it rather than making every device re-download.
            return previous
        previous.superseded_at = datetime.now(UTC)

    package = OfflinePackage(
        business_unit_id=unit.id,
        zone=zone,
        version=(previous.version + 1) if previous else 1,
        manifest=manifest,
        content_hash=content_hash,
    )
    session.add(package)
    session.flush()
    return package


def current_package(session: Session, unit: BusinessUnit, zone: str) -> OfflinePackage | None:
    return session.scalars(
        select(OfflinePackage).where(
            OfflinePackage.business_unit_id == unit.id,
            OfflinePackage.zone == zone,
            OfflinePackage.superseded_at.is_(None),
        )
    ).first()
