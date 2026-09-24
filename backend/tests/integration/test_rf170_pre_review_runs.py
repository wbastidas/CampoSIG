"""La pre-revisión de punta a punta: ejecutar, guardar y que el supervisor lo vea (RF-170, RF-180).

El criterio de aceptación de RF-170 es lo que se prueba: **toda OT sincronizada tiene una ejecución
en estado terminal, los fallos se reintentan, y nada bloquea la revisión humana.** Es una propiedad
de la cola, no de una función, así que hace falta la base: el worker corre, el `agent_run` queda, y
la pantalla del supervisor recibe el informe o recibe el motivo de que no haya.

Y la mitad que importa de RF-180: dos ejecuciones del mismo grafo sobre la misma captura dan el
mismo informe. Sin eso, «reproducir una ejecución» no significa nada y la traza es decorado.
"""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents.report import (
    AgentReport,
    Category,
    EvidenceRef,
    EvidenceType,
    Observation,
    RiskLevel,
    RunStatus,
    Severity,
)
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.prereview.models import AgentRun, AgentStepTrace, RunState
from app.prereview.service import (
    build_facts,
    execute,
    latest_report,
    latest_run,
    orders_without_a_terminal_run,
)
from app.responses.models import EvidenceStage
from app.responses.service import register_evidence, save_answers
from app.workers.pre_review import run_for_unit
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


def make_order(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str,
    photo_hash: str,
    longitude: float = -79.90,
    latitude: float = -2.17,
    started: str = "2026-09-22T08:00:00+00:00",
    finished: str = "2026-09-22T09:30:00+00:00",
):
    created = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        longitude=longitude,
        latitude=latitude,
        zone="Urbano",
        planner_id="planner.a",
    )
    created.state = WorkOrderState.SYNCED
    created.form_version = "1.0.0"
    created.code = code
    session.flush()
    response = save_answers(
        session,
        unit,
        created,
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
            "started_at": started,
            "finished_at": finished,
            "gps": {"latitude": latitude, "longitude": longitude, "accuracy_m": 4.0},
        },
        submit=True,
    )
    register_evidence(
        session,
        response,
        kind="foto",
        storage_key=f"s3://{code}-antes.jpg",
        content_hash=photo_hash,
        stage=EvidenceStage.BEFORE,
    )
    session.flush()
    return created


