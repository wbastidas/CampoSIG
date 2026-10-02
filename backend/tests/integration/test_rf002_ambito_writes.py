"""Ámbito on writes and on direct ids (RF-002), the half `test_rf002_ambito.py` left open.

The listings were scoped; the doors beside them were not. A zone-scoped planner whose map no longer
showed the south could still assign a southern order by id, hand work to a southern crew, read its
attachments, link it to a consignación or put it on a route — each a way around what the map hid.

The rule here is one sentence: **«no se asigna lo que no se ve».** Out of ámbito answers exactly
like «does not exist» (404, or the «no existe» failure of a lasso), never 403: a 403 would confirm
the id is real.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics import maintenance, operations
from app.attachments import service as attachments
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.auth.scope import may_see_crew, may_see_order
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit
from app.outages import service as outages
from app.routing import service as routing
from app.workorders import fronts
from app.workorders.models import WorkOrderState
from app.workorders.service import assign_many, crew_workload, list_crews
from tests.integration.test_rf002_ambito import (
    APG_FORM,
    MAINTENANCE_FORM,
    make_crew,
    make_order,
)

# The `unit` fixture, re-exported so pytest finds it here.
from tests.integration.test_rf002_ambito import unit as unit
from tests.integration.test_rf133_maintenance_board import NOW, an_inspection, finding

pytestmark = pytest.mark.integration

NORTH_PLANNER = Principal(
    subject="kc|planificador.norte",
    username="planificador.norte",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
    zones=frozenset({"norte"}),
)
NORTH_SUPERVISOR = Principal(
    subject="kc|supervisor.norte",
    username="supervisor.norte",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE"}),
    zones=frozenset({"norte"}),
)
NORTH_ADMIN = Principal(
    subject="kc|admin.norte",
    username="admin.norte",
    roles=frozenset({Role.FUNCTIONAL_ADMIN.value}),
    business_units=frozenset({"GYE"}),
    zones=frozenset({"norte"}),
)
UNRESTRICTED_PLANNER = Principal(
    subject="kc|planificador",
    username="planificador",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def as_(session: Session):
    """A client factory: `as_(principal)` sharing the test's transaction."""
    clients: list[TestClient] = []

    def build(principal: Principal) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: principal
        client = TestClient(app)
        clients.append(client)
        return client

    yield build
    for client in clients:
        client.close()


@pytest.fixture
def world(session: Session, unit: BusinessUnit):
    north_crew = make_crew(session, unit, code="C-N", zone="norte")
    south_crew = make_crew(session, unit, code="C-S", zone="sur")
    north = make_order(session, unit, zone="norte", state=WorkOrderState.PLANNED)
    south = make_order(
        session, unit, zone="sur", state=WorkOrderState.PLANNED, longitude=-80.0, latitude=-2.3
    )
    return {"north_crew": north_crew, "south_crew": south_crew, "north": north, "south": south}


class TestSingleObjectHelpers:
    def test_no_principal_narrows_nothing(self, world):
        assert may_see_order(None, world["south"]) is True
        assert may_see_crew(None, world["south_crew"]) is True

    def test_the_helpers_follow_may_see(self, world):
        assert may_see_order(NORTH_PLANNER, world["north"]) is True
        assert may_see_order(NORTH_PLANNER, world["south"]) is False
        assert may_see_crew(NORTH_PLANNER, world["north_crew"]) is True
        assert may_see_crew(NORTH_PLANNER, world["south_crew"]) is False

    def test_the_order_helper_reads_the_area_from_the_form(self, session: Session, unit, world):
        apg_only = Principal(
            subject="kc|apg",
            roles=frozenset({Role.PLANNER.value}),
            business_units=frozenset({"GYE"}),
            areas=frozenset({"apg"}),
        )
        assert may_see_order(apg_only, make_order(session, unit, form_code=APG_FORM)) is True
        assert may_see_order(apg_only, make_order(session, unit, form_code=MAINTENANCE_FORM)) is (
            False
        )

    def test_the_order_helper_reads_the_contractor_from_its_crew(
        self, session: Session, unit, world
    ):
        contractor = Principal(
            subject="kc|contratista",
            roles=frozenset({Role.SUPERVISOR.value}),
            business_units=frozenset({"GYE"}),
            contractor="ACME",
        )
        theirs = make_crew(session, unit, code="C-ACME", contractor="ACME")
        assert may_see_order(contractor, make_order(session, unit, crew=theirs)) is True
        assert may_see_order(contractor, world["north"]) is False


