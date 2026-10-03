"""Times per milestone, spontaneous findings and the order's owner (RF-047, RF-049, RF-312).

* RF-047 — «registro de tiempos automático por transición (EnCamino, EnSitio, inicio, fin) con
  posibilidad de corrección justificada»: «una edición manual del tiempo guarda el original y el
  motivo». Until now the only time was the server's, recorded whenever the phone happened to sync.
* RF-049 — «crear hallazgos o trabajos nuevos desde el campo, aunque no exista una OT»: «genera una
  propuesta de OT con GPS y fotos». Every push operation required an order, so this could not exist.
* RF-312 — «dueño explícito de cada OT (`planner_id`) y bitácora de traspasos». The owner existed;
  changing it did not.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit
from app.proposals.models import ProposalOrigin, WorkOrderProposal
from app.proposals.service import SpontaneousFindingError, raise_spontaneous
from app.sync.models import Device
from app.workorders.models import WorkOrderMilestone, WorkOrderState
from app.workorders.service import (
    MilestoneError,
    OwnershipError,
    correct_milestone,
    milestones_of,
    ownership_history,
    transfer_ownership,
    transition,
)
from tests.integration.test_rf102_sync_api import (
    PLANNER,
    TECHNICIAN,
    an_order,
    operation,
    push,
)
from tests.integration.test_rf102_sync_api import client as client
from tests.integration.test_rf102_sync_api import device as device
from tests.integration.test_rf102_sync_api import unit as unit
from tests.integration.test_rf102_sync_api import units as units

pytestmark = pytest.mark.integration

ON_SITE_AT = datetime(2026, 10, 1, 14, 5, tzinfo=UTC)
PHOTO = {"storage_key": "GYE/evidencia/foto/hallazgo.jpg", "content_hash": "c" * 64}

SUPERVISOR = Principal(
    subject="kc|supervisor",
    username="supervisor",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE"}),
)


def office(session: Session, who: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: who
    return TestClient(app)


def walk_to_site(client: TestClient, order: Any) -> None:
    push(
        client,
        operation("transition", order, target="descargada"),
        operation("transition", order, target="en_camino", occurred_at="2026-10-01T13:30:00+00:00"),
        operation("transition", order, target="en_sitio", occurred_at=ON_SITE_AT.isoformat()),
    )


class TestRf047Milestones:
    def test_a_device_transition_records_the_phones_time(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        order = an_order(session, unit)
        walk_to_site(client, order)
        rows = {row.milestone: row for row in milestones_of(session, order)}
        assert list(rows) == ["en_camino", "en_sitio"]
        assert rows["en_sitio"].device_time == ON_SITE_AT
        assert rows["en_sitio"].recorded_by == TECHNICIAN.subject
        assert rows["en_sitio"].effective_time == ON_SITE_AT

    def test_the_trail_carries_the_device_time_too(self, session: Session, unit, device, client):
        order = an_order(session, unit)
        walk_to_site(client, order)
        event = session.scalars(
            select(AuditEvent).where(
                AuditEvent.kind == "transicion", AuditEvent.payload["to"].astext == "en_sitio"
            )
        ).one()
        assert event.payload["device_time"] == ON_SITE_AT.isoformat()

    def test_a_resumed_job_does_not_restart_its_clock(self, session: Session, unit):
        order = an_order(session, unit, state=WorkOrderState.ON_SITE)
        first = datetime(2026, 10, 1, 15, 0, tzinfo=UTC)
        transition(session, order, WorkOrderState.IN_EXECUTION, occurred_at=first)
        transition(session, order, WorkOrderState.SUSPENDED, reason="lluvia")
        transition(
            session, order, WorkOrderState.IN_EXECUTION, occurred_at=first + timedelta(hours=2)
        )
        started = [row for row in milestones_of(session, order) if row.milestone == "inicio"]
        assert len(started) == 1
        assert started[0].device_time == first

    def test_a_transition_without_a_device_time_still_records_the_server_one(
        self, session: Session, unit
    ):
        order = an_order(session, unit, state=WorkOrderState.ON_SITE)
        transition(session, order, WorkOrderState.IN_EXECUTION, actor="kc|x")
        row = milestones_of(session, order)[0]
        assert row.device_time is None
        assert row.effective_time == row.recorded_at

    def test_a_correction_keeps_the_original_and_the_reason(
        self, session: Session, unit, device, client
    ):
        order = an_order(session, unit)
        walk_to_site(client, order)
        corrected = ON_SITE_AT - timedelta(minutes=20)
        body = push(
            client,
            operation(
                "time_correction",
                order,
                milestone="en_sitio",
                corrected_time=corrected.isoformat(),
                reason="marqué en sitio al terminar de estacionar, llegué antes",
            ),
        ).json()
        assert body["accepted"] == 1
        row = session.scalars(
            select(WorkOrderMilestone).where(WorkOrderMilestone.milestone == "en_sitio")
        ).one()
        assert row.device_time == ON_SITE_AT  # the original, untouched
        assert row.corrected_time == corrected
        assert row.correction_reason.startswith("marqué en sitio")
        assert row.corrected_by == TECHNICIAN.subject
        assert row.effective_time == corrected
        event = session.scalars(
            select(AuditEvent).where(AuditEvent.payload["field"].astext == "hito:en_sitio")
        ).one()
        assert event.payload["from"] == ON_SITE_AT.isoformat()
        assert event.payload["to"] == corrected.isoformat()
        assert event.reason.startswith("marqué en sitio")

    def test_a_correction_without_reason_is_parked(self, session: Session, unit, device, client):
        order = an_order(session, unit)
        walk_to_site(client, order)
        body = push(
            client,
            operation(
                "time_correction",
                order,
                milestone="en_sitio",
                corrected_time=ON_SITE_AT.isoformat(),
                reason="",
            ),
        ).json()
        assert body["rejected"] == 1
        assert "motivo" in body["operations"][0]["rejection_reason"]

    @pytest.mark.parametrize(
        ("milestone", "when", "message"),
        [
            ("en_sitio", datetime.now(UTC) + timedelta(days=1), "futuro"),
            ("fin", ON_SITE_AT, "todavía no pasó"),
            ("almuerzo", ON_SITE_AT, "no es un hito"),
            ("en_sitio", datetime(2026, 10, 1, 9, 0), "zona horaria"),
        ],
    )
    def test_impossible_corrections_are_refused(
        self, session: Session, unit, device, client, milestone, when, message
    ):
        order = an_order(session, unit)
        walk_to_site(client, order)
        with pytest.raises(MilestoneError, match=message):
            correct_milestone(
                session, order, milestone, corrected_time=when, reason="x", actor="kc|y"
            )

    def test_the_office_reads_and_corrects_through_the_api(
        self, session: Session, unit, device, client
    ):
        order = an_order(session, unit)
        walk_to_site(client, order)
        with office(session, SUPERVISOR) as api:
            response = api.put(
                f"/api/v1/planning/work-orders/{order.id}/milestones/en_camino",
                params={"business_unit": "GYE"},
                json={
                    "corrected_time": "2026-10-01T13:10:00+00:00",
                    "reason": "el técnico olvidó marcar al salir",
                },
            )
            assert response.status_code == 200, response.text
            listed = api.get(
                f"/api/v1/planning/work-orders/{order.id}/milestones",
                params={"business_unit": "GYE"},
            ).json()
        assert [row["milestone"] for row in listed] == ["en_camino", "en_sitio"]
        assert listed[0]["device_time"] == "2026-10-01T13:30:00+00:00"
        assert listed[0]["effective_time"] == "2026-10-01T13:10:00+00:00"
        assert listed[0]["corrected_by"] == SUPERVISOR.subject

    def test_a_technician_cannot_correct_from_the_web(self, session: Session, unit, device, client):
        order = an_order(session, unit)
        walk_to_site(client, order)
        response = client.put(
            f"/api/v1/planning/work-orders/{order.id}/milestones/en_sitio",
            params={"business_unit": "GYE"},
            json={"corrected_time": ON_SITE_AT.isoformat(), "reason": "x"},
        )
        assert response.status_code == 403


class TestRf049SpontaneousFinding:
    def test_a_finding_without_an_order_becomes_a_proposal_with_gps_and_photos(
        self, session: Session, unit: BusinessUnit, device: Device, client: TestClient
    ) -> None:
        body = push(
            client,
            operation(
                "field_finding",
                None,
                defect_code="cruceta_rota",
                latitude=-2.18,
                longitude=-79.91,
                accuracy_m=6.0,
                asset_type_key="support_structure",
                description="cruceta partida en el poste de la esquina",
                photos=[PHOTO],
            ),
        ).json()
        assert body["accepted"] == 1, body
        result = body["operations"][0]["result"]
        assert result["created"] is True
        proposal = session.scalars(select(WorkOrderProposal)).one()
        assert proposal.origin == ProposalOrigin.SPONTANEOUS
        assert proposal.source_work_order_id is None
        assert proposal.location is not None
        assert proposal.findings[0]["photos"][0]["content_hash"] == "c" * 64
        assert proposal.findings[0]["reported_by"] == TECHNICIAN.subject
        assert "sin OT previa" in proposal.justification

    def test_without_gps_it_is_parked(self, session: Session, unit, device, client):
        body = push(
            client, operation("field_finding", None, defect_code="cruceta_rota", photos=[PHOTO])
        ).json()
        assert body["rejected"] == 1
        assert "GPS" in body["operations"][0]["rejection_reason"]

    def test_without_photos_it_is_parked(self, session: Session, unit, device, client):
        body = push(
            client,
            operation(
                "field_finding",
                None,
                defect_code="cruceta_rota",
                latitude=-2.18,
                longitude=-79.91,
                photos=[{"storage_key": "sin-hash.jpg"}],
            ),
        ).json()
        assert body["rejected"] == 1
        assert "foto" in body["operations"][0]["rejection_reason"]

    @pytest.mark.parametrize(("latitude", "longitude"), [(0.0, 0.0), (91.0, -79.0), (-2.0, -181.0)])
    def test_an_impossible_position_is_refused(self, session: Session, unit, latitude, longitude):
        with pytest.raises(SpontaneousFindingError, match="GPS"):
            raise_spontaneous(
                session,
                unit,
                defect_code="cruceta_rota",
                latitude=latitude,
                longitude=longitude,
                photos=[PHOTO],
                actor="kc|x",
            )

    def test_without_defect_it_is_refused(self, session: Session, unit):
        with pytest.raises(SpontaneousFindingError, match="defecto"):
            raise_spontaneous(
                session,
                unit,
                defect_code=" ",
                latitude=-2.1,
                longitude=-79.9,
                photos=[PHOTO],
                actor="kc|x",
            )

    def test_the_same_asset_and_defect_joins_the_open_proposal(self, session: Session, unit):
        first, created = raise_spontaneous(
            session,
            unit,
            defect_code="cruceta_rota",
            asset_code="P-000452",
            latitude=-2.18,
            longitude=-79.91,
            photos=[PHOTO],
            actor="kc|a",
        )
        second, joined = raise_spontaneous(
            session,
            unit,
            defect_code="cruceta_rota",
            asset_code="P-000452",
            latitude=-2.18,
            longitude=-79.91,
            photos=[{**PHOTO, "content_hash": "d" * 64}],
            actor="kc|b",
        )
        assert created is True and joined is False
        assert second.id == first.id
        assert [f["reported_by"] for f in second.findings] == ["kc|a", "kc|b"]
        assert session.scalars(select(WorkOrderProposal)).all() == [first]

    def test_it_is_on_the_trail(self, session: Session, unit, device, client):
        push(
            client,
            operation(
                "field_finding",
                None,
                defect_code="cruceta_rota",
                latitude=-2.18,
                longitude=-79.91,
                photos=[PHOTO],
            ),
        )
        event = session.scalars(
            select(AuditEvent).where(AuditEvent.subject_type == "work_order_proposal")
        ).one()
        assert event.actor == TECHNICIAN.subject
        assert event.payload["origin"] == "hallazgo_espontaneo"
        assert event.payload["photos"] == ["c" * 64]

    def test_other_kinds_still_need_their_order(self, session: Session, unit, device, client):
        body = push(client, operation("time_correction", None, milestone="fin")).json()
        assert body["rejected"] == 1
        assert "necesita la OT" in body["operations"][0]["rejection_reason"]


class TestRf312Owner:
    def test_a_transfer_changes_the_owner_and_is_on_the_bitacora(self, session: Session, unit):
        order = an_order(session, unit)
        transfer_ownership(
            session, order, to="kc|otra.planificadora", reason="vacaciones", actor="kc|jefe"
        )
        assert order.planner_id == "kc|otra.planificadora"
        history = ownership_history(session, order)
        assert history == [
            {
                "from": PLANNER.subject,
                "to": "kc|otra.planificadora",
                "by": "kc|jefe",
                "reason": "vacaciones",
                "at": history[0]["at"],
            }
        ]

    @pytest.mark.parametrize(
        ("to", "reason", "message"),
        [("", "x", "a quién"), ("kc|otra", "", "motivo"), (PLANNER.subject, "x", "ya es")],
    )
    def test_an_incomplete_transfer_is_refused(self, session: Session, unit, to, reason, message):
        order = an_order(session, unit)
        with pytest.raises(OwnershipError, match=message):
            transfer_ownership(session, order, to=to, reason=reason, actor="kc|jefe")

    def test_through_the_api(self, session: Session, unit):
        order = an_order(session, unit)
        with office(session, SUPERVISOR) as api:
            response = api.post(
                f"/api/v1/planning/work-orders/{order.id}/owner",
                params={"business_unit": "GYE"},
                json={"planner_id": "kc|nuevo", "reason": "reorganización de zonas"},
            )
            assert response.status_code == 200, response.text
            history = api.get(
                f"/api/v1/planning/work-orders/{order.id}/owner/history",
                params={"business_unit": "GYE"},
            ).json()
        assert history["planner_id"] == "kc|nuevo"
        assert [t["to"] for t in history["transfers"]] == ["kc|nuevo"]
        assert history["transfers"][0]["by"] == SUPERVISOR.subject

    def test_a_technician_cannot_transfer(self, session: Session, unit, device, client):
        order = an_order(session, unit)
        response = client.post(
            f"/api/v1/planning/work-orders/{order.id}/owner",
            params={"business_unit": "GYE"},
            json={"planner_id": "kc|yo", "reason": "x"},
        )
        assert response.status_code == 403