@pytest.fixture
def client(session: Session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: SUPERVISOR
    with TestClient(app) as raw:
        yield raw
    app.dependency_overrides.clear()


class TestTheRun:
    def test_rf_170_una_ot_sincronizada_termina_con_una_ejecucion_en_estado_terminal(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = make_order(session, unit, code="OT-1", photo_hash="a" * 64)
        assert orders_without_a_terminal_run(session, unit) == [order]

        run = execute(session, unit, order)
        assert run.is_terminal
        assert run.report is not None
        assert orders_without_a_terminal_run(session, unit) == []

    def test_rf_204_sin_pasarela_el_informe_se_guarda_parcial_y_dice_que_falta(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = make_order(session, unit, code="OT-2", photo_hash="b" * 64)
        run = execute(session, unit, order, gateway_reachable=False)

        assert run.state == RunState.PARTIAL
        report = latest_report(session, order.id)
        assert report is not None
        assert report.skipped
        assert "No se ejecutó" in report.summary

    def test_rf_180_el_nodo_que_no_corrio_queda_en_la_traza_con_su_motivo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """«¿Por qué no hay sección visual?» tiene respuesta en el registro, no en la memoria de
        alguien sobre el despliegue."""
        order = make_order(session, unit, code="OT-3", photo_hash="c" * 64)
        run = execute(session, unit, order, gateway_reachable=False)
        session.refresh(run)

        skipped = [trace for trace in run.traces if trace.skipped_reason]
        assert skipped
        assert any(
            "visual" in trace.node or "visual" in (trace.skipped_reason or "") for trace in skipped
        )

    def test_rf_180_dos_ejecuciones_del_mismo_grafo_dan_el_mismo_informe(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Sin esto, «reproducir una ejecución» no significa nada y la traza es decorado."""
        order = make_order(session, unit, code="OT-4", photo_hash="d" * 64)
        first = execute(session, unit, order)
        second = execute(session, unit, order)
        session.flush()

        assert first.report is not None and second.report is not None
        # El presupuesto lleva la duración medida, que no puede ser igual; todo lo demás sí.
        one = dict(first.report.document)
        other = dict(second.report.document)
        one.pop("budget")
        other.pop("budget")
        assert one == other

    def test_una_ejecucion_fallida_queda_registrada_con_su_motivo_y_no_revienta(
        self, session: Session, unit: BusinessUnit, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """El único estado que RF-170 prohíbe es que la OT no tenga ejecución ninguna."""
        order = make_order(session, unit, code="OT-5", photo_hash="e" * 64)

        def explode(*args: object, **kwargs: object) -> None:
            raise RuntimeError("el grafo se rompió")

        monkeypatch.setattr("app.prereview.service.run_pre_review", explode)
        run = execute(session, unit, order)

        assert run.state == RunState.FAILED
        assert run.error is not None and "el grafo se rompió" in run.error
        assert run.is_terminal
        assert run.report is None


class TestTheCrossOrderRules:
    def test_rf_174_la_misma_foto_en_dos_ot_de_la_unidad_se_detecta(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El patrón que nada miraba: dentro de una OT la pantalla ya lo señala, entre OT no."""
        shared = hashlib.sha256(b"la misma foto").hexdigest()
        make_order(session, unit, code="OT-A", photo_hash=shared)
        second = make_order(session, unit, code="OT-B", photo_hash=shared)

        report = latest_report(session, execute(session, unit, second).work_order_id)
        assert report is not None
        messages = " ".join(item.message for item in report.observations)
        assert "mismo contenido" in messages
        assert "OT-A" in messages

    def test_adr_009_no_se_compara_contra_las_ot_de_otra_unidad(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un patrón que cruzara unidades sería un hallazgo que nadie en ninguna de las dos puede
        accionar, y leer las capturas de otra unidad es lo que ADR-009 prohíbe."""
        org = session.query(Organization).one()
        other_unit = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other_unit)
        session.flush()
        ingest_metadata(session, other_unit, build_metadata("cnel-gye"))

        shared = hashlib.sha256(b"foto compartida entre unidades").hexdigest()
        make_order(session, other_unit, code="OT-MAN", photo_hash=shared)
        mine = make_order(session, unit, code="OT-GYE", photo_hash=shared)

        facts = build_facts(session, unit, mine)
        assert all(other.code != "OT-MAN" for other in facts.other_orders)
        report = latest_report(session, execute(session, unit, mine).work_order_id)
        assert report is not None
        assert "OT-MAN" not in " ".join(item.message for item in report.observations)


class TestTheWorker:
    def test_rf_170_una_pasada_vacia_la_cola(self, session: Session, unit: BusinessUnit) -> None:
        for index in range(3):
            make_order(session, unit, code=f"OT-W{index}", photo_hash=f"{index}" * 64)

        report = run_for_unit(session, unit)
        assert report.considered == 3
        assert report.completed + report.partial == 3
        assert orders_without_a_terminal_run(session, unit) == []

    def test_una_pasada_sin_nada_pendiente_no_hace_nada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        assert run_for_unit(session, unit).considered == 0


class TestTheReviewScreen:
    def test_rf_111_el_informe_llega_al_detalle_de_la_revision(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        order = make_order(session, unit, code="OT-R1", photo_hash="f" * 64)
        execute(session, unit, order)
        session.flush()

        body = client.get(f"/api/v1/review/units/{unit.code}/work-orders/{order.id}").json()
        assert body["agent_report"] is not None
        assert body["agent_report"]["report"]["risk_level"] in ("low", "medium", "high")
        assert body["agent_report"]["run_state"] in RunState.TERMINAL

    def test_rf_204_sin_ejecucion_el_detalle_dice_que_no_hay_informe_y_no_falla(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Null es una respuesta ordinaria: la OT puede estar esperando el lote nocturno."""
        order = make_order(session, unit, code="OT-R2", photo_hash="0" * 64)

        body = client.get(f"/api/v1/review/units/{unit.code}/work-orders/{order.id}").json()
        assert body["agent_report"] is None
        # Y lo que sí sostiene la decisión sigue completo.
        assert body["compliance"]
        assert "blockers" in body

    def test_rf_204_una_ejecucion_fallida_se_distingue_de_no_haber_corrido(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """«No hay informe» tiene dos significados muy distintos, y quien decide sin uno debe saber
        cuál de los dos."""
        order = make_order(session, unit, code="OT-R3", photo_hash="1" * 64)
        run = AgentRun(
            business_unit_id=unit.id,
            work_order_id=order.id,
            graph_version="prereview-0.1.0",
            hardware_profile="A",
            state=RunState.FAILED,
            error="RuntimeError: el grafo se rompió",
            attempts=1,
        )
        session.add(run)
        session.flush()

        body = client.get(f"/api/v1/review/units/{unit.code}/work-orders/{order.id}").json()
        assert body["agent_report"]["report"] is None
        assert body["agent_report"]["run_state"] == RunState.FAILED
        assert "se rompió" in body["agent_report"]["error"]

    def test_rf_204_aprobar_funciona_sin_informe_de_agente(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """La propiedad que no se negocia: el agente no es una compuerta."""
        from app.responses.models import FormResponse

        order = make_order(session, unit, code="OT-R4", photo_hash="2" * 64)
        assert latest_run(session, order.id) is None

        # La segunda foto que el formulario exige, para que la aprobación sea alcanzable: lo que
        # este test prueba es que el agente no bloquea, no la compuerta de evidencia de I6.
        response = session.query(FormResponse).filter_by(work_order_id=order.id).one()
        register_evidence(
            session,
            response,
            kind="foto",
            storage_key="s3://OT-R4-antes-2.jpg",
            content_hash=hashlib.sha256(b"OT-R4 segunda").hexdigest(),
            stage=EvidenceStage.BEFORE,
        )
        session.flush()

        blockers = client.get(f"/api/v1/review/units/{unit.code}/work-orders/{order.id}").json()[
            "blockers"
        ]
        assert blockers == [], f"impedimentos deterministas inesperados: {blockers}"

        answer = client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={"decision": "aprobada", "note": "Sin informe de agente."},
        )
        assert answer.status_code == 200, answer.text


class TestTheGuardrailIsOnThePath:
    """RF-182: nothing is stored unvalidated.

    The golden sets of RNF-060 measure a corpus after the fact; this measures the report a
    supervisor is about to read. The graph is patched to produce personal data on purpose: the
    deterministic nodes never would, and that is exactly why the measure read zero without anything
    preventing anything.
    """

    def _seeded_report(self, work_order_id: str) -> AgentReport:
        return AgentReport(
            work_order_id=work_order_id,
            graph_version="test",
            hardware_profile="A",
            risk_level=RiskLevel.LOW,
            status=RunStatus.COMPLETE,
            summary="El cliente 0926687856 confirmó al 0991234567",
            observations=[
                Observation(
                    id="SEMBRADA-1",
                    category=Category.COHERENCE,
                    severity=Severity.MEDIUM,
                    message="Contactar a cliente@correo.com para confirmar la hora",
                    evidence=[EvidenceRef(type=EvidenceType.FIELD, json_path="$.answers.note")],
                ),
                Observation(
                    id="SEMBRADA-2",
                    category=Category.COHERENCE,
                    severity=Severity.HIGH,
                    message="El técnico mintió sobre la hora de llegada",
                    evidence=[EvidenceRef(type=EvidenceType.FIELD, json_path="$.answers.note")],
                ),
            ],
        )

    def test_personal_data_never_reaches_the_stored_report(
        self, session: Session, unit: BusinessUnit, monkeypatch
    ):
        order = make_order(session, unit, code="OT-GR-1", photo_hash="a" * 64)
        monkeypatch.setattr(
            "app.prereview.service.run_pre_review",
            lambda *args, **kwargs: self._seeded_report(str(order.id)),
        )
        execute(session, unit, order)
        stored = latest_report(session, order.id)
        assert stored is not None
        rendered = stored.model_dump_json()
        for secret in ("0926687856", "0991234567", "cliente@correo.com"):
            assert secret not in rendered, secret

    def test_the_accusatory_observation_is_refused_and_counted(
        self, session: Session, unit: BusinessUnit, monkeypatch
    ):
        order = make_order(session, unit, code="OT-GR-2", photo_hash="b" * 64)
        monkeypatch.setattr(
            "app.prereview.service.run_pre_review",
            lambda *args, **kwargs: self._seeded_report(str(order.id)),
        )
        execute(session, unit, order)
        stored = latest_report(session, order.id)
        assert stored is not None
        assert [item.id for item in stored.observations] == ["SEMBRADA-1"]
        assert stored.discarded == 1

    def test_the_finding_survives_the_redaction(
        self, session: Session, unit: BusinessUnit, monkeypatch
    ):
        """Deleting the observation would have cost a real finding; the address was incidental."""
        order = make_order(session, unit, code="OT-GR-3", photo_hash="c" * 64)
        monkeypatch.setattr(
            "app.prereview.service.run_pre_review",
            lambda *args, **kwargs: self._seeded_report(str(order.id)),
        )
        execute(session, unit, order)
        stored = latest_report(session, order.id)
        assert stored is not None
        assert "para confirmar la hora" in stored.observations[0].message

    def test_the_guardrail_leaves_a_trace_even_when_it_changed_nothing(
        self, session: Session, unit: BusinessUnit
    ):
        """«It ran and found nothing» and «it did not run» are different answers, and only one of
        them is reassuring (RF-180)."""
        order = make_order(session, unit, code="OT-GR-4", photo_hash="d" * 64)
        run = execute(session, unit, order)
        traces = [
            trace
            for trace in session.query(AgentStepTrace).filter(AgentStepTrace.agent_run_id == run.id)
            if trace.node == "guardrails"
        ]
        assert len(traces) == 1
        assert traces[0].output["attempts"] == 1
        assert traces[0].output["redactions"] == []

    def test_the_trace_records_what_was_redacted(
        self, session: Session, unit: BusinessUnit, monkeypatch
    ):
        order = make_order(session, unit, code="OT-GR-5", photo_hash="e" * 64)
        monkeypatch.setattr(
            "app.prereview.service.run_pre_review",
            lambda *args, **kwargs: self._seeded_report(str(order.id)),
        )
        run = execute(session, unit, order)
        trace = next(
            trace
            for trace in session.query(AgentStepTrace).filter(AgentStepTrace.agent_run_id == run.id)
            if trace.node == "guardrails"
        )
        assert trace.output["redactions"]
        assert trace.output["dropped"][0]["observation_id"] == "SEMBRADA-2"
