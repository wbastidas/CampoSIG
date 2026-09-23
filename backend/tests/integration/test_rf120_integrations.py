"""Integraciones corporativas (RF-120, RF-124, RF-125).

Dos clases de prueba, a propósito:

* con un transporte guionado, para ejercer todo lo que pasa cuando el otro sistema falla —que
  es la mitad del trabajo de una integración y la que nunca se puede provocar a voluntad
  contra un servidor real;
* **contra los simuladores de verdad**, levantados en el propio test, que es el criterio de
  aceptación de I8: "pruebas de contrato contra los simuladores".
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.gis_gateway.ingest import ingest_metadata
from app.integrations import callcentre_adapter, workorder_adapter
from app.integrations.models import Connector, Direction, EventKind, EventStatus
from app.integrations.service import (
    MAX_ATTEMPTS,
    abandon,
    backoff_for,
    connector_health,
    due_events,
    ledger,
    mark_delivered,
    mark_failed,
    publish,
    retry_now,
)
from app.integrations.transport import HttpTransport, RecordingTransport, Response, TransportError
from app.org.models import BusinessUnit, Organization
from app.responses.models import EvidenceStage, FormResponse
from app.responses.service import register_evidence, save_answers
from app.review.models import Decision
from app.review.service import decide
from app.workorders.models import WorkOrder, WorkOrderSource, WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[3]


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


# --- el bus ---------------------------------------------------------------------------
class TestTheEventBus:
    def test_rf_125_publishing_writes_a_row_and_touches_no_network(self, session, unit) -> None:
        event = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.OUTBOUND,
            kind=EventKind.WORK_ORDER_STATUS,
            idempotency_key="estado:OT-1:aprobada",
            payload={"external_ref": "OT-1"},
        )
        assert event.status == EventStatus.PENDING
        assert event.attempts == 0
        assert event.next_attempt_at is not None

    def test_rf_125_the_same_key_never_produces_two_calls(self, session, unit) -> None:
        first = publish(
            session,
            unit,
            connector=Connector.CALL_CENTRE,
            direction=Direction.OUTBOUND,
            kind=EventKind.CLAIM_CLOSED,
            idempotency_key="cierre:REC-1",
            payload={"claim_id": "REC-1"},
        )
        second = publish(
            session,
            unit,
            connector=Connector.CALL_CENTRE,
            direction=Direction.OUTBOUND,
            kind=EventKind.CLAIM_CLOSED,
            idempotency_key="cierre:REC-1",
            payload={"claim_id": "REC-1", "resolution": "corregido"},
        )
        assert first.id == second.id
        # Todavía pendiente: se actualiza con la verdad más nueva.
        assert second.payload["resolution"] == "corregido"

    def test_rf_125_republishing_something_ya_entregado_no_lo_reenvia(self, session, unit) -> None:
        """Una operación de negocio reintentada no le cuenta dos veces lo mismo al otro lado."""
        event = publish(
            session,
            unit,
            connector=Connector.CALL_CENTRE,
            direction=Direction.OUTBOUND,
            kind=EventKind.CLAIM_CLOSED,
            idempotency_key="cierre:REC-2",
            payload={"claim_id": "REC-2"},
        )
        mark_delivered(session, event, {"accepted": True})
        again = publish(
            session,
            unit,
            connector=Connector.CALL_CENTRE,
            direction=Direction.OUTBOUND,
            kind=EventKind.CLAIM_CLOSED,
            idempotency_key="cierre:REC-2",
            payload={"claim_id": "REC-2"},
        )
        assert again.status == EventStatus.DELIVERED
        assert again.attempts == 1

    def test_rf_125_a_retryable_failure_backs_off(self, session, unit) -> None:
        event = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.OUTBOUND,
            kind=EventKind.WORK_ORDER_STATUS,
            idempotency_key="estado:OT-9:aprobada",
        )
        mark_failed(session, event, TransportError("503", retryable=True))
        assert event.status == EventStatus.PENDING
        assert event.attempts == 1
        assert event.next_attempt_at is not None
        assert event.next_attempt_at > datetime.now(UTC)

    def test_rf_125_a_non_retryable_failure_stops_at_once(self, session, unit) -> None:
        """Un 400 significa que la petición está mal; mandarla cuatro veces más no la arregla."""
        event = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.OUTBOUND,
            kind=EventKind.WORK_ORDER_STATUS,
            idempotency_key="estado:OT-8:aprobada",
        )
        mark_failed(session, event, TransportError("400 bad request", retryable=False))
        assert event.status == EventStatus.FAILED
        assert event.attempts == 1
        assert event.next_attempt_at is None

    def test_rf_125_retries_stop_and_wait_for_a_person(self, session, unit) -> None:
        event = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.OUTBOUND,
            kind=EventKind.WORK_ORDER_STATUS,
            idempotency_key="estado:OT-7:aprobada",
        )
        for _ in range(MAX_ATTEMPTS):
            mark_failed(session, event, TransportError("503", retryable=True))
        assert event.status == EventStatus.FAILED
        assert event.needs_attention

    def test_rf_125_a_person_can_retry_and_the_counter_resets(self, session, unit) -> None:
        event = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.OUTBOUND,
            kind=EventKind.WORK_ORDER_STATUS,
            idempotency_key="estado:OT-6:aprobada",
        )
        for _ in range(MAX_ATTEMPTS):
            mark_failed(session, event, TransportError("503"))
        retry_now(session, event, by="soporte.1")
        assert event.status == EventStatus.PENDING
        assert event.attempts == 0
        assert "soporte.1" in (event.last_error or "")

    def test_rf_125_abandoning_keeps_the_record(self, session, unit) -> None:
        """Borrarlo sería la misma decisión sin la evidencia."""
        event = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.OUTBOUND,
            kind=EventKind.WORK_ORDER_STATUS,
            idempotency_key="estado:OT-5:aprobada",
        )
        abandon(session, event, reason="la OT se anuló en el sistema origen", by="soporte.1")
        assert event.status == EventStatus.ABANDONED
        assert "se anuló" in (event.last_error or "")
        assert ledger(session, unit)

    def test_rf_125_only_due_events_are_picked_up(self, session, unit) -> None:
        soon = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.OUTBOUND,
            kind=EventKind.WORK_ORDER_STATUS,
            idempotency_key="estado:OT-4:aprobada",
        )
        later = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.OUTBOUND,
            kind=EventKind.WORK_ORDER_STATUS,
            idempotency_key="estado:OT-3:aprobada",
        )
        later.next_attempt_at = datetime.now(UTC) + timedelta(hours=1)
        session.flush()
        due = due_events(session, unit)
        assert [row.id for row in due] == [soon.id]

    def test_rf_002_the_ledger_is_scoped_to_the_unit(self, session, unit) -> None:
        org = session.query(Organization).first()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        publish(
            session,
            other,
            connector=Connector.CALL_CENTRE,
            direction=Direction.OUTBOUND,
            kind=EventKind.CLAIM_CLOSED,
            idempotency_key="cierre:AJENO",
        )
        assert ledger(session, unit) == []

    def test_rf_125_connector_health_counts_what_needs_a_person(self, session, unit) -> None:
        failed = publish(
            session,
            unit,
            connector=Connector.CALL_CENTRE,
            direction=Direction.OUTBOUND,
            kind=EventKind.CLAIM_CLOSED,
            idempotency_key="cierre:REC-3",
        )
        mark_failed(session, failed, TransportError("400", retryable=False))
        health = {row["connector"]: row for row in connector_health(session, unit)}
        assert health[Connector.CALL_CENTRE.value]["waiting_for_a_person"] == 1
        assert health[Connector.WORK_ORDER_SYSTEM.value]["waiting_for_a_person"] == 0

    def test_the_backoff_is_bounded(self) -> None:
        assert backoff_for(0) < backoff_for(2) < backoff_for(4)
        assert backoff_for(99) == backoff_for(50)


# --- adaptador de OT con transporte guionado ------------------------------------------
class TestWorkOrderAdapter:
    def test_rf_120_importing_creates_the_missing_orders(self, session, unit) -> None:
        transport = RecordingTransport()
        transport.script(
            "GET",
            "http://ot/work-orders",
            Response(
                200,
                {
                    "items": [
                        {"external_ref": "OT-1", "type": "inspeccion_preventiva"},
                        {"external_ref": "OT-2", "type": "atencion_falla", "priority": "alta"},
                    ]
                },
            ),
        )
        summary = workorder_adapter.import_work_orders(
            session, unit, transport, base_url="http://ot"
        )
        assert summary["created"] == ["OT-1", "OT-2"]
        orders = session.query(WorkOrder).all()
        assert {o.external_ref for o in orders} == {"OT-1", "OT-2"}
        assert all(o.source == WorkOrderSource.EXTERNAL_SYSTEM for o in orders)

    def test_rf_120_importing_twice_creates_nothing_new(self, session, unit) -> None:
        """El sistema corporativo reenvía; una OT duplicada es una cuadrilla de más."""
        transport = RecordingTransport()
        transport.script(
            "GET",
            "http://ot/work-orders",
            Response(200, {"items": [{"external_ref": "OT-1", "type": "inspeccion_preventiva"}]}),
        )
        workorder_adapter.import_work_orders(session, unit, transport, base_url="http://ot")
        second = workorder_adapter.import_work_orders(
            session, unit, transport, base_url="http://ot"
        )
        assert second["created"] == []
        assert second["already_known"] == ["OT-1"]
        assert session.query(WorkOrder).count() == 1

    def test_rf_120_an_incomplete_item_is_rejected_with_a_reason(self, session, unit) -> None:
        transport = RecordingTransport()
        transport.script(
            "GET",
            "http://ot/work-orders",
            Response(200, {"items": [{"external_ref": "OT-9"}]}),
        )
        summary = workorder_adapter.import_work_orders(
            session, unit, transport, base_url="http://ot"
        )
        assert summary["created"] == []
        assert "type" in summary["rejected"][0]["reason"]
        assert session.query(WorkOrder).count() == 0

    def test_rf_125_an_import_that_could_not_happen_is_logged(self, session, unit) -> None:
        transport = RecordingTransport()
        transport.script("GET", "http://ot/work-orders", TransportError("no se pudo conectar"))
        with pytest.raises(TransportError):
            workorder_adapter.import_work_orders(session, unit, transport, base_url="http://ot")
        rows = ledger(session, unit, connector=Connector.WORK_ORDER_SYSTEM)
        assert rows and rows[0].status == EventStatus.PENDING
        assert "no se pudo conectar" in (rows[0].last_error or "")

    def test_rf_120_an_order_the_other_system_never_sent_is_not_reported(
        self, session, unit
    ) -> None:
        order = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            longitude=-79.9,
            latitude=-2.17,
        )
        assert workorder_adapter.enqueue_status_push(session, unit, order) is None

    def test_rf_120_each_state_is_reported_once(self, session, unit) -> None:
        order = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            asset_type_key="support_structure",
            longitude=-79.9,
            latitude=-2.17,
            external_ref="OT-77",
            source=WorkOrderSource.EXTERNAL_SYSTEM,
        )
        first = workorder_adapter.enqueue_status_push(session, unit, order, state="asignada")
        again = workorder_adapter.enqueue_status_push(session, unit, order, state="asignada")
        other = workorder_adapter.enqueue_status_push(session, unit, order, state="aprobada")
        assert first is not None and again is not None and other is not None
        assert first.id == again.id
        assert other.id != first.id

    def test_rf_120_delivering_an_unknown_kind_fails_without_retrying(self, session, unit) -> None:
        event = publish(
            session,
            unit,
            connector=Connector.WORK_ORDER_SYSTEM,
            direction=Direction.OUTBOUND,
            kind="algo_que_nadie_implemento",
            idempotency_key="raro:1",
        )
        workorder_adapter.deliver(session, event, RecordingTransport(), base_url="http://ot")
        assert event.status == EventStatus.FAILED
        assert event.next_attempt_at is None


# --- adaptador de call center ---------------------------------------------------------
class TestCallCentreAdapter:
    def test_rf_124_a_claim_becomes_a_work_order(self, session, unit) -> None:
        transport = RecordingTransport()
        transport.script(
            "GET",
            "http://cc/claims",
            Response(
                200,
                {
                    "items": [
                        {
                            "claim_id": "REC-1",
                            "kind": "luminaria_apagada",
                            "priority": "alta",
                            "address": "Av. Principal",
                            "asset_code": "L-1",
                        }
                    ]
                },
            ),
        )
        summary = callcentre_adapter.import_claims(session, unit, transport, base_url="http://cc")
        assert summary["created"] == ["REC-1"]
        order = session.query(WorkOrder).one()
        assert order.source == WorkOrderSource.CALL_CENTER
        assert order.form_code == "F-AP-01"
        assert order.external_ref == "REC-1"

    def test_rf_124_the_same_claim_never_sends_two_crews(self, session, unit) -> None:
        transport = RecordingTransport()
        transport.script(
            "GET",
            "http://cc/claims",
            Response(200, {"items": [{"claim_id": "REC-1", "kind": "sin_servicio"}]}),
        )
        callcentre_adapter.import_claims(session, unit, transport, base_url="http://cc")
        callcentre_adapter.import_claims(session, unit, transport, base_url="http://cc")
        assert session.query(WorkOrder).count() == 1

    def test_rf_124_an_unrouted_claim_kind_is_refused_not_guessed(self, session, unit) -> None:
        transport = RecordingTransport()
        transport.script(
            "GET",
            "http://cc/claims",
            Response(200, {"items": [{"claim_id": "REC-5", "kind": "algo_nuevo"}]}),
        )
        summary = callcentre_adapter.import_claims(session, unit, transport, base_url="http://cc")
        assert summary["created"] == []
        assert "no está enrutado" in summary["rejected"][0]["reason"]


# --- el bucle completo ---------------------------------------------------------------
class TestApprovalClosesTheClaim:
    def _claim_order(self, session, unit) -> WorkOrder:
        transport = RecordingTransport()
        transport.script(
            "GET",
            "http://cc/claims",
            Response(
                200,
                {
                    "items": [
                        {"claim_id": "REC-77", "kind": "luminaria_apagada", "priority": "alta"}
                    ]
                },
            ),
        )
        callcentre_adapter.import_claims(session, unit, transport, base_url="http://cc")
        order = session.query(WorkOrder).one()
        order.state = WorkOrderState.SYNCED
        order.form_version = "1.0.0"
        session.flush()
        return order

    def test_rf_124_approving_queues_the_closure_in_the_same_transaction(
        self, session, unit
    ) -> None:
        """Lo que se rompe si esto es un efecto secundario: el reclamo queda abierto."""
        order = self._claim_order(session, unit)
        save_answers(
            session,
            unit,
            order,
            answers={
                "work_order_code": "OT-1",
                "work_type": "luminaria_falla",
                "priority": "alta",
                "gps": {"latitude": -2.17, "longitude": -79.9, "accuracy_m": 4.0},
                "activities": [
                    {
                        "activity_code": "REEMPLAZO_LUMINARIA",
                        "quantity": 1,
                        "note": "reemplazo de módulo",
                    }
                ],
                "reported_failure": "apagada_de_noche",
                "cause_found": "lampara_o_modulo",
                "operative_at_close": True,
                # F-AP-01 lleva ahora el bloque de atributos del activo (B05), así que el
                # formulario pide identificar la luminaria y su tecnología: es lo que permite
                # medir la modernización a LED (RF-131) y llevar el censo.
                "code": "LUM-000123",
                "feeder_code": "04BH070T11",
                "technology": "led",
                "final_state": "resuelto",
                "photos_before": ["s3://a.jpg"],
                "photos_after": ["s3://b.jpg"],
                "summary": "se reemplazó el módulo LED",
            },
            submit=True,
        )
        response = session.query(FormResponse).one()
        for stage in (EvidenceStage.BEFORE, EvidenceStage.AFTER):
            register_evidence(
                session,
                response,
                kind="foto",
                storage_key=f"s3://{stage.value}.jpg",
                content_hash=hashlib.sha256(stage.value.encode()).hexdigest(),
                stage=stage,
            )

        decide(session, unit, order, decision=Decision.APPROVED, reviewer_sub="supervisor.1")

        closures = ledger(session, unit, connector=Connector.CALL_CENTRE)
        assert [row.kind for row in closures if row.direction == Direction.OUTBOUND] == [
            EventKind.CLAIM_CLOSED
        ]
        closure = next(row for row in closures if row.kind == EventKind.CLAIM_CLOSED)
        assert closure.payload["claim_id"] == "REC-77"
        assert closure.status == EventStatus.PENDING

        # Y el resultado va también al sistema de OT, porque la OT trae referencia externa.
        ot_events = ledger(session, unit, connector=Connector.WORK_ORDER_SYSTEM)
        assert {row.kind for row in ot_events if row.direction == Direction.OUTBOUND} == {
            EventKind.WORK_ORDER_STATUS,
            EventKind.WORK_ORDER_RESULT,
        }
        result = next(row for row in ot_events if row.kind == EventKind.WORK_ORDER_RESULT)
        assert result.payload["summary"] == "se reemplazó el módulo LED"
        assert result.payload["evidence"]


# --- contrato contra los simuladores de verdad ---------------------------------------
def _wait_for(url: str, *, attempts: int = 60) -> bool:
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=0.5) as raw:
                if raw.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.1)
    return False


class MockServer:
    """Runs one of the `tools/*-mock` servers for the duration of a test."""

    def __init__(self, script: Path, port: int) -> None:
        self.script = script
        self.port = port
        self.process: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> str:
        self.process = subprocess.Popen(
            [sys.executable, str(self.script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        base = f"http://127.0.0.1:{self.port}"
        if not _wait_for(f"{base}/health"):
            self.__exit__(None, None, None)
            pytest.skip(f"el simulador en {base} no arrancó")
        return base

    def __exit__(self, *_: object) -> None:
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                self.process.kill()


class TestContractAgainstTheRealMocks:
    """El criterio de aceptación de I8: pruebas de contrato contra los simuladores."""

    def test_rf_120_import_and_status_round_trip(self, session, unit) -> None:
        script = REPO_ROOT / "tools" / "legacy-ot-mock" / "app.py"
        with MockServer(script, 8182) as base_url:
            transport = HttpTransport()
            summary = workorder_adapter.import_work_orders(
                session, unit, transport, base_url=base_url
            )
            assert summary["created"] == ["OT-2026-000101", "OT-2026-000102"]

            order = session.query(WorkOrder).filter_by(external_ref="OT-2026-000101").one()
            event = workorder_adapter.enqueue_status_push(session, unit, order, state="aprobada")
            assert event is not None
            workorder_adapter.deliver(session, event, transport, base_url=base_url)
            assert event.status == EventStatus.DELIVERED
            assert event.response["external_ref"] == "OT-2026-000101"

            # Y el simulador lo recibió de verdad, que es lo que hace que esto sea un
            # contrato y no un mock de nosotros mismos.
            with urllib.request.urlopen(f"{base_url}/received-statuses") as raw:
                import json

                received = json.loads(raw.read())
            assert any(item["external_ref"] == "OT-2026-000101" for item in received["items"])

    def test_rf_124_claim_to_work_order_to_closure(self, session, unit) -> None:
        script = REPO_ROOT / "tools" / "call-centre-mock" / "app.py"
        with MockServer(script, 8183) as base_url:
            transport = HttpTransport()
            summary = callcentre_adapter.import_claims(session, unit, transport, base_url=base_url)
            assert summary["created"] == ["REC-2026-004411", "REC-2026-004412"]

            order = session.query(WorkOrder).filter_by(external_ref="REC-2026-004411").one()
            event = callcentre_adapter.enqueue_claim_closure(
                session, unit, order, summary="módulo LED reemplazado"
            )
            assert event is not None
            callcentre_adapter.deliver(session, event, transport, base_url=base_url)
            assert event.status == EventStatus.DELIVERED
            assert event.response["status"] == "closed"

            # El reclamo ya no está abierto en el otro sistema.
            with urllib.request.urlopen(f"{base_url}/claims") as raw:
                import json

                still_open = json.loads(raw.read())
            assert all(item["claim_id"] != "REC-2026-004411" for item in still_open["items"])

    def test_rf_125_closing_a_claim_that_does_not_exist_is_not_retried(self, session, unit) -> None:
        """Un 404 del otro lado no se arregla reintentando; se manda a la pantalla."""
        script = REPO_ROOT / "tools" / "call-centre-mock" / "app.py"
        with MockServer(script, 8183) as base_url:
            order = create_work_order(
                session,
                unit,
                work_type="luminaria_falla",
                form_code="F-AP-01",
                asset_type_key="street_light",
                longitude=-79.9,
                latitude=-2.17,
                external_ref="REC-INEXISTENTE",
                source=WorkOrderSource.CALL_CENTER,
            )
            event = callcentre_adapter.enqueue_claim_closure(session, unit, order)
            assert event is not None
            callcentre_adapter.deliver(session, event, HttpTransport(), base_url=base_url)
            assert event.status == EventStatus.FAILED
            assert event.next_attempt_at is None
            assert "404" in (event.last_error or "")
