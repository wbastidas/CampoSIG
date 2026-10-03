"""Attaching office files and getting them onto the phone (RF-017).

The acceptance criterion is «un PDF adjunto se abre en modo avión», so the work of this module is
not storing a file — evidence already does that — but making sure the file **is on the device
before the crew loses coverage**. That is why :func:`for_package` exists and why the manifest
carries the hashes.

Four rules:

* **A type the phone cannot open is refused at upload.** A DWG is a drawing to an engineer and an
  unopenable blob to a technician with gloves on, so the allowed list is PDF and images. Refused
  with the list, at the desk, instead of discovered in a substation.
* **There is a size limit, and it is a number in the message.** A crew with a 300 MB set of drawings
  and a 2G link has no drawings.
* **The same file twice is one attachment.** Keyed by content hash: the office re-sending the
  drawing is the office re-sending it, not a second plan.
* **Withdrawn, never deleted.** A crew may have executed the work with the old drawing, and a file
  that vanished makes the review of that work unanswerable. A withdrawal stops it travelling to new
  packages and says who withdrew it and why.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.attachments.models import AttachmentKind, WorkOrderAttachment
from app.audit.models import EventKind
from app.audit.service import record
from app.org.models import BusinessUnit
from app.workorders.models import WorkOrder

#: What a phone can actually open with no extra software. The list is short on purpose: a format the
#: technician cannot read is a file that wasted a download.
ALLOWED_MIME_TYPES = (
    "application/pdf",
    "image/jpeg",
    "image/png",
)

#: The most one attachment may weigh, in bytes. 25 MB: a set of drawings exported for the field
#: fits, and a 300 MB study does not — which is the point, because a package is downloaded over a
#: link the unit pays for and often over the mobile network of a rural parish.
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024

#: The most one work order's offline attachments may add up to. A limit per file is not enough: ten
#: 20 MB drawings are two hundred megabytes, and the crew still cannot download them.
MAX_OFFLINE_BYTES_PER_ORDER = 60 * 1024 * 1024


class AttachmentError(Exception):
    pass


class UnsupportedTypeError(AttachmentError):
    pass


class TooLargeError(AttachmentError):
    pass


@dataclass
class PackageAttachment:
    """One attachment as the offline manifest lists it."""

    id: uuid.UUID
    work_order_id: uuid.UUID
    title: str
    kind: str
    storage_key: str
    content_hash: str
    size_bytes: int
    mime_type: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "work_order_id": str(self.work_order_id),
            "title": self.title,
            "kind": self.kind,
            "storage_key": self.storage_key,
            # The hash is what lets a phone skip a download it already holds, and what lets it
            # notice that the drawing changed after the order was assigned — which happens.
            "content_hash": self.content_hash,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
        }


def attach(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    title: str,
    filename: str,
    storage_key: str,
    content_hash: str,
    size_bytes: int,
    mime_type: str,
    uploaded_by: str,
    kind: str = AttachmentKind.DOCUMENT,
    note: str | None = None,
    offline: bool = True,
) -> WorkOrderAttachment:
    """Attach one office file to a work order (RF-017).

    :raises UnsupportedTypeError: for a type the phone cannot open.
    :raises TooLargeError: over the per-file limit, or over what the order's package may carry.
    """
    if order.business_unit_id != unit.id:
        raise AttachmentError("la OT no es de esta unidad de negocio")
    if mime_type not in ALLOWED_MIME_TYPES:
        raise UnsupportedTypeError(
            f"«{mime_type}» no se puede abrir en el teléfono sin software adicional; "
            f"admitidos: {', '.join(ALLOWED_MIME_TYPES)}"
        )
    if not title.strip():
        raise AttachmentError("el adjunto necesita un título: «documento_1.pdf» no es un título")
    if size_bytes <= 0:
        raise AttachmentError("un adjunto de cero bytes no es un adjunto")
    if size_bytes > MAX_ATTACHMENT_BYTES:
        raise TooLargeError(
            f"el archivo pesa {_megabytes(size_bytes)} MB y el máximo por adjunto es "
            f"{_megabytes(MAX_ATTACHMENT_BYTES)} MB: una cuadrilla con un enlace lento y un "
            "archivo así no tiene el archivo"
        )

    existing = session.execute(
        select(WorkOrderAttachment).where(
            WorkOrderAttachment.work_order_id == order.id,
            WorkOrderAttachment.content_hash == content_hash,
        )
    ).scalar_one_or_none()
    if existing is not None:
        # The office re-sending the drawing is the office re-sending it. The title and the note are
        # refreshed —somebody may be correcting them— and a withdrawn one comes back.
        existing.title = title.strip()
        existing.note = note
        existing.kind = kind
        existing.offline = offline
        existing.withdrawn_at = None
        existing.withdrawn_by = None
        existing.withdrawn_reason = None
        session.flush()
        return existing

    if offline:
        _check_package_budget(session, order, adding=size_bytes)

    attachment = WorkOrderAttachment(
        business_unit_id=unit.id,
        work_order_id=order.id,
        kind=kind,
        title=title.strip(),
        note=note,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=size_bytes,
        mime_type=mime_type,
        filename=filename,
        offline=offline,
        uploaded_by=uploaded_by,
    )
    session.add(attachment)
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.CREATED,
        subject_type="work_order_attachment",
        subject_id=str(attachment.id),
        work_order_id=order.id,
        asset_code=order.asset_code,
        actor=uploaded_by,
        payload={
            "title": attachment.title,
            "kind": kind,
            "size_bytes": size_bytes,
            "mime_type": mime_type,
            "offline": offline,
        },
    )
    return attachment


def withdraw(
    session: Session,
    unit: BusinessUnit,
    attachment: WorkOrderAttachment,
    *,
    actor: str,
    reason: str,
) -> WorkOrderAttachment:
    """Stop an attachment travelling, without deleting it.

    A crew may have executed the work with this drawing. Deleting it would make the review of that
    work unanswerable, so the row stays, marked, with who withdrew it and why.
    """
    if not reason.strip():
        raise AttachmentError(
            "retirar un adjunto necesita un motivo: la cuadrilla pudo haber trabajado con él"
        )
    if attachment.withdrawn_at is not None:
        return attachment
    attachment.withdrawn_at = datetime.now(UTC)
    attachment.withdrawn_by = actor
    attachment.withdrawn_reason = reason.strip()
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.FIELD_CHANGED,
        subject_type="work_order_attachment",
        subject_id=str(attachment.id),
        work_order_id=attachment.work_order_id,
        actor=actor,
        payload={"field": "withdrawn_at", "reason": attachment.withdrawn_reason},
    )
    return attachment


def attachments_of(
    session: Session, order: WorkOrder, *, include_withdrawn: bool = False
) -> list[WorkOrderAttachment]:
    """This order's attachments, and the ones its work shares with it (RF-015).

    A civil work has one set of drawings and six fronts; copying the file six times would make six
    downloads of the same thing, so a front sees its parent's attachments too.
    """
    order_ids = [order.id]
    if order.parent_id is not None:
        order_ids.append(order.parent_id)
    query = select(WorkOrderAttachment).where(WorkOrderAttachment.work_order_id.in_(order_ids))
    if not include_withdrawn:
        query = query.where(WorkOrderAttachment.withdrawn_at.is_(None))
    return list(
        session.execute(
            query.order_by(WorkOrderAttachment.kind, WorkOrderAttachment.title)
        ).scalars()
    )


def for_package(
    session: Session, unit: BusinessUnit, *, order_ids: list[uuid.UUID]
) -> list[PackageAttachment]:
    """The attachments that travel in an offline package, for the given work orders (RF-017).

    This function is the acceptance criterion. «Se abre en modo avión» is false unless the file is
    listed here, so it is deliberately the *only* place that decides what travels: withdrawn ones do
    not, `offline=False` ones do not, and another unit's never do (ADR-009).
    """
    if not order_ids:
        return []
    rows = session.execute(
        select(WorkOrderAttachment)
        .where(
            WorkOrderAttachment.business_unit_id == unit.id,
            WorkOrderAttachment.work_order_id.in_(order_ids),
            WorkOrderAttachment.offline.is_(True),
            WorkOrderAttachment.withdrawn_at.is_(None),
        )
        # Ordered, and not as the database felt like returning them: the manifest that carries this
        # list is hashed, and two builds of the same package have to produce the same hash or every
        # publication would look like a change and every phone would re-download.
        .order_by(WorkOrderAttachment.work_order_id, WorkOrderAttachment.content_hash)
    ).scalars()
    return [
        PackageAttachment(
            id=row.id,
            work_order_id=row.work_order_id,
            title=row.title,
            kind=row.kind,
            storage_key=row.storage_key,
            content_hash=row.content_hash,
            size_bytes=row.size_bytes,
            mime_type=row.mime_type,
        )
        for row in rows
    ]


def offline_bytes(session: Session, order: WorkOrder) -> int:
    """What this order's offline attachments weigh, which is what a crew has to download."""
    total = session.execute(
        select(func.coalesce(func.sum(WorkOrderAttachment.size_bytes), 0)).where(
            WorkOrderAttachment.work_order_id == order.id,
            WorkOrderAttachment.offline.is_(True),
            WorkOrderAttachment.withdrawn_at.is_(None),
        )
    ).scalar_one()
    return int(total)


