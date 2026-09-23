"""Appending to the trail, and proving it was not tampered with (RF-160, RF-161).

The append is the only write in the system that touches :class:`AuditEvent`, and a structural test
keeps it that way. Everything else here reads.

Two things are worth explaining because they look like overkill until they are not:

**Appends serialise per business unit.** A hash chain has a tail, and two transactions that both
read the same tail produce two events claiming the same predecessor — one of which the unique
constraint rejects, at commit, after the domain work is done. So the append takes an advisory lock
on the unit first, for the rest of the transaction. The cost is real and small: these events happen
a handful of times per work order, not per request.

**The digest covers the event, not the row.** `id` and `occurred_at`'s microseconds are outside it,
because a chain whose verification depends on a server-generated default is a chain that fails on a
database upgrade for reasons nobody can explain. What is inside is everything a reader would care
about: the unit, the position, the kind, the subject, the actor, the payload and the reason.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.audit.models import ActorKind, AuditEvent

#: The digest of nothing, for the first event of a unit's chain.
GENESIS = ""


def _canonical(
    *,
    business_unit_id: uuid.UUID,
    sequence: int,
    kind: str,
    subject_type: str,
    subject_id: str,
    work_order_id: uuid.UUID | None,
    asset_code: str | None,
    actor_kind: str,
    actor: str,
    device_key: str | None,
    payload: dict[str, Any],
    reason: str | None,
    occurred_at: datetime,
) -> str:
    """The event as one deterministic string.

    Sorted keys and no whitespace, so the same event digests identically on any machine, in any
    Python version, whatever order the caller passed the fields in.
    """
    return json.dumps(
        {
            "business_unit_id": str(business_unit_id),
            "sequence": sequence,
            "kind": kind,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "work_order_id": str(work_order_id) if work_order_id else None,
            "asset_code": asset_code,
            "actor_kind": actor_kind,
            "actor": actor,
            "device_key": device_key,
            "payload": payload,
            "reason": reason,
            # Seconds, not microseconds: the second is what a person reads and what a report
            # quotes, and a digest that depended on microseconds could not survive being re-read
            # through a driver that rounds them.
            "occurred_at": occurred_at.replace(microsecond=0).isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(prev_hash: str, canonical: str) -> str:
    """The link: the previous digest and this event, hashed together."""
    return hashlib.sha256(f"{prev_hash}|{canonical}".encode()).hexdigest()


def _lock(session: Session, business_unit_id: uuid.UUID) -> None:
    """Serialise appends for one unit, for the rest of this transaction.

    Advisory and transaction-scoped: it needs no table, and it is released by the commit or the
    rollback whatever happens, including a failure in the domain work that follows.
    """
    # The lock's key is a stable 63-bit number derived from the unit. `hashtext` would be simpler
    # and is not documented as stable across versions, and a lock key that changes on an upgrade is
    # a lock two processes stop sharing.
    key = int.from_bytes(hashlib.sha256(business_unit_id.bytes).digest()[:8], "big") >> 1
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def _tail(session: Session, business_unit_id: uuid.UUID) -> AuditEvent | None:
    return session.scalars(
        select(AuditEvent)
        .where(AuditEvent.business_unit_id == business_unit_id)
        .order_by(AuditEvent.sequence.desc())
        .limit(1)
    ).first()


def record(
    session: Session,
    business_unit_id: uuid.UUID,
    *,
    kind: str,
    subject_type: str,
    subject_id: str,
    actor: str,
    actor_kind: str = ActorKind.PERSON,
    work_order_id: uuid.UUID | None = None,
    asset_code: str | None = None,
    device_key: str | None = None,
    payload: dict[str, Any] | None = None,
    reason: str | None = None,
    occurred_at: datetime | None = None,
) -> AuditEvent:
    """Append one event. The only function in the platform that writes to the trail.

    Called inside the transaction that did the thing being recorded, always: an event written in its
    own transaction can commit while the change rolls back, and a trail that records work that never
    happened is worse than no trail — it is a trail somebody would defend a decision with.
    """
    _lock(session, business_unit_id)
    previous = _tail(session, business_unit_id)
    sequence = (previous.sequence if previous else 0) + 1
    prev_hash = previous.hash if previous else GENESIS
    # The server's clock, read once, so the value inside the digest is the value in the column.
    when = occurred_at or session.scalar(select(func.now()))
    assert when is not None  # `now()` in a live transaction

    body = payload or {}
    canonical = _canonical(
        business_unit_id=business_unit_id,
        sequence=sequence,
        kind=kind,
        subject_type=subject_type,
        subject_id=subject_id,
        work_order_id=work_order_id,
        asset_code=asset_code,
        actor_kind=actor_kind,
        actor=actor,
        device_key=device_key,
        payload=body,
        reason=reason,
        occurred_at=when,
    )
    event = AuditEvent(
        business_unit_id=business_unit_id,
        sequence=sequence,
        kind=kind,
        subject_type=subject_type,
        subject_id=subject_id,
        work_order_id=work_order_id,
        asset_code=asset_code,
        actor_kind=actor_kind,
        actor=actor,
        device_key=device_key,
        payload=body,
        reason=reason,
        occurred_at=when,
        prev_hash=prev_hash,
        hash=digest(prev_hash, canonical),
    )
    session.add(event)
    session.flush()
    return event


def recompute(event: AuditEvent) -> str:
    """What this event's digest should be, from the row as it stands now."""
    return digest(
        event.prev_hash,
        _canonical(
            business_unit_id=event.business_unit_id,
            sequence=event.sequence,
            kind=event.kind,
            subject_type=event.subject_type,
            subject_id=event.subject_id,
            work_order_id=event.work_order_id,
            asset_code=event.asset_code,
            actor_kind=event.actor_kind,
            actor=event.actor,
            device_key=event.device_key,
            payload=event.payload,
            reason=event.reason,
            occurred_at=event.occurred_at,
        ),
    )


