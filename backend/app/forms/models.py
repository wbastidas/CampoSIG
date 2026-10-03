"""The published-form table (RF-032).

Why the shape lives in the database and not as more files: the files are the authoring surface and
they are **generated** from the data-model profile (rule 3), so they always describe the present.
What a work order needs is the past — the shape somebody published on the day it was created — and
that is a snapshot, not a source file. Keeping historical copies under `forms/` would also mean the
generator had to know not to touch them, which is a rule nobody remembers for long.

There is at most one `publicado` row per code: two would leave «which version does a new order get»
to whichever row a query happened to see first. The partial unique index below is what enforces it,
in the database, rather than a check in the service that a second writer could race.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
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


class PublishedForm(Base):
    """One frozen version of a work-type form."""

    __tablename__ = "published_form"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    #: Publication order, from the database. `published_at` cannot carry it: PostgreSQL's `now()` is
    #: the *transaction* clock, so two publications in one request share a timestamp to the
    #: microsecond and «newest first» becomes whatever the scan returns. The same defect appeared in
    #: the regulatory revision log earlier the same day; the lesson is that ordering an append-only
    #: log by a timestamp is a bug with a long fuse.
    sequence: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), nullable=False, unique=True
    )

    #: Not scoped to a business unit: a form is national, like the data model it is generated from
    #: (ADR-009 shares the mapping profile across units). What differs per unit are the catalogue
    #: values injected at composition time, and those are not frozen here.
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)

    #: The definition as published, and the blocks it referenced. Both, because freezing only the
    #: definition would leave the shape at the mercy of a block edit — the same bug one level down.
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    blocks: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    #: A hash over the frozen shape, so two versions that differ only in the number are visible as
    #: such, and so a test can prove publishing did not pick up a different file.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    published_by: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    obsoleted_by: Mapped[str | None] = mapped_column(String(255))
    obsoleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_published_form_version"),
        Index(
            "uq_published_form_current",
            "code",
            unique=True,
            postgresql_where="state = 'publicado'",
        ),
    )