def as_dict(attachment: WorkOrderAttachment) -> dict[str, Any]:
    return {
        "id": str(attachment.id),
        "work_order_id": str(attachment.work_order_id),
        "kind": attachment.kind,
        "title": attachment.title,
        "note": attachment.note,
        "filename": attachment.filename,
        "content_hash": attachment.content_hash,
        "size_bytes": attachment.size_bytes,
        "mime_type": attachment.mime_type,
        "offline": attachment.offline,
        "uploaded_by": attachment.uploaded_by,
        "uploaded_at": attachment.uploaded_at.isoformat() if attachment.uploaded_at else None,
        "withdrawn_at": attachment.withdrawn_at.isoformat() if attachment.withdrawn_at else None,
        "withdrawn_by": attachment.withdrawn_by,
        "withdrawn_reason": attachment.withdrawn_reason,
        "is_active": attachment.is_active,
    }


def _check_package_budget(session: Session, order: WorkOrder, *, adding: int) -> None:
    current = offline_bytes(session, order)
    if current + adding > MAX_OFFLINE_BYTES_PER_ORDER:
        raise TooLargeError(
            f"con este archivo la OT llevaría {_megabytes(current + adding)} MB de adjuntos "
            f"offline y el máximo es {_megabytes(MAX_OFFLINE_BYTES_PER_ORDER)} MB: un límite por "
            "archivo no alcanza, porque diez planos de 20 MB son doscientos megabytes y la "
            "cuadrilla sigue sin poder descargarlos. Marque como no-offline lo que no se abre en "
            "el sitio"
        )


def _megabytes(value: int) -> str:
    """Megabytes with one decimal, in es-EC: coma decimal (regla 11)."""
    return f"{value / (1024 * 1024):.1f}".replace(".", ",")
