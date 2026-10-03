"""Office attachments: the drawings and documents a crew needs on site (RF-017).

«Adjuntos de oficina: planos, diseños y documentos PDF visibles offline en el móvil», and the
acceptance is four words long: «un PDF adjunto se abre en modo avión».

Those four words are the whole design. A file the platform serves on demand is a file that does not
exist in a substation with no coverage, so an attachment is not «a link on the work-order screen»:
it is **part of the offline package**, listed in the manifest with its hash, downloaded before the
crew leaves, and opened from the device's own storage.

Three decisions follow:

* **The hash is in the manifest, not only in the row.** It is what lets a phone say «I already hold
  this plan» and skip a 4 MB download over a cellular link the unit pays for — and what lets it
  notice that the drawing changed after the work order was assigned, which happens.
* **Size is a first-class field, and there is a limit.** A crew with a 300 MB set of drawings and a
  2G link has no drawings. The limit lives in settings, and exceeding it is refused at upload with
  the number, rather than discovered by a technician standing in a field.
* **An attachment belongs to a work order, and may be shared by the fronts of one work.** A civil
  work has one set of drawings and six fronts (RF-015); copying the file six times would make six
  downloads of the same thing.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


class AttachmentKind(StrEnum):
    """What the office is sending, in the words the areas use.

    The kind is not decoration: a `plano` is what a crew opens on site and what has to be in the
    package; a `referencia` may be a 40 MB study that nobody reads in the field, and the planner
    decides whether it travels.
    """

    DRAWING = "plano"
    DESIGN = "diseno"
    DOCUMENT = "documento"
    PERMIT = "permiso"
    REFERENCE = "referencia"


class WorkOrderAttachment(Base):
    """One file the office attached to a work order."""

    __tablename__ = "work_order_attachment"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False
    )

    kind: Mapped[str] = mapped_column(String(16), nullable=False, default=AttachmentKind.DOCUMENT)
    #: What the crew sees in the list. Required: «documento_1.pdf» is not a title.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    #: Key in object storage. The file itself never touches the database, like evidence.
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    #: The name the office's file had. Kept so a crew asking «which one is the structural drawing?»
    #: can be answered with the name they know, not with a UUID.
    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    #: Whether this file travels in the offline package. True by default for what a crew opens on
    #: site; the planner turns it off for a study nobody reads in the field, because a package is
    #: something somebody downloads over a link the unit pays for.
    offline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    #: Withdrawn rather than deleted: a crew may have executed the work with the old drawing, and an
    #: attachment that vanished would make the review of that work unanswerable.
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_by: Mapped[str | None] = mapped_column(String(255))
    withdrawn_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        #: The same file twice on one order is the office sending it again, not two attachments.
        UniqueConstraint("work_order_id", "content_hash", name="uq_work_order_attachment_content"),
        Index("ix_work_order_attachment_order", "work_order_id"),
        Index("ix_work_order_attachment_unit", "business_unit_id", "offline"),
    )

    @property
    def is_active(self) -> bool:
        return self.withdrawn_at is None
