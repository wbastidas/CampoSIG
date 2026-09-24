"""Fault events in, the interruption record back (RF-123).

The OMS knows a feeder tripped before anybody calls; this platform knows what a crew found and when
service came back. RF-123 is those two halves: «recibir eventos de falla y devolver causa, elemento
y horas de reposición», and its acceptance is «una interrupción registrada en F-OP-03 se refleja en
el OMS».

**The report is built by the same classifier the regulatory export uses.** `interruptions.classify`
decides whether an interruption is computable against the threshold in force (ADR-007), and both the
FMIK/TTIK base of RF-132 and the message the OMS receives read it. Two readers of «is this
computable» would drift, and the one that drifted would be the one the regulator eventually sees.

**What the platform will not do is compute an index.** The report carries the duration, the kVA and
the cause; FMIK and TTIK need the unit's installed kVA as a denominator, which lives in the
corporate systems and not here. Sending an index against an assumed denominator would be sending a
number somebody later has to defend in front of the regulator.

**CIM (IEC 61968) is declared, not assumed.** The SRS says «cuando sea posible», and a full CIM
message needs the utility's own OMS profile — which endpoint, which schema version, which code
lists. So the payload carries the platform's own field names plus a `cim` block with the mappings
that are unambiguous, and says so. Inventing a whole CIM envelope would produce something that looks
interoperable and is not, which is worse than a plain payload the integration workshop can map.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.models import Connector, Direction, EventKind, IntegrationEvent
from app.integrations.service import mark_delivered, mark_failed, publish
from app.integrations.transport import Transport, TransportError
from app.org.models import BusinessUnit
from app.responses.models import FormResponse
from app.workorders.models import WorkOrder, WorkOrderSource
from app.workorders.service import create_work_order

#: The form an OMS fault event is attended with. One mapping, stated as configuration: a tripped
#: feeder is a fault attention, and nothing has to infer that.
FAULT_FORM = "F-OP-01"
FAULT_WORK_TYPE = "atencion_falla"


#: What each answer key is called in IEC 61968 where the mapping is unambiguous. Kept as data so the
#: integration workshop can read it, extend it, or replace it with the utility's own profile without
#: touching code — and so nothing here pretends to be a full CIM message.
CIM_MAPPING: dict[str, str] = {
    "interruption_cause": "OutageRecord.cause",
    "started_at_interruption": "OutageRecord.startTime",
    "restored_at_interruption": "OutageRecord.endTime",
    "protection_operated": "OutageRecord.ProtectiveDevice.mRID",
    "kva_affected": "OutageRecord.ratedPowerOutOfService",
}

#: Said in the payload, so whoever maps it knows what they are looking at.
CIM_NOTE = (
    "Correspondencia parcial con IEC 61968: solo los campos cuyo equivalente es inequívoco. Un "
    "mensaje CIM completo necesita el perfil del OMS de la distribuidora (endpoint, versión del "
    "esquema y listas de códigos), que es una decisión del taller de integración"
)


# --- inbound: fault events ------------------------------------------------------------------


def import_fault_events(
    session: Session,
    unit: BusinessUnit,
    transport: Transport,
    *,
    base_url: str,
) -> dict[str, Any]:
    """Turn the OMS's open fault events into work orders, once each (RF-011, RF-123).

    Idempotent by the OMS event id: a network that keeps reporting the same trip while a crew is on
    the way is normal, and it must not produce a second crew.
    """
    url = f"{base_url.rstrip('/')}/events"
    try:
        answer = transport.get(url)
    except TransportError as exc:
        event = publish(
            session,
            unit,
            connector=Connector.OMS,
            direction=Direction.INBOUND,
            kind=EventKind.FAULT_EVENT_RECEIVED,
            idempotency_key=f"import:{base_url}",
            payload={},
        )
        mark_failed(session, event, exc)
        raise

    created: list[str] = []
    known: list[str] = []
    rejected: list[dict[str, str]] = []

    for fault in answer.body.get("items") or []:
        event_id = str(fault.get("event_id") or "").strip()
        if not event_id:
            rejected.append({"event_id": "(sin id)", "reason": "el evento no trae identificador"})
            continue

        ledger = publish(
            session,
            unit,
            connector=Connector.OMS,
            direction=Direction.INBOUND,
            kind=EventKind.FAULT_EVENT_RECEIVED,
            idempotency_key=f"falla:{event_id}",
            payload=fault,
            external_ref=event_id,
        )

        existing = session.scalars(
            select(WorkOrder).where(
                WorkOrder.business_unit_id == unit.id, WorkOrder.external_ref == event_id
            )
        ).first()
        if existing is not None:
            known.append(event_id)
            ledger.work_order_id = existing.id
            mark_delivered(session, ledger, {"already_known": True})
            continue

        order = create_work_order(
            session,
            unit,
            work_type=FAULT_WORK_TYPE,
            form_code=FAULT_FORM,
            # The OMS's own urgency, when it has one. Not inferred from the affected-client count:
            # that arithmetic belongs to the planner and to Annex C, not to a connector.
            priority=str(fault.get("priority") or "alta"),
            source=WorkOrderSource.OMS_EVENT,
            external_ref=event_id,
            description=fault.get("description"),
            asset_type_key=fault.get("asset_type_key"),
            asset_code=fault.get("asset_code"),
            feeder_code=fault.get("feeder_code"),
            zone=fault.get("zone"),
        )
        ledger.work_order_id = order.id
        mark_delivered(session, ledger, {"created": True})
        created.append(event_id)

    session.flush()
    return {"created": created, "already_known": known, "rejected": rejected}


# --- outbound: the interruption record ------------------------------------------------------


def enqueue_interruption_report(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
) -> IntegrationEvent | None:
    """Queue the interruption this order registered, for the OMS (RF-123).

    Returns None when the order is not an interruption record — most orders are not, and an empty
    report would make the OMS's log unreadable for the ones that are.

    Published inside the approval's own transaction, like the claim closure of RF-124 and the
    material movements of RF-122: an approved interruption cannot leave the OMS with the fault still
    open.
    """
    # Imported here and not at module level, deliberately: `app.analytics.interruptions` reads
    # `app.review.service` for the compliance rule, and `app.review.service` calls this function on
    # approval. A module-level import would close that cycle. The form code and the classifier both
    # come from there, so nothing is duplicated to avoid the import — which is the trade this makes:
    # a deferred import instead of a second copy of «which form is an interruption».
    from app.analytics import interruptions

    if order.form_code != interruptions.INTERRUPTION_FORM:
        return None
    response = (
        session.execute(select(FormResponse).where(FormResponse.work_order_id == order.id))
        .scalars()
        .first()
    )
    if response is None or response.submitted_at is None:
        return None

    entry = interruptions.classify(session, order, response)
    answers = entry.answers
    payload: dict[str, Any] = {
        "work_order_id": str(order.id),
        "work_order_code": order.code,
        # The OMS's own event id when the order came from it, so the two systems can meet.
        "event_id": order.external_ref,
        "feeder_code": order.feeder_code,
        "asset_code": order.asset_code,
        "cause": answers.get("interruption_cause"),
        "element": answers.get("protection_operated"),
        "started_at": answers.get("started_at_interruption"),
        "restored_at": answers.get("restored_at_interruption"),
        "restoration_hours": entry.duration_hours,
        "kva_affected": entry.kva,
        "partial_restorations": entry.partial_restorations,
        # The verdict of the rule in force, with the norm it came from. The same classification the
        # regulatory export uses (RF-132), because two readers of this would drift.
        "computable": entry.computable,
        "threshold_seconds": entry.threshold_seconds,
        "threshold_norm": entry.threshold_norm,
        "threshold_verified": entry.threshold_verified,
        # No FMIK and no TTIK: the denominator is the unit's installed kVA and it does not live
        # here. An index against an assumed denominator is a number somebody has to defend later.
        "indices": None,
        "cim": {
            "note": CIM_NOTE,
            "fields": {cim: answers.get(key) for key, cim in CIM_MAPPING.items() if key in answers},
        },
    }
    return publish(
        session,
        unit,
        connector=Connector.OMS,
        direction=Direction.OUTBOUND,
        kind=EventKind.INTERRUPTION_REPORTED,
        # Keyed by the order: a correction after a return updates the report instead of sending the
        # OMS a second interruption for the same event.
        idempotency_key=f"interrupcion:{order.id}",
        payload=payload,
        order=order,
        external_ref=order.external_ref or order.code,
    )


def deliver(
    session: Session, event: IntegrationEvent, transport: Transport, *, base_url: str
) -> IntegrationEvent:
    """Send one queued interruption report."""
    if event.kind != EventKind.INTERRUPTION_REPORTED.value:
        return mark_failed(
            session,
            event,
            TransportError(
                f"el adaptador del OMS no sabe entregar eventos de tipo '{event.kind}'",
                retryable=False,
            ),
        )
    try:
        answer = transport.post(f"{base_url.rstrip('/')}/outages", event.payload)
    except TransportError as exc:
        return mark_failed(session, event, exc)
    return mark_delivered(session, event, answer)


def pending_reports(session: Session, unit: BusinessUnit) -> int:
    """Interruption reports still waiting to reach the OMS.

    For the integrations screen: «se reflejó en el OMS» is the acceptance criterion, and a number
    that stays above zero is the only way a person notices it did not.
    """
    rows = session.execute(
        select(IntegrationEvent).where(
            IntegrationEvent.business_unit_id == unit.id,
            IntegrationEvent.connector == Connector.OMS,
            IntegrationEvent.kind == EventKind.INTERRUPTION_REPORTED.value,
            IntegrationEvent.delivered_at.is_(None),
        )
    ).all()
    return len(rows)


def reported_at(session: Session, order: WorkOrder) -> datetime | None:
    """When this interruption reached the OMS, or None when it has not."""
    event = (
        session.execute(
            select(IntegrationEvent).where(
                IntegrationEvent.work_order_id == order.id,
                IntegrationEvent.kind == EventKind.INTERRUPTION_REPORTED.value,
            )
        )
        .scalars()
        .first()
    )
    if event is None or event.delivered_at is None:
        return None
    delivered = event.delivered_at
    return delivered if delivered.tzinfo else delivered.replace(tzinfo=UTC)
