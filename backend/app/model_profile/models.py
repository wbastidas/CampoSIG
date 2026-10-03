"""The versioned profile draft, as a table (RF-301).

Kept in a module named ``models`` because :func:`app.infra.database.import_all_models`
discovers by module name; a table in a differently-named module is a table Alembic cannot
see, which this codebase has already paid for once.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base

STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_SUPERSEDED = "superseded"


class ProfileDraft(Base):
    """One version of a data-model profile, in whatever state it is in."""

    __tablename__ = "profile_draft"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    #: The id the produced profile carries. Several units may share it, exactly as the
    #: file-based profiles do.
    profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_DRAFT)

    #: The snapshot the decisions were taken against. Kept so a published profile can be
    #: traced to the metadata that justified it.
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gis_metadata_snapshot.id", ondelete="SET NULL")
    )

    #: What the person chose: class per asset type, field per attribute.
    decisions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    #: The materialised profile. Present once the decisions build into one.
    document: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    #: What still blocks publication (RF-302). Empty means ready.
    problems: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(128))
    published_by: Mapped[str | None] = mapped_column(String(128))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "business_unit_id", "profile_id", "version", name="uq_profile_draft_version"
        ),
        # One open draft, and one published version, per unit and profile. Expressed as
        # partial unique indexes so the database refuses the race rather than the screen
        # discovering it afterwards.
        Index(
            "uq_profile_draft_open",
            "business_unit_id",
            "profile_id",
            unique=True,
            postgresql_where="status = 'draft'",
        ),
        Index(
            "uq_profile_draft_published",
            "business_unit_id",
            "profile_id",
            unique=True,
            postgresql_where="status = 'published'",
        ),
        Index("ix_profile_draft_unit", "business_unit_id", "status"),
    )

    @property
    def ready(self) -> bool:
        return self.document is not None and not self.problems
