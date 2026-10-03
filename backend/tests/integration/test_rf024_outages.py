"""Consignaciones, su ventana horaria y el permiso de trabajo (RF-024).

El criterio es una negativa —«no se habilita el formulario F-TR-02 sin un N.º de consignación»— y de
ahí sale casi todo lo que se prueba aquí:

* **El número es la autoridad, no el estado.** Una solicitud marcada como aprobada sin número no
  habilita nada: el número es lo que la cuadrilla repite por radio antes de tocar la línea y lo que
  se pide después si algo sale mal.
* **Dos personas.** Quien solicitó la consignación no la otorga. Un descargo que alguien se dio a sí
  mismo es justamente lo que el procedimiento existe para evitar.
* **Trabajar fuera de la ventana se registra, no se rechaza.** Rechazar la captura perdería el
  registro de lo que realmente pasó, que es lo único que una investigación necesita. La plataforma
  rechaza lo que no debe ocurrir y registra lo que ocurrió.
* **Una consignación sirve a varias OT.** Un corte del alimentador sur cubre todos los frentes que
  trabajan bajo él, y una solicitud por OT tendría al Centro de Control otorgando seis descargos
  para un solo corte.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError as DbIntegrityError
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.outages import service as outages
from app.outages.models import OutageRequest, OutageState
from app.responses.models import EvidenceStage
from app.responses.service import OutagePermitError, compose_for, register_evidence, save_answers
from app.workorders.models import WorkOrder, WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 26, 6, 0, tzinfo=UTC)
WINDOW_START = NOW
WINDOW_END = NOW + timedelta(hours=6)

PLANNER = Principal(
    subject="kc|planificador.demo",
    username="planificador.demo",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
)
CONTROL = Principal(
    subject="kc|centro.control",
    username="centro.control",
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


def a_request(
    session: Session,
    unit: BusinessUnit,
    *,
    requested_by: str = PLANNER.subject,
    start: datetime = WINDOW_START,
    end: datetime = WINDOW_END,
    equipment: str = "Alimentador 04BH070T11, tramo sur",
) -> OutageRequest:
    return outages.request_outage(
        session,
        unit,
        equipment=equipment,
        window_start=start,
        window_end=end,
        requested_by=requested_by,
        feeder_code="04BH070T11",
    )


def granted(
    session: Session, unit: BusinessUnit, *, number: str = "DESC-2026-0771"
) -> OutageRequest:
    request = a_request(session, unit)
    return outages.approve(session, unit, request, number=number, decided_by=CONTROL.subject)


def a_permit_order(session: Session, unit: BusinessUnit, *, code: str = "OT-PT-1") -> WorkOrder:
    """Una OT que se ejecuta con el permiso de trabajo."""
    order = create_work_order(
        session,
        unit,
        work_type="maniobra_con_corte",
        form_code="F-TR-02",
        asset_type_key="line_segment",
        asset_code="TRAMO-9",
        feeder_code="04BH070T11",
        planner_id=PLANNER.subject,
    )
    order.state = WorkOrderState.IN_EXECUTION
    order.form_version = "1.0.0"
    order.code = code
    session.flush()
    return order


def permit_answers(**overrides: Any) -> dict[str, Any]:
    answers: dict[str, Any] = {
        "work_order_code": "OT-PT-1",
        "work_type": "maniobra_con_corte",
        "priority": "alta",
        "feeder_code": "04BH070T11",
        "ats_reference": "ATS-2026-0001",
        "consigned_equipment": "Alimentador 04BH070T11, tramo sur",
        "sources_opened_at": (WINDOW_START + timedelta(minutes=10)).isoformat(),
        "sources_operated": "RECONECTADOR-7, SECCIONADOR-31",
        "locked_out": True,
        "absence_verified": True,
        "detector_used": "Fluke 1AC-E1, serie 88213",
        "grounded": True,
        "grounding_location": "Ambos extremos del tramo",
        "area_delimited": True,
        "photos_before": [f"s3://permiso-{index}.jpg" for index in range(5)],
    }
    answers.update(overrides)
    return answers


def with_photos(session: Session, response: Any, *, how_many: int = 5) -> None:
    for index in range(how_many):
        register_evidence(
            session,
            response,
            kind="foto",
            storage_key=f"s3://permiso-{index}.jpg",
            content_hash=hashlib.sha256(f"permiso{index}".encode()).hexdigest(),
            stage=EvidenceStage.BEFORE,
        )


def client_as(session: Session, who: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: who
    return TestClient(app)


@pytest.fixture
def client(session: Session):
    with client_as(session, PLANNER) as raw:
        yield raw


class TestRequestingAndGranting:
    def test_rf_024_una_solicitud_nace_sin_numero_y_sin_habilitar_nada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = a_request(session, unit)

        assert request.state == OutageState.REQUESTED
        assert request.number is None
        assert request.grants_permit is False

    def test_rf_024_el_centro_de_control_otorga_con_numero(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = granted(session, unit)

        assert request.state == OutageState.APPROVED
        assert request.number == "DESC-2026-0771"
        assert request.decided_by == CONTROL.subject
        assert request.grants_permit is True

    def test_rf_024_una_aprobacion_sin_numero_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El número es la autoridad: sin él, una fila aprobada no habilita nada."""
        request = a_request(session, unit)

        with pytest.raises(outages.OutageError, match="número es la autoridad"):
            outages.approve(session, unit, request, number="   ", decided_by=CONTROL.subject)

    def test_rf_024_una_fila_aprobada_sin_numero_no_habilita_nada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una combinación que `approve` rechaza y que solo se consigue editando la fila.

        Se prueba igual porque `grants_permit` es lo que la API publica, y porque una fila así —una
        carga directa, una migración a medias— no puede habilitar un permiso de trabajo. El sabotaje
        que le quitaba el número a esta propiedad pasó inadvertido sin este test.
        """
        request = a_request(session, unit)
        request.state = OutageState.APPROVED
        session.flush()

        assert request.number is None
        assert request.grants_permit is False

    def test_rf_024_quien_solicita_no_puede_otorgar(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un descargo que alguien se dio a sí mismo es lo que el procedimiento evita."""
        request = a_request(session, unit, requested_by=CONTROL.subject)

        with pytest.raises(outages.SelfApprovalError):
            outages.approve(session, unit, request, number="DESC-1", decided_by=CONTROL.subject)

    def test_rf_024_quien_solicita_tampoco_puede_negar(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = a_request(session, unit, requested_by=CONTROL.subject)

        with pytest.raises(outages.SelfApprovalError):
            outages.reject(session, unit, request, decided_by=CONTROL.subject, note="no")

    def test_rf_024_negar_exige_el_motivo(self, session: Session, unit: BusinessUnit) -> None:
        """«No» sin motivo manda al planificador al teléfono."""
        request = a_request(session, unit)

        with pytest.raises(outages.OutageError, match="por qué"):
            outages.reject(session, unit, request, decided_by=CONTROL.subject, note="  ")

    def test_rf_024_una_decision_no_se_toma_dos_veces(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = granted(session, unit)

        with pytest.raises(outages.NotDecidableError):
            outages.approve(session, unit, request, number="DESC-2", decided_by=CONTROL.subject)

    def test_rf_024_una_ventana_que_termina_antes_de_empezar_se_rechaza(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        with pytest.raises(outages.OutageError, match="ventana"):
            a_request(session, unit, start=WINDOW_END, end=WINDOW_START)

    def test_rf_024_el_numero_es_unico_por_unidad(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Dos filas con el mismo descargo harían «¿bajo qué consignación trabajaron?»

        incontestable.
        """
        granted(session, unit, number="DESC-DUP")
        second = a_request(session, unit)
        second.state = OutageState.APPROVED
        second.number = "DESC-DUP"

        with pytest.raises(DbIntegrityError):
            session.flush()
        session.rollback()

    def test_rf_024_el_mismo_numero_en_otra_unidad_es_valido(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        """Cada Centro de Control numera lo suyo."""
        granted(session, units["GYE"], number="DESC-1")
        granted(session, units["MAN"], number="DESC-1")

        assert len(outages.requests_of(session, units["MAN"])) == 1

    def test_rf_024_devolver_cierra_la_consignacion(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = granted(session, unit)

        outages.hand_back(session, unit, request, returned_by="kc|jefe.cuadrilla")

        assert request.state == OutageState.RETURNED
        assert request.returned_at is not None
        assert request.returned_by == "kc|jefe.cuadrilla"

    def test_rf_024_no_se_devuelve_una_que_no_fue_otorgada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = a_request(session, unit)

        with pytest.raises(outages.OutageError, match="aprobada"):
            outages.hand_back(session, unit, request, returned_by="kc|jefe.cuadrilla")

    def test_rf_024_una_ventana_pasada_vence_y_no_se_llama_rechazada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Nadie la negó: la ventana se fue. La distinción importa a quien pregunte por qué."""
        granted(session, unit)

        expired = outages.expire_due(session, unit, now=WINDOW_END + timedelta(minutes=1))

        assert [row.state for row in expired] == [OutageState.EXPIRED]

    def test_rf_024_una_ventana_vigente_no_vence(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        granted(session, unit)

        assert outages.expire_due(session, unit, now=WINDOW_START + timedelta(hours=1)) == []

    def test_rf_160_la_solicitud_y_la_decision_quedan_en_la_bitacora(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        granted(session, unit)

        events = list(
            session.execute(
                select(AuditEvent).where(AuditEvent.subject_type == "outage_request")
            ).scalars()
        )
        actors = {event.actor for event in events}
        assert actors == {PLANNER.subject, CONTROL.subject}


class TestLinkingWorkOrders:
    def test_rf_024_una_consignacion_sirve_a_varias_ot(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un corte del alimentador sur cubre todos los frentes que trabajan bajo él."""
        request = granted(session, unit)
        first = a_permit_order(session, unit, code="OT-PT-1")
        second = a_permit_order(session, unit, code="OT-PT-2")

        outages.link(session, unit, first, request, actor=PLANNER.subject)
        outages.link(session, unit, second, request, actor=PLANNER.subject)

        assert [order.code for order in outages.orders_under(session, request)] == [
            "OT-PT-1",
            "OT-PT-2",
        ]

    def test_rf_024_no_se_vincula_una_ot_de_otra_unidad(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        request = granted(session, units["GYE"])
        foreign = a_permit_order(session, units["MAN"], code="OT-X")

        with pytest.raises(outages.OutageError, match="unidad de negocio"):
            outages.link(session, units["GYE"], foreign, request, actor=PLANNER.subject)

    def test_rf_024_desvincular_deja_la_ot_sin_consignacion(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = granted(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)

        outages.unlink(session, unit, order, actor=PLANNER.subject)

        assert order.outage_request_id is None
        assert outages.orders_under(session, request) == []

    def test_rf_024_una_consignacion_otorgada_sin_ot_se_reporta(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una línea desenergizada para nada: clientes sin servicio y un índice que se reporta."""
        request = granted(session, unit)

        assert outages.unused_ids(session, unit) == [request.id]

        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)
        assert outages.unused_ids(session, unit) == []


class TestThePermitGate:
    def test_rf_024_sin_consignacion_el_permiso_no_se_puede_enviar(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El criterio de aceptación, tal cual."""
        order = a_permit_order(session, unit)

        with pytest.raises(OutagePermitError, match="necesita una consignación"):
            save_answers(session, unit, order, answers=permit_answers(), submit=True)

    def test_rf_024_con_una_solicitud_sin_otorgar_tampoco(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una solicitud no es una consignación: el número es lo que habilita."""
        request = a_request(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)

        with pytest.raises(OutagePermitError, match="todavía no tiene número"):
            save_answers(session, unit, order, answers=permit_answers(), submit=True)

    def test_rf_024_con_la_consignacion_otorgada_el_permiso_se_envia(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = granted(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)

        response = save_answers(session, unit, order, answers=permit_answers(), submit=True)

        assert response.submitted_at is None or response.state is not None
        assert response.answers["consigned_equipment"].startswith("Alimentador")

    def test_rf_024_una_consignacion_negada_no_habilita_el_permiso(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = a_request(session, unit)
        outages.reject(
            session, unit, request, decided_by=CONTROL.subject, note="mantenimiento mayor"
        )
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)

        with pytest.raises(OutagePermitError):
            save_answers(session, unit, order, answers=permit_answers(), submit=True)

    def test_rf_024_una_consignacion_vencida_ya_no_habilita_el_permiso(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """El caso peligroso: **tuvo** número, y la ventana se cerró.

        Es el que el sabotaje encontró: el test de la consignación negada pasaba por la guarda del
        número —una negada nunca tiene uno— y no por la del estado. Una vencida sí tiene número, y
        es además la situación real: la cuadrilla sigue con el papel en la mano y el equipo ya
        puede estar energizado.
        """
        request = granted(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)
        outages.expire_due(session, unit, now=WINDOW_END + timedelta(minutes=1))

        with pytest.raises(OutagePermitError, match="vencida"):
            save_answers(session, unit, order, answers=permit_answers(), submit=True)

    def test_rf_024_una_consignacion_devuelta_todavia_habilita_el_permiso(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La devolución es el último campo del propio formulario: cerrarlo no puede cerrarse la
        puerta a sí mismo."""
        request = granted(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)
        outages.hand_back(session, unit, request, returned_by="kc|jefe.cuadrilla")

        response = save_answers(session, unit, order, answers=permit_answers(), submit=True)

        assert response.answers["locked_out"] is True

    def test_rf_024_un_borrador_se_guarda_aunque_falte_la_consignacion(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La cuadrilla puede ir anotando: la puerta es el envío, no cada tecla."""
        order = a_permit_order(session, unit)

        response = save_answers(
            session, unit, order, answers={"consigned_equipment": "tramo sur"}, submit=False
        )

        assert response.answers["consigned_equipment"] == "tramo sur"

    def test_rf_024_la_regla_no_le_cobra_nada_a_los_demas_formularios(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una inspección preventiva no necesita descargo, y son casi todas las OT."""
        order = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            asset_code="P-000452",
            feeder_code="04BH070T11",
            planner_id=PLANNER.subject,
        )
        order.form_version = "1.1.0"
        order.code = "OT-MT-1"
        session.flush()

        response = save_answers(
            session,
            unit,
            order,
            answers={
                "work_order_code": "OT-MT-1",
                "work_type": "inspeccion_preventiva",
                "priority": "media",
                "code": "P-000452",
                "material": "concrete",
                "feeder_code": "04BH070T11",
                "ats_reference": "ATS-2026-0001",
                "general_condition": "bueno",
                "final_state": "resuelto",
                "photos_before": ["s3://a.jpg", "s3://b.jpg"],
            },
            submit=True,
        )

        assert response.answers["final_state"] == "resuelto"

    def test_rf_024_el_formulario_compuesto_dice_por_que_no_se_habilita(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una negativa que solo llega al enviar es una que la cuadrilla encuentra ya subida al

        poste.
        """
        order = a_permit_order(session, unit)

        composed = compose_for(session, unit, order)

        assert any("consignación" in warning for warning in composed.warnings)

    def test_rf_024_el_numero_otorgado_llega_al_formulario_para_leerlo_por_radio(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """En el formulario para que lo vean, nunca para que lo inventen."""
        request = granted(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)

        composed = compose_for(session, unit, order)

        assert composed.schema["properties"]["outage_number"]["default"] == "DESC-2026-0771"
        assert composed.schema["properties"]["outage_number"]["readOnly"] is True


class TestTheWindowIsRecordedNotEnforced:
    def test_rf_024_dentro_de_la_ventana_no_hay_nada_que_decir(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = granted(session, unit)

        check = outages.window_check(request, WINDOW_START + timedelta(hours=1))

        assert check.inside is True
        assert check.message is None

    def test_rf_024_antes_de_la_ventana_se_registra_cuantos_minutos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Trabajar antes de la ventana es trabajar en una línea que puede reenergizarse."""
        request = granted(session, unit)

        check = outages.window_check(request, WINDOW_START - timedelta(minutes=45))

        assert check.inside is False
        assert check.minutes_early == 45
        assert "antes" in (check.message or "")
        assert request.number in (check.message or "")

    def test_rf_024_despues_de_la_ventana_tambien(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = granted(session, unit)

        check = outages.window_check(request, WINDOW_END + timedelta(minutes=20))

        assert check.inside is False
        assert check.minutes_late == 20
        assert "después" in (check.message or "")

    def test_rf_024_fuera_de_la_ventana_no_impide_guardar_la_captura(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Rechazarla perdería el registro de lo que pasó, que es lo que una investigación

        necesita.
        """
        request = granted(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)

        late = (WINDOW_END + timedelta(hours=2)).isoformat()
        response = save_answers(
            session, unit, order, answers=permit_answers(sources_opened_at=late), submit=True
        )

        assert response.answers["sources_opened_at"] == late
        assert outages.window_check(request, WINDOW_END + timedelta(hours=2)).inside is False


class TestTheGoldenRules:
    def test_rf_024_no_se_verifica_ausencia_de_tension_sin_bloqueo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Las cinco reglas son condiciones entre sí, no un orden implícito en la pantalla."""
        from app.responses.service import AnswerValidationError

        request = granted(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)
        answers = permit_answers()
        answers.pop("locked_out")

        with pytest.raises(AnswerValidationError, match="bloqueo"):
            save_answers(session, unit, order, answers=answers, submit=True)

    def test_rf_024_no_se_pone_a_tierra_sin_verificar_y_sin_decir_con_que(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        from app.responses.service import AnswerValidationError

        request = granted(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)
        answers = permit_answers()
        answers.pop("detector_used")

        with pytest.raises(AnswerValidationError, match="detector"):
            save_answers(session, unit, order, answers=answers, submit=True)

    def test_rf_024_la_devolucion_necesita_el_responsable(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        from app.responses.service import AnswerValidationError

        request = granted(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)
        answers = permit_answers(returned_at=WINDOW_END.isoformat())

        with pytest.raises(AnswerValidationError, match="responsable"):
            save_answers(session, unit, order, answers=answers, submit=True)

    def test_rf_024_el_permiso_exige_cinco_fotos(self) -> None:
        """Es el formulario que se revisa cuando algo sale mal."""
        from app.forms.catalog import get_definition

        assert get_definition("F-TR-02").form.min_photos.before == 5

    def test_rf_024_el_permiso_tambien_exige_ats(self) -> None:
        """El permiso autoriza la maniobra; el ATS es el análisis de cómo hacerla sin lastimarse."""
        from app.forms.catalog import get_definition

        assert get_definition("F-TR-02").form.requires_ats is True


class TestTheApi:
    def payload(self) -> dict[str, Any]:
        return {
            "equipment": "Alimentador 04BH070T11, tramo sur",
            "window_start": WINDOW_START.isoformat(),
            "window_end": WINDOW_END.isoformat(),
            "feeder_code": "04BH070T11",
        }

    def test_rf_024_el_planificador_solicita(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        answer = client.post(f"/api/v1/outages/units/{unit.code}", json=self.payload())

        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["state"] == OutageState.REQUESTED.value
        assert body["requested_by"] == PLANNER.subject
        assert body["grants_permit"] is False

    def test_rf_024_el_planificador_no_otorga(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        """Quien pide no otorga, y el rol lo dice antes que el servicio."""
        request = a_request(session, unit)

        answer = client.post(
            f"/api/v1/outages/units/{unit.code}/{request.id}/approve", json={"number": "DESC-9"}
        )

        assert answer.status_code == 403

    def test_rf_024_el_centro_de_control_otorga_por_la_api(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = a_request(session, unit)

        with client_as(session, CONTROL) as raw:
            answer = raw.post(
                f"/api/v1/outages/units/{unit.code}/{request.id}/approve",
                json={"number": "DESC-2026-0771"},
            )

        assert answer.status_code == 200, answer.text
        assert answer.json()["grants_permit"] is True
        assert answer.json()["decided_by"] == CONTROL.subject

    def test_rf_024_otorgarse_a_si_mismo_es_un_403_que_explica(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = a_request(session, unit, requested_by=CONTROL.subject)

        with client_as(session, CONTROL) as raw:
            answer = raw.post(
                f"/api/v1/outages/units/{unit.code}/{request.id}/approve",
                json={"number": "DESC-9"},
            )

        assert answer.status_code == 403
        assert "sí mismo" in answer.json()["detail"]

    def test_rf_024_negar_sin_motivo_lo_rechaza_el_contrato(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        request = a_request(session, unit)

        with client_as(session, CONTROL) as raw:
            answer = raw.post(
                f"/api/v1/outages/units/{unit.code}/{request.id}/reject", json={"note": ""}
            )

        assert answer.status_code == 422

    def test_rf_024_la_lista_marca_las_otorgadas_sin_ot(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        granted(session, unit)

        answer = client.get(f"/api/v1/outages/units/{unit.code}")

        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["counts"][OutageState.APPROVED.value] == 1
        assert body["requests"][0]["unused"] is True

    def test_rf_024_el_detalle_trae_las_ot_bajo_la_consignacion(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        request = granted(session, unit)
        order = a_permit_order(session, unit)
        outages.link(session, unit, order, request, actor=PLANNER.subject)

        answer = client.get(f"/api/v1/outages/units/{unit.code}/{request.id}")

        assert answer.status_code == 200, answer.text
        assert [row["code"] for row in answer.json()["work_orders"]] == ["OT-PT-1"]

    def test_rf_024_vincular_por_la_api(
        self, client: TestClient, session: Session, unit: BusinessUnit
    ) -> None:
        request = granted(session, unit)
        order = a_permit_order(session, unit)

        answer = client.post(
            f"/api/v1/outages/units/{unit.code}/{request.id}/work-orders",
            json={"work_order_id": str(order.id)},
        )

        assert answer.status_code == 200, answer.text
        assert answer.json()["number"] == "DESC-2026-0771"

    def test_rf_024_un_tecnico_lee_pero_no_solicita(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La cuadrilla tiene que poder ver bajo qué consignación va a trabajar."""
        granted(session, unit)

        with client_as(session, TECHNICIAN) as raw:
            assert raw.get(f"/api/v1/outages/units/{unit.code}").status_code == 200
            assert (
                raw.post(f"/api/v1/outages/units/{unit.code}", json=self.payload()).status_code
                == 403
            )

    def test_rf_024_una_consignacion_de_otra_unidad_es_404(
        self, client: TestClient, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        foreign = granted(session, units["MAN"])

        answer = client.get(f"/api/v1/outages/units/GYE/{foreign.id}")

        assert answer.status_code == 404
