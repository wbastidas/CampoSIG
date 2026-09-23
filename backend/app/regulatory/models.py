"""Regulatory values as parameters, never as constants (SRS 1.4, ADR-007).

The numbers a regulator publishes change with each resolution, and a number in the source
code is a number nobody can date. So every regulatory limit lives here with three things
that make it auditable: its **value**, the **period it was in force**, and the **reference to
the norm** it comes from.

Two design points are load-bearing:

* **A parameter is never overwritten.** A new resolution closes the previous row and opens a
  new one. An approval made last year has to remain explicable against the limit that was in
  force last year, and an update in place destroys exactly that.
* **A value nobody verified is not a value.** ``verified_by`` and ``verified_at`` are the
  difference between a limit read from the official text and a plausible-looking number
  somebody typed. An unverified parameter still evaluates, but the rules report it as
  unverified instead of returning a compliance verdict (ADR-007's whole point is that a
  regulatory answer must be checkable).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


class RegulatoryParameter(Base):
    """One regulatory value, with its period of force and its source."""

    __tablename__ = "regulatory_parameter"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    #: Stable code the rules ask for, e.g. ``apg.restoration_hours.urban``. Canonical and
    #: platform-owned: it must not change when a resolution changes the value.
    code: Mapped[str] = mapped_column(String(128), nullable=False)

    #: JSONB because a limit is not always a scalar: it can be a threshold, a range, or a
    #: table keyed by voltage level. The rule that reads it knows its shape.
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text)

    #: The norm and, when it exists, the exact article or numeral. Without this an
    #: observation cannot cite its source, and an observation without a citation is an
    #: opinion (SRS 10.4: "cero observaciones sin evidencia citada").
    norm_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    article_ref: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(1000))

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    #: Null while in force. A new resolution closes this row rather than replacing it.
    effective_to: Mapped[date | None] = mapped_column(Date)

    #: Who read the official text and confirmed this value, and when. Unverified values
    #: evaluate but never produce a compliance verdict on their own.
    verified_by: Mapped[str | None] = mapped_column(String(255))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: True when the platform must refuse to evaluate at all without verification. Reserved
    #: for limits whose breach has a legal consequence.
    strict: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    #: Who loaded the row, and who last touched it (RF-150: «usuario que modificó»). Different
    #: from `verified_by`, which is a stronger claim: that somebody read the official text. A
    #: person can correct a typo in a description without certifying the figure.
    created_by: Mapped[str | None] = mapped_column(String(255))
    updated_by: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # One row per code and start date: re-importing the same resolution updates it
        # instead of stacking duplicates.
        UniqueConstraint("code", "effective_from", name="uq_regulatory_code_from"),
        Index("ix_regulatory_code", "code"),
        # The lookup every rule runs: the value in force for a code on a date.
        Index("ix_regulatory_in_force", "code", "effective_from", "effective_to"),
    )

    @property
    def is_verified(self) -> bool:
        return self.verified_by is not None and self.verified_at is not None

    def in_force_on(self, moment: date) -> bool:
        if moment < self.effective_from:
            return False
        return self.effective_to is None or moment <= self.effective_to


class RevisionAction:
    """What happened to a parameter. Plain constants; the set grows by addition."""

    #: A new period opened.
    CREATED = "creado"
    #: An existing period was edited in place — a corrected figure, a fixed citation.
    CORRECTED = "corregido"
    #: A period was closed because a newer resolution opened the next one.
    CLOSED = "cerrado"
    #: Somebody stated they had read the official text and the value matches (ADR-007).
    VERIFIED = "verificado"


class RegulatoryRevision(Base):
    """Every edit to a parameter, with who made it and what the row said before.

    The periods are the history of the *values* a regulator published. This is the history of the
    *edits* — and it exists because the one mutation the model allows is a correction to an open
    period, which would otherwise overwrite a figure with no trace. «Usuario que modificó» is only
    useful next to what they modified it from.

    Append-only by construction: nothing in the platform updates or deletes a row here, and there
    is no endpoint that could. It is **not** the M16 trail and does not share its hash chain: that
    trail is per business unit and is about field work, while a regulatory parameter is national
    (ADR-009 puts nothing corporate inside a unit's trail).
    """

    __tablename__ = "regulatory_revision"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    #: Insertion order, from the database. `at` cannot carry it: PostgreSQL's `now()` is the
    #: *transaction* clock, so every revision written in one request shares a timestamp to the
    #: microsecond and sorting by it returns them in whatever order the index felt like. A log
    #: whose order is arbitrary cannot answer «what did it say before», which is the only reason it
    #: exists.
    sequence: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), nullable=False, unique=True
    )

    parameter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regulatory_parameter.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: Denormalised on purpose: the code is what a person searches by, and a revision must stay
    #: readable even if somebody ever removes the parameter row it points at.
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    #: The fields that moved, as {field: {from, to}}. Empty for a creation, where everything is new.
    changed: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    note: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_regulatory_revision_code", "code", "sequence"),)
