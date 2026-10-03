"""URLs firmadas hacia el almacenamiento de objetos: el backend nunca sube ni baja bytes.

Evidencias y adjuntos comparten el mismo hueco desde hace varios incrementos: `register_evidence`
y `attachments.attach` registran un `storage_key` y un hash, y suponen que el archivo **ya está**
en SeaweedFS — pero nada en la plataforma le daba a un cliente la manera de ponerlo ahí. Este
módulo es esa manera: firma una URL de subida (`PUT`), el cliente sube directo al almacenamiento
con ella, y solo entonces llama al registro que ya existía.

Tres decisiones:

* **El backend firma, nunca transporta.** Una API que recibiera el archivo para reenviarlo se
  convertiría en un proxy de 25 MB por petición — el mismo argumento que ya hizo `attachments.py`
  para los adjuntos, y que vale igual para una foto o un audio de evidencia.
* **La política de qué se admite vive aquí, por propósito, no por cada llamador.** Un `adjunto`
  reutiliza los límites que `app.attachments.service` ya declara — el mismo número en dos sitios es
  el mismo número hasta que alguien cambia uno y no el otro—; una `evidencia` tiene los suyos,
  según el tipo (`EvidenceKind`), porque una firma no pesa como un audio.
* **La URL pública no es la interna.** La firma de una URL de S3 incluye el host: el que va a
  resolver el cliente que sube, no el nombre de servicio que solo el backend conoce dentro de
  Docker. `settings.s3_public_url` es ese host; `settings.s3_endpoint_url` queda para cuando el
  propio backend necesite hablar con el almacenamiento (hoy, nunca — firmar no requiere alcanzarlo).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.client import Config as BotoConfig

from app.attachments.service import ALLOWED_MIME_TYPES as ATTACHMENT_MIME_TYPES
from app.attachments.service import MAX_ATTACHMENT_BYTES
from app.org.models import BusinessUnit
from app.settings import get_settings

#: Qué puede subirse y con qué peso, por propósito. `adjunto` reutiliza los límites que
#: `app.attachments.service` ya declara, para que cambiarlos en un solo lugar los cambie en los
#: dos. Los de `evidencia` están aquí por tipo, porque una firma no pesa como un audio de campo.
_ATTACHMENT_LIMITS: dict[str, tuple[tuple[str, ...], int]] = {
    "adjunto": (ATTACHMENT_MIME_TYPES, MAX_ATTACHMENT_BYTES),
}
_EVIDENCE_LIMITS: dict[str, tuple[tuple[str, ...], int]] = {
    "foto": (("image/jpeg", "image/png"), 15 * 1024 * 1024),
    "audio": (("audio/mp4", "audio/aac", "audio/wav", "audio/ogg"), 20 * 1024 * 1024),
    "firma": (("image/png",), 2 * 1024 * 1024),
    "croquis": (("image/png", "image/jpeg"), 5 * 1024 * 1024),
    "documento": (("application/pdf",), MAX_ATTACHMENT_BYTES),
}

#: Un nombre de archivo se limpia antes de entrar en la clave: solo lo que un navegador o un
#: sistema de archivos aceptan sin escapes, y nada de rutas (`/`, `..`) que pudieran salirse del
#: prefijo de la unidad.
_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class StorageError(Exception):
    pass


@dataclass(frozen=True)
class PresignedUpload:
    url: str
    storage_key: str
    method: str
    expires_in: int
    #: Cabeceras que el cliente tiene que mandar exactamente así, o la firma no valida. Hoy es
    #: solo `Content-Type`; se devuelve en vez de suponerlo para no duplicar la regla en el cliente.
    headers: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "storage_key": self.storage_key,
            "method": self.method,
            "expires_in": self.expires_in,
            "headers": self.headers,
        }


def _client() -> Any:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_public_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        # SeaweedFS habla el estilo «path», no el «virtual-hosted» que asume un bucket por
        # subdominio: sin esto, la URL firmada apunta a un host que no existe.
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name="us-east-1",
    )


def read_object(storage_key: str) -> bytes:
    """Los bytes de un objeto, para verificar su hash (RF-073).

    Por el endpoint interno, no el público: el servidor habla con SeaweedFS dentro de su propia red.

    :raises StorageError: si el objeto no está, que es lo normal mientras la subida no termina.
    """
    settings = get_settings()
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name="us-east-1",
    )
    try:
        response = client.get_object(Bucket=settings.s3_bucket, Key=storage_key)
    except Exception as exc:  # botocore lanza varias clases; todas significan «no se pudo leer»
        raise StorageError(f"el archivo «{storage_key}» no está en el almacenamiento") from exc
    body: bytes = response["Body"].read()
    return body


def _safe_filename(filename: str) -> str:
    cleaned = _UNSAFE_FILENAME.sub("-", filename.strip()).strip("-")
    return cleaned or "archivo"


def storage_key_for(unit: BusinessUnit, *, purpose: str, kind: str, filename: str) -> str:
    """Una clave con la unidad al frente, para que un objeto nunca pueda leerse cruzando ADR-009.

    El nombre real del archivo viaja al final: es lo único de la clave que alguien reconoce, y
    perderlo detrás de un UUID puro haría ilegible cualquier auditoría manual del bucket.
    """
    return f"{unit.code}/{purpose}/{kind}/{uuid.uuid4()}-{_safe_filename(filename)}"


def presign_upload(
    unit: BusinessUnit,
    *,
    purpose: str,
    kind: str,
    filename: str,
    content_type: str,
    size_bytes: int,
) -> PresignedUpload:
    """Firmar una subida (RF-076, RF-017).

    :param purpose: `"adjunto"` o `"evidencia"`. Decide qué límites aplican.
    :param kind: para `evidencia`, el `EvidenceKind` (`foto`, `audio`, `firma`, `croquis`,
        `documento`); para `adjunto`, ignorado a efectos de límites (todos comparten los de
        `app.attachments.service`) pero igual entra en la clave, para que el bucket se lea solo.
    :raises StorageError: propósito desconocido, tipo no admitido, o peso fuera de rango.
    """
    limits = _ATTACHMENT_LIMITS if purpose == "adjunto" else _EVIDENCE_LIMITS
    allowed = limits.get(kind if purpose == "evidencia" else purpose)
    if allowed is None:
        known = ", ".join(_EVIDENCE_LIMITS) if purpose == "evidencia" else "adjunto"
        raise StorageError(f"«{kind}» no es un tipo admitido para {purpose}; admitidos: {known}")
    mime_types, max_bytes = allowed
    if content_type not in mime_types:
        raise StorageError(
            f"«{content_type}» no se puede subir como {kind}; admitidos: {', '.join(mime_types)}"
        )
    if size_bytes <= 0:
        raise StorageError("un archivo de cero bytes no es un archivo")
    if size_bytes > max_bytes:
        raise StorageError(
            f"el archivo pesa {_megabytes(size_bytes)} MB y el máximo para {kind} es "
            f"{_megabytes(max_bytes)} MB"
        )

    settings = get_settings()
    key = storage_key_for(unit, purpose=purpose, kind=kind, filename=filename)
    url = _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=settings.s3_presign_expires_seconds,
    )
    return PresignedUpload(
        url=url,
        storage_key=key,
        method="PUT",
        expires_in=settings.s3_presign_expires_seconds,
        headers={"Content-Type": content_type},
    )


def _megabytes(value: int) -> str:
    """Megabytes con una cifra decimal, en es-EC: coma decimal (regla 11)."""
    return f"{value / (1024 * 1024):.1f}".replace(".", ",")
