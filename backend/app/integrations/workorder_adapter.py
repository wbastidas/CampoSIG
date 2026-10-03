"""The corporate work-order platform, both directions (RF-120).

Two modes, and which one is in force changes what the platform is allowed to do:

* **satellite** — the corporate system owns the work-order number and the platform only
  executes. It imports orders and reports back; it does not invent numbers.
* **master** — the platform creates the work, and the corporate system is informed.

The mode lives in settings, not in the code path of each function, so a deployment that flips
it does not need a release. Importing is idempotent by the external reference, because the
external reference is the corporate system's identity for the job and receiving it twice is
normal — a retry, a re-run of a nightly job, a reconnect.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.models import Connector, Direction, EventKind, IntegrationEvent
from app.integrations.service import mark_delivered, mark_failed, publish
from app.integrations.transport import Transport, TransportError
from app.org.models import BusinessUnit
from app.workorders.models import WorkOrder, WorkOrderSource, WorkOrderState
from app.workorders.service import create_work_order


class Mode(StrEnum):
    #: The corporate platform owns the numbers; we execute (addendum 1.1).
    SATELLITE = "satelite"
    #: We own the numbers; the corporate platform is told.
    MASTER = "maestro"


#: What the corporate system's payload must contain for us to act on it. Anything else is
#: extra and is kept in the event payload rather than dropped.
REQUIRED_FIELDS = ("external_ref", "type")


def import_work_orders(
    session: Session,
    unit: BusinessUnit,
    transport: Transport,
    *,
    base_url: str,
    default_form_code: str = "F-OP-01",
    default_asset_type: str | None = "support_structure",
) -> dict[str, Any]:
    """Pull open work orders from the corporate platform and create the missing ones.

    Every exchange is logged first, so an import that produced a wrong order can be explained
    from what actually arrived rather than from what somebody remembers arriving.

    :returns: a summary — created, already known, and rejected with their reasons.
    """
    created: list[str] = []
    known: list[str] = []
    rejected: list[dict[str, str]] = []

    try:
        answer = transport.get(f"{base_url.rstrip('/')}/work-orders")
    except TransportError as exc:
        # The failure is recorded as an inbound event with no payload: an import that could
        # not even happen is information the integrations screen has to show.
        event = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.INBOUND,
            kind=EventKind.WORK_ORDER_IMPORTED,
            idempotency_key=f"import:{base_url}",
            payload={},
        )
        mark_failed(session, event, exc)
        raise

    for item in answer.body.get("items", []):
        external_ref = str(item.get("external_ref") or "")
        missing = [field for field in REQUIRED_FIELDS if not item.get(field)]
        if missing:
            rejected.append(
                {
                    "external_ref": external_ref or "(sin referencia)",
                    "reason": f"faltan campos obligatorios: {', '.join(missing)}",
                }
            )
            continue

        event = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.INBOUND,
            kind=EventKind.WORK_ORDER_IMPORTED,
            idempotency_key=f"ot:{external_ref}",
            payload=item,
            external_ref=external_ref,
        )

        existing = session.scalars(
            select(WorkOrder).where(
                WorkOrder.business_unit_id == unit.id, WorkOrder.external_ref == external_ref
            )
        ).first()
        if existing is not None:
            known.append(external_ref)
            event.work_order_id = existing.id
            mark_delivered(session, event, {"already_known": True})
            continue

        order = create_work_order(
            session,
            unit,
            work_type=str(item["type"]),
            form_code=str(item.get("form_code") or default_form_code),
            priority=str(item.get("priority") or "media"),
            source=WorkOrderSource.EXTERNAL_SYSTEM,
            external_ref=external_ref,
            description=item.get("description"),
            asset_type_key=item.get("asset_type_key") or default_asset_type,
            asset_code=item.get("asset_code"),
            feeder_code=item.get("feeder_code"),
            zone=item.get("zone"),
        )
        event.work_order_id = order.id
        mark_delivered(session, event, {"created": True})
        created.append(external_ref)

    session.flush()
    return {"created": created, "already_known": known, "rejected": rejected}


def enqueue_status_push(
    session: Session, unit: BusinessUnit, order: WorkOrder, *, state: str | None = None
) -> IntegrationEvent | None:
    """Queue "this is where your work order got to" for the corporate platform.

    Returns None for an order the corporate system does not know about: telling it about a
    work order it never sent would be inventing a record in somebody else's system.

    The idempotency key includes the state, so each state is reported once and a work order
    that goes back and forth reports each transition rather than overwriting the last.
    """
    if not order.external_ref:
        return None
    reported = state or order.state
    return publish(
        session,
        unit,
        connector=Connector.WORK_ORDER_SYSTEM,
        direction=Direction.OUTBOUND,
        kind=EventKind.WORK_ORDER_STATUS,
        idempotency_key=f"estado:{order.external_ref}:{reported}",
        payload={
            "external_ref": order.external_ref,
            "status": reported,
            "work_order_code": order.code,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        },
        order=order,
        external_ref=order.external_ref,
    )


def enqueue_result_push(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    summary: str | None,
    evidence_keys: list[str] | None = None,
) -> IntegrationEvent | None:
    """Queue the result of an approved work order: summary and evidence references (RF-120).

    Evidence travels as storage references, not as bytes. The corporate platform fetches what
    it wants; pushing megabytes of photographs through an integration endpoint is how an
    integration becomes the thing that falls over every evening.
    """
    if not order.external_ref:
        return None
    return publish(
        session,
        unit,
        connector=Connector.WORK_ORDER_SYSTEM,
        direction=Direction.OUTBOUND,
        kind=EventKind.WORK_ORDER_RESULT,
        idempotency_key=f"resultado:{order.external_ref}",
        payload={
            "external_ref": order.external_ref,
            "status": WorkOrderState.APPROVED.value,
            "summary": summary,
            "evidence": evidence_keys or [],
        },
        order=order,
        external_ref=order.external_ref,
    )


def deliver(
    session: Session, event: IntegrationEvent, transport: Transport, *, base_url: str
) -> IntegrationEvent:
    """Send one queued outbound event to the corporate platform."""
    endpoint = {
        EventKind.WORK_ORDER_STATUS.value: "/work-orders/status",
        EventKind.WORK_ORDER_RESULT.value: "/work-orders/status",
    }.get(event.kind)
    if endpoint is None:
        # An event kind this adapter does not know is a programming error, not a transport
        # failure, and retrying it forever would hide that.
        return mark_failed(
            session,
            event,
            TransportError(
                f"el adaptador de OT no sabe entregar eventos de tipo '{event.kind}'",
                retryable=False,
            ),
        )
    try:
        answer = transport.post(f"{base_url.rstrip('/')}{endpoint}", event.payload)
    except TransportError as exc:
        return mark_failed(session, event, exc)
    return mark_delivered(session, event, answer)