class TestAssignment:
    def test_assign_one_out_of_ambito_order_is_404(self, as_, world):
        response = as_(NORTH_PLANNER).post(
            f"/api/v1/planning/work-orders/{world['south'].id}/assign",
            params={"business_unit": "GYE"},
            json={"crew_id": str(world["north_crew"].id)},
        )
        assert response.status_code == 404

    def test_assign_one_to_an_out_of_ambito_crew_is_404(self, as_, world):
        response = as_(NORTH_PLANNER).post(
            f"/api/v1/planning/work-orders/{world['north'].id}/assign",
            params={"business_unit": "GYE"},
            json={"crew_id": str(world["south_crew"].id)},
        )
        assert response.status_code == 404
        assert world["north"].assigned_crew_id is None

    def test_assign_one_inside_the_ambito_still_works(self, as_, world):
        response = as_(NORTH_PLANNER).post(
            f"/api/v1/planning/work-orders/{world['north'].id}/assign",
            params={"business_unit": "GYE"},
            json={"crew_id": str(world["north_crew"].id)},
        )
        assert response.status_code == 200
        assert world["north"].assigned_crew_id == world["north_crew"].id

    def test_a_lasso_with_a_hidden_order_assigns_the_rest_and_says_no_existe(self, as_, world):
        response = as_(NORTH_PLANNER).post(
            "/api/v1/planning/assign-selection",
            params={"business_unit": "GYE"},
            json={
                "work_order_ids": [str(world["north"].id), str(world["south"].id)],
                "crew_id": str(world["north_crew"].id),
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["assigned"] == [str(world["north"].id)]
        assert body["failures"] == [
            {
                "work_order_id": str(world["south"].id),
                "message": "no existe en esta unidad de negocio",
            }
        ]
        assert world["south"].assigned_crew_id is None

    def test_a_lasso_onto_a_hidden_crew_is_404(self, as_, world):
        response = as_(NORTH_PLANNER).post(
            "/api/v1/planning/assign-selection",
            params={"business_unit": "GYE"},
            json={
                "work_order_ids": [str(world["north"].id)],
                "crew_id": str(world["south_crew"].id),
            },
        )
        assert response.status_code == 404

    def test_assign_many_without_a_principal_is_unchanged(self, session: Session, unit, world):
        assigned, failures = assign_many(
            session, unit, [world["north"].id, world["south"].id], crew=world["north_crew"]
        )
        assert len(assigned) == 2 and failures == []

    def test_suggestions_only_rank_crews_in_ambito(self, as_, world):
        body = (
            as_(NORTH_PLANNER)
            .get(
                f"/api/v1/planning/work-orders/{world['north'].id}/suggested-crews",
                params={"business_unit": "GYE"},
            )
            .json()
        )
        codes = [c["code"] for c in body["candidates"]] + [c["code"] for c in body["excluded"]]
        assert codes == ["C-N"]

    def test_suggestions_for_a_hidden_order_are_404(self, as_, world):
        response = as_(NORTH_PLANNER).get(
            f"/api/v1/planning/work-orders/{world['south'].id}/suggested-crews",
            params={"business_unit": "GYE"},
        )
        assert response.status_code == 404

    def test_the_workload_board_lists_crews_in_ambito(self, as_, session: Session, unit, world):
        body = as_(NORTH_PLANNER).get("/api/v1/planning/crews", params={"business_unit": "GYE"})
        assert [row["code"] for row in body.json()] == ["C-N"]
        assert [row["code"] for row in crew_workload(session, unit)] == ["C-N", "C-S"]


class TestFronts:
    def test_fronts_of_a_hidden_work_are_404(self, as_, world):
        response = as_(NORTH_PLANNER).get(
            f"/api/v1/planning/work-orders/{world['south'].id}/fronts",
            params={"business_unit": "GYE"},
        )
        assert response.status_code == 404

    def test_a_hidden_order_cannot_be_hung_as_a_front(self, as_, world):
        response = as_(NORTH_PLANNER).post(
            f"/api/v1/planning/work-orders/{world['north'].id}/fronts",
            params={"business_unit": "GYE"},
            json={"work_order_id": str(world["south"].id)},
        )
        assert response.status_code == 404
        assert world["south"].parent_id is None

    def test_the_list_hides_fronts_but_the_progress_counts_them_all(
        self, as_, session: Session, unit, world
    ):
        fronts.attach(session, unit, world["north"], world["south"], actor="x")
        visible = make_order(session, unit, zone="norte", state=WorkOrderState.PLANNED)
        fronts.attach(session, unit, world["north"], visible, actor="x")

        body = (
            as_(NORTH_PLANNER)
            .get(
                f"/api/v1/planning/work-orders/{world['north'].id}/fronts",
                params={"business_unit": "GYE"},
            )
            .json()
        )
        assert [f["work_order_id"] for f in body["fronts"]] == [str(visible.id)]
        assert body["progress"]["total"] == 2

    def test_the_works_list_only_has_works_in_ambito(self, as_, session: Session, unit, world):
        child = make_order(session, unit, zone="sur", state=WorkOrderState.PLANNED)
        fronts.attach(session, unit, world["south"], child, actor="x")

        assert (
            as_(NORTH_PLANNER).get("/api/v1/planning/works", params={"business_unit": "GYE"}).json()
            == []
        )
        assert len(fronts.parents_with_fronts(session, unit)) == 1


class TestCustody:
    def test_custody_of_a_hidden_order_is_still_404(self, as_, world):
        response = as_(NORTH_PLANNER).get(
            f"/api/v1/planning/work-orders/{world['south'].id}/custody",
            params={"business_unit": "GYE"},
        )
        assert response.status_code == 404


def _attachment(session: Session, unit: BusinessUnit, order):
    return attachments.attach(
        session,
        unit,
        order,
        title="Plano",
        filename="plano.pdf",
        storage_key=f"GYE/adjuntos/{order.id}/plano.pdf",
        content_hash="a" * 64,
        size_bytes=1000,
        mime_type="application/pdf",
        uploaded_by="x",
    )


class TestAttachments:
    def test_the_attachments_of_a_hidden_order_are_404(self, as_, session: Session, unit, world):
        _attachment(session, unit, world["south"])
        response = as_(NORTH_PLANNER).get(
            f"/api/v1/attachments/units/GYE/work-orders/{world['south'].id}"
        )
        assert response.status_code == 404

    def test_attaching_to_a_hidden_order_is_404(self, as_, world):
        response = as_(NORTH_PLANNER).post(
            f"/api/v1/attachments/units/GYE/work-orders/{world['south'].id}",
            json={
                "title": "Plano",
                "filename": "plano.pdf",
                "storage_key": "GYE/adjuntos/x/plano.pdf",
                "content_hash": "b" * 64,
                "size_bytes": 1000,
                "mime_type": "application/pdf",
            },
        )
        assert response.status_code == 404

    def test_withdrawing_a_hidden_orders_attachment_is_404(
        self, as_, session: Session, unit, world
    ):
        row = _attachment(session, unit, world["south"])
        response = as_(NORTH_PLANNER).post(
            f"/api/v1/attachments/units/GYE/{row.id}/withdraw", json={"reason": "viejo"}
        )
        assert response.status_code == 404
        assert row.withdrawn_at is None

    def test_inside_the_ambito_the_attachments_still_read(self, as_, session: Session, unit, world):
        _attachment(session, unit, world["north"])
        response = as_(NORTH_PLANNER).get(
            f"/api/v1/attachments/units/GYE/work-orders/{world['north'].id}"
        )
        assert response.status_code == 200
        assert len(response.json()["attachments"]) == 1


def _outage(session: Session, unit: BusinessUnit):
    start = datetime.now(UTC) + timedelta(days=1)
    return outages.request_outage(
        session,
        unit,
        equipment="Seccionador S-12",
        window_start=start,
        window_end=start + timedelta(hours=4),
        requested_by="kc|otro.planificador",
    )


class TestOutages:
    def test_linking_a_hidden_order_is_404(self, as_, session: Session, unit, world):
        row = _outage(session, unit)
        response = as_(NORTH_PLANNER).post(
            f"/api/v1/outages/units/GYE/{row.id}/work-orders",
            json={"work_order_id": str(world["south"].id)},
        )
        assert response.status_code == 404
        assert world["south"].outage_request_id is None

    def test_unlinking_a_hidden_order_is_404(self, as_, session: Session, unit, world):
        row = _outage(session, unit)
        outages.link(session, unit, world["south"], row, actor="x")
        response = as_(NORTH_PLANNER).delete(
            f"/api/v1/outages/units/GYE/work-orders/{world['south'].id}"
        )
        assert response.status_code == 404
        assert world["south"].outage_request_id == row.id

    def test_the_detail_names_only_orders_in_ambito_but_counts_them_all(
        self, as_, session: Session, unit, world
    ):
        row = _outage(session, unit)
        outages.link(session, unit, world["north"], row, actor="x")
        outages.link(session, unit, world["south"], row, actor="x")
        body = as_(NORTH_PLANNER).get(f"/api/v1/outages/units/GYE/{row.id}").json()
        assert [o["work_order_id"] for o in body["work_orders"]] == [str(world["north"].id)]
        assert body["orders"] == 2


class TestRouting:
    def test_a_route_through_a_hidden_order_is_refused_as_missing(
        self, session: Session, unit, world
    ):
        with pytest.raises(routing.RoutingError, match="no existen"):
            routing.suggest_route(
                session, unit, [world["north"].id, world["south"].id], principal=NORTH_PLANNER
            )

    def test_the_endpoint_refuses_it_too(self, as_, world):
        response = as_(NORTH_PLANNER).post(
            "/api/v1/routing/units/GYE/suggest",
            json={"work_order_ids": [str(world["north"].id), str(world["south"].id)]},
        )
        assert response.status_code == 422
        assert str(world["south"].id) in response.json()["detail"]

    def test_an_unrestricted_planner_routes_both(self, session: Session, unit, world):
        suggestion = routing.suggest_route(
            session, unit, [world["north"].id, world["south"].id], principal=UNRESTRICTED_PLANNER
        )
        assert len(suggestion.as_dict()["stops"]) == 2


class TestCrewAdministration:
    """Editing the roster is the functional administrator's, a corporate role that bypasses every
    ámbito (`Principal.is_corporate`) — so what narrows here is what planners and supervisors
    read."""

    def test_the_crew_list_is_scoped(self, as_, session: Session, unit, world):
        body = as_(NORTH_PLANNER).get("/api/v1/crews/units/GYE").json()
        assert [c["code"] for c in body] == ["C-N"]
        assert len(list_crews(session, unit)) == 2

    def test_the_history_of_a_hidden_crew_is_404(self, as_, world):
        assert as_(NORTH_PLANNER).get("/api/v1/crews/units/GYE/C-S/history").status_code == 404
        assert as_(NORTH_PLANNER).get("/api/v1/crews/units/GYE/C-N/history").status_code == 200

    def test_the_functional_administrator_still_sees_every_crew(self, as_, world):
        body = as_(NORTH_ADMIN).get("/api/v1/crews/units/GYE").json()
        assert [c["code"] for c in body] == ["C-N", "C-S"]


class TestBoards:
    def test_the_operational_board_counts_only_the_ambito(self, session: Session, unit, world):
        scoped = operations.build(session, unit.id, principal=NORTH_SUPERVISOR)
        whole = operations.build(session, unit.id)
        assert sum(scoped.by_state.values()) == 1
        assert sum(whole.by_state.values()) == 2
        assert [c.crew_name for c in scoped.crews] == ["Cuadrilla C-N"]

    def test_the_operational_endpoint_passes_the_principal(self, as_, world):
        body = as_(NORTH_SUPERVISOR).get("/api/v1/analytics/units/GYE/operations").json()
        assert sum(body["by_state"].values()) == 1

    def test_the_maintenance_board_is_scoped_to_the_findings(self, session: Session, unit):
        north = an_inspection(session, unit, code="OT-N", findings=[finding("D-01")])
        south = an_inspection(session, unit, code="OT-S", findings=[finding("D-02")])
        north.zone, south.zone = "norte", "sur"
        session.flush()
        period = {"since": NOW - timedelta(days=1), "until": NOW + timedelta(days=1)}

        scoped = maintenance.build(session, unit.id, principal=NORTH_SUPERVISOR, **period)
        whole = maintenance.build(session, unit.id, **period)
        assert (scoped.findings, whole.findings) == (1, 2)
        assert scoped.by_defect == {"D-01": 1}

    def test_the_maintenance_endpoint_passes_the_principal(self, as_, session: Session, unit):
        an_inspection(session, unit, code="OT-S", findings=[finding("D-02")]).zone = "sur"
        session.flush()
        body = (
            as_(NORTH_SUPERVISOR)
            .get(
                "/api/v1/analytics/units/GYE/maintenance",
                params={
                    "since": (NOW - timedelta(days=1)).isoformat(),
                    "until": (NOW + timedelta(days=1)).isoformat(),
                },
            )
            .json()
        )
        assert body["findings"] == 0