@dataclass(frozen=True)
class ChainCheck:
    """What the verification found."""

    events: int
    #: None when the chain holds. Otherwise the sequence number where it first breaks.
    broken_at: int | None
    #: Why, in words an auditor can put in a report.
    problem: str | None

    @property
    def intact(self) -> bool:
        return self.broken_at is None

    def as_dict(self) -> dict[str, Any]:
        return {
            "events": self.events,
            "intact": self.intact,
            "broken_at": self.broken_at,
            "problem": self.problem,
        }


def verify(session: Session, business_unit_id: uuid.UUID) -> ChainCheck:
    """Walk a unit's chain and say where it first breaks, if it does.

    Three different tamperings, three different findings, and they are worth distinguishing: an
    altered row is somebody editing history, a broken link is somebody removing an event, and a gap
    in the sequence is somebody removing the last one — which the links alone cannot see.
    """
    events = list(
        session.scalars(
            select(AuditEvent)
            .where(AuditEvent.business_unit_id == business_unit_id)
            .order_by(AuditEvent.sequence)
        )
    )
    expected_prev = GENESIS
    expected_sequence = 1
    for event in events:
        if event.sequence != expected_sequence:
            return ChainCheck(
                events=len(events),
                broken_at=event.sequence,
                problem=(
                    f"falta el evento {expected_sequence}: la secuencia salta a {event.sequence}"
                ),
            )
        if event.prev_hash != expected_prev:
            return ChainCheck(
                events=len(events),
                broken_at=event.sequence,
                problem=f"el evento {event.sequence} no encadena con el anterior",
            )
        if recompute(event) != event.hash:
            return ChainCheck(
                events=len(events),
                broken_at=event.sequence,
                problem=f"el evento {event.sequence} fue alterado después de escribirse",
            )
        expected_prev = event.hash
        expected_sequence += 1
    return ChainCheck(events=len(events), broken_at=None, problem=None)


def trail(
    session: Session,
    business_unit_id: uuid.UUID,
    *,
    work_order_id: uuid.UUID | None = None,
    asset_code: str | None = None,
    actor: str | None = None,
    device_key: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[AuditEvent]:
    """The four questions RF-161 asks: by work order, by asset, by user, by device.

    Oldest first, because the answer to all four is a story and a story read backwards is a
    different story. Paginated because a unit's trail grows without bound and the auditor's screen
    does not.
    """
    statement = select(AuditEvent).where(AuditEvent.business_unit_id == business_unit_id)
    if work_order_id is not None:
        statement = statement.where(AuditEvent.work_order_id == work_order_id)
    if asset_code is not None:
        statement = statement.where(AuditEvent.asset_code == asset_code)
    if actor is not None:
        statement = statement.where(AuditEvent.actor == actor)
    if device_key is not None:
        statement = statement.where(AuditEvent.device_key == device_key)
    if since is not None:
        statement = statement.where(AuditEvent.occurred_at >= since)
    if until is not None:
        statement = statement.where(AuditEvent.occurred_at <= until)
    return list(
        session.scalars(statement.order_by(AuditEvent.sequence).limit(limit).offset(offset))
    )


def count(session: Session, business_unit_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count(AuditEvent.id)).where(AuditEvent.business_unit_id == business_unit_id)
        )
        or 0
    )


def as_dict(event: AuditEvent) -> dict[str, Any]:
    return {
        "sequence": event.sequence,
        "kind": event.kind,
        "subject_type": event.subject_type,
        "subject_id": event.subject_id,
        "work_order_id": str(event.work_order_id) if event.work_order_id else None,
        "asset_code": event.asset_code,
        "actor_kind": event.actor_kind,
        "actor": event.actor,
        "device_key": event.device_key,
        "payload": event.payload,
        "reason": event.reason,
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "hash": event.hash,
        "prev_hash": event.prev_hash,
    }
