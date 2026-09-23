"""El tablero operativo, contra base real (RF-130).

Los tres primeros paneles —OT por estado, SLA y productividad— salen de las órdenes. El cuarto, los
tiempos, sale de la bitácora, y hasta que la bitácora existió no se podía calcular: la máquina de
estados movía un campo y no dejaba registro.

Lo que se prueba con cuidado son las tres maneras en que un tablero de tiempos miente:

* contando como cero una OT que todavía no llegó —arrastra el promedio hacia abajo justo cuando las
  cuadrillas están ocupadas—;
* escondiendo las OT sin registro, con lo que el promedio informa el mejor caso;
* reiniciando el reloj en una reasignación, con lo que el tiempo que cuesta reasignar desaparece.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.operations import MIN_FOR_A_DURATION, percentile
from app.audit import service as audit
from app.audit.models import EventKind
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.workorders.models import Crew, WorkOrder, WorkOrderState
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


def an_order(
    session: Session,
    unit: BusinessUnit,
    *,
    state: str = WorkOrderState.PLANNED,
    sla_due_at: datetime | None = None,
    crew: Crew | None = None,
) -> WorkOrder:
    order = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        planner_id="kc|planner.a",
    )
    order.state = state
    order.sla_due_at = sla_due_at
    if crew is not None:
        order.assigned_crew_id = crew.id
    session.flush()
    return order


def reached(
    session: Session, unit: BusinessUnit, order: WorkOrder, state: str, when: datetime
) -> None:
    """A milestone in the trail, at a chosen moment.

    Written through the trail's own append so the event is a real one — same digest, same chain.
    The dashboard reads what the platform writes, and a fixture that inserted rows directly would
    be testing a shape the platform never produces.
    """
    audit.record(
        session,
        unit.id,
        kind=EventKind.TRANSITION,
        subject_type="orden_trabajo",
        subject_id=str(order.id),
        work_order_id=order.id,
        actor="kc|alguien",
        payload={"from": "anterior", "to": state},
        occurred_at=when,
    )


def a_crew(session: Session, unit: BusinessUnit, name: str) -> Crew:
    crew = Crew(business_unit_id=unit.id, code=name[:32], name=name, zone="Urbano")
    session.add(crew)
    session.flush()
    return crew


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
    answer = client.get(f"/api/v1/analytics/units/{unit.code}/operations", params=params)
    assert answer.status_code == 200, answer.text
    return answer.json()


class TestWhereTheWorkIs:
    def test_rf_130_las_ot_se_cuentan_por_estado(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_order(session, unit, state=WorkOrderState.PLANNED)
        an_order(session, unit, state=WorkOrderState.PLANNED)
        an_order(session, unit, state=WorkOrderState.IN_EXECUTION)
        session.flush()

        counts = board(client, unit)["by_state"]
        assert counts[WorkOrderState.PLANNED] == 2
        assert counts[WorkOrderState.IN_EXECUTION] == 1

    def test_el_tablero_dice_cuándo_se_calculó(
        self, client: TestClient, unit: BusinessUnit
    ) -> None:
        """RF-130 pide datos de menos de cinco minutos, y la única forma de que alguien sepa si los
        que está mirando lo son es que el tablero diga a qué hora se hicieron."""
        assert board(client, unit)["computed_at"]


class TestTheSla:
    def test_rf_130_una_ot_vencida_y_abierta_se_cuenta(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_order(
            session,
            unit,
            state=WorkOrderState.IN_EXECUTION,
            sla_due_at=datetime.now(UTC) - timedelta(hours=3),
        )
        session.flush()
        assert board(client, unit)["sla"]["overdue"] == 1

    def test_una_ot_vencida_pero_cerrada_es_historia_y_no_una_alarma(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Un tablero que grita por trabajo terminado es un tablero que se deja de mirar."""
        an_order(
            session,
            unit,
            state=WorkOrderState.CLOSED,
            sla_due_at=datetime.now(UTC) - timedelta(days=2),
        )
        session.flush()
        assert board(client, unit)["sla"]["overdue"] == 0

    def test_por_vencer_mira_una_jornada_hacia_adelante(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        an_order(
            session,
            unit,
            state=WorkOrderState.ASSIGNED,
            sla_due_at=datetime.now(UTC) + timedelta(hours=2),
        )
        an_order(
            session,
            unit,
            state=WorkOrderState.ASSIGNED,
            sla_due_at=datetime.now(UTC) + timedelta(days=5),
        )
        session.flush()

        sla = board(client, unit)["sla"]
        assert sla["due_soon"] == 1
        assert sla["due_soon_hours"] == 8

    def test_las_ot_sin_sla_se_dicen_en_vez_de_callarse(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """«0 vencidas» sobre cien OT que nunca tuvieron fecha no informa de nada."""
        for _ in range(3):
            an_order(session, unit, state=WorkOrderState.ASSIGNED, sla_due_at=None)
        session.flush()
        assert board(client, unit)["sla"]["without_sla"] == 3


class TestTheTimes:
    def test_rf_130_el_tiempo_de_despacho_a_llegada_sale_de_la_bitácora(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        for index in range(MIN_FOR_A_DURATION):
            order = an_order(session, unit, state=WorkOrderState.ON_SITE)
            reached(session, unit, order, WorkOrderState.ASSIGNED, NOW)
            reached(
                session,
                unit,
                order,
                WorkOrderState.ON_SITE,
                NOW + timedelta(minutes=30 + index),
            )
        session.flush()

        leg = next(
            item for item in board(client, unit)["legs"] if item["key"] == "despacho_llegada"
        )
        assert leg["measured"] == MIN_FOR_A_DURATION
        assert leg["median_minutes"] == pytest.approx(32.0)

    def test_una_ot_que_todavía_no_llega_no_cuenta_como_cero_minutos(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Contarla arrastraría el promedio hacia abajo justo cuando las cuadrillas están ocupadas.

        No ha tardado cero en llegar: no ha llegado.
        """
        for _ in range(MIN_FOR_A_DURATION):
            order = an_order(session, unit, state=WorkOrderState.ON_SITE)
            reached(session, unit, order, WorkOrderState.ASSIGNED, NOW)
            reached(session, unit, order, WorkOrderState.ON_SITE, NOW + timedelta(minutes=60))
        running = an_order(session, unit, state=WorkOrderState.EN_ROUTE)
        reached(session, unit, running, WorkOrderState.ASSIGNED, NOW)
        session.flush()

        leg = next(
            item for item in board(client, unit)["legs"] if item["key"] == "despacho_llegada"
        )
        assert leg["measured"] == MIN_FOR_A_DURATION
        assert leg["in_progress"] == 1
        assert leg["median_minutes"] == pytest.approx(60.0)

    def test_una_ot_terminada_sin_registro_se_cuenta_aparte(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Las que vienen de antes de la bitácora. Esconderlas haría que el promedio informara el
        mejor caso, que es el de las OT que sí quedaron bien registradas."""
        old = an_order(session, unit, state=WorkOrderState.CLOSED)
        session.flush()

        leg = next(
            item for item in board(client, unit)["legs"] if item["key"] == "despacho_llegada"
        )
        assert leg["unrecorded"] == 1
        assert leg["measured"] == 0
        assert old.state == WorkOrderState.CLOSED

    def test_con_pocas_muestras_no_se_reporta_una_mediana(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit, state=WorkOrderState.ON_SITE)
        reached(session, unit, order, WorkOrderState.ASSIGNED, NOW)
        reached(session, unit, order, WorkOrderState.ON_SITE, NOW + timedelta(minutes=45))
        session.flush()

        leg = next(
            item for item in board(client, unit)["legs"] if item["key"] == "despacho_llegada"
        )
        assert leg["measured"] == 1
        assert leg["median_minutes"] is None
        # Pero la cuenta viaja: el supervisor ve que hay una, no que no hay nada.
        assert leg["min_sample"] == MIN_FOR_A_DURATION

    def test_una_reasignación_no_reinicia_el_reloj(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """El tiempo que cuesta reasignar es tiempo que el trabajo tardó. Un tablero que lo esconde
        es un tablero con el que no se puede averiguar por qué."""
        for _ in range(MIN_FOR_A_DURATION):
            order = an_order(session, unit, state=WorkOrderState.ON_SITE)
            reached(session, unit, order, WorkOrderState.ASSIGNED, NOW)
            # Reasignada dos horas después, y llegó media hora más tarde.
            reached(session, unit, order, WorkOrderState.ASSIGNED, NOW + timedelta(hours=2))
            reached(
                session, unit, order, WorkOrderState.ON_SITE, NOW + timedelta(hours=2, minutes=30)
            )
        session.flush()

        leg = next(
            item for item in board(client, unit)["legs"] if item["key"] == "despacho_llegada"
        )
        # 150 minutos desde el primer despacho, no 30 desde el segundo.
        assert leg["median_minutes"] == pytest.approx(150.0)

    def test_el_p90_dice_lo_que_tardan_las_malas(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """La mediana dice cómo es un día normal; el p90 y el máximo, los que no lo son.

        Con nueve trabajos de media hora y uno de cinco, el p90 interpolado da 57 minutos: es la
        aritmética correcta y una respuesta inútil a «¿cuál fue la peor?». Por eso el máximo viaja
        al lado — en una muestra pequeña el percentil esconde justo la cola que interesa.
        """
        minutes = [30, 30, 30, 30, 30, 30, 30, 30, 30, 300]
        for extra in minutes:
            order = an_order(session, unit, state=WorkOrderState.ON_SITE)
            reached(session, unit, order, WorkOrderState.ASSIGNED, NOW)
            reached(session, unit, order, WorkOrderState.ON_SITE, NOW + timedelta(minutes=extra))
        session.flush()

        leg = next(
            item for item in board(client, unit)["legs"] if item["key"] == "despacho_llegada"
        )
        assert leg["median_minutes"] == pytest.approx(30.0)
        assert leg["p90_minutes"] == pytest.approx(57.0)
        assert leg["worst_minutes"] == pytest.approx(300.0)


class TestProductivity:
    def test_rf_130_cada_cuadrilla_con_lo_que_cerró_y_lo_que_carga(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        fast = a_crew(session, unit, "Cuadrilla Norte")
        busy = a_crew(session, unit, "Cuadrilla Sur")
        for _ in range(3):
            order = an_order(session, unit, state=WorkOrderState.CLOSED, crew=fast)
            reached(session, unit, order, WorkOrderState.CLOSED_FIELD, NOW)
        an_order(session, unit, state=WorkOrderState.IN_EXECUTION, crew=busy)
        session.flush()

        crews = {item["crew_name"]: item for item in board(client, unit)["crews"]}
        assert crews["Cuadrilla Norte"]["closed_in_field"] == 3
        assert crews["Cuadrilla Sur"]["closed_in_field"] == 0
        assert crews["Cuadrilla Sur"]["open_now"] == 1

    def test_una_cuadrilla_sin_trabajo_aparece_con_cero(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Es el dato que importa para repartir: la que no tiene nada asignado."""
        a_crew(session, unit, "Cuadrilla Vacía")
        session.flush()
        crews = {item["crew_name"]: item for item in board(client, unit)["crews"]}
        assert crews["Cuadrilla Vacía"]["closed_in_field"] == 0
        assert crews["Cuadrilla Vacía"]["open_now"] == 0


class TestTheArithmetic:
    def test_la_mediana_de_una_muestra_impar_es_el_del_medio(self) -> None:
        assert percentile([1.0, 5.0, 9.0], 0.5) == pytest.approx(5.0)

    def test_la_mediana_de_una_par_interpola(self) -> None:
        assert percentile([1.0, 3.0], 0.5) == pytest.approx(2.0)

    def test_sin_muestra_no_hay_percentil(self) -> None:
        assert percentile([], 0.5) is None

    def test_el_p90_de_una_muestra_con_una_cola_la_ve(self) -> None:
        # La mediana de esta muestra es 1: el p90 existe precisamente para que la cola no se pierda.
        assert percentile([1.0] * 9 + [100.0], 0.5) == pytest.approx(1.0)
        tail = percentile([1.0] * 9 + [100.0], 0.9)
        assert tail is not None and tail > 10


class TestWhoMaySee:
    def test_un_técnico_no_ve_el_tablero_operativo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        with client_as(session, TECHNICIAN) as raw:
            answer = raw.get(f"/api/v1/analytics/units/{unit.code}/operations")
        assert answer.status_code == 403

    def test_adr_009_el_tablero_no_cuenta_ot_de_otra_unidad(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        ingest_metadata(session, other, build_metadata("cnel-gye"))
        an_order(session, other, state=WorkOrderState.IN_EXECUTION)
        session.flush()

        assert board(client, unit)["by_state"].get(WorkOrderState.IN_EXECUTION) is None
