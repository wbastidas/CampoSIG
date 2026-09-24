"""Emitir el acta y verificarla, de punta a punta (RF-115, ADR-009, ADR-013).

Lo que la verificación puede afirmar, y lo que no. El QR no prueba nada si la página se limita a
repetir el hash impreso al lado: eso sería la página haciendo eco del papel. Lo que la convierte
en verificación es que la plataforma **reconozca el código** y pueda decir «no consta» de uno que
nunca emitió.

Así que aquí se prueba: que la huella registrada sea la de los bytes entregados, que reimprimir
deje dos filas y no sobrescriba una, que un código inventado dé 404 con el texto que corresponde,
que la página pública no exija identidad y no revele más de lo necesario, y que el acta de otra
unidad de negocio no se pueda emitir.
"""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.reports.service import find_by_code
from app.responses.models import EvidenceStage, ValueOrigin
from app.responses.service import record_provenance, register_evidence, save_answers
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

SUPERVISOR = Principal(
    subject="kc|supervisor.demo",
    username="supervisor.demo",
    display_name="Supervisor Demo",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE", "MAN"}),
)

TECHNICIAN = Principal(
    subject="kc|tecnico.demo",
    username="tecnico.demo",
    display_name="Técnico Demo",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def unit(session: Session) -> BusinessUnit:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created = BusinessUnit(
        organization_id=org.id, code="GYE", name="Unidad Guayaquil", profile_id="cnel-gye"
    )
    session.add(created)
    session.flush()
    ingest_metadata(session, created, build_metadata("cnel-gye"))
    return created


@pytest.fixture
def order(session: Session, unit: BusinessUnit):
    created = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        longitude=-79.9,
        latitude=-2.17,
        zone="Urbano",
        planner_id="planner.a",
    )
    created.state = WorkOrderState.APPROVED
    created.form_version = "1.0.0"
    created.code = "OT-2026-000123"
    session.flush()
    return created


@pytest.fixture
def filled(session: Session, unit: BusinessUnit, order):
    """A work order with answers, a photograph and one AI-proposed value."""
    response = save_answers(
        session,
        unit,
        order,
        answers={
            "work_order_code": order.code or "OT-1",
            "work_type": "inspeccion_preventiva",
            "priority": "media",
            "general_condition": "regular",
            "code": "P-000452",
            "material": "concrete",
            "feeder_code": "04BH070T11",
            "height_m": 11.0,
            "final_state": "resuelto",
            # B04: el formulario exige ATS, así que la referencia es obligatoria.
            "ats_reference": "ATS-2026-0001",
            "customer_id": "0912345678",
        },
        submit=True,
    )
    register_evidence(
        session,
        response,
        kind="foto",
        storage_key="s3://antes-0.jpg",
        content_hash=hashlib.sha256(b"antes0").hexdigest(),
        stage=EvidenceStage.BEFORE,
    )
    record_provenance(
        session,
        response,
        field_key="material",
        origin=ValueOrigin.VISION,
        final_value="concrete",
        proposed_value="concrete",
        model_name="mobilenetv3-pole",
        model_version="2026.09",
        confidence=0.91,
        confirmed_by="tecnico.1",
    )
    session.flush()
    return response


