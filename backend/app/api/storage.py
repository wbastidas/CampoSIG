"""Firmar una subida al almacenamiento de objetos (RF-076, RF-017).

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

#: Quien sube evidencia desde el campo, y quien sube adjuntos desde la oficina (RF-076, RF-017).
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
    summary="Firmar la subida de un archivo de evidencia o de un adjunto (RF-076, RF-017)",
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


# --- subida por partes, reanudable (RF-104) ----------------------------------------------------
# «Cortar la red al 50 % y reanudar no reinicia la subida desde cero.» El teléfono abre la subida,
# pide URLs por parte, sube cada una directo al almacenamiento y, tras un corte, pregunta qué partes
# llegaron — al almacenamiento, no a su memoria — y sigue desde ahí. El backend sigue sin
# transportar un solo byte.


class MultipartRef(BaseModel):
    storage_key: str = Field(min_length=1, max_length=512)
    upload_id: str = Field(min_length=1, max_length=1024)


class PartsIn(MultipartRef):
    part_numbers: list[int] = Field(min_length=1, max_length=1000)


class CompletedPart(BaseModel):
    part_number: int = Field(ge=1, le=10_000)
    etag: str = Field(min_length=1, max_length=256)


class CompleteIn(MultipartRef):
    parts: list[CompletedPart] = Field(min_length=1, max_length=10_000)


def _owned(unit: Any, storage_key: str) -> None:
    # Una clave de otra unidad es «no existe» (ADR-009): firmar partes ajenas es escribir en ellas.
    if not storage.belongs_to(unit, storage_key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "la subida no existe en esta unidad")


@router.post(
    "/units/{unit_code}/multipart",
    dependencies=[Depends(require_roles(*UPLOADERS))],
    summary="Abrir una subida por partes, reanudable (RF-104)",
)
def multipart_start(unit_code: str, payload: PresignIn, session: SessionDep) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    try:
        upload = storage.start_multipart(
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


@router.post(
    "/units/{unit_code}/multipart/parts",
    dependencies=[Depends(require_roles(*UPLOADERS))],
    summary="URLs firmadas para las partes que faltan (RF-104)",
)
def multipart_parts(unit_code: str, payload: PartsIn, session: SessionDep) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    _owned(unit, payload.storage_key)
    try:
        urls = storage.presign_parts(payload.storage_key, payload.upload_id, payload.part_numbers)
    except storage.StorageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return {"urls": {str(number): url for number, url in urls.items()}}


@router.post(
    "/units/{unit_code}/multipart/status",
    dependencies=[Depends(require_roles(*UPLOADERS))],
    summary="Qué partes ya llegaron, para reanudar después de un corte (RF-104)",
)
def multipart_status(unit_code: str, payload: MultipartRef, session: SessionDep) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    _owned(unit, payload.storage_key)
    try:
        parts = storage.uploaded_parts(payload.storage_key, payload.upload_id)
    except storage.StorageError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return {"parts": parts}


@router.post(
    "/units/{unit_code}/multipart/complete",
    dependencies=[Depends(require_roles(*UPLOADERS))],
    summary="Cerrar la subida por partes (RF-104)",
)
def multipart_complete(unit_code: str, payload: CompleteIn, session: SessionDep) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    _owned(unit, payload.storage_key)
    try:
        storage.complete_multipart(
            payload.storage_key,
            payload.upload_id,
            [part.model_dump() for part in payload.parts],
        )
    except storage.StorageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return {"storage_key": payload.storage_key, "parts": len(payload.parts)}


@router.post(
    "/units/{unit_code}/multipart/abort",
    dependencies=[Depends(require_roles(*UPLOADERS))],
    summary="Abandonar una subida por partes (RF-104)",
)
def multipart_abort(unit_code: str, payload: MultipartRef, session: SessionDep) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    _owned(unit, payload.storage_key)
    storage.abort_multipart(payload.storage_key, payload.upload_id)
    return {"storage_key": payload.storage_key, "aborted": True}
