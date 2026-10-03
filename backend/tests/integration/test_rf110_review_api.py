"""La API de revisión, vista como la ve la pantalla (M11, RF-110, RF-112, RF-342).

El detalle se arma en el servidor a propósito: una pantalla que tuviera que hacer seis llamadas
y combinarlas sería una pantalla donde una llamada fallida quita un impedimento de la vista sin
que nadie se entere. Así que lo que se prueba aquí es que el detalle traiga **todo** lo que la
decisión necesita, y que aprobar con condiciones pendientes falle con la lista de razones.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.regulatory.service import set_parameter
from app.responses.models import EvidenceStage, ValueOrigin
from app.responses.service import record_provenance, register_evidence, save_answers
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration


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


#: The supervisor these tests act as. Identity comes from the token in production; here the
#: dependency is overridden, because what this file tests is the endpoints, not authentication.
#: Authentication has its own file, which exercises the real dependency.
SUPERVISOR = Principal(
    subject="kc|supervisor.demo",
    username="supervisor.demo",
    display_name="Supervisor Demo",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE", "MAN"}),
)


@pytest.fixture
def client(session: Session):
    """A client sharing the test's transaction, so nothing it writes escapes the rollback."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: SUPERVISOR
    # The endpoints commit; inside the test's outer transaction that is a nested flush, so the
    # fixture's rollback still undoes everything.
    with TestClient(app) as raw:
        yield raw
    app.dependency_overrides.clear()


def full_answers() -> dict:
    return {
        "work_order_code": "OT-1",
        "work_type": "inspeccion_preventiva",
        "priority": "media",
        "gps": {"latitude": -2.17, "longitude": -79.9, "accuracy_m": 4.0},
        "general_condition": "regular",
        "code": "P-000452",
        "material": "concrete",
        "feeder_code": "04BH070T11",
        "height_m": 11.0,
        "final_state": "resuelto",
        # B04: el formulario exige ATS, así que la referencia es obligatoria.
        "ats_reference": "ATS-2026-0001",
        "photos_before": ["s3://a.jpg", "s3://b.jpg"],
        "photos_after": [],
    }


@pytest.fixture
def order(session: Session, unit: BusinessUnit):
    created = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        longitude=-79.9,
        latitude=-2.17,
        zone="Urbano",
        planner_id="planner.a",
    )
    created.state = WorkOrderState.SYNCED
    created.form_version = "1.0.0"
    session.flush()
    return created


def add_photos(session: Session, response, before: int = 2) -> None:
    for index in range(before):
        register_evidence(
            session,
            response,
            kind="foto",
            storage_key=f"s3://antes-{index}.jpg",
            content_hash=hashlib.sha256(f"antes{index}".encode()).hexdigest(),
            stage=EvidenceStage.BEFORE,
        )


class TestTheQueue:
    def test_rf_110_the_queue_lists_what_awaits_a_decision(self, client, unit, order) -> None:
        answer = client.get(f"/api/v1/review/units/{unit.code}/queue")
        assert answer.status_code == 200
        body = answer.json()
        assert body["total"] == 1
        assert body["items"][0]["work_order_id"] == str(order.id)

    def test_rf_002_another_unit_sees_nothing(self, client, session, unit, order) -> None:
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        body = client.get(f"/api/v1/review/units/{other.code}/queue").json()
        assert body["total"] == 0

    def test_a_unit_outside_the_callers_scope_is_403_not_404(self, client) -> None:
        """Y eso vale también para una unidad que no existe, a propósito.

        Responder 404 para una inexistente y 403 para una ajena dejaría enumerar las unidades
        de negocio de la empresa preguntando una por una. El chequeo de ámbito corre antes del
        handler, así que ninguna de las dos se distingue desde fuera (ADR-009).
        """
        answer = client.get("/api/v1/review/units/NOEXISTE/queue")
        assert answer.status_code == 403
        assert "unidad de negocio" in answer.json()["detail"]