def make_client(session: Session, principal: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: principal
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with make_client(session, SUPERVISOR) as raw:
        yield raw


def acta_url(unit_code: str, order_id: object) -> str:
    return f"/api/v1/reports/units/{unit_code}/work-orders/{order_id}/acta"


class TestIssuing:
    def test_rf_115_el_acta_sale_en_pdf_con_su_codigo_y_su_huella(
        self, client: TestClient, session: Session, unit: BusinessUnit, order, filled
    ) -> None:
        answer = client.post(acta_url(unit.code, order.id))
        assert answer.status_code == 200, answer.text
        assert answer.headers["content-type"] == "application/pdf"
        assert answer.content.startswith(b"%PDF-")

        code = answer.headers["X-SIGEC-Verification-Code"]
        digest = answer.headers["X-SIGEC-Document-Hash"]
        # La única afirmación que la verificación puede sostener: la huella es la de los bytes
        # que se entregaron, no la de un render posterior.
        assert digest == hashlib.sha256(answer.content).hexdigest()

        record = find_by_code(session, code)
        assert record is not None
        assert record.content_hash == digest
        assert record.byte_size == len(answer.content)
        assert record.state_at_issue == WorkOrderState.APPROVED
        assert record.form_code == "F-MT-01"

    def test_adr_013_quien_emite_sale_del_token_y_no_del_cuerpo(
        self, client: TestClient, session: Session, unit: BusinessUnit, order, filled
    ) -> None:
        answer = client.post(acta_url(unit.code, order.id))
        record = find_by_code(session, answer.headers["X-SIGEC-Verification-Code"])
        assert record is not None
        assert record.issued_by == SUPERVISOR.subject

    def test_rf_115_reimprimir_deja_dos_filas_y_no_sobrescribe_una(
        self, client: TestClient, unit: BusinessUnit, order, filled
    ) -> None:
        """Dos papeles en el mundo son dos filas aquí.

        Devolver el mismo documento sería más limpio y más falso: la OT puede haberse corregido
        en medio, y entonces dos personas tendrían dos papeles distintos afirmando ser el mismo.
        """
        first = client.post(acta_url(unit.code, order.id))
        second = client.post(acta_url(unit.code, order.id))
        assert (
            first.headers["X-SIGEC-Verification-Code"]
            != second.headers["X-SIGEC-Verification-Code"]
        )

        listed = client.get(
            f"/api/v1/reports/units/{unit.code}/work-orders/{order.id}/documents"
        ).json()
        assert len(listed) == 2
        assert {row["verification_code"] for row in listed} == {
            first.headers["X-SIGEC-Verification-Code"],
            second.headers["X-SIGEC-Verification-Code"],
        }

    def test_rf_115_un_acta_de_una_ot_sin_aprobar_queda_registrada_como_borrador(
        self, client: TestClient, session: Session, unit: BusinessUnit, order, filled
    ) -> None:
        """Se permite emitirla —hace falta para revisar— y el registro concuerda con el papel."""
        order.state = WorkOrderState.SYNCED
        session.flush()
        answer = client.post(acta_url(unit.code, order.id))
        record = find_by_code(session, answer.headers["X-SIGEC-Verification-Code"])
        assert record is not None
        assert record.state_at_issue == WorkOrderState.SYNCED

    def test_rf_002_un_tecnico_no_emite_actas(
        self, session: Session, unit: BusinessUnit, order, filled
    ) -> None:
        with make_client(session, TECHNICIAN) as raw:
            assert raw.post(acta_url(unit.code, order.id)).status_code == 403

    def test_adr_009_una_ot_de_otra_unidad_da_404(
        self, client: TestClient, session: Session, unit: BusinessUnit, order, filled
    ) -> None:
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        # La OT existe, pero no en la unidad que se nombra: 404, no 403, para que sondear ids no
        # enseñe qué hay en otra unidad.
        assert client.post(acta_url(other.code, order.id)).status_code == 404


class TestTheVerificationPage:
    def test_rf_115_la_pagina_confirma_lo_emitido_sin_exigir_identidad(
        self, client: TestClient, session: Session, unit: BusinessUnit, order, filled
    ) -> None:
        """La abre el cliente cuya luminaria se repuso, que no tiene cuenta corporativa."""
        issued = client.post(acta_url(unit.code, order.id))
        code = issued.headers["X-SIGEC-Verification-Code"]

        # Sin sobrescribir `current_principal`: la ruta pública no lo pide.
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        with TestClient(app) as anonymous:
            page = anonymous.get(f"/verificar/{code}")

        assert page.status_code == 200
        assert page.headers["content-type"].startswith("text/html")
        assert "Acta verificada" in page.text
        assert issued.headers["X-SIGEC-Document-Hash"] in page.text
        assert order.code is not None and order.code in page.text

    def test_rf_115_la_pagina_nombra_la_ot_igual_que_el_papel_cuando_no_tiene_codigo(
        self, client: TestClient, session: Session, unit: BusinessUnit, order, filled
    ) -> None:
        """La mayoría de las OT de esta plataforma no tienen código legible.

        `create_work_order` no asigna ninguno —solo las importadas traen número externo—, así que
        el identificador suele ser el id. Cuando el acta imprimía el id y la página mostraba una
        raya, verificar fallaba justo en las OT que son la mayoría.
        """
        order.code = None
        session.flush()
        issued = client.post(acta_url(unit.code, order.id))
        page = client.get(f"/verificar/{issued.headers['X-SIGEC-Verification-Code']}")

        assert str(order.id) in page.text
        assert page.status_code == 200

    def test_rf_115_la_pagina_no_revela_datos_de_la_captura(
        self, client: TestClient, session: Session, unit: BusinessUnit, order, filled
    ) -> None:
        """Lo mínimo para distinguir un acta genuina de una invención, y nada más.

        Es una página pública, así que lo que muestre lo ve cualquiera con el papel en la mano —
        o con el código. Las respuestas, la cédula del cliente y el código del activo no son
        parte de verificar nada.
        """
        issued = client.post(acta_url(unit.code, order.id))
        page = client.get(f"/verificar/{issued.headers['X-SIGEC-Verification-Code']}")

        assert "0912345678" not in page.text
        assert "P-000452" not in page.text
        assert "04BH070T11" not in page.text

    def test_rf_115_un_codigo_que_nadie_emitio_no_consta(self, client: TestClient) -> None:
        """La frase que hace que valga la pena imprimir el QR."""
        page = client.get("/verificar/estecodigonoexiste")
        assert page.status_code == 404
        assert "no consta" in page.text
        assert "no proviene de esta" in page.text

    def test_rf_115_la_pagina_avisa_cuando_el_acta_era_un_borrador(
        self, client: TestClient, session: Session, unit: BusinessUnit, order, filled
    ) -> None:
        order.state = WorkOrderState.SYNCED
        session.flush()
        issued = client.post(acta_url(unit.code, order.id))
        page = client.get(f"/verificar/{issued.headers['X-SIGEC-Verification-Code']}")
        assert "todavía no estaba" in page.text

    def test_rf_115_el_codigo_no_se_devuelve_por_el_solo_hecho_de_pedirlo(
        self, client: TestClient
    ) -> None:
        """Repetir el código de la URL sería la página haciendo eco del papel.

        Un código inexistente no aparece en la respuesta: si apareciera, cualquiera podría
        fabricar una captura de pantalla «verificando» un documento inventado.
        """
        page = client.get("/verificar/inventado-por-alguien")
        assert "inventado-por-alguien" not in page.text
