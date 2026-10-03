"""El worker que drena el outbox (RF-125, ADR-012).

Tres propiedades tienen test porque cada una es una forma de perder o duplicar un intercambio:

* **una transacción por evento** — si el worker muere a mitad, lo entregado queda entregado y el
  resto intacto; una transacción alrededor del lote reenviaría todo tras un reinicio;
* **un conector roto no detiene a los otros** — un call center en mantenimiento no debe retener
  los estados de OT;
* **un conector sin configurar no consume reintentos** — todavía no está desplegado, y quemarle
  los intentos contra una cadena vacía los desperdicia.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.integrations.models import Connector, Direction, EventKind, EventStatus
from app.integrations.service import ledger, publish
from app.integrations.transport import RecordingTransport, Response, TransportError
from app.org.models import BusinessUnit, Organization
from app.workers.integration_delivery import DeliveryReport, connector_urls, run_once

pytestmark = pytest.mark.integration

URLS = {
    Connector.WORK_ORDER_SYSTEM.value: "http://ot",
    Connector.CALL_CENTRE.value: "http://cc",
    Connector.GIS.value: "",
}


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
    return created


def queue_status(session: Session, unit: BusinessUnit, key: str):
    return publish(
        session,
        unit,
        connector=Connector.WORK_ORDER_SYSTEM,
        direction=Direction.OUTBOUND,
        kind=EventKind.WORK_ORDER_STATUS,
        idempotency_key=key,
        payload={"external_ref": key, "status": "aprobada"},
    )


def queue_closure(session: Session, unit: BusinessUnit, key: str):
    return publish(
        session,
        unit,
        connector=Connector.CALL_CENTRE,
        direction=Direction.OUTBOUND,
        kind=EventKind.CLAIM_CLOSED,
        idempotency_key=key,
        payload={"claim_id": key},
    )


class TestOnePass:
    def test_rf_125_it_delivers_what_is_due(self, session, unit) -> None:
        queue_status(session, unit, "estado:OT-1:aprobada")
        queue_closure(session, unit, "cierre:REC-1")

        transport = RecordingTransport(default=Response(200, {"accepted": True}))
        report = run_once(session, unit, transport=transport, urls=URLS)

        assert report.delivered == 2
        assert report.failed == 0
        assert {row.status for row in ledger(session, unit)} == {EventStatus.DELIVERED}

    def test_rf_125_nothing_due_is_not_an_error(self, session, unit) -> None:
        report = run_once(session, unit, transport=RecordingTransport(), urls=URLS)
        assert report == DeliveryReport()

    def test_rf_125_a_broken_connector_does_not_stop_the_others(self, session, unit) -> None:
        """Un call center en mantenimiento no debe retener los estados de OT."""
        queue_status(session, unit, "estado:OT-2:aprobada")
        queue_closure(session, unit, "cierre:REC-2")

        transport = RecordingTransport()
        transport.script("POST", "http://ot/work-orders/status", Response(200, {"accepted": True}))
        transport.script("POST", "http://cc/claims/close", TransportError("503", retryable=True))

        report = run_once(session, unit, transport=transport, urls=URLS)
        assert report.delivered == 1
        assert report.failed == 1

        by_connector = {row.connector: row.status for row in ledger(session, unit)}
        assert by_connector[Connector.WORK_ORDER_SYSTEM.value] == EventStatus.DELIVERED
        assert by_connector[Connector.CALL_CENTRE.value] == EventStatus.PENDING

    def test_rf_125_an_unconfigured_connector_does_not_burn_retries(self, session, unit) -> None:
        """Un conector que no está desplegado no es un error."""
        queue_closure(session, unit, "cierre:REC-3")
        report = run_once(
            session,
            unit,
            transport=RecordingTransport(),
            urls={Connector.WORK_ORDER_SYSTEM.value: "http://ot"},
        )
        assert report.skipped == 1
        assert report.attempted == 0
        assert Connector.CALL_CENTRE.value in report.unconfigured

        event = ledger(session, unit)[0]
        assert event.status == EventStatus.PENDING
        assert event.attempts == 0

    def test_rf_125_an_adapter_that_raises_is_recorded_not_propagated(self, session, unit) -> None:
        """Un adaptador que lanza en vez de registrar es un defecto; el pase sigue."""
        queue_status(session, unit, "estado:OT-4:aprobada")

        class Exploding:
            def get(self, url: str, *, timeout: float = 10.0) -> Response:
                raise RuntimeError("algo inesperado")

            def post(self, url: str, payload: dict, *, timeout: float = 10.0) -> Response:
                raise RuntimeError("algo inesperado")

        report = run_once(session, unit, transport=Exploding(), urls=URLS)
        assert report.failed == 1
        assert "inesperado" in (ledger(session, unit)[0].last_error or "")

    def test_rf_125_the_batch_is_bounded(self, session, unit) -> None:
        for index in range(5):
            queue_status(session, unit, f"estado:OT-{index}:aprobada")
        transport = RecordingTransport(default=Response(200, {"accepted": True}))
        report = run_once(session, unit, transport=transport, urls=URLS, limit=2)
        assert report.delivered == 2
        pending = [r for r in ledger(session, unit) if r.status == EventStatus.PENDING]
        assert len(pending) == 3

    def test_rf_125_a_connector_with_no_adapter_fails_without_retrying(self, session, unit) -> None:
        publish(
            session,
            unit,
            connector=Connector.GIS,
            direction=Direction.OUTBOUND,
            kind="algo",
            idempotency_key="gis:1",
        )
        report = run_once(
            session,
            unit,
            transport=RecordingTransport(),
            urls={**URLS, Connector.GIS.value: "http://gis"},
        )
        assert report.failed == 1
        event = ledger(session, unit)[0]
        assert event.status == EventStatus.FAILED
        assert event.next_attempt_at is None

    def test_rf_002_a_pass_scoped_to_a_unit_leaves_the_others_alone(self, session, unit) -> None:
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        queue_closure(session, other, "cierre:AJENO")
        queue_status(session, unit, "estado:OT-5:aprobada")

        transport = RecordingTransport(default=Response(200, {"accepted": True}))
        report = run_once(session, unit, transport=transport, urls=URLS)

        assert report.delivered == 1
        assert ledger(session, other)[0].status == EventStatus.PENDING

    def test_rf_125_a_pass_over_every_unit_drains_all_of_them(self, session, unit) -> None:
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        queue_closure(session, other, "cierre:OTRA")
        queue_status(session, unit, "estado:OT-6:aprobada")

        transport = RecordingTransport(default=Response(200, {"accepted": True}))
        report = run_once(session, None, transport=transport, urls=URLS)
        assert report.delivered == 2


class TestConfiguration:
    def test_an_unset_connector_reads_as_unconfigured(self) -> None:
        """Y no como una URL rara: la cadena vacía es explícitamente "no desplegado"."""
        assert connector_urls()[Connector.CALL_CENTRE.value] == ""

    def test_the_gis_is_never_reached_over_http(self) -> None:
        """El agente arcpy tira de sus lotes; nadie le empuja nada (ADR-008)."""
        assert connector_urls()[Connector.GIS.value] == ""
