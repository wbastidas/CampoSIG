"""Aprobación en lote asistida, por HTTP (RF-176).

Lo que RF-176 concede y lo que exige a cambio: se puede aprobar en bloque, **solo** OT de riesgo
bajo, **solo** con acción humana explícita, y **siempre** apartando una muestra para verificación
individual. Las tres cosas se prueban aquí contra base real, porque el riesgo viene de un informe
guardado y los impedimentos de una captura de verdad.

La propiedad que más importa es negativa: el lote pasa por el **mismo** `decide` que una aprobación
individual. Un camino más rápido que se saltara los impedimentos de I6 sería una segunda puerta más
débil, y a partir de ahí la compuerta no significa nada.
"""

from __future__ import annotations

import hashlib
from random import Random

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.prereview.models import AgentRun, RunState, StoredReport
from app.responses.models import EvidenceStage
from app.responses.service import register_evidence, save_answers
from app.review.batch import approve_batch
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

INSPECTOR = Principal(
    subject="kc|inspector.demo",
    username="inspector.demo",
    roles=frozenset({Role.INSPECTOR.value}),
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


def make_approvable(session: Session, unit: BusinessUnit, *, code: str, photos: int = 2):
    """A work order with everything I6 asks for, so only the batch rules can refuse it."""
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
            # B04: el formulario exige ATS, así que la referencia es obligatoria.
            "ats_reference": "ATS-2026-0001",
        },
        submit=True,
    )
    for index in range(photos):
        register_evidence(
            session,
            response,
            kind="foto",
            storage_key=f"s3://{code}-{index}.jpg",
            content_hash=hashlib.sha256(f"{code}{index}".encode()).hexdigest(),
            stage=EvidenceStage.BEFORE,
        )
    session.flush()
    return order


def give_report(session: Session, unit: BusinessUnit, order, risk: str) -> AgentRun:
    """A stored report at a chosen risk level, which is what makes an order batchable."""
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
                "summary": f"riesgo {risk}",
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


def client_as(session: Session, principal: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: principal
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, SUPERVISOR) as raw:
        yield raw


def batch_url(unit_code: str) -> str:
    return f"/api/v1/review/units/{unit_code}/batch-approval"


