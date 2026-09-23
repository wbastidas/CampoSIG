"""El tablero de IA contra base real (RF-134, RF-111a).

Lo que se comprueba es lo que un analista decide con el tablero: qué campo necesita un lote de
etiquetado, qué clase visual está confundida, si la voz se está usando y qué versiones hay en la
flota. Con filas de procedencia de verdad, porque el riesgo de estos números no es la aritmética
—eso ya está probado— sino el denominador: contar las filas equivocadas da una tasa preciosa y
falsa, y nadie la audita porque el tablero se ve bien.

Dos propiedades concretas que se rompen fácil y aquí se fijan:

* la adopción de la voz se mide sobre **todas** las capturas de la persona, incluidas las que no
  tienen ningún valor de IA. Son justo las que muestran la no adopción;
* el periodo se cuenta por el envío, no por la sincronización: una captura hecha sin señal el lunes
  es trabajo del lunes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.responses.models import ValueOrigin
from app.responses.service import record_provenance, save_answers
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

ANALYST = Principal(
    subject="kc|analista.demo",
    username="analista.demo",
    roles=frozenset({Role.ML_ANALYST.value}),
    business_units=frozenset({"GYE"}),
)

TECHNICIAN = Principal(
    subject="kc|tecnico.demo",
    username="tecnico.demo",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


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


def capture(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str,
    who: str = "tecnico.1",
    submitted: datetime | None = None,
):
    """A submitted capture with no AI values at all, which is the denominator's hard case."""
    order = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        longitude=-79.90,
        latitude=-2.17,
        zone="Urbano",
        planner_id="planner.a",
    )
    order.state = WorkOrderState.SYNCED
    order.form_version = "1.0.0"
    order.code = code
    session.flush()
    response = save_answers(
        session,
        unit,
        order,
        answers={
            "work_order_code": code,
            "work_type": "inspeccion_preventiva",
            "priority": "media",
            "general_condition": "regular",
            "code": "P-000452",
            "material": "concrete",
            "feeder_code": "04BH070T11",
            "final_state": "resuelto",
        },
        captured_by=who,
        submit=True,
    )
    response.submitted_at = submitted or NOW
    session.flush()
    return response


def propose(
    session: Session,
    response: Any,
    *,
    field_key: str,
    origin: str,
    proposed: Any,
    final: Any,
    model: str = "mobilenetv3-pole",
    version: str = "2026.09",
    confidence: float = 0.9,
) -> None:
    record_provenance(
        session,
        response,
        field_key=field_key,
        origin=origin,
        proposed_value=proposed,
        final_value=final,
        model_name=model,
        model_version=version,
        confidence=confidence,
        confirmed_by="kc|tecnico.1",
    )


def client_as(session: Session, principal: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: principal
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, ANALYST) as raw:
        yield raw


def dashboard(client: TestClient, unit: BusinessUnit, **params: Any) -> dict[str, Any]:
    answer = client.get(f"/api/v1/analytics/units/{unit.code}/ai-dashboard", params=params)
    assert answer.status_code == 200, answer.text
    return answer.json()


