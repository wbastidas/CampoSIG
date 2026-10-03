"""The internal event bus: publish, deliver, retry, and let a person retry (RF-125).

The pattern is a transactional outbox, and the reason is the one failure that matters most:
an approval that closes a claim must not be able to succeed while the claim stays open. So
:func:`publish` only writes a row — in the caller's transaction, alongside the business
change — and delivery is a separate step that can fail as often as it likes.

Retries back off exponentially and then **stop**. A row that exhausted its attempts becomes
``FAILED`` and waits on the integrations screen, because a connector that has been refusing
calls for six hours needs a person to look at it, not a tighter loop.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.models import (
    Connector,
    Direction,
    EventStatus,
    IntegrationEvent,
)
from app.integrations.transport import Response, TransportError
from app.org.models import BusinessUnit
from app.workorders.models import WorkOrder

#: Attempts before a row waits for a person. Five spans roughly half an hour of backoff,
#: which is long enough to ride out a restart and short enough that nobody finds out about a
#: broken connector the next morning.
MAX_ATTEMPTS = 5

#: Base of the exponential backoff, in seconds.
BACKOFF_BASE_SECONDS = 30

#: Ceiling, so the last attempts are not hours apart.
BACKOFF_MAX_SECONDS = 600


def backoff_for(attempts: int) -> timedelta:
    """Delay before attempt number ``attempts + 1``.

    Shift-based rather than ``**``: the exponent is bounded by construction, so a bad attempt
    count cannot produce an interval measured in years.
    """
    exponent = min(max(attempts, 0), 10)
    seconds = min(BACKOFF_BASE_SECONDS << exponent, BACKOFF_MAX_SECONDS)
    return timedelta(seconds=seconds)


def publish(
    session: Session,
    unit: BusinessUnit,
    *,
    connector: Connector | str,
    direction: Direction | str,
    kind: str,
    idempotency_key: str,
    payload: dict[str, Any] | None = None,
    order: WorkOrder | None = None,
    external_ref: str | None = None,
) -> IntegrationEvent:
    """Record an exchange. Idempotent by (connector, direction, key).

    Called inside the transaction of whatever business change caused it. Nothing here talks to
    the network — that is what makes the event impossible to lose.

    Re-publishing a key that is still pending updates its payload: the newest truth is what
    should be delivered. Re-publishing one already delivered is a no-op, so a retried business
    operation does not tell the corporate system the same thing twice.
    """
    existing = session.scalars(
        select(IntegrationEvent).where(
            IntegrationEvent.connector == str(connector),
            IntegrationEvent.direction == str(direction),
            IntegrationEvent.idempotency_key == idempotency_key,
        )
    ).first()

    if existing is not None:
        if existing.status == EventStatus.DELIVERED:
            return existing
        existing.payload = payload or {}
        existing.status = EventStatus.PENDING
        existing.next_attempt_at = datetime.now(UTC)
        session.flush()
        return existing

    event = IntegrationEvent(
        business_unit_id=unit.id,
        connector=str(connector),
        direction=str(direction),
        kind=kind,
        idempotency_key=idempotency_key,
        payload=payload or {},
        work_order_id=order.id if order else None,
        external_ref=external_ref,
        status=EventStatus.PENDING,
        next_attempt_at=datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    return event


def due_events(
    session: Session,
    unit: BusinessUnit | None = None,
    *,
    connector: Connector | str | None = None,
    limit: int = 50,
    now: datetime | None = None,
) -> list[IntegrationEvent]:
    """Outbound events whose next attempt is due, oldest first."""
    moment = now or datetime.now(UTC)
    statement = select(IntegrationEvent).where(
        IntegrationEvent.status == EventStatus.PENDING,
        IntegrationEvent.direction == Direction.OUTBOUND,
        IntegrationEvent.next_attempt_at <= moment,
    )
    if unit is not None:
        statement = statement.where(IntegrationEvent.business_unit_id == unit.id)
    if connector is not None:
        statement = statement.where(IntegrationEvent.connector == str(connector))
    return list(
        session.scalars(
            statement.order_by(IntegrationEvent.next_attempt_at, IntegrationEvent.created_at).limit(
                limit
            )
        )
    )


def mark_delivered(
    session: Session, event: IntegrationEvent, response: Response | dict[str, Any] | None = None
) -> IntegrationEvent:
    body = response.body if isinstance(response, Response) else response
    event.status = EventStatus.DELIVERED
    event.attempts += 1
    event.delivered_at = datetime.now(UTC)
    event.next_attempt_at = None
    event.last_error = None
    event.response = body or {}
    session.flush()
    return event


def mark_failed(
    session: Session, event: IntegrationEvent, error: TransportError | Exception
) -> IntegrationEvent:
    """Record a failed attempt and schedule the next one, or stop and wait for a person.

    A non-retryable error stops immediately: a 400 means the request is wrong, and sending it
    four more times only adds four more entries to somebody else's error log.
    """
    event.attempts += 1
    event.last_error = str(error)[:2000]
    retryable = getattr(error, "retryable", True)

    if not retryable or event.attempts >= MAX_ATTEMPTS:
        event.status = EventStatus.FAILED
        event.next_attempt_at = None
    else:
        event.status = EventStatus.PENDING
        event.next_attempt_at = datetime.now(UTC) + backoff_for(event.attempts)
    session.flush()
    return event


def retry_now(
    session: Session, event: IntegrationEvent, *, by: str | None = None
) -> IntegrationEvent:
    """Put a failed event back in the queue, from the integrations screen (RF-125).

    The attempt counter is reset: a person pressing retry has usually fixed something, and
    keeping the old count would exhaust the new attempts immediately.
    """
    if event.status == EventStatus.DELIVERED:
        return event
    event.status = EventStatus.PENDING
    event.attempts = 0
    event.next_attempt_at = datetime.now(UTC)
    event.last_error = f"reintento manual solicitado por {by}" if by else "reintento manual"
    session.flush()
    return event


def abandon(session: Session, event: IntegrationEvent, *, reason: str, by: str) -> IntegrationEvent:
    """Give up on an event, on the record.

    Deleting it would be the same decision without the evidence, and the question "why was
    this never sent" has to stay answerable.
    """
    event.status = EventStatus.ABANDONED
    event.next_attempt_at = None
    event.last_error = f"descartado por {by}: {reason}"[:2000]
    session.flush()
    return event


def ledger(
    session: Session,
    unit: BusinessUnit,
    *,
    connector: Connector | str | None = None,
    status: EventStatus | str | None = None,
    order_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[IntegrationEvent]:
    """The consultable log of every exchange (RF-125)."""
    statement = select(IntegrationEvent).where(IntegrationEvent.business_unit_id == unit.id)
    if connector is not None:
        statement = statement.where(IntegrationEvent.connector == str(connector))
    if status is not None:
        statement = statement.where(IntegrationEvent.status == str(status))
    if order_id is not None:
        statement = statement.where(IntegrationEvent.work_order_id == order_id)
    return list(
        session.scalars(statement.order_by(IntegrationEvent.created_at.desc()).limit(limit))
    )


def connector_health(session: Session, unit: BusinessUnit) -> list[dict[str, Any]]:
    """Per-connector state for the integrations screen.

    ``waiting_for_a_person`` is the number that matters: pending events retry themselves, and
    failed ones do not.
    """
    rows = ledger(session, unit, limit=1000)
    summary: dict[str, dict[str, Any]] = {}
    for connector in Connector:
        summary[connector.value] = {
            "connector": connector.value,
            "pending": 0,
            "delivered": 0,
            "waiting_for_a_person": 0,
            "abandoned": 0,
            "last_error": None,
            "last_exchange_at": None,
        }
    for row in rows:
        bucket = summary.setdefault(
            row.connector,
            {
                "connector": row.connector,
                "pending": 0,
                "delivered": 0,
                "waiting_for_a_person": 0,
                "abandoned": 0,
                "last_error": None,
                "last_exchange_at": None,
            },
        )
        if row.status == EventStatus.PENDING:
            bucket["pending"] += 1
        elif row.status == EventStatus.DELIVERED:
            bucket["delivered"] += 1
        elif row.status == EventStatus.FAILED:
            bucket["waiting_for_a_person"] += 1
            if bucket["last_error"] is None:
                bucket["last_error"] = row.last_error
        elif row.status == EventStatus.ABANDONED:
            bucket["abandoned"] += 1
        if bucket["last_exchange_at"] is None and row.created_at is not None:
            bucket["last_exchange_at"] = row.created_at.isoformat()
    return [summary[key] for key in sorted(summary)]