class TestWhatItApproves:
    def test_rf_176_aprueba_las_de_riesgo_bajo_y_aparta_una_muestra(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        orders = [make_approvable(session, unit, code=f"OT-L{i}") for i in range(10)]
        for order in orders:
            give_report(session, unit, order, "low")
        session.flush()

        answer = client.post(
            batch_url(unit.code),
            json={"work_order_ids": [str(order.id) for order in orders]},
        )
        assert answer.status_code == 200, answer.text
        body = answer.json()

        # Diez de riesgo bajo: nueve aprobadas y una apartada.
        assert len(body["approved"]) == 9
        assert len(body["sampled"]) == 1
        assert body["refused"] == []
        # Y se dice, porque «9 aprobadas» sin «1 apartada» haría creer que el lote terminó.
        assert "apartadas para verificación" in body["sample_note"]

    def test_rf_176_las_apartadas_no_quedan_aprobadas(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Es la mitad del requerimiento: si se aprobaran igual, el muestreo sería decorativo."""
        orders = [make_approvable(session, unit, code=f"OT-S{i}") for i in range(4)]
        for order in orders:
            give_report(session, unit, order, "low")
        session.flush()

        body = client.post(
            batch_url(unit.code), json={"work_order_ids": [str(o.id) for o in orders]}
        ).json()
        held = set(body["sampled"])
        assert held

        for order in orders:
            session.refresh(order)
            if str(order.id) in held:
                assert order.state != WorkOrderState.APPROVED
            else:
                assert order.state == WorkOrderState.APPROVED

    def test_rf_176_una_de_riesgo_medio_se_rechaza_con_su_motivo(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        low = make_approvable(session, unit, code="OT-LOW")
        medium = make_approvable(session, unit, code="OT-MED")
        give_report(session, unit, low, "low")
        give_report(session, unit, medium, "medium")
        session.flush()

        body = client.post(
            batch_url(unit.code), json={"work_order_ids": [str(low.id), str(medium.id)]}
        ).json()
        refused = {item["code"]: item["reason"] for item in body["refused"]}
        assert "OT-MED" in refused
        assert "riesgo medio" in refused["OT-MED"]

    def test_rf_176_sin_informe_no_se_aprueba_en_lote(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Sin informe no es riesgo bajo: una OT que nadie pre-revisó es justo la que un lote no
        debería tragarse."""
        order = make_approvable(session, unit, code="OT-NR")
        session.flush()

        body = client.post(batch_url(unit.code), json={"work_order_ids": [str(order.id)]}).json()
        assert body["approved"] == []
        assert "sin informe" in body["refused"][0]["reason"]

    def test_rf_176_los_impedimentos_de_i6_siguen_valiendo_en_un_lote(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """La propiedad negativa que más importa: el lote pasa por el mismo `decide`.

        Un camino más rápido que se saltara los impedimentos sería una segunda puerta más débil, y a
        partir de ahí la compuerta no significa nada.

        Cinco OT sin foto, no una: con una sola, la muestra se la lleva entera —su piso es uno— y el
        lote no llegaría nunca a `decide`. Y todas sin foto a propósito: así, sea cual sea la que
        toque la muestra, las demás tienen que rechazarse, sin depender de la semilla del azar.
        """
        orders = [make_approvable(session, unit, code=f"OT-NOPIC{i}", photos=0) for i in range(5)]
        for order in orders:
            give_report(session, unit, order, "low")
        session.flush()

        body = client.post(
            batch_url(unit.code), json={"work_order_ids": [str(o.id) for o in orders]}
        ).json()
        assert body["approved"] == []
        assert len(body["refused"]) == 4
        assert all("fotos" in item["reason"].lower() for item in body["refused"])
        for order in orders:
            session.refresh(order)
            assert order.state != WorkOrderState.APPROVED


class TestWhoMayDoIt:
    def test_rf_176_un_inspector_no_aprueba_en_lote(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Puede decidir sobre una OT, pero no es quien firma un bloque de ellas."""
        order = make_approvable(session, unit, code="OT-INSP")
        give_report(session, unit, order, "low")
        session.flush()

        with client_as(session, INSPECTOR) as raw:
            answer = raw.post(batch_url(unit.code), json={"work_order_ids": [str(order.id)]})
        assert answer.status_code == 403

    def test_adr_009_una_ot_de_otra_unidad_se_rechaza_en_vez_de_ignorarse(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Descartarla en silencio dejaría creer que el lote cubrió una OT que nunca tocó."""
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        ingest_metadata(session, other, build_metadata("cnel-gye"))
        foreign = make_approvable(session, other, code="OT-MAN")
        give_report(session, other, foreign, "low")
        session.flush()

        body = client.post(batch_url(unit.code), json={"work_order_ids": [str(foreign.id)]}).json()
        assert body["approved"] == []
        assert "no existe en esta unidad" in body["refused"][0]["reason"]
        session.refresh(foreign)
        assert foreign.state != WorkOrderState.APPROVED


class TestTheAudit:
    def test_cada_aprobacion_del_lote_queda_firmada_por_la_persona_del_token(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """ADR-013: la identidad sale del token, también en un lote."""
        from app.review.models import ReviewDecision

        orders = [make_approvable(session, unit, code=f"OT-A{i}") for i in range(3)]
        for order in orders:
            give_report(session, unit, order, "low")
        session.flush()

        client.post(batch_url(unit.code), json={"work_order_ids": [str(o.id) for o in orders]})
        decisions = session.query(ReviewDecision).all()
        assert decisions
        assert all(row.reviewer_sub == SUPERVISOR.subject for row in decisions)
        assert all("lote" in (row.note or "") for row in decisions)


class TestThePreview:
    def test_la_pantalla_puede_decir_cuántas_quedarán_apartadas_antes_de_confirmar(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        body = client.get(f"{batch_url(unit.code)}/preview", params={"size": 40}).json()
        assert body == {"batch_size": 40, "sampled": 2, "would_approve": 38}


class TestTheSampleItself:
    def test_la_muestra_se_toma_solo_de_las_elegibles(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Muestrear una que se iba a rechazar de todos modos desperdiciaría la muestra."""
        low = [make_approvable(session, unit, code=f"OT-E{i}") for i in range(4)]
        for order in low:
            give_report(session, unit, order, "low")
        high = make_approvable(session, unit, code="OT-HIGH")
        give_report(session, unit, high, "high")
        session.flush()

        outcome = approve_batch(
            session,
            unit,
            [*low, high],
            reviewer_sub=SUPERVISOR.subject,
            rng=Random(7),
        )
        assert len(outcome.sampled) == 1
        assert str(high.id) not in outcome.sampled
        assert len(outcome.approved) == 3
        assert [item.code for item in outcome.refused] == ["OT-HIGH"]

    def test_un_lote_de_una_sola_ot_la_aparta_entera(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El piso de la muestra es uno, así que un lote de una no aprueba nada.

        Que es lo correcto: aprobar de una en una ya existe, y se llama aprobar.
        """
        order = make_approvable(session, unit, code="OT-ONE")
        give_report(session, unit, order, "low")
        session.flush()

        outcome = approve_batch(session, unit, [order], reviewer_sub=SUPERVISOR.subject)
        assert outcome.approved == []
        assert outcome.sampled == [str(order.id)]


class TestTheQueueSaysTheRisk:
    def test_la_cola_trae_el_riesgo_para_que_la_selección_no_sea_a_ciegas(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Sin esto, el supervisor selecciona y el servidor le rechaza la mitad del lote."""
        low = make_approvable(session, unit, code="OT-Q1")
        medium = make_approvable(session, unit, code="OT-Q2")
        make_approvable(session, unit, code="OT-Q3")
        give_report(session, unit, low, "low")
        give_report(session, unit, medium, "medium")
        session.flush()

        body = client.get(f"/api/v1/review/units/{unit.code}/queue").json()
        risk = {item["code"]: item["risk_level"] for item in body["items"]}
        assert risk["OT-Q1"] == "low"
        assert risk["OT-Q2"] == "medium"
        # Sin informe es None, y no «low»: de eso depende que el lote no se la trague.
        assert risk["OT-Q3"] is None
        state = {item["code"]: item["pre_review_state"] for item in body["items"]}
        assert state["OT-Q1"] == RunState.DONE
        assert state["OT-Q3"] is None

    def test_el_riesgo_de_la_cola_no_cuesta_una_consulta_por_fila(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """La cola tiene dos segundos con diez mil OT (RNF). `latest_report` por fila serían dos
        consultas y una validación del documento completo por cada una."""
        orders = [make_approvable(session, unit, code=f"OT-N{i}") for i in range(12)]
        for order in orders:
            give_report(session, unit, order, "low")
        session.flush()

        statements: list[str] = []

        @event.listens_for(session.get_bind(), "before_cursor_execute")
        def record(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
            statements.append(statement)

        try:
            body = client.get(f"/api/v1/review/units/{unit.code}/queue").json()
        finally:
            event.remove(session.get_bind(), "before_cursor_execute", record)

        assert len(body["items"]) == 12
        risk_queries = [text for text in statements if "agent_run" in text]
        assert len(risk_queries) == 1, risk_queries
