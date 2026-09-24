"""El informe retenido y liberado, por HTTP (RF-111a).

El criterio de aceptación tiene dos mitades y las dos son comprobables: el informe **se oculta**
hasta que el supervisor registra su decisión, y **luego se muestra** y se registra la concordancia.
La segunda mitad importa tanto como la primera: retener el informe y no mostrarlo nunca le costaría
al supervisor la realimentación y a la plataforma su única oportunidad de que alguien le diga que el
informe estaba equivocado.

Lo que se prueba con más cuidado es qué **no** se retiene. Los hallazgos deterministas, los
impedimentos y las fotos no son del agente y no se ocultan nunca: son de lo que depende una
aprobación, y RF-204 exige poder aprobar sin informe ninguno.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.prereview.models import AgentRun, RunState, StoredReport
from app.responses.service import save_answers
from app.review.blind import agreement
from app.review.blind import assign as assign_blind
from app.review.models import BlindReview, ReviewDecision
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

SUPERVISOR = Principal(
    subject="kc|supervisor.demo",
    username="supervisor.demo",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE"}),
)

TECHNICIAN = Principal(
    subject="kc|tecnico.demo",
    username="tecnico.demo",
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


def make_order(session: Session, unit: BusinessUnit, code: str = "OT-B1"):
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
    save_answers(
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
            # B04: el formulario exige ATS, así que la referencia es obligatoria.
            "ats_reference": "ATS-2026-0001",
        },
        submit=True,
    )
    session.flush()
    return order


def give_report(session: Session, unit: BusinessUnit, order, risk: str = "high") -> AgentRun:
    run = AgentRun(
        business_unit_id=unit.id,
        work_order_id=order.id,
        graph_version="prereview-0.1.0",
        hardware_profile="A",
        state=RunState.DONE,
        attempts=1,
    )
    session.add(run)
    session.flush()
    session.add(
        StoredReport(
            agent_run_id=run.id,
            risk_level=risk,
            summary=f"riesgo {risk}",
            document={
                "work_order_id": str(order.id),
                "graph_version": "prereview-0.1.0",
                "hardware_profile": "A",
                "risk_level": risk,
                "status": "complete",
                "summary": "una foto repetida entre dos OT",
                "observations": [],
                "models": {},
                "budget": {"llm_calls": 0, "tokens": 0, "duration_s": 0.0},
                "skipped": [],
                "discarded": 0,
            },
            observation_count=0,
        )
    )
    session.flush()
    return run


@pytest.fixture
def client(session: Session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: SUPERVISOR
    with TestClient(app) as raw:
        yield raw


def detail_of(client: TestClient, unit: BusinessUnit, order) -> dict:
    answer = client.get(f"/api/v1/review/units/{unit.code}/work-orders/{order.id}")
    assert answer.status_code == 200, answer.text
    return answer.json()


class TestWhatIsWithheld:
    def test_rf_111a_el_informe_no_viaja_mientras_la_ot_está_en_la_muestra_ciega(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        order = make_order(session, unit)
        give_report(session, unit, order, "high")
        assign_blind(session, order.id, unit.id, rate=1.0)
        session.flush()

        body = detail_of(client, unit, order)
        assert body["agent_report"]["blind"] is True
        assert body["agent_report"]["report"] is None

    def test_ni_el_riesgo_ni_el_resumen_se_cuelan_en_la_respuesta(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Retener el informe y mandar «riesgo alto» al lado sería retenerlo de adorno: el anclaje
        lo produce el veredicto, no el documento."""
        order = make_order(session, unit)
        give_report(session, unit, order, "high")
        assign_blind(session, order.id, unit.id, rate=1.0)
        session.flush()

        raw = client.get(f"/api/v1/review/units/{unit.code}/work-orders/{order.id}").text
        assert "una foto repetida entre dos OT" not in raw
        assert '"risk_level"' not in raw

    def test_lo_determinista_no_se_oculta_nunca(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Los hallazgos normativos, los impedimentos y las fotos no son del agente. Ocultarlos
        sería esconder justo de lo que depende una aprobación (RF-204)."""
        order = make_order(session, unit)
        give_report(session, unit, order, "high")
        assign_blind(session, order.id, unit.id, rate=1.0)
        session.flush()

        body = detail_of(client, unit, order)
        assert body["agent_report"]["blind"] is True
        # Están presentes como claves, con su contenido, sean o no vacías en esta captura.
        assert "compliance" in body
        assert "blockers" in body
        assert "missing_photos" in body
        assert body["form"]["code"] == "F-MT-01"

    def test_una_ot_fuera_de_la_muestra_trae_su_informe_como_siempre(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        order = make_order(session, unit)
        give_report(session, unit, order, "medium")
        session.flush()

        body = detail_of(client, unit, order)
        assert body["agent_report"]["blind"] is False
        assert body["agent_report"]["report"]["risk_level"] == "medium"


class TestTheReveal:
    def test_rf_111a_después_de_decidir_el_informe_aparece(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """«Luego se muestra». Retenerlo y no mostrarlo nunca le costaría al supervisor la
        realimentación y a la plataforma su única oportunidad de que le digan que se equivocó."""
        order = make_order(session, unit)
        give_report(session, unit, order, "high")
        assign_blind(session, order.id, unit.id, rate=1.0)
        session.flush()
        assert detail_of(client, unit, order)["agent_report"]["report"] is None

        answer = client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={"decision": "devuelta", "note": "falta la foto del después"},
        )
        assert answer.status_code == 200, answer.text
        # Y se le dice a la pantalla, para que no cierre la OT antes de mostrarlo.
        assert answer.json()["was_blind"] is True

        after = detail_of(client, unit, order)
        assert after["agent_report"]["blind"] is False
        assert after["agent_report"]["report"]["risk_level"] == "high"

    def test_la_concordancia_queda_registrada_con_los_dos_veredictos(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        order = make_order(session, unit)
        give_report(session, unit, order, "high")
        assign_blind(session, order.id, unit.id, rate=1.0)
        session.flush()

        client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={"decision": "devuelta", "note": "x"},
        )
        row = session.query(BlindReview).one()
        assert row.revealed_at is not None
        assert row.supervisor_verdict == "con_problema"
        assert row.agent_verdict == "con_problema"

    def test_la_decisión_queda_marcada_como_ciega_sin_que_nadie_lo_declare(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """El campo era un booleano que mandaba el navegador: lo que se está midiendo rellenando su
        propia calificación."""
        order = make_order(session, unit)
        give_report(session, unit, order, "low")
        assign_blind(session, order.id, unit.id, rate=1.0)
        session.flush()

        client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={"decision": "devuelta", "note": "x"},
        )
        assert session.query(ReviewDecision).one().blind_sample is True

    def test_un_campo_blind_sample_enviado_por_el_cliente_se_ignora(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """No basta con dejar de usarlo: si el modelo lo aceptara, volvería a usarse."""
        order = make_order(session, unit)
        session.flush()

        answer = client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={"decision": "devuelta", "note": "x", "blind_sample": True},
        )
        assert answer.status_code == 200, answer.text
        assert session.query(ReviewDecision).one().blind_sample is None

    def test_sin_informe_el_sorteo_se_cierra_sin_par(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Contarla como concordancia halagaría al agente; como discrepancia lo castigaría por un
        lote nocturno que no había corrido."""
        order = make_order(session, unit)
        assign_blind(session, order.id, unit.id, rate=1.0)
        session.flush()

        client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={"decision": "devuelta", "note": "x"},
        )
        row = session.query(BlindReview).one()
        assert row.revealed_at is not None
        assert row.agent_verdict is None
        assert agreement(session, unit.id).unpaired == 1
        assert agreement(session, unit.id).paired == 0