class TestTheDetail:
    def test_rf_110_the_detail_carries_everything_the_decision_needs(
        self, client, session, unit, order
    ) -> None:
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        add_photos(session, response)
        record_provenance(
            session,
            response,
            field_key="material",
            origin=ValueOrigin.VISION,
            final_value="concrete",
            proposed_value="concrete",
            model_name="mobilenetv3-pole",
            model_version="2026.09",
            confidence=0.91,
            confirmed_by="tecnico.1",
        )
        session.flush()

        body = client.get(f"/api/v1/review/units/{unit.code}/work-orders/{order.id}").json()

        assert body["work_order"]["work_order_id"] == str(order.id)
        assert body["form"]["code"] == "F-MT-01"
        assert body["response"]["answers"]["material"] == "concrete"
        assert body["photo_counts"]["antes"] == 2
        assert body["missing_photos"] == []
        # La procedencia marca qué venía de un modelo: es el trabajo principal del supervisor
        # en una captura asistida.
        entry = next(item for item in body["provenance"] if item["field_key"] == "material")
        assert entry["is_ai"] is True
        assert entry["confirmed_by"] == "tecnico.1"
        assert entry["accepted_unchanged"] is True
        # Y las reglas deterministas viajan con su cita, incluso cuando no aplican.
        assert body["compliance"]
        assert all("outcome" in finding for finding in body["compliance"])
        assert body["blockers"] == []

    def test_rf_110_the_blockers_are_listed_not_implied(self, client, session, unit, order) -> None:
        """Un borrador sin fotos tiene dos impedimentos, y los dos se ven."""
        save_answers(session, unit, order, answers={"code": "P-1"}, submit=False)
        body = client.get(f"/api/v1/review/units/{unit.code}/work-orders/{order.id}").json()
        assert len(body["blockers"]) >= 2
        assert any("borrador" in reason for reason in body["blockers"])

    def test_rf_350_a_regulatory_breach_appears_with_its_citation(
        self, client, session, unit, order
    ) -> None:
        set_parameter(
            session,
            code="grounding.max_resistance_ohm.poste",
            value=25,
            unit="ohm",
            norm_ref="Norma de prueba",
            article_ref="Numeral 5.3",
            effective_from=date(2020, 1, 1),
            verified_by="analista.1",
            strict=True,
        )
        answers = full_answers() | {"earth_resistance_ohm": 90.0, "grounding_context": "poste"}
        response = save_answers(session, unit, order, answers=answers, submit=True)
        add_photos(session, response)
        session.flush()

        body = client.get(f"/api/v1/review/units/{unit.code}/work-orders/{order.id}").json()
        breach = next(finding for finding in body["compliance"] if finding["outcome"] == "incumple")
        assert breach["article_ref"] == "Numeral 5.3"
        assert breach["blocking"] is True
        assert any("Numeral 5.3" in reason for reason in body["blockers"])

    def test_another_units_order_is_404(self, client, session, unit, order) -> None:
        org = session.query(Organization).one()
        other = BusinessUnit(
            organization_id=org.id, code="MAN", name="Unidad Manabí", profile_id="cnel-gye"
        )
        session.add(other)
        session.flush()
        answer = client.get(f"/api/v1/review/units/{other.code}/work-orders/{order.id}")
        assert answer.status_code == 404


class TestTheDecision:
    def test_rf_112_approving_a_complete_capture_works(self, client, session, unit, order) -> None:
        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        add_photos(session, response)
        session.flush()

        answer = client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={"decision": "aprobada"},
        )
        assert answer.status_code == 200
        assert answer.json()["work_order_state"] == WorkOrderState.APPROVED

    def test_rf_112_approving_with_pending_conditions_returns_the_reasons(
        self, client, session, unit, order
    ) -> None:
        """422 con la lista: el supervisor no debería adivinar qué condición falló."""
        save_answers(session, unit, order, answers={"code": "P-1"}, submit=False)
        answer = client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={"decision": "aprobada"},
        )
        assert answer.status_code == 422
        detail = answer.json()["detail"]
        assert detail["blockers"]

    def test_rf_112_returning_with_observations_stores_them(
        self, client, session, unit, order
    ) -> None:
        save_answers(session, unit, order, answers=full_answers(), submit=True)
        answer = client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={
                "decision": "devuelta",
                "note": "falta la foto de después",
                "observations": [
                    {"field_key": "photos_after", "message": "adjunte la foto de cierre"}
                ],
            },
        )
        assert answer.status_code == 200
        assert answer.json()["work_order_state"] == WorkOrderState.RETURNED

        body = client.get(f"/api/v1/review/units/{unit.code}/work-orders/{order.id}").json()
        assert body["observations"][0]["field_key"] == "photos_after"
        assert body["history"][0]["decision"] == "devuelta"
        # Y el autor sale del token, no del cuerpo de la petición.
        assert body["history"][0]["reviewer_sub"] == SUPERVISOR.subject

    def test_rf_112_deciding_on_something_not_awaiting_review_is_409(
        self, client, session, unit, order
    ) -> None:
        order.state = WorkOrderState.APPROVED
        session.flush()
        answer = client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={"decision": "aprobada"},
        )
        assert answer.status_code == 409


class TestTheGisTray:
    def test_rf_342_the_tray_is_empty_before_anything_is_staged(self, client, unit) -> None:
        body = client.get(f"/api/v1/review/units/{unit.code}/gis-tray").json()
        assert body == {"proposals": [], "batches": []}

    def test_rf_342_an_approved_order_reaches_the_tray(self, client, session, unit, order) -> None:
        """La bandeja es el último control humano antes de la geodatabase corporativa."""
        from app.gis_gateway.asbuilt import build_proposal, stage_from_work_order
        from app.org.service import resolver_for_unit

        response = save_answers(session, unit, order, answers=full_answers(), submit=True)
        add_photos(session, response)
        session.flush()
        client.post(
            f"/api/v1/review/units/{unit.code}/work-orders/{order.id}/decision",
            json={"decision": "aprobada"},
        )
        session.refresh(order)

        proposal = build_proposal(
            resolver_for_unit(unit),
            asset_type_key="support_structure",
            action="update",
            attributes={"material": "concrete"},
            gis_global_id="{11111111-2222-3333-4444-555555555555}",
        )
        # El id lo genera el dispositivo: es la clave de idempotencia que impide que un reenvío
        # cree un segundo poste en la geodatabase (RF-353).
        proposal["proposal_id"] = uuid.uuid4()
        stage_from_work_order(session, unit, order, [proposal])
        session.flush()

        body = client.get(f"/api/v1/review/units/{unit.code}/gis-tray").json()
        assert body["proposals"]
        assert body["proposals"][0]["work_order_id"] == str(order.id)
        assert body["proposals"][0]["asset_type_key"] == "support_structure"
