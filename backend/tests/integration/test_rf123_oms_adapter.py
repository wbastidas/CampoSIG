"""Eventos de falla del OMS, y la interrupción de vuelta (RF-123).

El criterio es «una interrupción registrada en F-OP-03 se refleja en el OMS», y lo que más se prueba
aquí son las cuatro cosas que deciden si eso es cierto o solo parece:

* **El informe lo arma el mismo clasificador que la exportación regulatoria** (RF-132). Dos lectores
  de «¿es computable esta interrupción?» se desviarían, y el que se desviara sería el que acaba
  viendo el regulador. Hay un test que compara las dos salidas campo por campo.
* **La plataforma no calcula FMIK ni TTIK.** El denominador es el kVA instalado de la unidad, que
  vive en los sistemas corporativos: un índice contra un denominador supuesto es un número que
  alguien tiene que defender después ante el regulador.
* **Un evento del OMS se vuelve una OT y solo una.** Una red que sigue reportando el mismo disparo
  mientras la cuadrilla va en camino es lo normal, no un caso raro.
* **La correspondencia con CIM está declarada, no supuesta.** «Cuando sea posible» dice el SRS, y un
  mensaje CIM completo necesita el perfil del OMS de la distribuidora; el payload lleva las
  correspondencias inequívocas y lo dice con palabras.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import interruptions
from app.gis_gateway.ingest import ingest_metadata
from app.integrations import oms_adapter
from app.integrations.models import (
    Connector,
    Direction,
    EventKind,
    EventStatus,
    IntegrationEvent,
)
from app.integrations.transport import RecordingTransport, Response, TransportError
from app.org.models import BusinessUnit, Organization
from app.regulatory.service import set_parameter
from app.responses.models import FormResponse
from app.responses.service import save_answers
from app.review.service import Decision, decide
from app.workers.integration_delivery import deliver_one, run_once
from app.workorders.models import WorkOrder, WorkOrderSource, WorkOrderState
from app.workorders.service import create_work_order, transition
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

BASE = "http://oms.test"
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
START = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)


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
def threshold(session: Session) -> None:
    """El umbral de «no computable» en vigencia, que es lo que clasifica una interrupción."""
    set_parameter(
        session,
        code="interruption.non_computable_seconds",
        value=180,
        unit="s",
        norm_ref="ARCERNNR 002/20",
        article_ref="Art. 8",
        effective_from=date(2026, 1, 1),
        verified_by="kc|regulatorio.1",
    )
    session.flush()


def an_interruption(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str,
    seconds: float | None = 3600,
    kva: float | None = 250,
    cause: str = "descarga_atmosferica",
    external_ref: str | None = None,
) -> WorkOrder:
    order = create_work_order(
        session,
        unit,
        work_type="interrupcion",
        form_code="F-OP-03",
        asset_type_key="line_segment",
        asset_code="TRAMO-9",
        feeder_code="04BH070T11",
        external_ref=external_ref,
        longitude=-79.90,
        latitude=-2.17,
        zone="Urbano",
        planner_id="kc|planner.a",
    )
    order.state = WorkOrderState.SYNCED
    order.form_version = "1.0.0"
    order.code = code
    session.flush()

    answers: dict[str, Any] = {
        "work_order_code": code,
        "work_type": "interrupcion",
        "priority": "alta",
        "feeder_code": "04BH070T11",
        "substation_code": "SE-NORTE",
        "interruption_kind": "no_programada",
        "interruption_origin": "interna",
        "started_at_interruption": START.isoformat(),
        "protection_operated": "RECONECTADOR-7",
        "transformers_affected": 12,
        "interruption_cause": cause,
    }
    if seconds is not None:
        answers["interruption_seconds"] = seconds
        answers["restored_at_interruption"] = (START + timedelta(seconds=seconds)).isoformat()
    if kva is not None:
        answers["kva_affected"] = kva

    response = save_answers(session, unit, order, answers=answers, submit=True)
    response.submitted_at = NOW
    session.flush()
    return order


def a_fault(event_id: str, **extra: Any) -> dict[str, Any]:
    return {"event_id": event_id, "feeder_code": "04BH070T11", **extra}


def events_transport(items: list[dict[str, Any]]) -> RecordingTransport:
    transport = RecordingTransport()
    transport.script("GET", f"{BASE}/events", Response(200, {"items": items}))
    return transport


def reports(session: Session) -> list[IntegrationEvent]:
    return list(
        session.execute(
            select(IntegrationEvent).where(
                IntegrationEvent.kind == EventKind.INTERRUPTION_REPORTED.value
            )
        ).scalars()
    )


class TestFaultEventsArrive:
    def test_rf_123_un_evento_de_falla_se_vuelve_una_ot(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        report = oms_adapter.import_fault_events(
            session,
            unit,
            events_transport([a_fault("OMS-1", priority="critica", asset_code="SEC-1")]),
            base_url=BASE,
        )

        assert report["created"] == ["OMS-1"]
        order = session.execute(
            select(WorkOrder).where(WorkOrder.external_ref == "OMS-1")
        ).scalar_one()
        assert order.source == WorkOrderSource.OMS_EVENT
        assert order.form_code == oms_adapter.FAULT_FORM
        assert order.priority == "critica"
        assert order.feeder_code == "04BH070T11"

    def test_rf_123_el_mismo_evento_dos_veces_no_manda_dos_cuadrillas(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Una red que sigue reportando el disparo mientras la cuadrilla va es lo normal."""
        oms_adapter.import_fault_events(
            session, unit, events_transport([a_fault("OMS-1")]), base_url=BASE
        )

        second = oms_adapter.import_fault_events(
            session, unit, events_transport([a_fault("OMS-1")]), base_url=BASE
        )

        assert second["created"] == []
        assert second["already_known"] == ["OMS-1"]
        assert len(list(session.execute(select(WorkOrder.id)).all())) == 1

    def test_rf_123_un_evento_sin_identificador_se_rechaza_con_su_motivo(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        report = oms_adapter.import_fault_events(
            session, unit, events_transport([{"feeder_code": "X"}]), base_url=BASE
        )

        assert report["created"] == []
        assert "identificador" in report["rejected"][0]["reason"]

    def test_rf_123_sin_prioridad_del_oms_se_usa_alta_y_no_se_infiere_de_los_clientes(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Esa aritmética es del planificador y del anexo C, no de un conector."""
        oms_adapter.import_fault_events(
            session,
            unit,
            events_transport([a_fault("OMS-1", clients_affected=4000)]),
            base_url=BASE,
        )

        order = session.execute(
            select(WorkOrder).where(WorkOrder.external_ref == "OMS-1")
        ).scalar_one()
        assert order.priority == "alta"

    def test_rf_123_el_evento_entrante_queda_en_la_bitacora_con_su_payload(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Cuando una importación resulta equivocada, la única forma de saber qué mandó el otro
        sistema es haberlo guardado."""
        oms_adapter.import_fault_events(
            session,
            unit,
            events_transport([a_fault("OMS-1", description="Apertura de seccionador")]),
            base_url=BASE,
        )

        event = session.execute(
            select(IntegrationEvent).where(
                IntegrationEvent.kind == EventKind.FAULT_EVENT_RECEIVED.value
            )
        ).scalar_one()
        assert event.direction == Direction.INBOUND
        assert event.connector == Connector.OMS
        assert event.payload["description"] == "Apertura de seccionador"

    def test_rf_123_un_fallo_del_oms_queda_registrado_y_se_propaga(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        transport = RecordingTransport()
        transport.script("GET", f"{BASE}/events", TransportError("503", retryable=True))

        with pytest.raises(TransportError):
            oms_adapter.import_fault_events(session, unit, transport, base_url=BASE)

        event = session.execute(
            select(IntegrationEvent).where(
                IntegrationEvent.kind == EventKind.FAULT_EVENT_RECEIVED.value
            )
        ).scalar_one()
        assert event.attempts == 1
        assert "503" in (event.last_error or "")

    def test_rf_123_las_ot_del_oms_no_cruzan_unidades(
        self, session: Session, units: dict[str, BusinessUnit]
    ) -> None:
        oms_adapter.import_fault_events(
            session, units["GYE"], events_transport([a_fault("OMS-1")]), base_url=BASE
        )

        created = oms_adapter.import_fault_events(
            session, units["MAN"], events_transport([a_fault("OMS-1")]), base_url=BASE
        )

        # Cada unidad tiene su propia OT: el `external_ref` es único por unidad, no global.
        assert created["created"] == ["OMS-1"]
        assert len(list(session.execute(select(WorkOrder.id)).all())) == 2


class TestTheInterruptionGoesBack:
    def test_rf_123_al_aprobar_la_interrupcion_se_encola_el_informe(
        self, session: Session, unit: BusinessUnit, threshold: None
    ) -> None:
        """El criterio de aceptación, y dentro de la transacción de la aprobación."""
        order = an_interruption(session, unit, code="OT-INT-1", external_ref="OMS-9")
        transition(session, order, WorkOrderState.IN_REVIEW)

        decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="kc|sup.1")

        event = reports(session)[0]
        assert event.connector == Connector.OMS
        assert event.direction == Direction.OUTBOUND
        assert event.payload["event_id"] == "OMS-9"
        assert event.payload["cause"] == "descarga_atmosferica"
        assert event.payload["element"] == "RECONECTADOR-7"
        assert event.payload["restoration_hours"] == 1.0

    def test_rf_123_una_ot_que_no_es_un_registro_de_interrupcion_no_reporta_nada(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """La mayoría de las OT no son interrupciones, y un informe vacío ensucia el log del OMS.

        Con captura **enviada**, a propósito: la primera versión de este test usaba una OT sin
        captura, así que pasaba por la guarda siguiente y no probaba nada del código de formulario.
        Lo descubrió el sabotaje correspondiente, que quedó invisible.
        """
        order = create_work_order(
            session,
            unit,
            work_type="mantenimiento_correctivo",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            asset_code="P-000452",
            feeder_code="04BH070T11",
            planner_id="kc|planner.a",
        )
        order.state = WorkOrderState.SYNCED
        order.form_version = "1.1.0"
        order.code = "OT-MT-1"
        session.flush()
        response = save_answers(
            session,
            unit,
            order,
            answers={
                "work_order_code": "OT-MT-1",
                "work_type": "mantenimiento_correctivo",
                "priority": "media",
                "code": "P-000452",
                "material": "concrete",
                "feeder_code": "04BH070T11",
                "ats_reference": "ATS-2026-0001",
                "general_condition": "regular",
                "final_state": "resuelto",
            },
            submit=True,
        )
        response.submitted_at = NOW
        session.flush()

        assert oms_adapter.enqueue_interruption_report(session, unit, order) is None

    def test_rf_123_una_interrupcion_en_borrador_todavia_no_reporta(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Un borrador no es un registro: la cuadrilla está escribiéndolo.

        Con borrador guardado y no sin captura, por la misma razón que el test anterior: sin
        respuesta, la guarda que se ejercita es otra.
        """
        order = create_work_order(
            session,
            unit,
            work_type="interrupcion",
            form_code="F-OP-03",
            asset_type_key="line_segment",
            feeder_code="04BH070T11",
            planner_id="kc|planner.a",
        )
        order.form_version = "1.0.0"
        order.code = "OT-INT-BORRADOR"
        session.flush()
        save_answers(session, unit, order, answers={"feeder_code": "04BH070T11"}, submit=False)

        assert oms_adapter.enqueue_interruption_report(session, unit, order) is None

    def test_rf_123_el_informe_usa_el_mismo_clasificador_que_la_exportacion(
        self, session: Session, unit: BusinessUnit, threshold: None
    ) -> None:
        """Dos lectores de «¿es computable?» se desviarían, y el que se desviara lo vería el
        regulador. Este test compara las dos salidas."""
        order = an_interruption(session, unit, code="OT-INT-1")

        event = oms_adapter.enqueue_interruption_report(session, unit, order)
        assert event is not None
        base = interruptions.collect(
            session, unit.id, since=NOW - timedelta(days=1), until=NOW + timedelta(days=1)
        )

        exported = base.rows[0]
        assert event.payload["computable"] is exported.computable
        assert event.payload["threshold_seconds"] == exported.threshold_seconds
        assert event.payload["threshold_norm"] == exported.threshold_norm
        assert event.payload["restoration_hours"] == exported.duration_hours
        assert event.payload["kva_affected"] == exported.kva

    def test_rf_123_una_interrupcion_corta_se_reporta_como_no_computable(
        self, session: Session, unit: BusinessUnit, threshold: None
    ) -> None:
        """Clasificada, no escondida: ocurrió, y el OMS tiene que saber que ocurrió."""
        order = an_interruption(session, unit, code="OT-INT-CORTA", seconds=60)

        event = oms_adapter.enqueue_interruption_report(session, unit, order)

        assert event is not None
        assert event.payload["computable"] is False
        assert event.payload["restoration_hours"] is not None

    def test_rf_123_sin_umbral_cargado_el_informe_dice_que_no_pudo_clasificar(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        """Nulo y no `false`: «no se pudo clasificar» y «no es computable» son cosas distintas."""
        order = an_interruption(session, unit, code="OT-INT-1")

        event = oms_adapter.enqueue_interruption_report(session, unit, order)

        assert event is not None
        assert event.payload["computable"] is None
        assert event.payload["threshold_seconds"] is None

    def test_rf_123_el_informe_no_lleva_indices(
        self, session: Session, unit: BusinessUnit, threshold: None
    ) -> None:
        """El denominador de FMIK y TTIK es el kVA instalado de la unidad, y no vive aquí."""
        order = an_interruption(session, unit, code="OT-INT-1")

        event = oms_adapter.enqueue_interruption_report(session, unit, order)

        assert event is not None
        assert event.payload["indices"] is None

    def test_rf_123_la_correspondencia_cim_esta_declarada_con_sus_limites(
        self, session: Session, unit: BusinessUnit, threshold: None
    ) -> None:
        """«Cuando sea posible»: las inequívocas van, y el resto se dice en palabras."""
        order = an_interruption(session, unit, code="OT-INT-1")

        event = oms_adapter.enqueue_interruption_report(session, unit, order)

        assert event is not None
        cim = event.payload["cim"]
        assert cim["fields"]["OutageRecord.cause"] == "descarga_atmosferica"
        assert "perfil del OMS" in cim["note"]

    def test_rf_123_reaprobar_actualiza_el_informe_en_vez_de_mandar_dos(
        self, session: Session, unit: BusinessUnit, threshold: None
    ) -> None:
        order = an_interruption(session, unit, code="OT-INT-1")

        oms_adapter.enqueue_interruption_report(session, unit, order)
        oms_adapter.enqueue_interruption_report(session, unit, order)

        assert len(reports(session)) == 1

    def test_rf_123_una_correccion_despues_de_una_devolucion_actualiza_lo_que_verá_el_oms(
        self, session: Session, unit: BusinessUnit, threshold: None
    ) -> None:
        """El informe pendiente lleva la última verdad, no la primera."""
        order = an_interruption(session, unit, code="OT-INT-1")
        oms_adapter.enqueue_interruption_report(session, unit, order)

        response = session.execute(
            select(FormResponse).where(FormResponse.work_order_id == order.id)
        ).scalar_one()
        # La corrección realista cambia también la hora de reposición, y con ella la duración. Es
        # el caso que importa: si la clave de idempotencia dependiera de un valor corregible, una
        # corrección le mandaría al OMS una **segunda** interrupción por el mismo evento.
        response.answers = {
            **response.answers,
            "interruption_cause": "vegetacion",
            "interruption_seconds": 7200,
            "restored_at_interruption": (START + timedelta(seconds=7200)).isoformat(),
        }
        session.flush()
        oms_adapter.enqueue_interruption_report(session, unit, order)

        assert len(reports(session)) == 1
        assert reports(session)[0].payload["cause"] == "vegetacion"
        assert reports(session)[0].payload["restoration_hours"] == 2.0


class TestDelivery:
    def test_rf_123_el_informe_llega_al_endpoint_de_interrupciones(
        self, session: Session, unit: BusinessUnit, threshold: None
    ) -> None:
        order = an_interruption(session, unit, code="OT-INT-1")
        oms_adapter.enqueue_interruption_report(session, unit, order)
        transport = RecordingTransport(
            default=Response(200, {"accepted": True, "outage_record_id": "OR-000001"})
        )

        deliver_one(session, reports(session)[0], transport=transport, base_url=BASE)

        assert [url for _method, url, _payload in transport.calls] == [f"{BASE}/outages"]
        assert reports(session)[0].status == EventStatus.DELIVERED
        assert reports(session)[0].response["outage_record_id"] == "OR-000001"

    def test_rf_123_el_worker_entrega_los_informes_del_oms(
        self, session: Session, unit: BusinessUnit, threshold: None
    ) -> None:
        order = an_interruption(session, unit, code="OT-INT-1")
        oms_adapter.enqueue_interruption_report(session, unit, order)

        report = run_once(
            session,
            unit,
            transport=RecordingTransport(default=Response(200, {"accepted": True})),
            urls={Connector.OMS.value: BASE},
        )

        assert report.delivered == 1

    def test_rf_123_hasta_que_se_entrega_el_pendiente_no_baja(
        self, session: Session, unit: BusinessUnit, threshold: None
    ) -> None:
        """«Se reflejó en el OMS» es el criterio, y este número es cómo una persona lo nota."""
        order = an_interruption(session, unit, code="OT-INT-1")
        oms_adapter.enqueue_interruption_report(session, unit, order)
        assert oms_adapter.pending_reports(session, unit) == 1
        assert oms_adapter.reported_at(session, order) is None

        run_once(
            session,
            unit,
            transport=RecordingTransport(default=Response(200, {"accepted": True})),
            urls={Connector.OMS.value: BASE},
        )

        assert oms_adapter.pending_reports(session, unit) == 0
        assert oms_adapter.reported_at(session, order) is not None

    def test_rf_123_un_tipo_que_el_adaptador_no_conoce_falla_sin_reintentos(
        self, session: Session, unit: BusinessUnit
    ) -> None:
        from app.integrations.service import publish

        event = publish(
            session,
            unit,
            connector=Connector.OMS,
            direction=Direction.INBOUND,
            kind=EventKind.FAULT_EVENT_RECEIVED,
            idempotency_key="raro",
            payload={},
        )

        deliver_one(session, event, transport=RecordingTransport(), base_url=BASE)

        assert event.status == EventStatus.FAILED
        assert event.needs_attention is True
