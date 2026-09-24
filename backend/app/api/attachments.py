"""Adjuntos de oficina (RF-017).

Los sube quien planifica o la oficina técnica; los lee cualquiera que ejecute o revise el trabajo —
incluida la cuadrilla, que es para quien existen.

La subida llega como metadatos, no como bytes: el archivo va al almacenamiento de objetos por la
vía que ya usan las evidencias, y esta API registra qué es, cuánto pesa y con qué hash. Así el
endpoint no se convierte en un proxy de 25 MB por petición, y el hash que queda registrado es el
que el cliente calculó sobre lo que subió.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.attachments import service as attachments
from app.attachments.models import AttachmentKind, WorkOrderAttachment
from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.workorders.models import WorkOrder

router = APIRouter(
    prefix="/api/v1/attachments", tags=["attachments"], dependencies=[Depends(unit_scope)]
)

SessionDep = Annotated[Session, Depends(get_session)]

#: Quien adjunta: planificación y la oficina técnica.
WRITERS = (Role.PLANNER, Role.FUNCTIONAL_ADMIN, Role.GIS_EDITOR)

#: Quien lee: además, la cuadrilla y el supervisor. El técnico es el destinatario del adjunto.
READERS = (*WRITERS, Role.SUPERVISOR, Role.TECHNICIAN, Role.CREW_LEADER, Role.INSPECTOR)


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _order(session: Session, unit: BusinessUnit, work_order_id: uuid.UUID) -> WorkOrder:
    order = session.get(WorkOrder, work_order_id)
    if order is None or order.business_unit_id != unit.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "la OT no existe en esta unidad de negocio")
    return order


def _attachment(
    session: Session, unit: BusinessUnit, attachment_id: uuid.UUID
) -> WorkOrderAttachment:
    row = session.get(WorkOrderAttachment, attachment_id)
    if row is None or row.business_unit_id != unit.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "el adjunto no existe en esta unidad de negocio"
        )
    return row


class AttachIn(BaseModel):
    """Los metadatos del archivo ya subido al almacenamiento.

    Sin `uploaded_by`: el autor sale del token. Un adjunto cuyo autor pudiera escribir el llamante
    sería un plano que nadie firmó, y el plano es lo que la cuadrilla va a ejecutar.
    """

    title: str = Field(min_length=1, max_length=255)
    filename: str = Field(min_length=1, max_length=255)
    storage_key: str = Field(min_length=1, max_length=512)
    content_hash: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(gt=0)
    mime_type: str = Field(min_length=1, max_length=64)
    kind: AttachmentKind = AttachmentKind.DOCUMENT
    note: str | None = Field(default=None, max_length=2000)
    #: False para lo que no se abre en el sitio: un estudio de 20 MB que nadie lee con guantes.
    offline: bool = True


class WithdrawIn(BaseModel):
    """El motivo es obligatorio: la cuadrilla pudo haber trabajado con este plano."""

    reason: str = Field(min_length=1, max_length=2000)


@router.get(
    "/units/{unit_code}/work-orders/{work_order_id}",
    summary="Los adjuntos de una OT, incluidos los de su obra (RF-017)",
)
def index(
    unit_code: str,
    work_order_id: uuid.UUID,
    session: SessionDep,
    include_withdrawn: Annotated[bool, Query()] = False,
    _: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    order = _order(session, unit, work_order_id)
    rows = attachments.attachments_of(session, order, include_withdrawn=include_withdrawn)
    return {
        "work_order_id": str(order.id),
        # Lo que la cuadrilla va a descargar, dicho en claro: es lo que decide si el paquete cabe
        # en el enlace que de verdad tiene.
        "offline_bytes": attachments.offline_bytes(session, order),
        "max_offline_bytes": attachments.MAX_OFFLINE_BYTES_PER_ORDER,
        "attachments": [attachments.as_dict(row) for row in rows],
    }


@router.post(
    "/units/{unit_code}/work-orders/{work_order_id}",
    dependencies=[Depends(require_roles(*WRITERS))],
    summary="Adjuntar un plano o documento a la OT (RF-017)",
)
def attach(
    unit_code: str,
    work_order_id: uuid.UUID,
    payload: AttachIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*WRITERS))] = None,
) -> dict[str, Any]:
    """El archivo ya está en el almacenamiento; esto registra qué es y con qué hash."""
    unit = _unit(session, unit_code)
    order = _order(session, unit, work_order_id)
    try:
        row = attachments.attach(
            session,
            unit,
            order,
            title=payload.title,
            filename=payload.filename,
            storage_key=payload.storage_key,
            content_hash=payload.content_hash,
            size_bytes=payload.size_bytes,
            mime_type=payload.mime_type,
            uploaded_by=principal.subject,
            kind=payload.kind.value,
            note=payload.note,
            offline=payload.offline,
        )
    except attachments.UnsupportedTypeError as exc:
        # 415: el tipo es el problema, y la diferencia con «pesa demasiado» importa para quien
        # tiene que volver a exportar el archivo.
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    except attachments.TooLargeError as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except attachments.AttachmentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return attachments.as_dict(row)


@router.post(
    "/units/{unit_code}/{attachment_id}/withdraw",
    dependencies=[Depends(require_roles(*WRITERS))],
    summary="Retirar un adjunto sin borrarlo (RF-017)",
)
def withdraw(
    unit_code: str,
    attachment_id: uuid.UUID,
    payload: WithdrawIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*WRITERS))] = None,
) -> dict[str, Any]:
    """Retirado, nunca borrado: la cuadrilla pudo ejecutar el trabajo con el plano viejo."""
    unit = _unit(session, unit_code)
    row = _attachment(session, unit, attachment_id)
    try:
        attachments.withdraw(session, unit, row, actor=principal.subject, reason=payload.reason)
    except attachments.AttachmentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return attachments.as_dict(row)
