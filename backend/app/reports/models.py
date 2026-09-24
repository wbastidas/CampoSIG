"""Documents the platform issued, so a QR code can verify one (RF-115).

The register exists because of what "verification" has to mean. A QR that merely opens a page
showing the hash printed next to it verifies nothing: the page would be echoing the paper. What
makes it verification is that the platform recognises the code, and can say which work order
the document belongs to, when it was issued and by whom — and can say **no consta** for a code
it never issued.

So every issuance is a row. Reprinting is a new row, not an edit: two pieces of paper exist in
the world, and an audit that could not tell them apart would be worse than no register.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base

#: The only kind so far. Named rather than implied so the register can hold the GIS batch
#: export sheet later without a migration.
KIND_ACTA = "acta"


class IssuedDocument(Base):
    """One PDF the platform produced, identified by an unguessable code."""

    __tablename__ = "issued_document"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False
    )
    response_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("form_response.id", ondelete="SET NULL")
    )

    kind: Mapped[str] = mapped_column(String(24), nullable=False, default=KIND_ACTA)

    #: What the QR carries. Unguessable on purpose: a sequential code would let anybody
    #: enumerate every acta the utility ever issued.
    verification_code: Mapped[str] = mapped_column(String(32), nullable=False)

    #: SHA-256 of the PDF bytes. Printed on the document so a person holding the file can
    #: check it with `sha256sum`, and stored here so the platform can confirm it.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)

    #: The state the work order was in when this was printed. An acta of a work order that was
    #: not yet approved is a draft, and the paper says so; the register has to agree.
    state_at_issue: Mapped[str] = mapped_column(String(32), nullable=False)
    form_code: Mapped[str | None] = mapped_column(String(32))
    form_version: Mapped[str | None] = mapped_column(String(16))

    issued_by: Mapped[str] = mapped_column(String(255), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("verification_code", name="uq_issued_document_code"),
        Index("ix_issued_document_order", "work_order_id"),
        Index("ix_issued_document_unit", "business_unit_id"),
    )
