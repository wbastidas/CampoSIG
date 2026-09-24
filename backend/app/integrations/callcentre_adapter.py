"""Claims in, closures out (RF-124).

The half that is easy to get wrong is the second one. A crew replaces the lamp, a supervisor
approves the work, everyone considers the job done — and the customer's claim stays open,
because closing it was a side effect nobody guaranteed. So the closure is published as an
event inside the approval's own transaction: the approval cannot succeed without it existing.

A claim becomes a work order exactly once, keyed by the claim id. The call centre re-sending
an open claim is normal, and it must not produce a second crew visit.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.models import Connector, Direction, EventKind, IntegrationEvent
from app.integrations.service import mark_delivered, mark_failed, publish
from app.integrations.transport import Transport, TransportError
from app.org.models import BusinessUnit
from app.workorders.models import WorkOrder, WorkOrderSource
from app.workorders.service import create_work_order

#: Claim kind → the work type and form the platform executes it with. Configuration, not
#: intelligence: a claim about a dark street is a street-light job, and nothing has to infer
#: that. Unknown kinds are rejected with a reason rather than mapped to a guess.
CLAIM_ROUTING: dict[str, dict[str, str]] = {
    "luminaria_apagada": {
        "work_type": "luminaria_falla",
        "form_code": "F-AP-01",
        "asset_type_key": "street_light",
    },
    "sin_servicio": {
        "work_type": "atencion_falla",
        "form_code": "F-OP-01",
        "asset_type_key": "support_structure",
    },
    "poste_danado": {
        "work_type": "atencion_falla",
        "form_code": "F-OP-01",
        "asset_type_key": "support_structure",
    },
}


def import_claims(
    session: Session,
    unit: BusinessUnit,
    transport: Transport,
    *,
    base_url: str,
) -> dict[str, Any]:
    """Turn open claims into work orders, once each.

    :returns: created, already known, and rejected with their reasons.
    """
    created: list[str] = []
    known: list[str] = []
    rejected: list[dict[str, str]] = []

    try:
        answer = transport.get(f"{base_url.rstrip('/')}/claims")
    except TransportError as exc:
        event = publish(
            session,
            unit,
            connector=Connector.CALL_CENTRE,
            direction=Direction.INBOUND,
            kind=EventKind.CLAIM_RECEIVED,
            idempotency_key=f"import:{base_url}",
            payload={},
        )
        mark_failed(session, event, exc)
        raise

    for claim in answer.body.get("items", []):
        claim_id = str(claim.get("claim_id") or "")
        if not claim_id:
            rejected.append({"claim_id": "(sin id)", "reason": "el reclamo no trae identificador"})
            continue

        routing = CLAIM_ROUTING.get(str(claim.get("kind") or ""))
        if routing is None:
            rejected.append(
                {
                    "claim_id": claim_id,
                    "reason": (
                        f"el tipo de reclamo '{claim.get('kind')}' no está enrutado; "
                        "añadirlo a CLAIM_ROUTING antes de importarlo"
                    ),
                }
            )
            continue

        event = publish(
            session,
            unit,
            connector=Connector.CALL_CENTRE,
            direction=Direction.INBOUND,
            kind=EventKind.CLAIM_RECEIVED,
            idempotency_key=f"reclamo:{claim_id}",
            payload=claim,
            external_ref=claim_id,
        )

        existing = session.scalars(
            select(WorkOrder).where(
                WorkOrder.business_unit_id == unit.id, WorkOrder.external_ref == claim_id
            )
        ).first()
        if existing is not None:
            known.append(claim_id)
            event.work_order_id = existing.id
            mark_delivered(session, event, {"already_known": True})
            continue

        order = create_work_order(
            session,
            unit,
            work_type=routing["work_type"],
            form_code=routing["form_code"],
            asset_type_key=routing["asset_type_key"],
            priority=str(claim.get("priority") or "media"),
            source=WorkOrderSource.CALL_CENTER,
            external_ref=claim_id,
            description=claim.get("address"),
            asset_code=claim.get("asset_code"),
            zone=claim.get("zone"),
        )
        event.work_order_id = order.id
        mark_delivered(session, event, {"created": True})
        created.append(claim_id)

    session.flush()
    return {"created": created, "already_known": known, "rejected": rejected}


def enqueue_claim_closure(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    summary: str | None = None,
) -> IntegrationEvent | None:
    """Queue the closure of the claim this work order came from.

    Returns None when the order did not come from a claim. Published inside the approval's
    transaction, so an approved job can never leave its claim open.
    """
    if not order.external_ref or order.source != WorkOrderSource.CALL_CENTER:
        return None
    return publish(
        session,
        unit,
        connector=Connector.CALL_CENTRE,
        direction=Direction.OUTBOUND,
        kind=EventKind.CLAIM_CLOSED,
        idempotency_key=f"cierre:{order.external_ref}",
        payload={
            "claim_id": order.external_ref,
            "work_order_code": order.code,
            "resolution": summary or "trabajo ejecutado y aprobado",
            "closed_at": order.updated_at.isoformat() if order.updated_at else None,
        },
        order=order,
        external_ref=order.external_ref,
    )


def deliver(
    session: Session, event: IntegrationEvent, transport: Transport, *, base_url: str
) -> IntegrationEvent:
    """Send one queued closure to the call centre."""
    if event.kind != EventKind.CLAIM_CLOSED:
        return mark_failed(
            session,
            event,
            TransportError(
                f"el adaptador de call center no entrega eventos de tipo '{event.kind}'",
                retryable=False,
            ),
        )
    try:
        answer = transport.post(f"{base_url.rstrip('/')}/claims/close", event.payload)
    except TransportError as exc:
        return mark_failed(session, event, exc)
    return mark_delivered(session, event, answer)