class TestAcceptancePerField:
    def test_rf_134_la_aceptación_por_campo_sale_de_las_filas_de_procedencia(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        for index in range(10):
            response = capture(session, unit, code=f"OT-A{index}")
            # Seis aceptadas, cuatro corregidas: 60 %.
            propose(
                session,
                response,
                field_key="material",
                origin=ValueOrigin.VISION.value,
                proposed="concrete",
                final="concrete" if index < 6 else "wood",
            )
        session.flush()

        panel = {item["field_key"]: item for item in dashboard(client, unit)["fields"]}
        assert panel["material"]["proposals"] == 10
        assert panel["material"]["accepted"] == 6
        assert panel["material"]["corrected"] == 4
        assert panel["material"]["acceptance"] == pytest.approx(0.6)

    def test_un_campo_con_pocas_propuestas_trae_la_cuenta_pero_no_la_tasa(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """«100 % de aceptación» sobre dos propuestas es ruido con signo de porcentaje."""
        for index in range(2):
            response = capture(session, unit, code=f"OT-P{index}")
            propose(
                session,
                response,
                field_key="material",
                origin=ValueOrigin.VISION.value,
                proposed="concrete",
                final="concrete",
            )
        session.flush()

        body = dashboard(client, unit)
        panel = {item["field_key"]: item for item in body["fields"]}
        assert panel["material"]["proposals"] == 2
        assert panel["material"]["acceptance"] is None
        # Y el tablero dice cuál es el mínimo, para que el lector sepa por qué falta.
        assert body["min_for_a_rate"] >= 2

    def test_los_valores_manuales_no_diluyen_ninguna_tasa(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Un campo que ningún modelo propuso no es una propuesta aceptada."""
        response = capture(session, unit, code="OT-M1")
        record_provenance(
            session,
            response,
            field_key="general_condition",
            origin=ValueOrigin.MANUAL.value,
            final_value="regular",
        )
        session.flush()

        fields = [item["field_key"] for item in dashboard(client, unit)["fields"]]
        assert "general_condition" not in fields


class TestVisualClasses:
    def test_rf_134_una_clase_dice_cuántas_veces_se_corrigió_y_en_qué(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Siempre a la misma clase es una confusión que se arregla en el set de entrenamiento."""
        for index in range(12):
            response = capture(session, unit, code=f"OT-V{index}")
            propose(
                session,
                response,
                field_key="material",
                origin=ValueOrigin.VISION.value,
                proposed="concrete",
                final="concrete" if index < 5 else "wood",
            )
        session.flush()

        panel = {item["proposed_class"]: item for item in dashboard(client, unit)["visual_classes"]}
        assert panel["concrete"]["proposals"] == 12
        assert panel["concrete"]["corrected"] == 7
        assert panel["concrete"]["became"][0] == {"value": "wood", "times": 7}

    def test_la_voz_no_aparece_como_clase_visual(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        response = capture(session, unit, code="OT-VZ")
        propose(
            session,
            response,
            field_key="material",
            origin=ValueOrigin.VOICE.value,
            proposed="hormigón",
            final="hormigón",
        )
        session.flush()
        assert dashboard(client, unit)["visual_classes"] == []


class TestTheWordErrorEstimate:
    def test_rf_134_el_error_de_palabras_se_estima_sobre_los_campos_dictados(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        for index in range(6):
            response = capture(session, unit, code=f"OT-W{index}")
            propose(
                session,
                response,
                field_key="notes",
                origin=ValueOrigin.VOICE.value,
                proposed="poste de madera en buen estado",
                final="poste de hormigón en buen estado",
                model="whisper-small-ec",
            )
        session.flush()

        panel = dashboard(client, unit)["word_errors"]
        # Seis campos de seis palabras, una palabra mal en cada uno.
        assert panel["measured_fields"] == 6
        assert panel["reference_words"] == 36
        assert panel["errors"] == 6
        assert panel["error_rate"] == pytest.approx(1 / 6)

    def test_un_valor_que_no_es_texto_se_cuenta_como_no_medible(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Una tasa calculada sobre tres campos de cuatrocientos no es la tasa de nada, y la única
        forma de que el lector lo sepa es que el tablero cuente lo que no pudo medir."""
        response = capture(session, unit, code="OT-N1")
        propose(
            session,
            response,
            field_key="height_m",
            origin=ValueOrigin.VOICE.value,
            proposed=11,
            final=12,
        )
        session.flush()

        panel = dashboard(client, unit)["word_errors"]
        assert panel["unmeasurable_fields"] == 1
        assert panel["measured_fields"] == 0
        assert panel["error_rate"] is None


class TestVoiceAdoption:
    def test_rf_134_quien_no_dicta_aparece_con_cero_y_no_desaparece(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """El caso que rompe el denominador ingenuo.

        Contar solo las capturas que ya tienen un valor de IA haría que quien nunca dicta no tuviera
        capturas, y la adopción saldría alta justo donde es más baja.
        """
        for index in range(6):
            response = capture(session, unit, code=f"OT-D{index}", who="dicta.mucho")
            propose(
                session,
                response,
                field_key="notes",
                origin=ValueOrigin.VOICE.value,
                proposed="sin novedad",
                final="sin novedad",
            )
        for index in range(5):
            capture(session, unit, code=f"OT-T{index}", who="escribe.todo")
        session.flush()

        panel = {item["user"]: item for item in dashboard(client, unit)["voice_adoption"]}
        assert panel["dicta.mucho"]["adoption"] == pytest.approx(1.0)
        assert panel["escribe.todo"]["responses"] == 5
        assert panel["escribe.todo"]["voice_fields"] == 0
        assert panel["escribe.todo"]["adoption"] == pytest.approx(0.0)


class TestTheFleet:
    def test_rf_134_cada_versión_en_la_flota_con_su_aceptación_y_su_última_vez(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        for index in range(6):
            response = capture(session, unit, code=f"OT-F{index}", submitted=NOW)
            propose(
                session,
                response,
                field_key="material",
                origin=ValueOrigin.VISION.value,
                proposed="concrete",
                final="concrete",
                version="2026.08",
            )
        for index in range(6):
            response = capture(
                session, unit, code=f"OT-G{index}", submitted=NOW + timedelta(days=3)
            )
            propose(
                session,
                response,
                field_key="material",
                origin=ValueOrigin.VISION.value,
                proposed="concrete",
                final="wood",
                version="2026.09",
            )
        session.flush()

        panel = {item["model_version"]: item for item in dashboard(client, unit)["fleet"]}
        assert panel["2026.08"]["acceptance"] == pytest.approx(1.0)
        # La versión nueva acepta peor: es exactamente la comparación para la que sirve el panel.
        assert panel["2026.09"]["acceptance"] == pytest.approx(0.0)
        assert panel["2026.09"]["last_seen"] > panel["2026.08"]["last_seen"]


class TestThePeriod:
    def test_el_periodo_se_cuenta_por_el_envío_y_no_por_la_sincronización(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Una captura hecha sin señal el lunes es trabajo del lunes."""
        old = capture(session, unit, code="OT-OLD", submitted=NOW - timedelta(days=30))
        propose(
            session,
            old,
            field_key="material",
            origin=ValueOrigin.VISION.value,
            proposed="concrete",
            final="concrete",
        )
        recent = capture(session, unit, code="OT-NEW", submitted=NOW)
        propose(
            session,
            recent,
            field_key="material",
            origin=ValueOrigin.VISION.value,
            proposed="concrete",
            final="wood",
        )
        session.flush()

        body = dashboard(client, unit, since=(NOW - timedelta(days=7)).isoformat())
        panel = {item["field_key"]: item for item in body["fields"]}
        assert panel["material"]["proposals"] == 1
        assert panel["material"]["corrected"] == 1

    def test_un_periodo_al_revés_se_rechaza_en_vez_de_devolver_cero(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        """Devolver un tablero vacío haría creer que no hubo trabajo."""
        answer = client.get(
            f"/api/v1/analytics/units/{unit.code}/ai-dashboard",
            params={"since": NOW.isoformat(), "until": (NOW - timedelta(days=1)).isoformat()},
        )
        assert answer.status_code == 422


class TestWhoMaySee:
    def test_rf_134_un_técnico_no_ve_el_tablero(self, session: Session, unit: BusinessUnit) -> None:
        """No porque los números sean secretos: una tasa de aceptación por persona en las manos
        equivocadas deja de ser señal de entrenamiento y pasa a ser un expediente."""
        with client_as(session, TECHNICIAN) as raw:
            answer = raw.get(f"/api/v1/analytics/units/{unit.code}/ai-dashboard")
        assert answer.status_code == 403

    def test_adr_009_el_tablero_de_una_unidad_no_cuenta_capturas_de_otra(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        ingest_metadata(session, other, build_metadata("cnel-gye"))
        foreign = capture(session, other, code="OT-MAN", who="tecnico.manabi")
        propose(
            session,
            foreign,
            field_key="material",
            origin=ValueOrigin.VISION.value,
            proposed="concrete",
            final="wood",
        )
        session.flush()

        body = dashboard(client, unit)
        assert body["fields"] == []
        assert [item["user"] for item in body["voice_adoption"]] == []


class TestTheAgreementTravelsWithIt:
    def test_rf_111a_el_tablero_muestra_el_kappa_de_la_muestra_ciega(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        """Es el criterio de aceptación de RF-111a, literal."""
        body = dashboard(client, unit)
        assert "agreement" in body
        assert body["agreement"]["kappa_floor"] == pytest.approx(0.6)
