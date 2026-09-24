"""Obras con varios frentes: OT padre y OT hijas (RF-015).

El criterio es una frase —«una OT padre muestra el avance agregado de sus hijas»— y todo lo que se
prueba aquí existe para que ese agregado sea honesto:

* **Un padre no se cierra sobre un frente abierto.** Sin esa regla el agregado miente exactamente el
  día en que alguien se apoya en él: el día en que la obra se reporta terminada.
* **Anular tampoco cae en cascada.** Una cascada anularía trabajo que una cuadrilla puede estar
  haciendo, desde una pantalla donde nadie está mirando esos frentes.
* **Un nivel, no un árbol.** Un frente no puede tener frentes: «el avance» dejaría de tener un
  significado único y se abriría la puerta a un ciclo que nadie nota hasta que algo se cuelga.
* **Anulado cuenta como resuelto y no como logrado.** Una obra cuyos cuatro frentes se anularon está
  terminada y no se construyó nada; un «4 de 4» a secas diría lo contrario, así que el anulado se
  reporta además por separado.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.workorders import fronts
from app.workorders.models import Crew, WorkOrder, WorkOrderState
from app.workorders.service import OpenFrontsError, assign, create_work_order, transition
from tests.conftest import build_metadata

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
ACTOR = "kc|planificador.demo"


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


@pytest.fixture
def crew(session: Session, unit: BusinessUnit) -> Crew:
    created = Crew(business_unit_id=unit.id, code="C-1", name="Cuadrilla 1")
    session.add(created)
    session.flush()
    return created


def an_order(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str,
    state: str = WorkOrderState.PLANNED,
    work_type: str = "obra_civil",
) -> WorkOrder:
    order = create_work_order(
        session,
        unit,
        work_type=work_type,
        form_code="F-IC-03",
        asset_type_key="support_structure",
        asset_code=f"P-{code}",
        planner_id=ACTOR,
    )
    order.code = code
    order.state = state
    session.flush()
    return order


def a_work_with_fronts(
    session: Session, unit: BusinessUnit, *, how_many: int = 3
) -> tuple[WorkOrder, list[WorkOrder]]:
    parent = an_order(session, unit, code="OBRA-1")
    children = []
    for index in range(how_many):
        child = an_order(session, unit, code=f"FRENTE-{index + 1}")
        fronts.attach(session, unit, parent, child, actor=ACTOR)
        children.append(child)
    return parent, children


def settle(session: Session, order: WorkOrder, *, state: str = WorkOrderState.CLOSED) -> None:
    """Llevar un frente a un estado terminal sin recorrer la máquina entera."""
    order.state = state
    session.flush()


def client_as(session: Session, who: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: who
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, PLANNER) as raw:
        yield raw


class TestAttaching:
    def test_rf_015_una_ot_se_cuelga_como_frente_de_una_obra(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        parent = an_order(session, unit, code="OBRA-1")
        child = an_order(session, unit, code="FRENTE-1")

        fronts.attach(session, unit, parent, child, actor=ACTOR)

        assert child.parent_id == parent.id
        assert child.is_front is True
        assert parent.is_front is False
        assert [row.code for row in fronts.children_of(session, parent)] == ["FRENTE-1"]

    def test_rf_015_un_frente_no_puede_tener_frentes(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un nivel, no un árbol: con nietos, «el avance» deja de tener un significado único."""
        _parent, children = a_work_with_fronts(session, unit, how_many=1)
        grandchild = an_order(session, unit, code="NIETO-1")

        with pytest.raises(fronts.FrontError, match="un nivel"):
            fronts.attach(session, unit, children[0], grandchild, actor=ACTOR)

    def test_rf_015_una_obra_con_frentes_no_puede_volverse_frente(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        parent, _children = a_work_with_fronts(session, unit, how_many=1)
        other = an_order(session, unit, code="OBRA-2")

        with pytest.raises(fronts.FrontError, match="padre y frente"):
            fronts.attach(session, unit, other, parent, actor=ACTOR)

    def test_rf_015_una_ot_no_puede_ser_frente_de_si_misma(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit, code="OBRA-1")

        with pytest.raises(fronts.FrontError, match="de sí misma"):
            fronts.attach(session, unit, order, order, actor=ACTOR)

    def test_rf_015_un_frente_no_se_roba_de_otra_obra(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Moverlo en silencio cambiaría el avance de dos obras a la vez."""
        _parent, children = a_work_with_fronts(session, unit, how_many=1)
        other = an_order(session, unit, code="OBRA-2")

        with pytest.raises(fronts.FrontError, match="otra obra"):
            fronts.attach(session, unit, other, children[0], actor=ACTOR)

    def test_rf_015_colgar_el_mismo_frente_dos_veces_es_inocuo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        parent, children = a_work_with_fronts(session, unit, how_many=1)

        fronts.attach(session, unit, parent, children[0], actor=ACTOR)

        assert len(fronts.children_of(session, parent)) == 1

    def test_rf_015_no_se_cruzan_unidades_de_negocio(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        """ADR-009: un frente de otra unidad pondría sus cuadrillas dentro de esta obra."""
        parent = an_order(session, units["GYE"], code="OBRA-1")
        foreign = an_order(session, units["MAN"], code="FRENTE-X")

        with pytest.raises(fronts.FrontError, match="unidad de negocio"):
            fronts.attach(session, units["GYE"], parent, foreign, actor=ACTOR)

    def test_rf_015_una_obra_ya_en_campo_no_admite_frentes_nuevos(
        self, session: Session, unit: BusinessUnit, crew: Crew
    ) -> None:
        """Añadir uno cambiaría en silencio lo que significaba «hecho» para quien ya la miró."""
        parent = an_order(session, unit, code="OBRA-1")
        assign(session, parent, crew=crew)
        child = an_order(session, unit, code="FRENTE-1")

        with pytest.raises(fronts.FrontError, match="no admite frentes"):
            fronts.attach(session, unit, parent, child, actor=ACTOR)

    def test_rf_160_colgar_un_frente_queda_en_la_bitacora(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        parent, children = a_work_with_fronts(session, unit, how_many=1)

        event = session.execute(
            select(AuditEvent).where(
                AuditEvent.subject_id == str(children[0].id),
                AuditEvent.payload["field"].astext == "parent_id",
            )
        ).scalar_one()
        assert event.payload["parent_code"] == parent.code
        assert event.actor == ACTOR

    def test_rf_015_separar_un_frente_lo_deja_como_ot_ordinaria(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Separar, no anular: el frente sigue siendo trabajo y conserva lo que capturó."""
        parent, children = a_work_with_fronts(session, unit, how_many=2)

        fronts.detach(session, unit, children[0], actor=ACTOR)

        assert children[0].parent_id is None
        assert [row.code for row in fronts.children_of(session, parent)] == ["FRENTE-2"]

    def test_rf_015_separar_algo_que_no_es_frente_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        order = an_order(session, unit, code="OBRA-1")

        with pytest.raises(fronts.FrontError, match="no es frente"):
            fronts.detach(session, unit, order, actor=ACTOR)


class TestTheAggregate:
    def test_rf_015_el_avance_es_una_fraccion_con_su_denominador(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """«6 de 11» dice lo que «55 %» no dice, que es cuánto falta y de qué."""
        parent, children = a_work_with_fronts(session, unit, how_many=3)
        settle(session, children[0])

        progress = fronts.progress_of(session, parent)

        assert progress.total == 3
        assert progress.closed == 1
        assert progress.pending == 2
        assert progress.done == 1
        assert "1 de 3 frentes resueltos" in progress.summary()

    def test_rf_015_un_frente_anulado_cuenta_como_resuelto_y_se_dice_aparte(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una obra cuyos frentes se anularon está terminada y no se construyó nada."""
        parent, children = a_work_with_fronts(session, unit, how_many=2)
        settle(session, children[0], state=WorkOrderState.CANCELLED)
        settle(session, children[1], state=WorkOrderState.CANCELLED)

        progress = fronts.progress_of(session, parent)

        assert progress.is_complete is True
        assert progress.closed == 0
        assert progress.cancelled == 2
        assert "2 anulado(s)" in progress.summary()

    def test_rf_015_los_frentes_en_campo_y_en_revision_se_cuentan_aparte(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        parent, children = a_work_with_fronts(session, unit, how_many=3)
        settle(session, children[0], state=WorkOrderState.IN_EXECUTION)
        settle(session, children[1], state=WorkOrderState.IN_REVIEW)

        progress = fronts.progress_of(session, parent)

        assert progress.in_field == 1
        assert progress.in_review == 1
        assert progress.pending == 1
        assert progress.is_complete is False

    def test_rf_015_una_obra_sin_frentes_no_esta_completa_por_vacia(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Cero de cero no es «hecho»: es una obra a la que todavía no le colgaron nada."""
        parent = an_order(session, unit, code="OBRA-1")

        progress = fronts.progress_of(session, parent)

        assert progress.total == 0
        assert progress.is_complete is False
        assert progress.summary() == "sin frentes"

    def test_rf_015_el_avance_nombra_los_frentes_que_faltan(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        parent, children = a_work_with_fronts(session, unit, how_many=3)
        settle(session, children[0])

        progress = fronts.progress_of(session, parent)

        assert progress.open_codes == ["FRENTE-2", "FRENTE-3"]

    def test_rf_015_el_avance_no_cuenta_frentes_de_otra_obra(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        parent, _children = a_work_with_fronts(session, unit, how_many=2)
        other = an_order(session, unit, code="OBRA-2")
        stray = an_order(session, unit, code="FRENTE-9")
        fronts.attach(session, unit, other, stray, actor=ACTOR)

        assert fronts.progress_of(session, parent).total == 2
        assert fronts.progress_of(session, other).total == 1

    def test_rf_015_la_lista_de_obras_trae_cada_una_con_su_avance(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        _parent, children = a_work_with_fronts(session, unit, how_many=2)
        settle(session, children[0])

        works = fronts.parents_with_fronts(session, unit)

        assert [row[0].code for row in works] == ["OBRA-1"]
        assert works[0][1].done == 1

    def test_rf_015_la_lista_de_obras_no_ve_las_de_otra_unidad(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        a_work_with_fronts(session, units["GYE"], how_many=1)

        assert fronts.parents_with_fronts(session, units["MAN"]) == []


class TestTheParentCannotCloseOverOpenWork:
    def test_rf_015_cerrar_una_obra_con_un_frente_abierto_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La regla que hace honesto el agregado, el día en que alguien se apoya en él."""
        parent, children = a_work_with_fronts(session, unit, how_many=2)
        settle(session, children[0])
        parent.state = WorkOrderState.APPROVED
        session.flush()

        with pytest.raises(OpenFrontsError, match="FRENTE-2"):
            transition(session, parent, WorkOrderState.CLOSED)

    def test_rf_015_con_todos_los_frentes_resueltos_la_obra_cierra(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        parent, children = a_work_with_fronts(session, unit, how_many=2)
        for child in children:
            settle(session, child)
        parent.state = WorkOrderState.APPROVED
        session.flush()

        transition(session, parent, WorkOrderState.CLOSED)

        assert parent.state == WorkOrderState.CLOSED

    def test_rf_015_un_frente_en_revision_tambien_frena_el_cierre_de_la_obra(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La oficina todavía está decidiendo, y una devolución mandaría ese frente otra vez al
        campo. Cerrar la obra encima sería cerrarla sobre trabajo que puede volver.

        Este test existe porque el sabotaje correspondiente —sacar `en_revision` de los estados
        abiertos— pasó inadvertido: los conteos lo veían, el cierre no.
        """
        parent, children = a_work_with_fronts(session, unit, how_many=2)
        settle(session, children[0])
        settle(session, children[1], state=WorkOrderState.IN_REVIEW)
        parent.state = WorkOrderState.APPROVED
        session.flush()

        with pytest.raises(OpenFrontsError, match="FRENTE-2"):
            transition(session, parent, WorkOrderState.CLOSED)

    def test_rf_015_un_frente_devuelto_tambien_frena_el_cierre(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Devuelta manda la cuadrilla otra vez al campo: es lo más abierto que hay."""
        parent, children = a_work_with_fronts(session, unit, how_many=1)
        settle(session, children[0], state=WorkOrderState.RETURNED)
        parent.state = WorkOrderState.APPROVED
        session.flush()

        with pytest.raises(OpenFrontsError):
            transition(session, parent, WorkOrderState.CLOSED)

    def test_rf_015_anular_una_obra_con_frentes_abiertos_no_cae_en_cascada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una cascada anularía trabajo que una cuadrilla puede estar haciendo ahora mismo."""
        parent, children = a_work_with_fronts(session, unit, how_many=2)
        settle(session, children[0], state=WorkOrderState.IN_EXECUTION)

        with pytest.raises(OpenFrontsError):
            transition(session, parent, WorkOrderState.CANCELLED, reason="cambio de alcance")

        assert children[0].state == WorkOrderState.IN_EXECUTION
        assert children[1].state == WorkOrderState.PLANNED

    def test_rf_015_una_ot_sin_frentes_transiciona_como_siempre(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La regla no puede cobrarle nada a las OT que no son obras, que son casi todas."""
        order = an_order(session, unit, code="OT-1")

        transition(session, order, WorkOrderState.CANCELLED, reason="duplicada")

        assert order.state == WorkOrderState.CANCELLED

    def test_rf_015_un_frente_se_cierra_sin_pedirle_permiso_a_la_obra(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El trabajo pasa en los frentes: la regla es del padre, no del hijo."""
        _parent, children = a_work_with_fronts(session, unit, how_many=2)
        children[0].state = WorkOrderState.APPROVED
        session.flush()

        transition(session, children[0], WorkOrderState.CLOSED)

        assert children[0].state == WorkOrderState.CLOSED

    def test_rf_015_un_frente_separado_deja_de_bloquear_a_su_obra(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        parent, children = a_work_with_fronts(session, unit, how_many=2)
        settle(session, children[0])
        parent.state = WorkOrderState.APPROVED
        session.flush()
        fronts.detach(session, unit, children[1], actor=ACTOR)

        transition(session, parent, WorkOrderState.CLOSED)

        assert parent.state == WorkOrderState.CLOSED


class TestTheApi:
    def url(self, unit: BusinessUnit, path: str) -> str:
        return f"/api/v1/planning{path}?business_unit={unit.code}"

    def test_rf_015_el_detalle_de_la_obra_trae_los_frentes_y_el_avance(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        parent, children = a_work_with_fronts(session, unit, how_many=2)
        settle(session, children[0])

        answer = client.get(self.url(unit, f"/work-orders/{parent.id}/fronts"))

        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["progress"]["total"] == 2
        assert body["progress"]["done"] == 1
        assert "1 de 2 frentes resueltos" in body["progress"]["summary"]
        assert [row["code"] for row in body["fronts"]] == ["FRENTE-1", "FRENTE-2"]

    def test_rf_015_la_lista_de_obras_responde_con_su_avance(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        a_work_with_fronts(session, unit, how_many=2)

        answer = client.get(self.url(unit, "/works"))

        assert answer.status_code == 200, answer.text
        assert answer.json()[0]["progress"]["total"] == 2

    def test_rf_015_el_planificador_cuelga_un_frente(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        parent = an_order(session, unit, code="OBRA-1")
        child = an_order(session, unit, code="FRENTE-1")

        answer = client.post(
            self.url(unit, f"/work-orders/{parent.id}/fronts"),
            json={"work_order_id": str(child.id)},
        )

        assert answer.status_code == 200, answer.text
        assert answer.json()["progress"]["total"] == 1

    def test_rf_015_un_enlace_invalido_es_un_422_que_explica(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        _parent, children = a_work_with_fronts(session, unit, how_many=1)
        grandchild = an_order(session, unit, code="NIETO-1")

        answer = client.post(
            self.url(unit, f"/work-orders/{children[0].id}/fronts"),
            json={"work_order_id": str(grandchild.id)},
        )

        assert answer.status_code == 422
        assert "un nivel" in answer.json()["detail"]

    def test_rf_015_separar_por_la_api_devuelve_el_avance_nuevo(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        parent, children = a_work_with_fronts(session, unit, how_many=2)

        answer = client.delete(self.url(unit, f"/work-orders/{parent.id}/fronts/{children[0].id}"))

        assert answer.status_code == 200, answer.text
        assert answer.json()["progress"]["total"] == 1

    def test_rf_015_separar_algo_que_no_es_frente_de_esa_obra_es_404(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        parent, _children = a_work_with_fronts(session, unit, how_many=1)
        stray = an_order(session, unit, code="OT-SUELTA")

        answer = client.delete(self.url(unit, f"/work-orders/{parent.id}/fronts/{stray.id}"))

        assert answer.status_code == 404

    def test_rf_015_un_tecnico_no_cuelga_ni_separa_frentes(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        parent = an_order(session, unit, code="OBRA-1")
        child = an_order(session, unit, code="FRENTE-1")

        with client_as(session, TECHNICIAN) as raw:
            answer = raw.post(
                self.url(unit, f"/work-orders/{parent.id}/fronts"),
                json={"work_order_id": str(child.id)},
            )

        assert answer.status_code == 403

    def test_rf_015_una_obra_de_otra_unidad_es_404(
        self, client: TestClient, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        foreign = an_order(session, units["MAN"], code="OBRA-X")

        answer = client.get(self.url(units["GYE"], f"/work-orders/{foreign.id}/fronts"))

        assert answer.status_code == 404


def test_rf_015_los_conteos_de_frentes_salen_en_una_consulta(
    session: Session, units: dict[str, BusinessUnit]
) -> None:
    """Para una pantalla de lista: una consulta y no una por fila.

    Con una obra en cada unidad, porque el sabotaje que quitaba el filtro de unidad a esta consulta
    pasó inadvertido con una sola: el conteo salía igual y el cruce no se veía.
    """
    parent, _children = a_work_with_fronts(session, units["GYE"], how_many=3)
    other, _fronts = a_work_with_fronts(session, units["MAN"], how_many=2)

    counts: dict[Any, int] = fronts.front_counts(session, units["GYE"])

    assert counts == {parent.id: 3}
    assert other.id not in counts
