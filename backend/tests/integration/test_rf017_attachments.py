"""Adjuntos de oficina que se abren en modo avión (RF-017).

El criterio de aceptación son cuatro palabras —«un PDF adjunto se abre en modo avión»— y de ahí sale
todo lo que se prueba aquí. Un archivo que el servidor entrega cuando se lo piden es un archivo que
no existe en una subestación sin cobertura, así que la prueba central no es «se guardó la fila»: es
que el adjunto **aparece en el manifiesto del paquete offline**, con su hash y su peso.

Lo demás son las cuatro negativas que hacen que eso sea cierto en el campo y no solo en el papel:

* **Un tipo que el teléfono no abre se rechaza en el escritorio.** Un DWG es un plano para quien
  diseña y un archivo inútil para quien lo abre con guantes puestos.
* **Hay un límite y el número va en el mensaje.** Una cuadrilla con doscientos megabytes de planos y
  un enlace de 2G no tiene planos. Y el límite por archivo no alcanza: diez planos de 20 MB pasan
  uno por uno y no pasan juntos.
* **El mismo archivo dos veces es uno.** La oficina reenviando el plano es la oficina reenviándolo,
  no un segundo plano.
* **Retirado, nunca borrado.** La cuadrilla pudo ejecutar el trabajo con el plano viejo, y un
  adjunto desaparecido dejaría sin respuesta la revisión de ese trabajo.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.attachments import service as attachments
from app.attachments.models import AttachmentKind, WorkOrderAttachment
from app.audit.models import AuditEvent
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.sync.service import build_offline_package
from app.workorders import fronts
from app.workorders.models import WorkOrder, WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

ZONE = "norte"

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
BOTH_UNITS = Principal(
    subject="kc|planificador.matriz",
    username="planificador.matriz",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE", "MAN"}),
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
        ingest_metadata(session, unit, build_metadata("cnel-gye"))
        created[code] = unit
    return created


@pytest.fixture
def unit(units: dict[str, BusinessUnit]) -> BusinessUnit:
    return units["GYE"]


def an_order(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str = "OT-2026-0001",
    state: str = WorkOrderState.ASSIGNED,
    zone: str | None = ZONE,
) -> WorkOrder:
    order = create_work_order(
        session,
        unit,
        work_type="mantenimiento_preventivo",
        form_code="F-MT-01",
        asset_type_key="transformer",
        asset_code="TRF-2201",
        zone=zone,
        planner_id=PLANNER.subject,
    )
    order.state = state
    order.code = code
    session.flush()
    return order


def a_pdf(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    title: str = "Plano estructural del poste 4471",
    body: str = "plano-v1",
    size_bytes: int = 2 * 1024 * 1024,
    mime_type: str = "application/pdf",
    kind: str = AttachmentKind.DRAWING,
    offline: bool = True,
) -> WorkOrderAttachment:
    digest = hashlib.sha256(body.encode()).hexdigest()
    return attachments.attach(
        session,
        unit,
        order,
        title=title,
        filename=f"{title}.pdf",
        storage_key=f"s3://adjuntos/{digest}.pdf",
        content_hash=digest,
        size_bytes=size_bytes,
        mime_type=mime_type,
        uploaded_by=PLANNER.subject,
        kind=kind,
        offline=offline,
    )


def package_attachments(
    session: Session, unit: BusinessUnit, *, zone: str = ZONE
) -> dict[str, Any]:
    """La parte «attachments» del manifiesto, o un vacío explícito si no viaja nada."""
    package = build_offline_package(
        session, unit, zone=zone, tile_url=f"/tiles/{zone}.pmtiles", asset_count=1200
    )
    parts = {part["name"]: part for part in package.manifest["parts"]}
    return parts.get("attachments", {"count": 0, "items": []})


def client_as(session: Session, who: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: who
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, PLANNER) as raw:
        yield raw


class TestAirplaneMode:
    """«Un PDF adjunto se abre en modo avión» — es decir: está en el paquete antes de salir."""

    def test_rf_017_el_pdf_adjunto_viaja_en_el_paquete_offline(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit)
        attachment = a_pdf(session, unit, order)

        part = package_attachments(session, unit)

        assert part["count"] == 1
        item = part["items"][0]
        assert item["id"] == str(attachment.id)
        assert item["storage_key"] == attachment.storage_key
        # El hash es lo que deja al teléfono saltarse una descarga que ya tiene, y notar que el
        # plano cambió después de asignar la OT.
        assert item["content_hash"] == attachment.content_hash
        assert item["size_bytes"] == 2 * 1024 * 1024
        assert part["size_bytes"] == 2 * 1024 * 1024

    def test_rf_017_el_paquete_de_la_zona_no_exige_que_nadie_enumere_las_ot(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Se deriva de la zona: un adjunto que viaja solo si alguien lo listó no viaja nunca.

        La API publica paquetes por zona y no recibe ids de OT. Si el manifiesto solo llevara los
        adjuntos de las OT que el llamante enumera, este requerimiento estaría declarado y apuntando
        a nada: nadie los enumera.
        """
        order = an_order(session, unit)
        a_pdf(session, unit, order)

        with client_as(session, PLANNER) as api:
            published = api.post(
                "/api/v1/dispatch/units/GYE/packages",
                json={"zone": ZONE, "tile_url": "/tiles/norte.pmtiles", "asset_count": 10},
            )

        assert published.status_code == 201
        parts = {part["name"]: part for part in published.json()["manifest"]["parts"]}
        assert parts["attachments"]["count"] == 1

    def test_rf_017_una_ot_en_borrador_no_manda_planos_al_campo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Nadie la está ejecutando: su plano no tiene por qué pesar en la descarga."""
        order = an_order(session, unit, state=WorkOrderState.DRAFT)
        a_pdf(session, unit, order)

        assert package_attachments(session, unit)["count"] == 0

    def test_rf_017_los_adjuntos_de_otra_zona_no_viajan(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        other = an_order(session, unit, code="OT-2026-0002", zone="sur")
        a_pdf(session, unit, other)

        assert package_attachments(session, unit, zone=ZONE)["count"] == 0
        assert package_attachments(session, unit, zone="sur")["count"] == 1

    def test_rf_017_el_paquete_de_una_unidad_nunca_lleva_el_plano_de_otra(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        """Aunque le pasen el id de la OT ajena: el filtro por unidad es del servicio (ADR-009).

        Se prueba contra `for_package` y no por la zona porque la derivación ya filtra por unidad:
        si el filtro viviera solo ahí, un llamante con una lista de ids se llevaría los planos de
        Manabí en el paquete de Guayaquil y ninguna prueba de zona lo notaría.
        """
        foreign = an_order(session, units["MAN"], code="OT-MAN-1")
        a_pdf(session, units["MAN"], foreign)

        travelling = attachments.for_package(session, units["GYE"], order_ids=[foreign.id])

        assert travelling == []

    def test_rf_017_lo_marcado_como_no_offline_no_viaja(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un estudio de 20 MB que nadie lee con guantes puestos no baja al teléfono."""
        order = an_order(session, unit)
        a_pdf(session, unit, order, title="Estudio de cargabilidad", offline=False)

        assert package_attachments(session, unit)["count"] == 0

    def test_rf_017_el_hash_del_manifiesto_no_cambia_si_los_adjuntos_no_cambian(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Dos publicaciones iguales dan el mismo hash, o cada una haría redescargar a todos."""
        order = an_order(session, unit)
        a_pdf(session, unit, order, title="Plano A", body="plano-a")
        a_pdf(session, unit, order, title="Plano B", body="plano-b")

        first = build_offline_package(
            session, unit, zone=ZONE, tile_url="/tiles/norte.pmtiles", asset_count=1200
        )
        second = build_offline_package(
            session, unit, zone=ZONE, tile_url="/tiles/norte.pmtiles", asset_count=1200
        )

        assert second.content_hash == first.content_hash
        assert second.version == first.version

    def test_rf_017_cambiar_el_plano_cambia_el_hash_del_paquete(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit)
        a_pdf(session, unit, order)
        before = build_offline_package(
            session, unit, zone=ZONE, tile_url="/tiles/norte.pmtiles", asset_count=1200
        )

        a_pdf(session, unit, order, title="Plano corregido", body="plano-v2")
        after = build_offline_package(
            session, unit, zone=ZONE, tile_url="/tiles/norte.pmtiles", asset_count=1200
        )

        assert after.content_hash != before.content_hash
        assert after.version == before.version + 1


class TestWhatIsRefused:
    def test_rf_017_un_dwg_se_rechaza_con_la_lista_de_admitidos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit)

        with pytest.raises(attachments.UnsupportedTypeError, match="application/pdf"):
            a_pdf(session, unit, order, mime_type="image/vnd.dwg")

    def test_rf_017_un_archivo_sobre_el_limite_por_adjunto_se_rechaza_con_el_numero(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit)

        with pytest.raises(attachments.TooLargeError, match="25,0 MB"):
            a_pdf(session, unit, order, size_bytes=attachments.MAX_ATTACHMENT_BYTES + 1)

    def test_rf_017_diez_planos_que_pasan_uno_por_uno_no_pasan_juntos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El límite por archivo no alcanza: es el total lo que la cuadrilla descarga."""
        order = an_order(session, unit)
        for index in range(3):
            a_pdf(
                session,
                unit,
                order,
                title=f"Plano {index}",
                body=f"p{index}",
                size_bytes=20 * 1024 * 1024,
            )

        with pytest.raises(attachments.TooLargeError, match="60,0 MB"):
            a_pdf(session, unit, order, title="Plano 4", body="p4", size_bytes=20 * 1024 * 1024)

    def test_rf_017_lo_que_no_viaja_no_gasta_el_presupuesto_del_paquete(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Marcar un estudio como no-offline es justamente la salida que ofrece el mensaje."""
        order = an_order(session, unit)
        for index in range(3):
            a_pdf(
                session,
                unit,
                order,
                title=f"Plano {index}",
                body=f"p{index}",
                size_bytes=20 * 1024 * 1024,
            )

        study = a_pdf(
            session,
            unit,
            order,
            title="Estudio",
            body="estudio",
            size_bytes=20 * 1024 * 1024,
            offline=False,
        )

        assert study.id is not None
        assert attachments.offline_bytes(session, order) == 60 * 1024 * 1024

    def test_rf_017_retirar_un_plano_libera_el_presupuesto_del_paquete(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Lo retirado no se descarga, así que no puede seguir ocupando el cupo de la OT."""
        order = an_order(session, unit)
        for index in range(3):
            a_pdf(
                session,
                unit,
                order,
                title=f"Plano {index}",
                body=f"p{index}",
                size_bytes=20 * 1024 * 1024,
            )
        replaced = attachments.attachments_of(session, order)[0]
        attachments.withdraw(
            session, unit, replaced, actor=PLANNER.subject, reason="lo reemplaza el definitivo"
        )

        assert attachments.offline_bytes(session, order) == 40 * 1024 * 1024
        final = a_pdf(
            session, unit, order, title="Plano final", body="final", size_bytes=20 * 1024 * 1024
        )

        assert final.id is not None

    def test_rf_017_un_adjunto_de_cero_bytes_no_es_un_adjunto(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit)

        with pytest.raises(attachments.AttachmentError, match="cero bytes"):
            a_pdf(session, unit, order, size_bytes=0)

    def test_rf_017_un_adjunto_necesita_titulo(self, session: Session, unit: BusinessUnit) -> None:
        order = an_order(session, unit)

        with pytest.raises(attachments.AttachmentError, match="título"):
            a_pdf(session, unit, order, title="   ")

    def test_rf_017_una_ot_de_otra_unidad_no_recibe_adjuntos(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        """ADR-009 desde el servicio, no solo desde la API."""
        order = an_order(session, units["MAN"], code="OT-MAN-1")

        with pytest.raises(attachments.AttachmentError, match="unidad de negocio"):
            a_pdf(session, units["GYE"], order)


class TestReSendingAndWithdrawing:
    def test_rf_017_el_mismo_archivo_dos_veces_es_un_solo_adjunto(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit)
        first = a_pdf(session, unit, order, title="Plano estructural")
        again = a_pdf(session, unit, order, title="Plano estructural (rev. B)")

        assert again.id == first.id
        # El título se actualiza: quien reenvía puede estar corrigiéndolo.
        assert again.title == "Plano estructural (rev. B)"
        rows = session.execute(
            select(WorkOrderAttachment).where(WorkOrderAttachment.work_order_id == order.id)
        ).scalars()
        assert len(list(rows)) == 1

    def test_rf_017_reenviar_un_adjunto_retirado_lo_devuelve_al_paquete(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit)
        attachment = a_pdf(session, unit, order)
        attachments.withdraw(
            session, unit, attachment, actor=PLANNER.subject, reason="se subió el plano equivocado"
        )
        assert package_attachments(session, unit)["count"] == 0

        a_pdf(session, unit, order)

        assert attachment.withdrawn_at is None
        assert attachment.withdrawn_reason is None
        assert package_attachments(session, unit)["count"] == 1

    def test_rf_017_un_adjunto_retirado_deja_de_viajar_pero_no_desaparece(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La cuadrilla pudo ejecutar el trabajo con este plano: la fila se queda, marcada."""
        order = an_order(session, unit)
        attachment = a_pdf(session, unit, order)

        attachments.withdraw(
            session, unit, attachment, actor=PLANNER.subject, reason="lo reemplaza el diseño final"
        )

        assert package_attachments(session, unit)["count"] == 0
        assert session.get(WorkOrderAttachment, attachment.id) is not None
        assert attachment.withdrawn_by == PLANNER.subject
        assert attachment.withdrawn_reason == "lo reemplaza el diseño final"
        assert attachment.is_active is False
        assert attachments.attachments_of(session, order) == []
        assert attachments.attachments_of(session, order, include_withdrawn=True) == [attachment]

    def test_rf_017_retirar_sin_motivo_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit)
        attachment = a_pdf(session, unit, order)

        with pytest.raises(attachments.AttachmentError, match="motivo"):
            attachments.withdraw(session, unit, attachment, actor=PLANNER.subject, reason="  ")

    def test_rf_017_retirar_dos_veces_conserva_el_primer_motivo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit)
        attachment = a_pdf(session, unit, order)
        attachments.withdraw(
            session, unit, attachment, actor=PLANNER.subject, reason="motivo original"
        )

        attachments.withdraw(session, unit, attachment, actor=TECHNICIAN.subject, reason="otro")

        assert attachment.withdrawn_reason == "motivo original"
        assert attachment.withdrawn_by == PLANNER.subject


class TestFrontsShareTheDrawings:
    def test_rf_017_un_frente_abre_el_plano_de_su_obra(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una obra con seis frentes tiene un juego de planos, no seis copias (RF-015)."""
        parent = an_order(session, unit, code="OBRA-2026-0001", state=WorkOrderState.PLANNED)
        front = an_order(session, unit, code="OBRA-2026-0001-F1")
        fronts.attach(session, unit, parent, front, actor=PLANNER.subject)
        plan = a_pdf(session, unit, parent, title="Planos de la obra")

        visible = attachments.attachments_of(session, front)

        assert visible == [plan]

    def test_rf_017_el_paquete_lleva_el_plano_de_la_obra_por_el_frente_asignado(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La obra padre no se ejecuta: si el paquete solo mirara la OT asignada, el frente saldría
        al campo sin los planos que están en la obra."""
        parent = an_order(session, unit, code="OBRA-2026-0001", state=WorkOrderState.PLANNED)
        front = an_order(session, unit, code="OBRA-2026-0001-F1")
        fronts.attach(session, unit, parent, front, actor=PLANNER.subject)
        plan = a_pdf(session, unit, parent, title="Planos de la obra")

        part = package_attachments(session, unit)

        assert part["count"] == 1
        assert part["items"][0]["id"] == str(plan.id)


class TestApi:
    def test_rf_017_el_autor_sale_del_token_y_no_del_cuerpo(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        """Un plano cuyo autor pudiera escribir el llamante es un plano que nadie firmó."""
        order = an_order(session, unit)
        digest = hashlib.sha256(b"plano-api").hexdigest()

        response = client.post(
            f"/api/v1/attachments/units/GYE/work-orders/{order.id}",
            json={
                "title": "Diseño de la acometida",
                "filename": "acometida.pdf",
                "storage_key": f"s3://adjuntos/{digest}.pdf",
                "content_hash": digest,
                "size_bytes": 1024,
                "mime_type": "application/pdf",
                "kind": "diseno",
                "uploaded_by": "kc|otra.persona",
            },
        )

        assert response.status_code == 200, response.text
        assert response.json()["uploaded_by"] == PLANNER.subject

    def test_rf_017_el_indice_dice_cuanto_pesa_la_descarga(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        """Lo que la cuadrilla va a descargar, dicho antes de salir y no en el sitio."""
        order = an_order(session, unit)
        a_pdf(session, unit, order, size_bytes=3 * 1024 * 1024)

        response = client.get(f"/api/v1/attachments/units/GYE/work-orders/{order.id}")

        assert response.status_code == 200
        body = response.json()
        assert body["offline_bytes"] == 3 * 1024 * 1024
        assert body["max_offline_bytes"] == attachments.MAX_OFFLINE_BYTES_PER_ORDER
        assert len(body["attachments"]) == 1

    def test_rf_017_la_cuadrilla_lee_sus_adjuntos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Existen para quien ejecuta el trabajo: negarle la lectura al técnico los vaciaría."""
        order = an_order(session, unit)
        a_pdf(session, unit, order)

        with client_as(session, TECHNICIAN) as api:
            response = api.get(f"/api/v1/attachments/units/GYE/work-orders/{order.id}")

        assert response.status_code == 200
        assert len(response.json()["attachments"]) == 1

    def test_rf_017_la_cuadrilla_no_adjunta(self, session: Session, unit: BusinessUnit) -> None:
        order = an_order(session, unit)
        digest = hashlib.sha256(b"desde-el-campo").hexdigest()

        with client_as(session, TECHNICIAN) as api:
            response = api.post(
                f"/api/v1/attachments/units/GYE/work-orders/{order.id}",
                json={
                    "title": "Plano",
                    "filename": "plano.pdf",
                    "storage_key": "s3://adjuntos/x.pdf",
                    "content_hash": digest,
                    "size_bytes": 1024,
                    "mime_type": "application/pdf",
                },
            )

        assert response.status_code == 403

    def test_rf_017_un_tipo_no_admitido_responde_415(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        """415 y no 413: la diferencia importa para quien tiene que volver a exportar el archivo."""
        order = an_order(session, unit)
        digest = hashlib.sha256(b"dwg").hexdigest()

        response = client.post(
            f"/api/v1/attachments/units/GYE/work-orders/{order.id}",
            json={
                "title": "Plano CAD",
                "filename": "plano.dwg",
                "storage_key": "s3://adjuntos/plano.dwg",
                "content_hash": digest,
                "size_bytes": 1024,
                "mime_type": "image/vnd.dwg",
            },
        )

        assert response.status_code == 415
        assert "application/pdf" in response.json()["detail"]

    def test_rf_017_un_archivo_demasiado_grande_responde_413(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        order = an_order(session, unit)
        digest = hashlib.sha256(b"gigante").hexdigest()

        response = client.post(
            f"/api/v1/attachments/units/GYE/work-orders/{order.id}",
            json={
                "title": "Levantamiento completo",
                "filename": "levantamiento.pdf",
                "storage_key": "s3://adjuntos/levantamiento.pdf",
                "content_hash": digest,
                "size_bytes": attachments.MAX_ATTACHMENT_BYTES + 1,
                "mime_type": "application/pdf",
            },
        )

        assert response.status_code == 413
        assert "25,0 MB" in response.json()["detail"]

    def test_rf_017_retirar_exige_motivo(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        order = an_order(session, unit)
        attachment = a_pdf(session, unit, order)

        response = client.post(
            f"/api/v1/attachments/units/GYE/{attachment.id}/withdraw", json={"reason": ""}
        )

        assert response.status_code == 422
        assert session.get(WorkOrderAttachment, attachment.id) is not None

    def test_rf_017_retirar_desde_la_api_deja_el_motivo_y_el_autor(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        order = an_order(session, unit)
        attachment = a_pdf(session, unit, order)

        response = client.post(
            f"/api/v1/attachments/units/GYE/{attachment.id}/withdraw",
            json={"reason": "el diseño cambió tras la inspección"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["is_active"] is False
        assert body["withdrawn_by"] == PLANNER.subject
        assert body["withdrawn_reason"] == "el diseño cambió tras la inspección"

    def test_rf_017_no_se_lee_el_adjunto_de_otra_unidad(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        order = an_order(session, units["MAN"], code="OT-MAN-1")
        attachment = a_pdf(session, units["MAN"], order)

        with client_as(session, BOTH_UNITS) as api:
            read = api.get(f"/api/v1/attachments/units/GYE/work-orders/{order.id}")
            withdrawn = api.post(
                f"/api/v1/attachments/units/GYE/{attachment.id}/withdraw",
                json={"reason": "desde la unidad equivocada"},
            )

        assert read.status_code == 404
        assert withdrawn.status_code == 404
        # Y sobre todo: sigue activo. Un 404 que además retiró el adjunto sería peor que un 200.
        assert attachment.is_active is True

    def test_rf_017_una_ot_inexistente_no_revela_nada(
        self, session: Session, unit: BusinessUnit, client: TestClient
    ) -> None:
        response = client.get(f"/api/v1/attachments/units/GYE/work-orders/{uuid.uuid4()}")

        assert response.status_code == 404


class TestAuditTrail:
    def test_rf_017_adjuntar_y_retirar_quedan_en_la_bitacora(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Quién mandó el plano con el que trabajó la cuadrilla, y quién lo retiró (RF-160)."""
        order = an_order(session, unit)
        attachment = a_pdf(session, unit, order)
        attachments.withdraw(
            session, unit, attachment, actor=TECHNICIAN.subject, reason="ilegible al imprimir"
        )

        events = list(
            session.execute(
                select(AuditEvent)
                .where(AuditEvent.subject_id == str(attachment.id))
                .order_by(AuditEvent.sequence)
            ).scalars()
        )

        assert [event.actor for event in events] == [PLANNER.subject, TECHNICIAN.subject]
        assert events[0].payload["title"] == attachment.title
        assert events[0].payload["size_bytes"] == 2 * 1024 * 1024
        assert events[1].payload["reason"] == "ilegible al imprimir"
