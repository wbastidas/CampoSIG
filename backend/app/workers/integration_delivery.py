"""The process that drains the integration outbox (RF-120, RF-124, RF-125, ADR-012).

:func:`publish` writes events; this delivers them. The split is the whole point of ADR-012, and
it puts two requirements on this module:

* **Losing an event must be impossible.** Each event is delivered and marked in its own
  transaction, so a worker killed mid-pass leaves the events it already delivered marked
  delivered and the rest exactly as they were — pending, due, and picked up by the next pass.
  One transaction around the whole batch would risk re-sending everything after a crash.
* **One broken connector must not stop the others.** A call centre in maintenance should not
  hold back the work-order statuses. So a failure is recorded against its own event and the
  pass continues.

There is no retry logic here. Retries are the ledger's: this asks for what is due, tries once,
and records the outcome.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.integrations import callcentre_adapter, workorder_adapter
from app.integrations.models import Connector, EventStatus, IntegrationEvent
from app.integrations.service import due_events, mark_failed
from app.integrations.transport import HttpTransport, Transport, TransportError
from app.org.models import BusinessUnit
from app.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class DeliveryReport:
    """What one pass did. Returned rather than logged only, so a test can assert on it."""

    delivered: int = 0
    failed: int = 0
    #: Events whose connector has no URL configured. Not failures: the connector is simply
    #: not deployed yet, and burning its retries against an empty string would waste them.
    skipped: int = 0
    #: Connectors that had no URL, so the operator can see what is unconfigured.
    unconfigured: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)

    @property
    def attempted(self) -> int:
        return self.delivered + self.failed

    def as_dict(self) -> dict[str, Any]:
        return {
            "delivered": self.delivered,
            "failed": self.failed,
            "skipped": self.skipped,
            "unconfigured": sorted(self.unconfigured),
            "errors": self.errors,
        }


def connector_urls() -> dict[str, str]:
    """Base URL per connector, from settings. Empty string means not configured."""
    settings = get_settings()
    return {
        Connector.WORK_ORDER_SYSTEM.value: settings.work_order_system_url,
        Connector.CALL_CENTRE.value: settings.call_centre_url,
        # The GIS is not reached over HTTP at all: the arcpy agent pulls its batches
        # (ADR-008). Listed so the worker says "not configured" rather than "unknown".
        Connector.GIS.value: "",
    }


def deliver_one(
    session: Session,
    event: IntegrationEvent,
    *,
    transport: Transport,
    base_url: str,
) -> IntegrationEvent:
    """Route one event to the adapter that knows how to send it."""
    if event.connector == Connector.WORK_ORDER_SYSTEM:
        return workorder_adapter.deliver(session, event, transport, base_url=base_url)
    if event.connector == Connector.CALL_CENTRE:
        return callcentre_adapter.deliver(session, event, transport, base_url=base_url)
    # A connector with no adapter is a programming error, not a transport failure. Marked
    # non-retryable so it surfaces on the screen instead of retrying forever.
    return mark_failed(
        session,
        event,
        TransportError(
            f"no hay adaptador de entrega para el conector '{event.connector}'", retryable=False
        ),
    )


def run_once(
    session: Session,
    unit: BusinessUnit | None = None,
    *,
    transport: Transport | None = None,
    urls: dict[str, str] | None = None,
    limit: int | None = None,
) -> DeliveryReport:
    """Deliver everything currently due. One transaction per event.

    :param unit: restrict to one business unit. None drains every unit, which is what the
        scheduled worker does.
    """
    settings = get_settings()
    sender = transport or HttpTransport()
    endpoints = urls if urls is not None else connector_urls()
    report = DeliveryReport()

    events = due_events(session, unit, limit=limit or settings.integration_batch_size)
    for event in events:
        base_url = endpoints.get(event.connector, "")
        if not base_url:
            report.skipped += 1
            report.unconfigured.add(event.connector)
            continue

        try:
            deliver_one(session, event, transport=sender, base_url=base_url)
        except Exception as exc:
            # An adapter raising instead of recording is a bug, but the pass has other events
            # to deliver and the ledger is where this belongs.
            mark_failed(session, event, exc)
            logger.exception("fallo inesperado entregando el evento %s", event.id)

        # Committed per event: a worker killed here leaves what it delivered marked delivered
        # and the rest untouched. One transaction around the batch would re-send everything.
        session.commit()

        if event.status == EventStatus.DELIVERED:
            report.delivered += 1
        else:
            report.failed += 1
            if event.last_error:
                report.errors.append(f"{event.connector}/{event.kind}: {event.last_error}")

    if report.unconfigured:
        logger.info(
            "conectores sin URL configurada, %d evento(s) en espera: %s",
            report.skipped,
            ", ".join(sorted(report.unconfigured)),
        )
    return report