class TestTheDrawItself:
    def test_un_segundo_sorteo_no_reabre_el_primero(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una nueva ejecución de la pre-revisión no puede darle otra oportunidad de ser medida, ni
        liberar un informe que estaba retenido."""
        order = make_order(session, unit)
        first = assign_blind(session, order.id, unit.id, rate=1.0)
        second = assign_blind(session, order.id, unit.id, rate=1.0)
        assert first is not None
        assert second is not None
        assert first.id == second.id
        assert session.query(BlindReview).count() == 1

    def test_la_tasa_en_vigor_queda_en_la_fila(self, session: Session, unit: BusinessUnit) -> None:
        """Si se recalculara desde el ajuste, cambiarlo reescribiría el denominador de una
        métrica de calidad sin que nadie lo hubiera decidido."""
        order = make_order(session, unit)
        row = assign_blind(session, order.id, unit.id, rate=1.0)
        assert row is not None and row.rate == pytest.approx(1.0)

    def test_la_pre_revisión_sortea_al_guardar_el_informe(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Antes de que haya una persona involucrada: un sorteo hecho en el camino de una petición
        sería un sorteo en el que participa lo que se está midiendo."""
        from app.prereview.service import execute
        from app.settings import get_settings

        settings = get_settings()
        original = settings.blind_sample_rate
        settings.blind_sample_rate = 1.0
        try:
            order = make_order(session, unit)
            execute(session, unit, order, gateway_reachable=False)
        finally:
            settings.blind_sample_rate = original
        assert session.query(BlindReview).count() == 1


class TestWhoSeesTheNumber:
    def test_el_tablero_da_la_tabla_y_el_kappa(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        body = client.get(f"/api/v1/review/units/{unit.code}/agent-agreement").json()
        assert body["paired"] == 0
        assert body["kappa"] is None
        # El piso de RNF-060 viaja con el número: un 0,58 suelto no dice si pasa o no.
        assert body["kappa_floor"] == pytest.approx(0.6)

    def test_un_técnico_no_ve_la_concordancia(self, session: Session, unit: BusinessUnit) -> None:
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: TECHNICIAN
        with TestClient(app) as raw:
            answer = raw.get(f"/api/v1/review/units/{unit.code}/agent-agreement")
        assert answer.status_code == 403
