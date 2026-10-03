"""El tablero de mantenimiento, contra base real (RF-133).

Tres preguntas con las que se planifica: qué alimentador se está deteriorando, qué activo vuelve, y
qué queda pendiente. Las tres salen de los hallazgos que registran las cuadrillas, que viven dentro
del JSONB de una captura y **no tienen estado**.

De ahí la decisión que más se prueba aquí: «abierto» es una definición y no un hecho. Significa que
no hay ninguna OT posterior cerrada sobre el mismo activo, es una aproximación, y el payload lo dice
con palabras — un número de pendientes cuya definición nadie puede ver es uno que se discute en vez
de trabajarse.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.maintenance import OPEN_DEFINITION
from app.audit import service as audit
from app.audit.models import EventKind
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.responses.service import save_answers
from app.workorders.models import WorkOrder, WorkOrderState
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


def an_inspection(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str,
    asset: str = "P-000452",
    feeder: str = "04BH070T11",
    findings: list[dict] | None = None,
    defects: list[str] | None = None,
    condition: str = "regular",
    submitted: datetime | None = None,
) -> WorkOrder:
    """Una inspección enviada, con sus hallazgos."""
    order = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        asset_code=asset,
        feeder_code=feeder,
        longitude=-79.90,
        latitude=-2.17,
        zone="Urbano",
        planner_id="kc|planner.a",
    )
    order.state = WorkOrderState.SYNCED
    order.form_version = "1.0.0"
    order.code = code
    session.flush()

    answers: dict[str, object] = {
        "work_order_code": code,
        "work_type": "inspeccion_preventiva",
        "priority": "media",
        "general_condition": condition,
        "code": asset,
        "material": "concrete",
        "feeder_code": feeder,
        "final_state": "resuelto",
        # B04: el formulario exige ATS, así que la referencia es obligatoria.
        "ats_reference": "ATS-2026-0001",
    }
    if findings is not None:
        answers["findings"] = findings
    if defects is not None:
        answers["defects"] = defects

    response = save_answers(session, unit, order, answers=answers, submit=True)
    response.submitted_at = submitted or NOW
    session.flush()
    return order


def attended(session: Session, unit: BusinessUnit, *, asset: str, when: datetime) -> WorkOrder:
    """Una OT cerrada sobre el mismo activo, con su transición en la bitácora.

    El momento sale de la bitácora y no de `updated_at`, porque esa columna se mueve con cualquier
    edición de la fila —una nota, una reasignación—, y entonces reasignar una OT vieja hoy cerraría
    un hallazgo de ayer. El evento, además, no se puede reescribir (RF-160).
    """
    order = create_work_order(
        session,
        unit,
        work_type="mantenimiento_correctivo",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        asset_code=asset,
        planner_id="kc|planner.a",
    )
    order.state = WorkOrderState.CLOSED
    session.flush()
    audit.record(
        session,
        unit.id,
        kind=EventKind.TRANSITION,
        subject_type="orden_trabajo",
        subject_id=str(order.id),
        work_order_id=order.id,
        asset_code=asset,
        actor="kc|sup.1",
        payload={"from": "aprobada", "to": WorkOrderState.CLOSED.value},
        occurred_at=when,
    )
    return order


def client_as(session: Session, principal: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: principal
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, SUPERVISOR) as raw:
        yield raw


def board(client: TestClient, unit: BusinessUnit, **params: object) -> dict:
    answer = client.get(f"/api/v1/analytics/units/{unit.code}/maintenance", params=params)
    assert answer.status_code == 200, answer.text
    return answer.json()


def finding(defect: str, criticality: str = "alta", asset: str | None = None, wants: bool = False):
    """Una fila de la tabla de hallazgos.

    Sin activo por omisión: el hallazgo hereda el de la captura, que es lo que hace la plataforma.
    Un activo fijo aquí haría que los tests de reincidencia midieran el del helper y no el de la OT.
    """
    row: dict[str, object] = {
        "defect_code": defect,
        "criticality": criticality,
        "generate_work_order": wants,
    }
    if asset is not None:
        row["asset_code"] = asset
    return row


class TestTheHeat:
    def test_rf_133_los_defectos_se_reparten_por_alimentador(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        for index in range(3):
            an_inspection(
                session,
                unit,
                code=f"OT-N{index}",
                feeder="ALIM-NORTE",
                findings=[finding("cruceta_podrida")],
            )
        an_inspection(
            session, unit, code="OT-S1", feeder="ALIM-SUR", findings=[finding("aislador_roto")]
        )
        session.flush()

        heat = {row["feeder_code"]: row for row in board(client, unit)["heat"]["by_feeder"]}
        assert heat["ALIM-NORTE"]["defects"] == 3
        assert heat["ALIM-NORTE"]["share"] == pytest.approx(0.75)
        assert heat["ALIM-NORTE"]["top_defect"] == {"defect_code": "cruceta_podrida", "times": 3}

    def test_el_alimentador_con_más_defectos_va_primero(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_inspection(session, unit, code="OT-A", feeder="ALIM-A", findings=[finding("x")])
        for index in range(2):
            an_inspection(
                session, unit, code=f"OT-B{index}", feeder="ALIM-B", findings=[finding("y")]
            )
        session.flush()
        assert board(client, unit)["heat"]["by_feeder"][0]["feeder_code"] == "ALIM-B"

    def test_un_hallazgo_sin_alimentador_se_cuenta_aparte(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Un mapa de calor que los descartara en silencio subreportaría todos los alimentadores."""
        order = an_inspection(session, unit, code="OT-SF", findings=[finding("x")])
        order.feeder_code = None
        from app.responses.models import FormResponse

        response = session.query(FormResponse).filter_by(work_order_id=order.id).one()
        response.answers = {k: v for k, v in response.answers.items() if k != "feeder_code"}
        session.flush()

        heat = board(client, unit)["heat"]
        assert heat["without_feeder"] == 1
        assert heat["by_feeder"] == []


