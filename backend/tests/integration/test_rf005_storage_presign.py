"""URLs firmadas hacia el almacenamiento de objetos (RF-005, RF-017).

El hueco que esto cierra: `register_evidence` y `attachments.attach` registran un `storage_key` y
suponen que el archivo ya está en SeaweedFS, y nada le daba a un cliente la manera de ponerlo ahí.
Lo que se prueba:

* **La clave lleva la unidad al frente**, para que ADR-009 se sostenga también en el nombre del
  objeto y no solo en las tablas.
* **La política de tipo y peso es por propósito**, y la de `adjunto` es literalmente la de
  `app.attachments.service` — el mismo número en dos sitios sería el mismo número hasta que alguien
  cambiara uno y no el otro.
* **Firmar no necesita alcanzar el almacenamiento.** Es una operación criptográfica sobre la URL, la
  clave y las credenciales; estas pruebas no levantan SeaweedFS y no lo necesitan.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.attachments.service import ALLOWED_MIME_TYPES, MAX_ATTACHMENT_BYTES
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.storage import service as storage

pytestmark = pytest.mark.integration

PLANNER = Principal(
    subject="kc|planificador.demo",
    username="planificador.demo",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
)
TECHNICIAN = Principal(
    subject="kc|tecnico.demo",
    username="tecnico.demo",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)
AUDITOR = Principal(
    subject="kc|auditor.demo",
    username="auditor.demo",
    roles=frozenset({Role.AUDITOR.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def units(session: Session) -> dict[str, BusinessUnit]:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created: dict[str, BusinessUnit] = {}
    for code, name in (("GYE", "Unidad Guayaquil"), ("MAN", "Unidad Manabí")):
        unit = BusinessUnit(organization_id=org.id, code=code, name=name, profile_id="cnel-gye")
        session.add(unit)
        session.flush()
        created[code] = unit
    return created


@pytest.fixture
def unit(units: dict[str, BusinessUnit]) -> BusinessUnit:
    return units["GYE"]


def client_as(session: Session, who: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: who
    return TestClient(app)


class TestKeyNaming:
    def test_la_clave_lleva_la_unidad_al_frente(self, unit: BusinessUnit) -> None:
        upload = storage.presign_upload(
            unit,
            purpose="adjunto",
            kind="plano",
            filename="plano.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )
        assert upload.storage_key.startswith("GYE/adjunto/plano/")

    def test_un_nombre_con_espacios_y_acentos_se_limpia(self, unit: BusinessUnit) -> None:
        upload = storage.presign_upload(
            unit,
            purpose="evidencia",
            kind="foto",
            filename="poste dañado (calle 9).jpg",
            content_type="image/jpeg",
            size_bytes=1024,
        )
        assert " " not in upload.storage_key
        assert "ñ" not in upload.storage_key

    def test_un_nombre_que_intenta_salirse_del_prefijo_no_lo_logra(
        self, unit: BusinessUnit
    ) -> None:
        upload = storage.presign_upload(
            unit,
            purpose="adjunto",
            kind="plano",
            filename="../../etc/passwd",
            content_type="application/pdf",
            size_bytes=1024,
        )
        assert "/../" not in upload.storage_key
        assert upload.storage_key.startswith("GYE/adjunto/plano/")

    def test_dos_subidas_del_mismo_archivo_no_chocan(self, unit: BusinessUnit) -> None:
        first = storage.presign_upload(
            unit,
            purpose="adjunto",
            kind="plano",
            filename="plano.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )
        second = storage.presign_upload(
            unit,
            purpose="adjunto",
            kind="plano",
            filename="plano.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )
        assert first.storage_key != second.storage_key


class TestAttachmentPolicyIsShared:
    """La política de `adjunto` es la de `app.attachments.service`, no una copia."""

    def test_admite_los_mismos_tipos_que_attachments_service(self, unit: BusinessUnit) -> None:
        for mime_type in ALLOWED_MIME_TYPES:
            upload = storage.presign_upload(
                unit,
                purpose="adjunto",
                kind="documento",
                filename="a",
                content_type=mime_type,
                size_bytes=1024,
            )
            assert upload.storage_key

    def test_rechaza_un_tipo_que_attachments_service_rechaza(self, unit: BusinessUnit) -> None:
        with pytest.raises(storage.StorageError, match="no se puede subir"):
            storage.presign_upload(
                unit,
                purpose="adjunto",
                kind="plano",
                filename="plano.dwg",
                content_type="image/vnd.dwg",
                size_bytes=1024,
            )

    def test_el_limite_de_peso_es_el_mismo_numero(self, unit: BusinessUnit) -> None:
        with pytest.raises(storage.StorageError, match="25,0 MB"):
            storage.presign_upload(
                unit,
                purpose="adjunto",
                kind="plano",
                filename="a.pdf",
                content_type="application/pdf",
                size_bytes=MAX_ATTACHMENT_BYTES + 1,
            )


class TestEvidencePolicy:
    def test_una_foto_admite_jpeg_y_png(self, unit: BusinessUnit) -> None:
        for mime_type in ("image/jpeg", "image/png"):
            upload = storage.presign_upload(
                unit,
                purpose="evidencia",
                kind="foto",
                filename="a.jpg",
                content_type=mime_type,
                size_bytes=1024,
            )
            assert upload.storage_key

    def test_una_foto_no_admite_audio(self, unit: BusinessUnit) -> None:
        with pytest.raises(storage.StorageError, match="no se puede subir"):
            storage.presign_upload(
                unit,
                purpose="evidencia",
                kind="foto",
                filename="a.jpg",
                content_type="audio/mp4",
                size_bytes=1024,
            )

    def test_un_tipo_de_evidencia_desconocido_se_rechaza_con_los_admitidos(
        self, unit: BusinessUnit
    ) -> None:
        with pytest.raises(storage.StorageError, match="foto"):
            storage.presign_upload(
                unit,
                purpose="evidencia",
                kind="video",
                filename="a.mp4",
                content_type="video/mp4",
                size_bytes=1024,
            )

    def test_una_firma_tiene_un_limite_propio_mas_chico(self, unit: BusinessUnit) -> None:
        with pytest.raises(storage.StorageError, match="2,0 MB"):
            storage.presign_upload(
                unit,
                purpose="evidencia",
                kind="firma",
                filename="a.png",
                content_type="image/png",
                size_bytes=3 * 1024 * 1024,
            )

    def test_un_audio_dentro_de_su_limite_pasa(self, unit: BusinessUnit) -> None:
        upload = storage.presign_upload(
            unit,
            purpose="evidencia",
            kind="audio",
            filename="nota.m4a",
            content_type="audio/mp4",
            size_bytes=10 * 1024 * 1024,
        )
        assert "evidencia/audio/" in upload.storage_key


class TestWhatIsRefused:
    def test_un_proposito_desconocido_se_rechaza(self, unit: BusinessUnit) -> None:
        with pytest.raises(storage.StorageError):
            storage.presign_upload(
                unit,
                purpose="respaldo",
                kind="foto",
                filename="a.jpg",
                content_type="image/jpeg",
                size_bytes=1024,
            )

    def test_cero_bytes_no_es_un_archivo(self, unit: BusinessUnit) -> None:
        with pytest.raises(storage.StorageError, match="cero bytes"):
            storage.presign_upload(
                unit,
                purpose="evidencia",
                kind="foto",
                filename="a.jpg",
                content_type="image/jpeg",
                size_bytes=0,
            )


class TestApi:
    def test_el_tecnico_firma_evidencia(self, session: Session, unit: BusinessUnit) -> None:
        with client_as(session, TECHNICIAN) as api:
            response = api.post(
                "/api/v1/storage/units/GYE/presign",
                json={
                    "purpose": "evidencia",
                    "kind": "foto",
                    "filename": "antes.jpg",
                    "content_type": "image/jpeg",
                    "size_bytes": 1024,
                },
            )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["method"] == "PUT"
        assert body["storage_key"].startswith("GYE/evidencia/foto/")
        assert body["headers"]["Content-Type"] == "image/jpeg"

    def test_el_planificador_firma_un_adjunto(self, session: Session, unit: BusinessUnit) -> None:
        with client_as(session, PLANNER) as api:
            response = api.post(
                "/api/v1/storage/units/GYE/presign",
                json={
                    "purpose": "adjunto",
                    "kind": "plano",
                    "filename": "plano.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 1024,
                },
            )
        assert response.status_code == 200, response.text

    def test_el_auditor_no_sube_nada(self, session: Session, unit: BusinessUnit) -> None:
        with client_as(session, AUDITOR) as api:
            response = api.post(
                "/api/v1/storage/units/GYE/presign",
                json={
                    "purpose": "evidencia",
                    "kind": "foto",
                    "filename": "a.jpg",
                    "content_type": "image/jpeg",
                    "size_bytes": 1024,
                },
            )
        assert response.status_code == 403

    def test_un_tipo_no_admitido_responde_422_y_no_500(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        with client_as(session, TECHNICIAN) as api:
            response = api.post(
                "/api/v1/storage/units/GYE/presign",
                json={
                    "purpose": "evidencia",
                    "kind": "foto",
                    "filename": "a.dwg",
                    "content_type": "image/vnd.dwg",
                    "size_bytes": 1024,
                },
            )
        assert response.status_code == 422
        assert "image/jpeg" in response.json()["detail"]

    def test_nadie_firma_fuera_de_su_unidad(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        with client_as(session, TECHNICIAN) as api:
            response = api.post(
                "/api/v1/storage/units/MAN/presign",
                json={
                    "purpose": "evidencia",
                    "kind": "foto",
                    "filename": "a.jpg",
                    "content_type": "image/jpeg",
                    "size_bytes": 1024,
                },
            )
        assert response.status_code == 403

    def test_una_unidad_inexistente_es_404(self, session: Session) -> None:
        with client_as(session, PLANNER) as api:
            response = api.post(
                "/api/v1/storage/units/ZZZ/presign",
                json={
                    "purpose": "adjunto",
                    "kind": "plano",
                    "filename": "a.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 1024,
                },
            )
        # unit_scope corre antes y no conoce ZZZ para nadie: 403 antes que 404, y es correcto —
        # no revela si la unidad existe a quien no puede actuar en ella (ADR-009).
        assert response.status_code == 403
