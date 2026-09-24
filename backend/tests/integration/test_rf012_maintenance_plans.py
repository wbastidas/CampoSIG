"""Planes de mantenimiento preventivo, contra base real (RF-012).

El criterio de aceptación es un conteo: «un plan mensual genera N OT en la fecha programada». Un
conteo es toda la dificultad — una OT de más manda una cuadrilla a un poste que está bien, una de
menos deja una inspección sin hacer y el área se entera en la auditoría — así que lo que más se
prueba aquí es que **volver a correr el plan no emite nada** y que cada negativa quedó registrada
con su motivo.

Lo segundo es la honestidad del alcance expandido: «todos los postes del alimentador X» es una
pregunta que esta plataforma no puede contestar, porque el inventario vive en el SIG (ADR-006). Lo
que sí puede contestar es «los activos de ese alimentador en los que ya trabajamos», que es un
subconjunto, y el caveat viaja con el conteo en vez de dejar que un 8 se lea como un 11.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.models import AuditEvent, EventKind
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.plans import service as plans
from app.plans.models import Cadence, IssueOutcome, MaintenancePlan, PlanIssue, PlanScope
from app.plans.service import EXPANSION_CAVEAT
from app.responses.service import save_answers
from app.workers.plan_generation import run_once
from app.workorders.models import Priority, WorkOrder, WorkOrderSource, WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

#: El 5 de cada mes, que es la fecha programada de los tests.
DAY = 5
JANUARY = date(2026, 1, DAY)
FEBRUARY = date(2026, 2, DAY)


def principal(*roles: Role, username: str = "planificador.demo") -> Principal:
    return Principal(
        subject=f"kc|{username}",
        username=username,
        roles=frozenset(role.value for role in roles),
        business_units=frozenset({"GYE"}),
    )


PLANNER = principal(Role.PLANNER)
SUPERVISOR = principal(Role.SUPERVISOR, username="supervisor.demo")
TECHNICIAN = principal(Role.TECHNICIAN, username="tecnico.demo")


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


def a_plan(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str = "PLAN-MT-01",
    assets: list[str] | None = ("P-001", "P-002", "P-003"),
    cadence: Cadence = Cadence.MONTHLY,
    scope: PlanScope = PlanScope.ASSETS,
    scope_value: str | None = None,
    starts_on: date = JANUARY,
    form_code: str = "F-MT-01",
    day_of_month: int = DAY,
    **kwargs: object,
) -> MaintenancePlan:
    targets = (
        [{"asset_code": asset, "sort_order": index} for index, asset in enumerate(assets)]
        if assets is not None
        else None
    )
    return plans.save_plan(
        session,
        unit,
        code=code,
        name="Inspección preventiva de estructuras",
        work_type="inspeccion_preventiva",
        form_code=form_code,
        cadence=cadence.value,
        scope=scope.value,
        scope_value=scope_value,
        asset_type_key="support_structure",
        day_of_month=day_of_month,
        starts_on=starts_on,
        actor="kc|planificador.demo",
        targets=targets,
        **kwargs,  # type: ignore[arg-type]
    )


def an_order(
    session: Session,
    unit: BusinessUnit,
    *,
    asset: str,
    state: str = WorkOrderState.ASSIGNED,
    feeder: str | None = None,
    zone: str | None = None,
) -> WorkOrder:
    order = create_work_order(
        session,
        unit,
        work_type="mantenimiento_correctivo",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        asset_code=asset,
        feeder_code=feeder,
        zone=zone,
        planner_id="kc|planner.a",
    )
    order.state = state
    session.flush()
    return order


def attended(session: Session, unit: BusinessUnit, *, asset: str, when: datetime) -> WorkOrder:
    """Una OT cerrada sobre el activo, con su transición en la bitácora.

    El momento sale de la bitácora y no de `updated_at`: esa columna se mueve con cualquier edición
    de la fila, y entonces reasignar una OT vieja hoy «atendería» el activo hoy.
    """
    order = an_order(session, unit, asset=asset, state=WorkOrderState.CLOSED)
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


def client_as(session: Session, who: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: who
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, PLANNER) as raw:
        yield raw


class TestWritingAPlan:
    def test_rf_012_un_plan_se_guarda_con_su_ruta_en_orden(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La lista es el alcance, y su orden es la ruta que la cuadrilla maneja."""
        plan = a_plan(session, unit, assets=["P-003", "P-001", "P-002"])

        assert [row.asset_code for row in plans.targets_of(session, plan)] == [
            "P-003",
            "P-001",
            "P-002",
        ]

    def test_rf_012_guardar_otra_vez_reemplaza_la_ruta_entera(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una actualización parcial dejaría el orden de visita mezclado entre dos versiones."""
        a_plan(session, unit, assets=["P-001", "P-002"])
        plan = a_plan(session, unit, assets=["P-009"])

        assert [row.asset_code for row in plans.targets_of(session, plan)] == ["P-009"]

    def test_rf_012_un_activo_repetido_en_la_lista_entra_una_vez(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        plan = a_plan(session, unit, assets=["P-001", "P-001"])

        assert len(plans.targets_of(session, plan)) == 1

    def test_rf_012_un_formulario_que_no_existe_se_rechaza_al_guardar(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Delante de la persona que lo escribió, no a las 04:30 en el log de un worker."""
        with pytest.raises(plans.PlanError, match="formulario"):
            a_plan(session, unit, code="PLAN-X", form_code="F-NO-EXISTE")

    def test_rf_012_el_dia_31_se_rechaza_y_se_explica_por_que(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """No existe en febrero, y las dos formas de arreglarlo dan conteos anuales distintos."""
        with pytest.raises(plans.PlanError, match="febrero"):
            a_plan(session, unit, code="PLAN-31", day_of_month=31)

    def test_rf_012_una_frecuencia_en_dias_sin_dias_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        with pytest.raises(plans.PlanError, match="días"):
            a_plan(session, unit, code="PLAN-D", cadence=Cadence.CUSTOM_DAYS)

    def test_rf_012_un_plan_por_alimentador_sin_alimentador_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        with pytest.raises(plans.PlanError, match="código del alcance"):
            a_plan(session, unit, code="PLAN-F", scope=PlanScope.FEEDER, assets=None)

    def test_rf_012_un_plan_por_activos_sin_activos_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """No emitiría nada, y lo haría sin decir por qué."""
        with pytest.raises(plans.PlanError, match="al menos un activo"):
            a_plan(session, unit, code="PLAN-V", assets=None)

    def test_rf_160_guardar_un_plan_queda_en_la_bitacora_con_su_autor(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        a_plan(session, unit)

        event = session.execute(
            select(AuditEvent).where(AuditEvent.subject_type == "maintenance_plan")
        ).scalar_one()
        assert event.actor == "kc|planificador.demo"
        assert event.payload["cadence"] == Cadence.MONTHLY.value

    def test_rf_012_el_plan_no_cruza_unidades_de_negocio(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        a_plan(session, units["GYE"])

        assert plans.plans_of(session, units["MAN"]) == []
        with pytest.raises(plans.UnknownPlanError):
            plans.get_plan(session, units["MAN"], "PLAN-MT-01")


class TestFiring:
    def test_rf_012_un_plan_mensual_emite_una_ot_por_activo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El criterio de aceptación, tal cual: N activos, N OT, en la fecha programada."""
        plan = a_plan(session, unit)

        run = plans.run_plan(session, unit, plan, on=JANUARY)

        assert len(run.issued) == 3
        assert run.period == "2026-01"
        orders = list(
            session.execute(
                select(WorkOrder).where(WorkOrder.source == WorkOrderSource.PREVENTIVE_PLAN.value)
            ).scalars()
        )
        assert len(orders) == 3
        assert {order.asset_code for order in orders} == {"P-001", "P-002", "P-003"}
        assert all(order.state == WorkOrderState.PLANNED for order in orders)
        assert all("2026-01" in (order.description or "") for order in orders)

    def test_rf_012_volver_a_correr_el_mismo_periodo_no_emite_nada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La guarda es la etiqueta de periodo, y es lo que hace inocuo un reintento del job."""
        plan = a_plan(session, unit)
        plans.run_plan(session, unit, plan, on=JANUARY)

        again = plans.run_plan(session, unit, plan, on=date(2026, 1, 27))

        assert again.issued == []
        assert sorted(again.already_issued) == ["P-001", "P-002", "P-003"]
        assert session.execute(select(WorkOrder.id)).all().__len__() == 3

    def test_rf_012_el_mes_siguiente_emite_otra_vez_si_se_hizo_el_trabajo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        plan = a_plan(session, unit)
        for order in session.execute(select(WorkOrder)).scalars():
            order.state = WorkOrderState.CLOSED
        plans.run_plan(session, unit, plan, on=JANUARY)
        for order in session.execute(select(WorkOrder)).scalars():
            order.state = WorkOrderState.CLOSED
        session.flush()

        february = plans.run_plan(session, unit, plan, on=FEBRUARY)

        assert len(february.issued) == 3
        assert february.period == "2026-02"

    def test_rf_012_el_mes_siguiente_no_apila_una_ot_sobre_la_de_enero_sin_ejecutar(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Doce OT sobre el mismo poste porque nadie ejecutó ninguna sería el peor resultado.

        La guarda de «trabajo pendiente» es la misma que usa RF-013, y aquí hace algo que vale
        escribir: un plan cuyos periodos no se ejecutan **no se acumula**, y cada periodo saltado
        queda registrado con su motivo, que es lo que el área necesita ver para saber que va
        atrasada en vez de ver una bandeja con doce OT iguales.
        """
        plan = a_plan(session, unit, assets=["P-001"])
        plans.run_plan(session, unit, plan, on=JANUARY)

        february = plans.run_plan(session, unit, plan, on=FEBRUARY)

        assert february.issued == []
        assert february.skipped_pending == ["P-001"]
        pending = next(
            issue
            for issue in plans.history(session, plan)
            if issue.period == "2026-02" and issue.outcome == IssueOutcome.PENDING_WORK
        )
        assert "trabajo pendiente" in (pending.reason or "")

    def test_rf_012_la_unicidad_por_periodo_esta_en_la_base(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una comprobación en la función la corren a la vez el job nocturno y un planificador."""
        plan = a_plan(session, unit, assets=["P-001"])
        plans.run_plan(session, unit, plan, on=JANUARY)

        session.add(
            PlanIssue(
                plan_id=plan.id,
                period="2026-01",
                asset_code="P-001",
                outcome=IssueOutcome.ISSUED,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_rf_012_un_plan_de_alcance_completo_tampoco_puede_emitir_dos_veces(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El `asset_code` nulo necesita su índice: PostgreSQL trata los NULL como distintos."""
        plan = a_plan(session, unit, assets=["P-001"])
        session.add(PlanIssue(plan_id=plan.id, period="2026-01", outcome=IssueOutcome.ISSUED))
        session.flush()

        session.add(PlanIssue(plan_id=plan.id, period="2026-01", outcome=IssueOutcome.ISSUED))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_rf_012_un_activo_con_trabajo_pendiente_no_recibe_otra_ot(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Mandar una preventiva a un activo con cuadrilla en camino es mandar dos veces."""
        plan = a_plan(session, unit)
        an_order(session, unit, asset="P-002")

        run = plans.run_plan(session, unit, plan, on=JANUARY)

        assert len(run.issued) == 2
        assert run.skipped_pending == ["P-002"]

    def test_rf_012_la_negativa_queda_registrada_con_su_motivo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un plan que emitió 2 de 3 y no explicó el tercero es un plan en el que no se confía."""
        plan = a_plan(session, unit)
        an_order(session, unit, asset="P-002")
        plans.run_plan(session, unit, plan, on=JANUARY)

        skipped = next(
            issue
            for issue in plans.history(session, plan)
            if issue.outcome == IssueOutcome.PENDING_WORK
        )
        assert skipped.asset_code == "P-002"
        assert "trabajo pendiente" in (skipped.reason or "")
        assert skipped.work_order_id is None

    def test_rf_012_una_ot_cerrada_en_el_activo_no_frena_la_preventiva(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Lo contrario dejaría un activo sin preventivo para siempre tras su primera OT."""
        plan = a_plan(session, unit, assets=["P-001"])
        an_order(session, unit, asset="P-001", state=WorkOrderState.CLOSED)

        assert len(plans.run_plan(session, unit, plan, on=JANUARY).issued) == 1

    def test_rf_012_la_guarda_de_atendido_hace_poco_salta_el_activo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """No se manda a inspeccionar un poste que se atendió la semana pasada."""
        plan = a_plan(session, unit, assets=["P-001", "P-002"], skip_if_attended_within_days=30)
        attended(session, unit, asset="P-002", when=datetime.now(UTC) - timedelta(days=3))

        run = plans.run_plan(session, unit, plan, on=JANUARY)

        assert len(run.issued) == 1
        assert run.skipped_recent == ["P-002"]

    def test_rf_012_fuera_de_la_ventana_de_la_guarda_si_se_emite(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        plan = a_plan(session, unit, assets=["P-002"], skip_if_attended_within_days=30)
        attended(session, unit, asset="P-002", when=datetime.now(UTC) - timedelta(days=60))

        assert len(plans.run_plan(session, unit, plan, on=JANUARY).issued) == 1

    def test_rf_012_sin_guarda_declarada_la_fecha_de_atencion_no_importa(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un plan de calendario fijo —una inspección regulatoria— emite igual: es una decisión."""
        plan = a_plan(session, unit, assets=["P-002"])
        attended(session, unit, asset="P-002", when=datetime.now(UTC) - timedelta(days=1))

        assert len(plans.run_plan(session, unit, plan, on=JANUARY).issued) == 1

    def test_rf_160_la_corrida_queda_en_la_bitacora_con_sus_conteos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        plan = a_plan(session, unit)
        an_order(session, unit, asset="P-003")
        plans.run_plan(session, unit, plan, on=JANUARY)

        event = session.execute(
            select(AuditEvent).where(AuditEvent.subject_type == "plan_run")
        ).scalar_one()
        assert event.payload["issued"] == 2
        assert event.payload["skipped_pending"] == 1
        assert event.payload["period"] == "2026-01"


class TestTheExpandedScope:
    def test_rf_012_un_plan_por_alimentador_expande_lo_que_la_plataforma_vio(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        an_order(session, unit, asset="P-010", feeder="ALIM-SUR", state=WorkOrderState.CLOSED)
        an_order(session, unit, asset="P-011", feeder="ALIM-SUR", state=WorkOrderState.CLOSED)
        an_order(session, unit, asset="P-020", feeder="ALIM-NORTE", state=WorkOrderState.CLOSED)
        plan = a_plan(
            session,
            unit,
            code="PLAN-SUR",
            scope=PlanScope.FEEDER,
            scope_value="ALIM-SUR",
            assets=None,
        )

        run = plans.run_plan(session, unit, plan, on=JANUARY)

        assert len(run.issued) == 2

    def test_rf_012_la_expansion_dice_lo_que_no_puede_saber(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El inventario vive en el SIG: un 8 no se puede leer como los 11 del alimentador."""
        an_order(session, unit, asset="P-010", feeder="ALIM-SUR", state=WorkOrderState.CLOSED)
        plan = a_plan(
            session,
            unit,
            code="PLAN-SUR",
            scope=PlanScope.FEEDER,
            scope_value="ALIM-SUR",
            assets=None,
        )

        run = plans.run_plan(session, unit, plan, on=JANUARY)

        assert run.caveats == [EXPANSION_CAVEAT]
        assert "SIG" in run.caveats[0]
        issued = next(i for i in plans.history(session, plan) if i.outcome == IssueOutcome.ISSUED)
        assert issued.caveats == [EXPANSION_CAVEAT]

    def test_rf_012_una_lista_explicita_no_lleva_caveat(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Es exacta: la escribió el área."""
        plan = a_plan(session, unit, assets=["P-001"])

        assert plans.run_plan(session, unit, plan, on=JANUARY).caveats == []

    def test_rf_012_un_alcance_vacio_dice_por_que_en_vez_de_emitir_cero_en_silencio(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        plan = a_plan(
            session,
            unit,
            code="PLAN-X",
            scope=PlanScope.FEEDER,
            scope_value="ALIM-NUEVO",
            assets=None,
        )

        run = plans.run_plan(session, unit, plan, on=JANUARY)

        assert run.issued == []
        assert run.note is not None
        assert "ALIM-NUEVO" in run.note

    def test_rf_012_la_expansion_respeta_el_tipo_de_activo_del_plan(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        an_order(session, unit, asset="P-010", feeder="ALIM-SUR", state=WorkOrderState.CLOSED)
        luminaria = an_order(
            session, unit, asset="LUM-1", feeder="ALIM-SUR", state=WorkOrderState.CLOSED
        )
        luminaria.asset_type_key = "street_light"
        session.flush()
        plan = a_plan(
            session,
            unit,
            code="PLAN-SUR",
            scope=PlanScope.FEEDER,
            scope_value="ALIM-SUR",
            assets=None,
        )

        run = plans.run_plan(session, unit, plan, on=JANUARY)

        assert len(run.issued) == 1

    def test_rf_012_la_expansion_por_zona_tambien_funciona(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        an_order(session, unit, asset="P-030", zone="Urbano", state=WorkOrderState.CLOSED)
        plan = a_plan(
            session, unit, code="PLAN-Z", scope=PlanScope.ZONE, scope_value="Urbano", assets=None
        )

        assert len(plans.run_plan(session, unit, plan, on=JANUARY).issued) == 1

    def test_rf_012_la_expansion_no_ve_activos_de_otra_unidad(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        an_order(
            session, units["MAN"], asset="P-999", feeder="ALIM-SUR", state=WorkOrderState.CLOSED
        )
        plan = a_plan(
            session,
            units["GYE"],
            code="PLAN-SUR",
            scope=PlanScope.FEEDER,
            scope_value="ALIM-SUR",
            assets=None,
        )

        assert plans.run_plan(session, units["GYE"], plan, on=JANUARY).issued == []


class TestTheDailyPass:
    def test_rf_012_la_pasada_dispara_solo_los_planes_vencidos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        a_plan(session, unit, code="MENSUAL", assets=["P-001"])
        a_plan(
            session,
            unit,
            code="ANUAL",
            assets=["P-002"],
            cadence=Cadence.ANNUAL,
            starts_on=date(2026, 4, DAY),
        )

        report = plans.run_due(session, unit, on=JANUARY)

        assert [run.plan_code for run in report.runs] == ["MENSUAL"]
        assert report.not_due == ["ANUAL"]
        assert report.issued == 1

    def test_rf_012_un_plan_inactivo_no_dispara(self, session: Session, unit: BusinessUnit) -> None:
        a_plan(session, unit, assets=["P-001"], active=False)

        assert plans.run_due(session, unit, on=JANUARY).runs == []

    def test_rf_012_un_plan_vencido_por_fecha_de_fin_no_dispara(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        a_plan(session, unit, assets=["P-001"], ends_on=date(2026, 1, 1))

        report = plans.run_due(session, unit, on=JANUARY)

        assert report.runs == []
        assert report.not_due == ["PLAN-MT-01"]

    def test_rf_012_antes_de_la_fecha_de_inicio_no_dispara(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        a_plan(session, unit, assets=["P-001"], starts_on=date(2026, 6, DAY))

        assert plans.run_due(session, unit, on=JANUARY).runs == []

    def test_rf_012_el_worker_recorre_todas_las_unidades(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        a_plan(session, units["GYE"], assets=["P-001"])
        a_plan(session, units["MAN"], code="PLAN-MAN", assets=["P-500"])

        result = run_once(session, on=JANUARY)

        assert result.issued == 2
        assert set(result.units) == {"GYE", "MAN"}
        assert result.failed == {}

    def test_rf_012_correr_el_worker_dos_veces_la_misma_noche_es_inocuo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        a_plan(session, unit, assets=["P-001", "P-002"])

        first = run_once(session, on=JANUARY)
        second = run_once(session, on=JANUARY)

        assert first.issued == 2
        assert second.issued == 0


class TestCoverageAndCompletion:
    def test_rf_012_la_cobertura_lleva_su_denominador(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """«8 de 11» dice algo que «73 %» no dice, que es que faltan tres."""
        plan = a_plan(session, unit)
        an_order(session, unit, asset="P-003")
        plans.run_plan(session, unit, plan, on=datetime.now(UTC).date())

        state = plans.coverage(session, unit, plan)

        assert state["targets"] == 3
        assert state["issued"] == 2
        assert state["skipped_pending"] == 1

    def test_rf_012_el_cumplimiento_no_es_lo_mismo_que_la_emision(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un plan que emitió once OT que nadie ejecutó cumple 0 %, y ese número importa."""
        plan = a_plan(session, unit, assets=["P-001", "P-002"])
        plans.run_plan(session, unit, plan, on=datetime.now(UTC).date())

        before = plans.completion(session, unit, plan)
        assert before == {"period": before["period"], "issued": 2, "submitted": 0}

        order = session.execute(
            select(WorkOrder).where(WorkOrder.asset_code == "P-001")
        ).scalar_one()
        order.form_version = "1.0.0"
        order.code = "OT-P1"
        session.flush()
        response = save_answers(
            session,
            unit,
            order,
            answers={
                "work_order_code": "OT-P1",
                "work_type": "inspeccion_preventiva",
                "priority": "media",
                "general_condition": "bueno",
                "code": "P-001",
                "material": "concrete",
                "feeder_code": "04BH070T11",
                "final_state": "resuelto",
            },
            submit=True,
        )
        response.submitted_at = datetime.now(UTC)
        session.flush()

        assert plans.completion(session, unit, plan)["submitted"] == 1

    def test_rf_012_un_formulario_a_medio_llenar_no_cuenta_como_cumplido(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una cuadrilla que abrió el formulario y guardó un borrador no hizo el trabajo.

        Contarlo sería el número más favorable de dos, y el que el área reportaría sin saberlo.
        """
        plan = a_plan(session, unit, assets=["P-001"])
        plans.run_plan(session, unit, plan, on=datetime.now(UTC).date())
        order = session.execute(
            select(WorkOrder).where(WorkOrder.asset_code == "P-001")
        ).scalar_one()
        order.form_version = "1.0.0"
        order.code = "OT-BORRADOR"
        session.flush()
        save_answers(session, unit, order, answers={"code": "P-001"}, submit=False)

        assert plans.completion(session, unit, plan) == {
            "period": plans.completion(session, unit, plan)["period"],
            "issued": 1,
            "submitted": 0,
        }

    def test_rf_012_sin_nada_emitido_el_cumplimiento_no_divide_por_cero(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        plan = a_plan(session, unit)

        assert plans.completion(session, unit, plan)["issued"] == 0


class TestTheApi:
    def payload(self, **overrides: object) -> dict[str, object]:
        body: dict[str, object] = {
            "name": "Inspección preventiva de estructuras",
            "work_type": "inspeccion_preventiva",
            "form_code": "F-MT-01",
            "cadence": Cadence.MONTHLY.value,
            "scope": PlanScope.ASSETS.value,
            "priority": Priority.MEDIUM.value,
            "day_of_month": DAY,
            "starts_on": JANUARY.isoformat(),
            "targets": [{"asset_code": "P-001"}, {"asset_code": "P-002"}],
        }
        body.update(overrides)
        return body

    def test_rf_012_el_planificador_guarda_un_plan(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        answer = client.put(f"/api/v1/plans/units/{unit.code}/plan/PLAN-A", json=self.payload())

        assert answer.status_code == 200, answer.text
        assert answer.json()["created_by"] == PLANNER.subject

    def test_rf_012_el_autor_sale_del_token_y_no_del_cuerpo(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Un plan cuyo autor el llamante pudiera escribir es un plan que nadie firmó."""
        answer = client.put(
            f"/api/v1/plans/units/{unit.code}/plan/PLAN-A",
            json=self.payload(created_by="kc|alguien.mas"),
        )

        assert answer.status_code == 200, answer.text
        assert answer.json()["created_by"] == PLANNER.subject

    def test_rf_012_un_dia_del_mes_imposible_es_un_422_que_explica(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        answer = client.put(
            f"/api/v1/plans/units/{unit.code}/plan/PLAN-A", json=self.payload(day_of_month=31)
        )

        assert answer.status_code == 422
        assert "febrero" in answer.json()["detail"]

    def test_rf_012_un_tecnico_no_ve_ni_escribe_planes(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        with client_as(session, TECHNICIAN) as raw:
            assert raw.get(f"/api/v1/plans/units/{unit.code}").status_code == 403
            assert (
                raw.put(
                    f"/api/v1/plans/units/{unit.code}/plan/PLAN-A", json=self.payload()
                ).status_code
                == 403
            )

    def test_rf_012_el_supervisor_mira_pero_no_escribe(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Es quien responde por qué se mandó una cuadrilla, así que tiene que poder verlo."""
        a_plan(session, unit)
        with client_as(session, SUPERVISOR) as raw:
            assert raw.get(f"/api/v1/plans/units/{unit.code}").status_code == 200
            assert (
                raw.put(
                    f"/api/v1/plans/units/{unit.code}/plan/PLAN-A", json=self.payload()
                ).status_code
                == 403
            )

    def test_rf_012_disparar_por_la_api_emite_y_dice_qué_emitió(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        a_plan(session, unit, assets=["P-001", "P-002"])

        answer = client.post(
            f"/api/v1/plans/units/{unit.code}/plan/PLAN-MT-01/run", json={"on": JANUARY.isoformat()}
        )

        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert len(body["issued"]) == 2
        assert body["period"] == "2026-01"
        assert body["targets"] == 2

    def test_rf_012_disparar_dos_veces_por_la_api_no_duplica(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        a_plan(session, unit, assets=["P-001"])
        url = f"/api/v1/plans/units/{unit.code}/plan/PLAN-MT-01/run"

        client.post(url, json={"on": JANUARY.isoformat()})
        second = client.post(url, json={"on": JANUARY.isoformat()})

        assert second.json()["issued"] == []
        assert second.json()["already_issued"] == ["P-001"]

    def test_rf_012_el_detalle_trae_el_historial_con_los_motivos(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        plan = a_plan(session, unit)
        an_order(session, unit, asset="P-002")
        plans.run_plan(session, unit, plan, on=JANUARY)

        answer = client.get(f"/api/v1/plans/units/{unit.code}/plan/PLAN-MT-01")

        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert len(body["history"]) == 3
        assert any(item["outcome"] == IssueOutcome.PENDING_WORK.value for item in body["history"])
        assert [row["asset_code"] for row in body["targets"]] == ["P-001", "P-002", "P-003"]

    def test_rf_012_un_plan_que_no_existe_es_un_404(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        assert client.get(f"/api/v1/plans/units/{unit.code}/plan/NADA").status_code == 404

    def test_rf_012_la_pasada_por_la_api_es_la_misma_del_job(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        a_plan(session, unit, assets=["P-001"])

        answer = client.post(
            f"/api/v1/plans/units/{unit.code}/run-due", json={"on": JANUARY.isoformat()}
        )

        assert answer.status_code == 200, answer.text
        assert answer.json()["issued"] == 1