class TestRecurrence:
    def test_rf_133_un_activo_con_varios_hallazgos_se_destaca(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_inspection(session, unit, code="OT-R1", asset="P-TERCO", findings=[finding("x")])
        an_inspection(session, unit, code="OT-R2", asset="P-TERCO", findings=[finding("x")])
        an_inspection(session, unit, code="OT-R3", asset="P-SANO", findings=[finding("x")])
        session.flush()

        rows = board(client, unit)["recurrence"]
        assert [row["asset_code"] for row in rows] == ["P-TERCO"]
        assert rows[0]["findings"] == 2
        # El mismo defecto dos veces: una reparación que no aguantó.
        assert rows[0]["defects"] == {"x": 2}

    def test_un_activo_con_defectos_distintos_se_distingue_del_que_repite_uno(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Un defecto tres veces es una reparación que no aguantó; tres defectos distintos es un
        activo al final de su vida, y el planificador hace cosas diferentes."""
        an_inspection(
            session,
            unit,
            code="OT-V1",
            asset="P-VIEJO",
            findings=[finding("cruceta_podrida"), finding("aislador_roto")],
        )
        an_inspection(
            session, unit, code="OT-V2", asset="P-VIEJO", findings=[finding("poste_fisurado")]
        )
        session.flush()

        rows = board(client, unit)["recurrence"]
        assert rows[0]["asset_code"] == "P-VIEJO"
        assert len(rows[0]["defects"]) == 3

    def test_la_peor_criticidad_del_activo_viaja(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_inspection(
            session,
            unit,
            code="OT-C1",
            asset="P-C",
            findings=[finding("x", "baja"), finding("y", "critica")],
        )
        an_inspection(session, unit, code="OT-C2", asset="P-C", findings=[finding("z", "media")])
        session.flush()
        assert board(client, unit)["recurrence"][0]["worst_criticality"] == "critica"


class TestTheBacklog:
    def test_rf_133_los_hallazgos_abiertos_se_cuentan_por_criticidad(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_inspection(
            session,
            unit,
            code="OT-B1",
            findings=[finding("x", "critica"), finding("y", "alta"), finding("z", "alta")],
        )
        session.flush()

        backlog = board(client, unit)["backlog"]
        assert backlog["open_by_criticality"] == {"critica": 1, "alta": 2}
        assert backlog["open"] == 3

    def test_las_criticidades_van_de_peor_a_mejor(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """«alta» antes que «critica» por orden alfabético pondría la segunda peor primero."""
        an_inspection(
            session,
            unit,
            code="OT-O1",
            findings=[finding("a", "baja"), finding("b", "critica"), finding("c", "media")],
        )
        session.flush()
        assert list(board(client, unit)["backlog"]["open_by_criticality"]) == [
            "critica",
            "media",
            "baja",
        ]

    def test_rf_133_un_hallazgo_con_ot_posterior_cerrada_deja_de_estar_abierto(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_inspection(
            session, unit, code="OT-AT", asset="P-ATENDIDO", findings=[finding("x", "alta")]
        )
        attended(session, unit, asset="P-ATENDIDO", when=NOW + timedelta(days=1))
        session.flush()

        backlog = board(client, unit)["backlog"]
        assert backlog["open"] == 0
        assert backlog["attended"] == 1

    def test_una_ot_anterior_al_hallazgo_no_lo_cierra(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """El trabajo que lo cierra es el que vino después. Si no, cualquier activo con historia
        aparecería sin pendientes."""
        attended(session, unit, asset="P-ANTES", when=NOW - timedelta(days=10))
        an_inspection(session, unit, code="OT-AN", asset="P-ANTES", findings=[finding("x", "alta")])
        session.flush()

        from app.analytics.maintenance import _last_attended

        # Guarda del propio test: si la bitácora no trajera nada, el test pasaría por vacuidad y no
        # estaría comprobando el orden de los momentos.
        assert _last_attended(session, unit.id, {"P-ANTES"}), "la bitácora no registró el cierre"
        assert board(client, unit)["backlog"]["open"] == 1

    def test_la_definición_de_abierto_viaja_con_el_número(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_inspection(session, unit, code="OT-D1", findings=[finding("x")])
        session.flush()
        definition = board(client, unit)["backlog"]["definition"]
        assert definition == OPEN_DEFINITION
        assert "aproximación" in definition

    def test_un_hallazgo_sin_activo_no_se_llama_abierto_ni_atendido(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """No hay con qué seguirlo, y llamarlo de cualquiera de las dos formas sería una afirmación
        que el dato no sostiene."""
        order = an_inspection(
            session,
            unit,
            code="OT-SA",
            findings=[{"defect_code": "x", "criticality": "alta"}],
        )
        order.asset_code = None
        from app.responses.models import FormResponse

        response = session.query(FormResponse).filter_by(work_order_id=order.id).one()
        response.answers = {k: v for k, v in response.answers.items() if k != "code"}
        session.flush()

        backlog = board(client, unit)["backlog"]
        assert backlog["untrackable"] == 1
        assert backlog["open"] == 0
        assert backlog["attended"] == 0

    def test_el_hallazgo_sigue_al_activo_que_identificó_la_captura(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """La OT pudo crearse sin activo y la cuadrilla leerlo de la placa en sitio.

        El código de la captura es entonces el mejor dato que hay, y contar ese hallazgo como
        imposible de seguir sería descartar el que más se sabe. La lista simple de defectos ya lo
        hacía; la tabla de hallazgos no, y esa diferencia entre los dos lectores era el defecto.
        """
        order = an_inspection(
            session,
            unit,
            code="OT-SC",
            asset="P-000777",
            findings=[{"defect_code": "x", "criticality": "alta"}],
        )
        order.asset_code = None
        session.flush()

        backlog = board(client, unit)["backlog"]
        assert backlog["untrackable"] == 0
        assert backlog["open"] == 1

    def test_los_que_la_cuadrilla_pidió_convertir_en_ot_se_cuentan(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_inspection(
            session,
            unit,
            code="OT-W1",
            findings=[finding("x", wants=True), finding("y", wants=False)],
        )
        session.flush()
        assert board(client, unit)["backlog"]["wants_order"] == 1


class TestBothSourcesOfDefects:
    def test_la_lista_simple_de_defectos_también_cuenta(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Un tablero que leyera solo la tabla de hallazgos perdería todos los defectos anotados en
        una inspección de rutina, que son la mayoría."""
        an_inspection(session, unit, code="OT-L1", defects=["cruceta_podrida", "aislador_roto"])
        session.flush()

        body = board(client, unit)
        assert body["findings"] == 2
        assert body["by_defect"]["cruceta_podrida"] == 1

    def test_un_defecto_sin_criticidad_la_hereda_del_estado_del_activo(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Inventar «alta» pondría trabajo en la cabeza de la lista de un planificador que nadie
        pidió que estuviera ahí."""
        an_inspection(session, unit, code="OT-CR", defects=["x"], condition="critico")
        session.flush()
        assert board(client, unit)["backlog"]["open_by_criticality"] == {"critica": 1}


class TestTheFilters:
    def test_rf_133_se_puede_filtrar_por_tipo_de_defecto(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_inspection(session, unit, code="OT-F1", findings=[finding("cruceta_podrida")])
        an_inspection(session, unit, code="OT-F2", findings=[finding("aislador_roto")])
        session.flush()

        body = board(client, unit, defect_code="cruceta_podrida")
        assert body["findings"] == 1
        assert body["defect_filter"] == "cruceta_podrida"
        assert list(body["by_defect"]) == ["cruceta_podrida"]

    def test_rf_133_se_puede_filtrar_por_periodo(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_inspection(
            session,
            unit,
            code="OT-VIEJA",
            findings=[finding("x")],
            submitted=NOW - timedelta(days=90),
        )
        an_inspection(session, unit, code="OT-NUEVA", findings=[finding("x")])
        session.flush()
        assert board(client, unit, since=(NOW - timedelta(days=7)).isoformat())["findings"] == 1

    def test_sin_hallazgos_el_tablero_está_vacío_y_no_falla(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        body = board(client, unit)
        assert body["findings"] == 0
        assert body["heat"]["by_feeder"] == []
        assert body["backlog"]["open"] == 0


class TestWhoMaySee:
    def test_un_técnico_no_ve_el_tablero_de_mantenimiento(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        with client_as(session, TECHNICIAN) as raw:
            answer = raw.get(f"/api/v1/analytics/units/{unit.code}/maintenance")
        assert answer.status_code == 403

    def test_adr_009_no_cuenta_hallazgos_de_otra_unidad(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        ingest_metadata(session, other, build_metadata("cnel-gye"))
        an_inspection(session, other, code="OT-MAN", findings=[finding("x")])
        session.flush()
        assert board(client, unit)["findings"] == 0
