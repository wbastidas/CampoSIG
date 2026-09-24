"""OT propuestas desde hallazgos, y las tres decisiones de la bandeja (RF-013, RF-114).

Lo que más se prueba aquí no es que se creen propuestas, sino **lo que la generación se niega a
hacer**: un activo con OT abierta no se vuelve a proponer (RF-014), un activo con propuesta abierta
tampoco, y un hallazgo sin código de activo no se puede proponer en absoluto. Los tres se cuentan y
viajan en el informe: una pasada que los descartara en silencio se vería igual que una que los
pasó por alto.

Lo segundo es que **nada llega a `work_order` sin una persona**. `approve` es el único camino, toma
al decisor de un token, y ninguna tarea programada lo llama.

Y lo tercero, la aritmética del anexo C: severidad por consecuencia, el ajuste por exposición de la
zona, y sobre todo los *caveats*. Una prioridad presentada como cálculo cuando la mitad de sus
entradas fueron omisiones es como un supervisor aprende a ignorar la bandeja entera.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent, EventKind
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.catalogs.loader import apply_seeds
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.proposals import service as proposals
from app.proposals.criticality import DEFAULT_CONSEQUENCE, DEFAULT_SEVERITY
from app.proposals.models import ProposalOrigin, ProposalState, WorkOrderProposal
from app.responses.service import save_answers
from app.workorders.models import Priority, WorkOrder, WorkOrderSource, WorkOrderState
from app.workorders.service import create_work_order
from app.zones.models import Zone, ZoneOrigin
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
SINCE = NOW - timedelta(days=30)
UNTIL = NOW + timedelta(days=1)


def principal(*roles: Role, username: str = "supervisor.demo", units: str = "GYE") -> Principal:
    return Principal(
        subject=f"kc|{username}",
        username=username,
        roles=frozenset(role.value for role in roles),
        business_units=frozenset({units}),
    )


SUPERVISOR = principal(Role.SUPERVISOR)
PLANNER = principal(Role.PLANNER, username="planificador.demo")
TECHNICIAN = principal(Role.TECHNICIAN, username="tecnico.demo")
ANALYST = principal(Role.ML_ANALYST, username="analista.demo")


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
def catalogs_loaded(session: Session) -> None:
    """Las semillas reales, porque la criticidad sale de ellas y no del código.

    Con las semillas cargadas los números de los tests son los del anexo C tal como los declara el
    área; sin ellas, toda propuesta sale estimada. Ambos casos se prueban.
    """
    apply_seeds(session)
    session.flush()


def finding_row(
    defect: str,
    *,
    criticality: str = "alta",
    asset: str | None = None,
    wants: bool = True,
) -> dict[str, Any]:
    """Una fila de la tabla de hallazgos, como la envía la cuadrilla."""
    row: dict[str, Any] = {
        "defect_code": defect,
        "criticality": criticality,
        "generate_work_order": wants,
    }
    if asset is not None:
        row["asset_code"] = asset
    return row


#: Lo que el formulario de cada tipo de activo exige además del código y el alimentador. Sale del
#: modelo canónico de activos, no de nombres del modelo de CNEL (regla 4).
REQUIRED_BY_TYPE: dict[str, dict[str, Any]] = {
    "support_structure": {"material": "concrete"},
    "street_light": {"technology": "led"},
    "distribution_transformer": {"rated_kva": 50},
}


def an_inspection(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str,
    asset: str = "P-000452",
    asset_type: str = "support_structure",
    feeder: str = "04BH070T11",
    zone: str | None = "Urbano",
    findings: list[dict[str, Any]] | None = None,
    defects: list[str] | None = None,
    submitted: datetime | None = None,
    forget_asset: bool = False,
) -> WorkOrder:
    """Una inspección enviada con sus hallazgos, que es de donde sale toda propuesta.

    :param forget_asset: borra el activo de la OT y del formulario después de enviarlo, que es la
        única forma de tener un hallazgo sin activo: el formulario exige el código, y la cuadrilla
        que no pudo identificar el activo es la que deja la OT sin él.
    """
    order = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key=asset_type,
        asset_code=asset,
        feeder_code=feeder,
        longitude=-79.90,
        latitude=-2.17,
        zone=zone,
        planner_id="kc|planner.a",
    )
    order.state = WorkOrderState.SYNCED
    order.form_version = "1.0.0"
    order.code = code
    session.flush()

    answers: dict[str, Any] = {
        "work_order_code": code,
        "work_type": "inspeccion_preventiva",
        "priority": "media",
        "general_condition": "regular",
        "code": asset,
        "feeder_code": feeder,
        "final_state": "resuelto",
        **REQUIRED_BY_TYPE.get(asset_type, {}),
    }
    if findings is not None:
        answers["findings"] = findings
    if defects is not None:
        answers["defects"] = defects

    response = save_answers(session, unit, order, answers=answers, submit=True)
    response.submitted_at = submitted or NOW
    if forget_asset:
        order.asset_code = None
        response.answers = {key: value for key, value in response.answers.items() if key != "code"}
    session.flush()
    return order


def an_open_order(
    session: Session,
    unit: BusinessUnit,
    *,
    asset: str,
    state: str = WorkOrderState.ASSIGNED,
) -> WorkOrder:
    order = create_work_order(
        session,
        unit,
        work_type="mantenimiento_correctivo",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        asset_code=asset,
        planner_id="kc|planner.a",
    )
    order.state = state
    session.flush()
    return order


def a_zone(session: Session, unit: BusinessUnit, *, code: str, exposure: bool) -> Zone:
    """Una zona real, con su polígono, porque la exposición es una columna de la zona."""
    zone = Zone(
        business_unit_id=unit.id,
        code=code,
        name=f"Zona {code}",
        geom=func.ST_Multi(
            func.ST_SetSRID(
                func.ST_GeomFromText(
                    "POLYGON((-80.0 -2.3,-79.8 -2.3,-79.8 -2.0,-80.0 -2.0,-80.0 -2.3))"
                ),
                4326,
            )
        ),
        origin=ZoneOrigin.DRAWN,
        exposure=exposure,
        created_by="admin.funcional",
        updated_by="admin.funcional",
    )
    session.add(zone)
    session.flush()
    return zone


def generate(session: Session, unit: BusinessUnit, **kwargs: Any) -> proposals.GenerationReport:
    return proposals.generate_from_findings(session, unit, since=SINCE, until=UNTIL, **kwargs)


def tray(session: Session, unit: BusinessUnit) -> list[WorkOrderProposal]:
    return proposals.tray(session, unit)


def client_as(session: Session, who: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: who
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, SUPERVISOR) as raw:
        yield raw


class TestGeneration:
    def test_rf_013_un_hallazgo_marcado_se_vuelve_una_propuesta(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-1", findings=[finding_row("cruceta_podrida")])

        report = generate(session, unit)

        assert len(report.created) == 1
        row = tray(session, unit)[0]
        assert row.asset_code == "P-000452"
        assert row.defect_code == "cruceta_podrida"
        assert row.state == ProposalState.OPEN
        assert row.origin == ProposalOrigin.FIELD_FINDING
        assert row.work_type == proposals.PROPOSED_WORK_TYPE
        # El hallazgo viaja con ella: la propuesta se lee sin reabrir la captura.
        assert row.findings[0]["defect_code"] == "cruceta_podrida"
        assert "OT-1" in row.justification

    def test_rf_013_sin_marca_de_la_cuadrilla_no_se_propone_nada(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """La marca «generar OT» es la señal más barata y fiable que hay."""
        an_inspection(
            session, unit, code="OT-2", findings=[finding_row("poste_inclinado", wants=False)]
        )

        assert generate(session, unit).created == []

    def test_rf_013_el_supervisor_puede_proponer_desde_todo_hallazgo(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(
            session, unit, code="OT-3", findings=[finding_row("poste_inclinado", wants=False)]
        )

        report = generate(session, unit, only_wanted=False)

        assert len(report.created) == 1

    def test_rf_013_la_lista_simple_de_defectos_tambien_produce_propuestas(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """B05 registra lo que se vio sin pedir OT, y son la mayoría de los defectos.

        Solo con `only_wanted=False`, porque esa lista no lleva marca: el lector de hallazgos le
        pone `wants_order=False` a todas, y proponerlas por omisión llenaría la bandeja de
        inspecciones de rutina.
        """
        an_inspection(session, unit, code="OT-4", defects=["aislador_roto"])

        assert generate(session, unit).created == []
        assert len(generate(session, unit, only_wanted=False).created) == 1

    def test_rf_013_fuera_del_periodo_no_entra(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(
            session,
            unit,
            code="OT-5",
            findings=[finding_row("cruceta_podrida")],
            submitted=SINCE - timedelta(days=5),
        )

        assert generate(session, unit).created == []

    def test_rf_014_un_activo_con_ot_abierta_no_se_vuelve_a_proponer(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """«Alerta si existe una OT abierta sobre el mismo activo», aquí como negativa.

        Una bandeja con propuestas de trabajo ya programado es una bandeja que un supervisor
        aprende a hojear.
        """
        an_inspection(session, unit, code="OT-6", findings=[finding_row("poste_fisurado")])
        an_open_order(session, unit, asset="P-000452")

        report = generate(session, unit)

        assert report.created == []
        assert report.skipped_open_order == ["P-000452"]

    def test_rf_014_una_ot_cerrada_en_el_activo_no_impide_proponer(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Lo contrario dejaría un activo sin propuestas para siempre tras su primera OT."""
        an_inspection(session, unit, code="OT-7", findings=[finding_row("poste_fisurado")])
        an_open_order(session, unit, asset="P-000452", state=WorkOrderState.CLOSED)

        assert len(generate(session, unit).created) == 1

    def test_rf_014_una_ot_devuelta_si_es_trabajo_pendiente(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Devuelta manda a la cuadrilla otra vez al campo: hay trabajo pendiente en el activo."""
        an_inspection(session, unit, code="OT-6b", findings=[finding_row("poste_fisurado")])
        an_open_order(session, unit, asset="P-000452", state=WorkOrderState.RETURNED)

        assert generate(session, unit).skipped_open_order == ["P-000452"]

    def test_rf_014_una_ot_en_revision_no_frena_ninguna_propuesta(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Su trabajo de campo ya está hecho; lo que falta es un supervisor.

        Y que un supervisor esté ocupado no es una razón para dejar de proponer trabajo. Este es el
        caso que la primera versión tenía mal: incluía `sincronizada` y `en_revision` entre los
        estados pendientes, que son justo los de la OT cuya captura produjo el hallazgo.
        """
        an_inspection(session, unit, code="OT-6c", findings=[finding_row("poste_fisurado")])
        an_open_order(session, unit, asset="P-000452", state=WorkOrderState.IN_REVIEW)

        assert len(generate(session, unit).created) == 1

    def test_rf_013_la_ot_del_hallazgo_no_se_frena_a_si_misma(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Es la única OT que con certeza existe sobre ese activo: contarla callaría al generador.

        Se prueba con la OT en `devuelta`, que sí es trabajo pendiente, porque ahí la regla y la
        excepción se cruzan: la OT frena a las demás propuestas del activo y no a la de su propio
        hallazgo.
        """
        source = an_inspection(session, unit, code="OT-6d", findings=[finding_row("aislador_roto")])
        source.state = WorkOrderState.RETURNED
        session.flush()

        assert len(generate(session, unit).created) == 1

    def test_rf_013_dos_hallazgos_del_mismo_defecto_y_activo_son_una_propuesta(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Una cruceta inspeccionada tres veces en un mes es un trabajo, no tres."""
        an_inspection(session, unit, code="OT-8", findings=[finding_row("cruceta_podrida")])
        an_inspection(
            session,
            unit,
            code="OT-9",
            findings=[finding_row("cruceta_podrida")],
            submitted=NOW - timedelta(days=2),
        )

        report = generate(session, unit)

        assert len(report.created) == 1
        assert len(report.skipped_duplicate) == 1

    def test_rf_013_dos_defectos_distintos_en_el_mismo_activo_son_dos_propuestas(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(
            session,
            unit,
            code="OT-10",
            findings=[finding_row("cruceta_podrida"), finding_row("retenida_floja")],
        )

        assert len(generate(session, unit).created) == 2

    def test_rf_013_una_segunda_pasada_no_duplica(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """La generación se corre a mano y por lote: repetirla no puede llenar la bandeja."""
        an_inspection(session, unit, code="OT-11", findings=[finding_row("cruceta_podrida")])

        first = generate(session, unit)
        second = generate(session, unit)

        assert len(first.created) == 1
        assert second.created == []
        assert second.skipped_duplicate == ["P-000452/cruceta_podrida"]

    def test_rf_013_la_unicidad_esta_en_la_base_y_no_solo_en_la_funcion(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Una comprobación en la función es una que un segundo trabajador corre en paralelo."""
        an_inspection(session, unit, code="OT-12", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)

        session.add(
            WorkOrderProposal(
                business_unit_id=unit.id,
                origin=ProposalOrigin.VISION,
                state=ProposalState.OPEN,
                asset_code="P-000452",
                defect_code="cruceta_podrida",
                work_type="correctivo",
                priority=Priority.MEDIUM.value,
                criticality={},
                justification="una segunda propuesta del mismo par",
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_rf_013_un_defecto_rechazado_puede_volver_a_proponerse(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """El índice es parcial sobre el estado abierto: lo descartado puede reaparecer."""
        an_inspection(session, unit, code="OT-13", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        proposals.reject(
            session,
            unit,
            tray(session, unit)[0],
            reason_code="no_es_defecto",
            actor="kc|supervisor.demo",
        )

        an_inspection(
            session,
            unit,
            code="OT-14",
            findings=[finding_row("cruceta_podrida")],
            submitted=NOW - timedelta(hours=1),
        )
        assert len(generate(session, unit).created) == 1

    def test_rf_013_un_hallazgo_sin_activo_se_cuenta_aparte(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """No hay nada sobre lo que proponer trabajo, y ocultarlo sería perder el hallazgo."""
        an_inspection(
            session, unit, code="OT-15", findings=[finding_row("aislador_roto")], forget_asset=True
        )

        report = generate(session, unit)

        assert report.created == []
        assert report.skipped_no_asset == 1

    def test_rf_013_el_informe_es_serializable_completo(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-16", findings=[finding_row("cruceta_podrida")])

        payload = generate(session, unit).as_dict()

        assert set(payload) == {
            "created",
            "skipped_open_order",
            "skipped_duplicate",
            "skipped_no_asset",
        }
        assert all(isinstance(item, str) for item in payload["created"])

    def test_rf_013_no_cruza_unidades_de_negocio(
        self, session: Session, units: dict[str, BusinessUnit], catalogs_loaded: None
    ) -> None:
        an_inspection(session, units["GYE"], code="OT-17", findings=[finding_row("aislador_roto")])

        assert generate(session, units["MAN"]).created == []
        assert tray(session, units["MAN"]) == []

    def test_rf_160_la_propuesta_queda_en_la_bitacora(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-18", findings=[finding_row("puesta_tierra_faltante")])
        generate(session, unit)

        event = session.execute(
            select(AuditEvent).where(
                AuditEvent.subject_type == "work_order_proposal",
                AuditEvent.kind == EventKind.CREATED,
            )
        ).scalar_one()
        assert event.payload["defect_code"] == "puesta_tierra_faltante"
        assert "priority" in event.payload and "score" in event.payload

    def test_rf_013_la_propuesta_hereda_el_punto_de_la_captura(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Sin punto la propuesta no se puede dibujar, y la bandeja es también un mapa."""
        an_inspection(session, unit, code="OT-19", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)

        row = tray(session, unit)[0]
        longitude, latitude = session.execute(
            select(
                func.ST_X(WorkOrderProposal.location),
                func.ST_Y(WorkOrderProposal.location),
            ).where(WorkOrderProposal.id == row.id)
        ).one()
        assert round(float(longitude), 2) == -79.90
        assert round(float(latitude), 2) == -2.17

    def test_rf_013_el_formulario_sale_del_catalogo_de_formularios(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Del `applies_to_asset_types` de los formularios, no de una tabla aparte (regla 3)."""
        an_inspection(session, unit, code="OT-20", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)

        assert tray(session, unit)[0].form_code is not None


class TestTheAnnexCArithmetic:
    def test_rf_013_severidad_por_consecuencia_sale_de_los_catalogos(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """`puesta_tierra_faltante` es severidad 4 y la estructura consecuencia 3: 12, o P2."""
        an_inspection(session, unit, code="OT-21", findings=[finding_row("puesta_tierra_faltante")])
        generate(session, unit)

        row = tray(session, unit)[0]
        assert row.criticality["severity"] == 4
        assert row.criticality["consequence"] == 3
        assert row.criticality["score"] == 12
        assert row.priority == Priority.HIGH.value
        assert row.criticality["annex_band"] == "P2"

    def test_rf_013_la_exposicion_de_la_zona_sube_la_consecuencia_un_nivel(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """«Un ajuste por exposición (zona urbana o escolar, vía principal: +1 nivel)»."""
        a_zone(session, unit, code="Urbano", exposure=True)
        an_inspection(session, unit, code="OT-22", findings=[finding_row("puesta_tierra_faltante")])
        generate(session, unit)

        row = tray(session, unit)[0]
        assert row.criticality["exposed"] is True
        assert row.criticality["consequence"] == 4
        assert row.criticality["score"] == 16
        assert "exposición" in row.criticality["explanation"]

    def test_rf_013_una_zona_sin_exposicion_no_sube_nada(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        a_zone(session, unit, code="Urbano", exposure=False)
        an_inspection(session, unit, code="OT-23", findings=[finding_row("puesta_tierra_faltante")])
        generate(session, unit)

        row = tray(session, unit)[0]
        assert row.criticality["exposed"] is False
        assert row.criticality["score"] == 12

    def test_rf_013_una_zona_inactiva_no_expone(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Una zona que se dio de baja no puede seguir subiendo prioridades."""
        zone = a_zone(session, unit, code="Urbano", exposure=True)
        zone.active = False
        session.flush()
        an_inspection(session, unit, code="OT-24", findings=[finding_row("puesta_tierra_faltante")])
        generate(session, unit)

        assert tray(session, unit)[0].criticality["exposed"] is False

    def test_rf_013_la_zona_de_otra_unidad_no_expone(
        self, session: Session, units: dict[str, BusinessUnit], catalogs_loaded: None
    ) -> None:
        a_zone(session, units["MAN"], code="Urbano", exposure=True)
        an_inspection(
            session, units["GYE"], code="OT-25", findings=[finding_row("puesta_tierra_faltante")]
        )
        generate(session, units["GYE"])

        assert tray(session, units["GYE"])[0].criticality["exposed"] is False

    def test_rf_013_un_tramo_de_red_lleva_el_caveat_del_catalogo(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """El 4 de un tramo es una aproximación declarada, y viaja con esas palabras.

        Sin el caveat, un 4 se lee como una medición: la plataforma no sabe si ese tramo es troncal
        con un hospital detrás.
        """
        an_inspection(
            session,
            unit,
            code="OT-26",
            asset="TRAMO-9",
            asset_type="line_segment",
            findings=[finding_row("conductor_bajo")],
        )
        generate(session, unit)

        row = tray(session, unit)[0]
        assert row.criticality["estimated"] is True
        assert any("ramal de media tensión" in caveat for caveat in row.criticality["caveats"])
        assert row.criticality["score"] == 20
        assert row.priority == Priority.CRITICAL.value

    def test_rf_013_sin_catalogos_toda_propuesta_sale_estimada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Y lo dice, en vez de presentar un 9 por omisión como si fuera el anexo."""
        an_inspection(session, unit, code="OT-27", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)

        row = tray(session, unit)[0]
        assert row.criticality["severity"] == DEFAULT_SEVERITY
        assert row.criticality["consequence"] == DEFAULT_CONSEQUENCE
        assert row.criticality["estimated"] is True
        assert len(row.criticality["caveats"]) == 2
        assert "cruceta_podrida" in " ".join(row.criticality["caveats"])

    def test_rf_013_el_plazo_sugerido_sale_del_catalogo_de_prioridad(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-28", findings=[finding_row("puesta_tierra_faltante")])
        generate(session, unit)

        assert tray(session, unit)[0].suggested_deadline_hours == 72

    def test_rf_013_la_baja_no_lleva_plazo_porque_el_anexo_no_le_pone_uno(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """P4 es «plan de mantenimiento», que no es un reloj: darle horas es inventar un SLA."""
        an_inspection(
            session,
            unit,
            code="OT-29",
            asset="LUM-3",
            asset_type="street_light",
            findings=[finding_row("luminaria_dia")],
        )
        generate(session, unit)

        row = tray(session, unit)[0]
        assert row.priority == Priority.LOW.value
        assert row.suggested_deadline_hours is None

    def test_rf_013_la_criticidad_guardada_no_se_mueve_cuando_el_catalogo_se_mueve(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Un supervisor que mira una decisión de marzo tiene que ver los números de marzo."""
        an_inspection(session, unit, code="OT-30", findings=[finding_row("puesta_tierra_faltante")])
        generate(session, unit)
        before = dict(tray(session, unit)[0].criticality)

        from app.catalogs import service as catalogs

        catalogs.upsert_entry(
            session,
            "defect",
            entry_code="puesta_tierra_faltante",
            label="Falta puesta a tierra",
            attributes={"severity": 1},
            actor="admin.funcional",
        )
        session.flush()

        assert tray(session, unit)[0].criticality == before


class TestTheTray:
    def test_rf_114_lo_peor_primero_y_lo_mas_viejo_antes(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Una P1 que quedó debajo de veinte P4 es el fallo que este orden evita."""
        an_inspection(
            session,
            unit,
            code="OT-31",
            asset="LUM-1",
            asset_type="street_light",
            findings=[finding_row("luminaria_dia")],
        )
        an_inspection(
            session,
            unit,
            code="OT-32",
            asset="TRAMO-1",
            asset_type="line_segment",
            findings=[finding_row("conductor_bajo")],
        )
        generate(session, unit)

        rows = tray(session, unit)
        assert [row.priority for row in rows] == [
            Priority.CRITICAL.value,
            Priority.LOW.value,
        ]

    def test_rf_114_los_conteos_incluyen_lo_ya_decidido(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(
            session,
            unit,
            code="OT-33",
            findings=[finding_row("cruceta_podrida"), finding_row("retenida_floja")],
        )
        generate(session, unit)
        proposals.reject(
            session,
            unit,
            tray(session, unit)[0],
            reason_code="ya_resuelto",
            actor="kc|supervisor.demo",
        )

        counted = proposals.counts(session, unit)
        assert counted[ProposalState.REJECTED.value] == 1
        assert counted[ProposalState.OPEN.value] == 1

    def test_rf_114_los_motivos_de_rechazo_salen_del_catalogo(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        codes = {entry.code for entry in proposals.reject_reasons(session)}

        assert "no_es_defecto" in codes
        assert all(entry.attributes.get("signal") for entry in proposals.reject_reasons(session))

    def test_rf_114_sin_catalogo_cargado_la_lista_esta_vacia_y_no_revienta(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        assert proposals.reject_reasons(session) == []


class TestApproval:
    def test_rf_013_al_aprobarla_pasa_a_una_ot_planificada(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-34", findings=[finding_row("puesta_tierra_faltante")])
        generate(session, unit)
        proposal = tray(session, unit)[0]

        order = proposals.approve(session, unit, proposal, actor="kc|supervisor.demo")

        assert order.state == WorkOrderState.PLANNED
        assert order.source == WorkOrderSource.AI_FINDING
        assert order.asset_code == "P-000452"
        assert order.priority == Priority.HIGH.value
        assert order.description == proposal.justification
        assert proposal.state == ProposalState.APPROVED
        assert proposal.work_order_id == order.id
        assert proposal.decided_by == "kc|supervisor.demo"
        assert proposal.decided_at is not None

    def test_rf_013_el_plazo_sugerido_llega_al_sla_de_la_ot(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-35", findings=[finding_row("puesta_tierra_faltante")])
        generate(session, unit)

        order = proposals.approve(session, unit, tray(session, unit)[0], actor="kc|supervisor.demo")

        assert order.sla_due_at is not None
        hours = (order.sla_due_at - datetime.now(UTC)).total_seconds() / 3600
        assert 71 < hours <= 72

    def test_rf_013_el_supervisor_puede_cambiar_la_prioridad_calculada(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Saben si ese tramo es troncal, que es justo lo que la plataforma no puede saber."""
        an_inspection(
            session,
            unit,
            code="OT-36",
            asset="TRAMO-2",
            asset_type="line_segment",
            findings=[finding_row("conductor_deshilachado")],
        )
        generate(session, unit)
        proposal = tray(session, unit)[0]
        computed = proposal.priority

        order = proposals.approve(
            session,
            unit,
            proposal,
            actor="kc|supervisor.demo",
            priority=Priority.CRITICAL.value,
        )

        assert computed != Priority.CRITICAL.value
        assert order.priority == Priority.CRITICAL.value
        event = session.execute(
            select(AuditEvent)
            .where(AuditEvent.subject_id == str(proposal.id))
            .where(AuditEvent.kind == EventKind.DECIDED)
        ).scalar_one()
        assert event.payload["priority_overridden"] is True

    def test_rf_013_una_decision_no_se_toma_dos_veces(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-37", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        proposal = tray(session, unit)[0]
        proposals.approve(session, unit, proposal, actor="kc|supervisor.demo")

        with pytest.raises(proposals.NotOpenError):
            proposals.approve(session, unit, proposal, actor="kc|otro.supervisor")

    def test_rf_013_una_propuesta_sin_formulario_mapeado_igual_se_puede_aprobar(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Negarse dejaría al supervisor con una propuesta aprobada y ningún trabajo."""
        an_inspection(session, unit, code="OT-38", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        proposal = tray(session, unit)[0]
        proposal.form_code = None
        session.flush()

        order = proposals.approve(session, unit, proposal, actor="kc|supervisor.demo")

        assert order.form_code == proposals._fallback_form()


class TestMerge:
    def test_rf_114_fusionar_deja_los_hallazgos_en_la_ot_de_destino(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Una fusión que no dejara rastro haría que la cuadrilla llegue sin saber por qué."""
        an_inspection(session, unit, code="OT-39", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        proposal = tray(session, unit)[0]
        target = an_open_order(session, unit, asset="P-000999")
        target.description = "Cambio de crucetas planificado a mano"
        session.flush()

        proposals.merge(session, unit, proposal, into=target, actor="kc|supervisor.demo")

        assert proposal.state == ProposalState.MERGED
        assert proposal.merged_into_id == target.id
        assert proposal.work_order_id is None
        assert "Cambio de crucetas planificado a mano" in target.description
        assert proposal.justification in target.description

    def test_rf_114_no_se_fusiona_en_trabajo_ya_cerrado(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-40", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        closed = an_open_order(session, unit, asset="P-000998", state=WorkOrderState.CLOSED)

        with pytest.raises(proposals.ProposalError, match="cerrado"):
            proposals.merge(
                session,
                unit,
                tray(session, unit)[0],
                into=closed,
                actor="kc|supervisor.demo",
            )

    def test_rf_114_no_se_fusiona_en_una_ot_de_otra_unidad(
        self, session: Session, units: dict[str, BusinessUnit], catalogs_loaded: None
    ) -> None:
        an_inspection(
            session, units["GYE"], code="OT-41", findings=[finding_row("cruceta_podrida")]
        )
        generate(session, units["GYE"])
        foreign = an_open_order(session, units["MAN"], asset="P-000997")

        with pytest.raises(proposals.ProposalError, match="unidad de negocio"):
            proposals.merge(
                session,
                units["GYE"],
                tray(session, units["GYE"])[0],
                into=foreign,
                actor="kc|supervisor.demo",
            )

    def test_rf_114_una_fusion_no_crea_una_ot(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-42", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        target = an_open_order(session, unit, asset="P-000996")
        before = len(list(session.execute(select(WorkOrder.id)).all()))

        proposals.merge(
            session, unit, tray(session, unit)[0], into=target, actor="kc|supervisor.demo"
        )

        assert len(list(session.execute(select(WorkOrder.id)).all())) == before


class TestRejection:
    def test_rf_114_el_motivo_tiene_que_estar_en_el_catalogo(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Texto libre no puede ser una etiqueta de entrenamiento."""
        an_inspection(session, unit, code="OT-43", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)

        with pytest.raises(proposals.UnknownReasonError, match="no_es_defecto"):
            proposals.reject(
                session,
                unit,
                tray(session, unit)[0],
                reason_code="porque_no",
                actor="kc|supervisor.demo",
            )

    def test_rf_114_el_rechazo_guarda_el_motivo_y_la_senal(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-44", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        proposal = tray(session, unit)[0]

        proposals.reject(
            session,
            unit,
            proposal,
            reason_code="no_es_defecto",
            actor="kc|supervisor.demo",
            note="la cruceta está nueva",
        )

        assert proposal.state == ProposalState.REJECTED
        assert proposal.reject_reason_code == "no_es_defecto"
        assert proposal.reject_note == "la cruceta está nueva"
        event = session.execute(
            select(AuditEvent)
            .where(AuditEvent.subject_id == str(proposal.id))
            .where(AuditEvent.kind == EventKind.DECIDED)
        ).scalar_one()
        # La señal se resuelve el día de la decisión: el catálogo se mueve y un conjunto de
        # entrenamiento tiene que saber qué quiso decir la etiqueta ese día.
        assert event.payload["signal"] == "falso_positivo"

    def test_rf_114_un_rechazo_no_crea_ninguna_ot(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Una propuesta rechazada no puede quedar como una OT que nunca fue trabajo."""
        an_inspection(session, unit, code="OT-45", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        before = len(list(session.execute(select(WorkOrder.id)).all()))

        proposals.reject(
            session,
            unit,
            tray(session, unit)[0],
            reason_code="ya_resuelto",
            actor="kc|supervisor.demo",
        )

        assert len(list(session.execute(select(WorkOrder.id)).all())) == before

    def test_rf_114_los_rechazos_se_agrupan_por_la_senal_que_llevan(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """«No es un defecto» y «ya está resuelto» son cosas opuestas para un entrenamiento."""
        an_inspection(
            session,
            unit,
            code="OT-46",
            findings=[
                finding_row("cruceta_podrida"),
                finding_row("retenida_floja"),
                finding_row("poste_inclinado"),
            ],
        )
        generate(session, unit)
        rows = tray(session, unit)
        for row, reason in zip(rows, ("no_es_defecto", "ya_resuelto", "duplicado"), strict=True):
            proposals.reject(session, unit, row, reason_code=reason, actor="kc|supervisor.demo")

        assert proposals.training_signals(session, unit) == {
            "falso_positivo": 1,
            "ninguna": 2,
        }

    def test_rf_114_un_motivo_que_desaparecio_del_catalogo_no_se_cuenta_como_nada(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Se cuenta como «sin clasificar»: perderlo dejaría un rechazo fuera del total."""
        an_inspection(session, unit, code="OT-47", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        proposal = tray(session, unit)[0]
        proposals.reject(
            session,
            unit,
            proposal,
            reason_code="no_es_defecto",
            actor="kc|supervisor.demo",
        )
        proposal.reject_reason_code = "un_motivo_retirado"
        session.flush()

        assert proposals.training_signals(session, unit) == {"sin_clasificar": 1}


class TestTheApi:
    def test_rf_114_el_supervisor_ve_la_bandeja_con_los_motivos(
        self, client: TestClient, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-48", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)

        answer = client.get(f"/api/v1/proposals/units/{unit.code}")

        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert len(body["proposals"]) == 1
        assert body["counts"][ProposalState.OPEN.value] == 1
        assert any(item["code"] == "no_es_defecto" for item in body["reject_reasons"])
        row = body["proposals"][0]
        # Regla 8: el valor de IA viaja con su origen, versión de modelo y confianza — nulos aquí,
        # porque el hallazgo es de una persona, y presentes en el contrato.
        assert {"model_name", "model_version", "confidence"} <= set(row)
        assert "explanation" in row["criticality"]

    def test_rf_013_un_tecnico_no_ve_la_bandeja(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        with client_as(session, TECHNICIAN) as raw:
            assert raw.get(f"/api/v1/proposals/units/{unit.code}").status_code == 403

    def test_rf_013_el_supervisor_no_levanta_propuestas_a_mano(
        self, client: TestClient, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Levantar propuestas no es decidir, y un botón que le llenara su propia bandeja
        sería una cosa rara de poner delante de un supervisor."""
        answer = client.post(f"/api/v1/proposals/units/{unit.code}/generate", json={})

        assert answer.status_code == 403

    def test_rf_013_el_planificador_levanta_propuestas(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-49", findings=[finding_row("cruceta_podrida")])

        with client_as(session, PLANNER) as raw:
            answer = raw.post(
                f"/api/v1/proposals/units/{unit.code}/generate",
                json={"since": SINCE.isoformat(), "until": UNTIL.isoformat()},
            )

        assert answer.status_code == 200, answer.text
        assert len(answer.json()["created"]) == 1

    def test_rf_013_un_periodo_al_reves_se_rechaza(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        with client_as(session, PLANNER) as raw:
            answer = raw.post(
                f"/api/v1/proposals/units/{unit.code}/generate",
                json={"since": UNTIL.isoformat(), "until": SINCE.isoformat()},
            )

        assert answer.status_code == 422

    def test_rf_013_aprobar_por_la_api_toma_al_decisor_del_token(
        self, client: TestClient, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        """Una decisión cuyo autor el llamante pudiera escribir es una que nadie firmó."""
        an_inspection(session, unit, code="OT-50", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        proposal = tray(session, unit)[0]

        answer = client.post(
            f"/api/v1/proposals/units/{unit.code}/{proposal.id}/approve",
            json={"decided_by": "kc|alguien.mas", "note": "va"},
        )

        assert answer.status_code == 200, answer.text
        assert answer.json()["proposal"]["decided_by"] == SUPERVISOR.subject
        assert answer.json()["state"] == WorkOrderState.PLANNED.value

    def test_rf_013_aprobar_dos_veces_por_la_api_es_un_conflicto(
        self, client: TestClient, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-51", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        proposal = tray(session, unit)[0]
        url = f"/api/v1/proposals/units/{unit.code}/{proposal.id}/approve"

        assert client.post(url, json={}).status_code == 200
        assert client.post(url, json={}).status_code == 409

    def test_rf_114_rechazar_con_un_motivo_desconocido_dice_cuales_hay(
        self, client: TestClient, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-52", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        proposal = tray(session, unit)[0]

        answer = client.post(
            f"/api/v1/proposals/units/{unit.code}/{proposal.id}/reject",
            json={"reason_code": "porque_no"},
        )

        assert answer.status_code == 422
        assert "no_es_defecto" in answer.json()["detail"]

    def test_rf_114_fusionar_en_una_ot_de_otra_unidad_es_un_404(
        self,
        client: TestClient,
        session: Session,
        units: dict[str, BusinessUnit],
        catalogs_loaded: None,
    ) -> None:
        an_inspection(
            session, units["GYE"], code="OT-53", findings=[finding_row("cruceta_podrida")]
        )
        generate(session, units["GYE"])
        proposal = tray(session, units["GYE"])[0]
        foreign = an_open_order(session, units["MAN"], asset="P-000995")

        answer = client.post(
            f"/api/v1/proposals/units/GYE/{proposal.id}/merge",
            json={"work_order_id": str(foreign.id)},
        )

        assert answer.status_code == 404

    def test_rf_013_una_propuesta_de_otra_unidad_no_se_decide_desde_esta(
        self,
        client: TestClient,
        session: Session,
        units: dict[str, BusinessUnit],
        catalogs_loaded: None,
    ) -> None:
        an_inspection(
            session, units["MAN"], code="OT-54", findings=[finding_row("cruceta_podrida")]
        )
        generate(session, units["MAN"])
        foreign = tray(session, units["MAN"])[0]

        answer = client.post(f"/api/v1/proposals/units/GYE/{foreign.id}/approve", json={})

        assert answer.status_code == 404

    def test_rf_114_el_analista_ve_las_senales_de_entrenamiento(
        self, session: Session, unit: BusinessUnit, catalogs_loaded: None
    ) -> None:
        an_inspection(session, unit, code="OT-55", findings=[finding_row("cruceta_podrida")])
        generate(session, unit)
        proposals.reject(
            session,
            unit,
            tray(session, unit)[0],
            reason_code="no_es_defecto",
            actor="kc|supervisor.demo",
        )

        with client_as(session, ANALYST) as raw:
            answer = raw.get(f"/api/v1/proposals/units/{unit.code}/training-signals")

        assert answer.status_code == 200, answer.text
        assert answer.json() == {"falso_positivo": 1}

    def test_rf_013_una_unidad_fuera_del_alcance_no_dice_si_existe(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """403 y no 404 a propósito (ADR-009): quien está en una unidad no puede enumerar las otras.

        El 404 queda para la unidad que el token sí alcanza y la base no tiene.
        """
        assert client.get("/api/v1/proposals/units/NADA").status_code == 403

    def test_rf_013_una_unidad_alcanzable_que_no_existe_es_un_404(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        who = principal(Role.SUPERVISOR, units="FANTASMA")
        with client_as(session, who) as raw:
            assert raw.get("/api/v1/proposals/units/FANTASMA").status_code == 404
