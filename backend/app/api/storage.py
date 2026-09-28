"""Firmar una subida al almacenamiento de objetos (RF-005, RF-017).

El paso que faltaba entre «tengo el archivo en el teléfono» y «el servidor sabe que existe»:
esto entrega una URL de `PUT`, el cliente sube el archivo directo a SeaweedFS con ella, y solo
entonces llama a los endpoints que ya existían —`attachments.attach`, la sincronización de
evidencias— con el `storage_key` que aquí se le dio y el hash que calculó sobre lo que subió.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.storage import service as storage

router = APIRouter(prefix="/api/v1/storage", tags=["storage"], dependencies=[Depends(unit_scope)])

SessionDep = Annotated[Session, Depends(get_session)]

#: Quien sube evidencia desde el campo, y quien sube adjuntos desde la oficina (RF-005, RF-017).
#: Un solo endpoint para los dos: la política de qué se admite vive en `app.storage.service`, por
#: propósito, así que el rol no tiene que decidir nada que el servicio no vaya a comprobar igual.
UPLOADERS = (
    Role.TECHNICIAN,
    Role.CREW_LEADER,
    Role.INSPECTOR,
    Role.PLANNER,
    Role.FUNCTIONAL_ADMIN,
    Role.GIS_EDITOR,
)


def _unit(session: Session, code: str) -> Any:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


class PresignIn(BaseModel):
    purpose: str = Field(pattern="^(adjunto|evidencia)$")
    #: El tipo dentro del propósito: para `evidencia`, un `EvidenceKind` (`foto`, `audio`,
    #: `firma`, `croquis`, `documento`); para `adjunto`, cualquier `AttachmentKind`.
    kind: str = Field(min_length=1, max_length=32)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=64)
    size_bytes: int = Field(gt=0)


@router.post(
    "/units/{unit_code}/presign",
    dependencies=[Depends(require_roles(*UPLOADERS))],
    summary="Firmar la subida de un archivo de evidencia o de un adjunto (RF-005, RF-017)",
)
def presign(unit_code: str, payload: PresignIn, session: SessionDep) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    try:
        upload = storage.presign_upload(
            unit,
            purpose=payload.purpose,
            kind=payload.kind,
            filename=payload.filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
        )
    except storage.StorageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return upload.as_dict()
