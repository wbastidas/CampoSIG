"""The append-only audit trail (RF-160, RF-161).

What makes this table different from every other one is what it must *not* allow. RF-160's
acceptance criterion is two things: no endpoint that edits or deletes the trail, and a hash chain
that proves nothing was edited or deleted behind the application's back. So the immutability is
enforced three times over, at three different distances from the person who would have to defeat it:

1. **In the database.** Migration 0015 installs a trigger that raises on UPDATE and on DELETE. A
   developer with a psql prompt and good intentions cannot quietly fix a row.
2. **In the code.** A structural test walks the whole application's syntax tree and fails if
   anything but the append function writes to this table, or if the audit router ever grows a
   DELETE, PUT or PATCH route.
3. **In the data.** Every row carries the digest of the row before it, so removing or altering one
   breaks the chain at that point and the verification says where.

The chain is per business unit, not global. Partly ADR-009 — a unit's trail is the unit's — and
partly concurrency: appends serialise against the chain's tail, and one global chain would make
every unit in the country wait behind every other.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DDL,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


class EventKind:
    """What happened. Plain constants: the set grows by addition and never branches on itself."""

    #: A work order, a response or any other record came into existence.
    CREATED = "creacion"
    #: A field's value changed, with the value before and after, and where the new one came from.
    FIELD_CHANGED = "cambio_campo"
    #: A work order moved between states (SRS 3.3).
    TRANSITION = "transicion"
    #: Somebody read an evidence file. Reading a photograph of a customer's premises is an access
    #: worth recording (LOPDP), and RF-160 lists it explicitly.
    EVIDENCE_READ = "acceso_evidencia"
    #: Something left the platform: an acta, a CSV, a batch towards the GIS.
    EXPORTED = "exportacion"
    #: A decision a person took: an approval, a return, a publication.
    DECIDED = "decision"


class ActorKind:
    """Who acted. The distinction RF-160 asks for is human against machine."""

    PERSON = "persona"
    #: A worker, a scheduled pass, the arcpy agent's service account.
    SYSTEM = "sistema"
    #: A model proposed the value. Never the author of a definitive value (regla 8), but it is who
    #: the value came from and the trail has to say so.
    MODEL = "modelo"


class AuditEvent(Base):
    """One immutable entry in a business unit's trail.

    Nothing here is nullable that a reader would need: an event whose actor is unknown is recorded
    with the system as its actor and says which worker, rather than leaving a null that a future
    reader will interpret as "somebody".
    """

    __tablename__ = "audit_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="RESTRICT"), nullable=False
    )
    #: Position in this unit's chain, from 1. Unique per unit, which is what makes a removed row
    #: detectable even if somebody also recomputed the hashes.
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    #: What the event is about: 'orden_trabajo', 'respuesta', 'evidencia', 'documento', 'perfil'…
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    #: The subject's identifier as text, because subjects are not all UUIDs — an asset code is not.
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    #: The work order the event belongs to, when there is one. Denormalised on purpose: RF-161's
    #: first question is "the complete history of this work order", and it should not need a join
    #: through five tables to answer.
    work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="RESTRICT")
    )
    #: The asset, for the second question RF-161 asks.
    asset_code: Mapped[str | None] = mapped_column(String(64))

    actor_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    #: The token's subject for a person, the worker's name for the system, the model's name and
    #: version for a model.
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    #: The device the action came from, for the fourth question RF-161 asks.
    device_key: Mapped[str | None] = mapped_column(String(128))

    #: The event's own detail: before and after for a field change, the states for a transition, the
    #: storage key for an access. Whatever it is, it is inside the digest.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    #: Free-text reason where the domain required one (a suspension, a return, an annulment).
    reason: Mapped[str | None] = mapped_column(Text)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    #: Digest of the previous event in this unit's chain. Empty string for the first one, rather
    #: than null: a chain that starts with a null is a chain whose first link cannot be checked.
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("business_unit_id", "sequence", name="uq_audit_event_sequence"),
        # The three questions of RF-161, each one an index rather than a scan: an auditor asking for
        # one work order's history should not wait for the unit's whole trail.
        Index("ix_audit_event_work_order", "work_order_id", "sequence"),
        Index("ix_audit_event_asset", "business_unit_id", "asset_code"),
        Index("ix_audit_event_actor", "business_unit_id", "actor"),
        Index("ix_audit_event_device", "business_unit_id", "device_key"),
        Index("ix_audit_event_unit_time", "business_unit_id", "occurred_at"),
    )


#: The append-only guard, as DDL attached to the table.
#:
#: Attached here and not only written into migration 0015 so that **every** database that has this
#: table has the guard: the test suite builds its schema from the metadata, and a guard the tests
#: do not have is a guard whose test would prove nothing. Migration 0015 carries its own literal
#: copy, as migrations should — they are frozen snapshots and must not import application code that
#: will have moved on by the time somebody replays them.
APPEND_ONLY_GUARD = DDL(  # type: ignore[no-untyped-call]
    """
    CREATE OR REPLACE FUNCTION audit_event_is_append_only() RETURNS trigger AS $$
    BEGIN
        -- El doble es de SQLAlchemy, que interpola al estilo de printf dentro de un DDL: con un
        -- solo signo se come la palabra siguiente y el disparador queda con el mensaje mutilado.
        RAISE EXCEPTION 'audit_event es append-only (RF-160): %% rechazado', TG_OP;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER audit_event_no_update
        BEFORE UPDATE ON audit_event
        FOR EACH ROW EXECUTE FUNCTION audit_event_is_append_only();

    CREATE TRIGGER audit_event_no_delete
        BEFORE DELETE ON audit_event
        FOR EACH ROW EXECUTE FUNCTION audit_event_is_append_only();
    """
)

event.listen(AuditEvent.__table__, "after_create", APPEND_ONLY_GUARD)
