"""Ámbito: área, zona, agencia y contratista, on top of the business-unit scope (RF-002).

The acceptance criterion is literal: «un supervisor de APG de la zona Norte no ve OT de
Mantenimiento de la zona Sur». Until this module existed that sentence was false — a `Principal`
only ever escaped by business unit (ADR-009), and any role inside a unit saw every área, zona,
agencia and contratista in it.

Three layers, each with its own tests:

* `Principal.may_see` — the rule itself, pure Python, no database.
* `work_order_scope`/`crew_scope` — the same rule as a `WHERE` clause, exercised against real rows.
* The API endpoints that list work (review's queue, the planning map, the dispatch board and the
  crew-positions map) — proving the rule actually reaches a request, not just the service layer.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.auth.scope import crew_scope, work_order_scope
from app.auth.tokens import principal_from_claims
from app.dispatch.positions import report
from app.dispatch.service import dispatch_board, record_delivery
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.review.service import queue_size, review_queue
from app.sync.service import enrol_device
from app.workorders.models import Crew, WorkOrderState
from app.workorders.service import create_work_order

pytestmark = pytest.mark.integration

#: F-AP-01 is APG; F-MT-01 is Mantenimiento (see the catalogue). Picked to match the SRS's own
#: example rather than invent a pair of areas nobody will recognise.
APG_FORM = "F-AP-01"
MAINTENANCE_FORM = "F-MT-01"


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


def make_order(
    session: Session,
    unit: BusinessUnit,
    *,
    form_code: str = MAINTENANCE_FORM,
    zone: str | None = None,
    agency: str | None = None,
    crew: Crew | None = None,
    state: str = WorkOrderState.SYNCED,
    longitude: float = -79.9,
    latitude: float = -2.17,
):
    order = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code=form_code,
        longitude=longitude,
        latitude=latitude,
        zone=zone,
        planner_id="planner.a",
    )
    order.state = state
    order.agency = agency
    if crew is not None:
        order.assigned_crew_id = crew.id
    session.flush()
    return order


def make_crew(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str = "C-01",
    zone: str | None = None,
    agency: str | None = None,
    contractor: str | None = None,
) -> Crew:
    crew = Crew(
        business_unit_id=unit.id,
        code=code,
        name=f"Cuadrilla {code}",
        zone=zone,
        agency=agency,
        contractor=contractor,
    )
    session.add(crew)
    session.flush()
    return crew


class TestClaimMapping:
    def test_areas_zones_agencies_and_contractor_come_from_the_token(self):
        principal = principal_from_claims(
            {
                "sub": "u1",
                "areas": "apg, mantenimiento",
                "zones": ["norte"],
                "agencies": "AG-01",
                "contratista": "Contratista XYZ",
            }
        )
        assert principal.areas == frozenset({"apg", "mantenimiento"})
        assert principal.zones == frozenset({"norte"})
        assert principal.agencies == frozenset({"AG-01"})
        assert principal.contractor == "Contratista XYZ"

    def test_no_claim_at_all_means_unrestricted(self):
        principal = principal_from_claims({"sub": "u1", "business_units": ["GYE"]})
        assert principal.areas == frozenset()
        assert principal.zones == frozenset()
        assert principal.agencies == frozenset()
        assert principal.contractor is None

    def test_the_english_claim_name_also_works(self):
        principal = principal_from_claims({"sub": "u1", "contractor": "ACME"})
        assert principal.contractor == "ACME"


class TestMaySee:
    """The rule, in isolation: what counts as inside one person's ámbito."""

    def test_an_unrestricted_person_sees_everything(self):
        principal = Principal(subject="u", business_units=frozenset({"GYE"}))
        assert principal.may_see(area="apg", zone="sur", agency="AG-02", contractor="X")

    def test_area_scoped_excludes_another_area(self):
        principal = Principal(
            subject="u", business_units=frozenset({"GYE"}), areas=frozenset({"apg"})
        )
        assert principal.may_see(area="apg")
        assert not principal.may_see(area="mantenimiento")

    def test_a_record_with_no_area_is_not_excluded_by_an_area_scope(self):
        principal = Principal(
            subject="u", business_units=frozenset({"GYE"}), areas=frozenset({"apg"})
        )
        assert principal.may_see(area=None)

    def test_zone_scoped_excludes_another_zone_but_not_an_unset_one(self):
        principal = Principal(
            subject="u", business_units=frozenset({"GYE"}), zones=frozenset({"norte"})
        )
        assert principal.may_see(zone="norte")
        assert not principal.may_see(zone="sur")
        assert principal.may_see(zone=None)

    def test_agency_scoped_follows_the_same_rule_as_zone(self):
        principal = Principal(
            subject="u", business_units=frozenset({"GYE"}), agencies=frozenset({"AG-01"})
        )
        assert principal.may_see(agency="AG-01")
        assert not principal.may_see(agency="AG-02")
        assert principal.may_see(agency=None)

    def test_contractor_scoped_excludes_in_house_work_too(self):
        """The one dimension that narrows by presence: in-house work is not this contractor's."""
        principal = Principal(subject="u", business_units=frozenset({"GYE"}), contractor="ACME")
        assert principal.may_see(contractor="ACME")
        assert not principal.may_see(contractor="OTRA")
        assert not principal.may_see(contractor=None)

    def test_a_corporate_role_bypasses_every_dimension(self):
        principal = Principal(
            subject="u", roles=frozenset({Role.AUDITOR.value}), areas=frozenset({"apg"})
        )
        assert principal.may_see(area="mantenimiento", zone="x", agency="y", contractor="z")

    def test_scopes_combine_as_and_not_or(self):
        """Restricted on two axes means both have to match, not either."""
        principal = Principal(
            subject="u",
            business_units=frozenset({"GYE"}),
            areas=frozenset({"apg"}),
            zones=frozenset({"norte"}),
        )
        assert principal.may_see(area="apg", zone="norte")
        assert not principal.may_see(area="apg", zone="sur")
        assert not principal.may_see(area="mantenimiento", zone="norte")


class TestWorkOrderScope:
    """The same rule, as a `WHERE` clause over real rows."""

    def test_unrestricted_returns_none(self):
        principal = Principal(subject="u", business_units=frozenset({"GYE"}))
        assert work_order_scope(principal) is None

    def test_the_srs_example_literally(self, session: Session, unit: BusinessUnit):
        """Un supervisor de APG de la zona Norte no ve OT de Mantenimiento de la zona Sur."""
        apg_norte = make_order(session, unit, form_code=APG_FORM, zone="norte")
        make_order(session, unit, form_code=MAINTENANCE_FORM, zone="sur")

        principal = Principal(
            subject="supervisor.apg",
            roles=frozenset({Role.SUPERVISOR.value}),
            business_units=frozenset({"GYE"}),
            areas=frozenset({"apg"}),
            zones=frozenset({"norte"}),
        )
        orders = review_queue(session, unit, principal=principal)
        assert [o.id for o in orders] == [apg_norte.id]

    def test_a_work_order_with_no_zone_is_still_visible_to_a_zone_scoped_supervisor(
        self, session: Session, unit: BusinessUnit
    ):
        order = make_order(session, unit, zone=None)
        principal = Principal(
            subject="u", business_units=frozenset({"GYE"}), zones=frozenset({"norte"})
        )
        orders = review_queue(session, unit, principal=principal)
        assert [o.id for o in orders] == [order.id]

    def test_contractor_scope_only_sees_its_own_crews_work(
        self, session: Session, unit: BusinessUnit
    ):
        own_crew = make_crew(session, unit, code="C-01", contractor="ACME")
        other_crew = make_crew(session, unit, code="C-02", contractor="OTRA")
        in_house_crew = make_crew(session, unit, code="C-03", contractor=None)
        mine = make_order(session, unit, crew=own_crew)
        make_order(session, unit, crew=other_crew)
        make_order(session, unit, crew=in_house_crew)
        make_order(session, unit, crew=None)  # unassigned

        principal = Principal(subject="u", business_units=frozenset({"GYE"}), contractor="ACME")
        orders = review_queue(session, unit, principal=principal)
        assert [o.id for o in orders] == [mine.id]

    def test_queue_size_matches_the_same_scope(self, session: Session, unit: BusinessUnit):
        make_order(session, unit, form_code=APG_FORM)
        make_order(session, unit, form_code=MAINTENANCE_FORM)
        principal = Principal(
            subject="u", business_units=frozenset({"GYE"}), areas=frozenset({"apg"})
        )
        assert queue_size(session, unit, principal=principal) == 1


class TestCrewScope:
    def test_unrestricted_returns_none(self):
        assert crew_scope(Principal(subject="u", business_units=frozenset({"GYE"}))) is None

    def test_dispatch_board_only_lists_crews_in_scope(self, session: Session, unit: BusinessUnit):
        make_crew(session, unit, code="C-01", zone="norte")
        make_crew(session, unit, code="C-02", zone="sur")
        principal = Principal(
            subject="u", business_units=frozenset({"GYE"}), zones=frozenset({"norte"})
        )
        board = dispatch_board(session, unit, principal=principal)
        assert [row.code for row in board] == ["C-01"]

    def test_dispatch_board_contractor_scope_excludes_other_crews(
        self, session: Session, unit: BusinessUnit
    ):
        make_crew(session, unit, code="C-01", contractor="ACME")
        make_crew(session, unit, code="C-02", contractor="OTRA")
        make_crew(session, unit, code="C-03", contractor=None)
        principal = Principal(subject="u", business_units=frozenset({"GYE"}), contractor="ACME")
        board = dispatch_board(session, unit, principal=principal)
        assert [row.code for row in board] == ["C-01"]


#: The administrator these endpoint tests act as, for whichever call does not care about ámbito.
ADMIN = Principal(
    subject="kc|admin.funcional",
    username="admin.funcional",
    roles=frozenset({Role.FUNCTIONAL_ADMIN.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def client(session: Session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as raw:
        yield raw
    app.dependency_overrides.clear()


class TestApiEnforcement:
    """The same ámbito, reached through the actual HTTP endpoints."""

    def test_the_review_queue_honours_the_callers_ambito(
        self, client, session: Session, unit: BusinessUnit
    ):
        apg_norte = make_order(session, unit, form_code=APG_FORM, zone="norte")
        make_order(session, unit, form_code=MAINTENANCE_FORM, zone="sur")

        scoped = Principal(
            subject="supervisor.apg",
            roles=frozenset({Role.SUPERVISOR.value}),
            business_units=frozenset({"GYE"}),
            areas=frozenset({"apg"}),
            zones=frozenset({"norte"}),
        )
        client.app.dependency_overrides[current_principal] = lambda: scoped
        body = client.get("/api/v1/review/units/GYE/queue").json()
        assert [item["work_order_id"] for item in body["items"]] == [str(apg_norte.id)]
        assert body["total"] == 1

    def test_a_direct_id_outside_the_ambito_is_404_not_a_leak(
        self, client, session: Session, unit: BusinessUnit
    ):
        outside = make_order(session, unit, form_code=MAINTENANCE_FORM, zone="sur")
        scoped = Principal(
            subject="supervisor.apg",
            roles=frozenset({Role.SUPERVISOR.value}),
            business_units=frozenset({"GYE"}),
            areas=frozenset({"apg"}),
        )
        client.app.dependency_overrides[current_principal] = lambda: scoped
        response = client.get(f"/api/v1/review/units/GYE/work-orders/{outside.id}")
        assert response.status_code == 404

    def test_the_planning_map_honours_the_ambito(
        self, client, session: Session, unit: BusinessUnit
    ):
        inside = make_order(session, unit, form_code=APG_FORM, zone="norte")
        make_order(session, unit, form_code=MAINTENANCE_FORM, zone="sur")

        scoped = Principal(
            subject="planificador.apg",
            roles=frozenset({Role.PLANNER.value}),
            business_units=frozenset({"GYE"}),
            areas=frozenset({"apg"}),
        )
        client.app.dependency_overrides[current_principal] = lambda: scoped
        body = client.get(
            "/api/v1/planning/work-orders.geojson",
            params={
                "business_unit": "GYE",
                "west": -80.5,
                "south": -2.5,
                "east": -79.5,
                "north": -1.9,
            },
        ).json()
        ids = [f["id"] for f in body["features"]]
        assert ids == [str(inside.id)]

    def test_the_dispatch_board_honours_the_ambito(
        self, client, session: Session, unit: BusinessUnit
    ):
        make_crew(session, unit, code="C-01", zone="norte")
        make_crew(session, unit, code="C-02", zone="sur")
        scoped = Principal(
            subject="supervisor.norte",
            roles=frozenset({Role.SUPERVISOR.value}),
            business_units=frozenset({"GYE"}),
            zones=frozenset({"norte"}),
        )
        client.app.dependency_overrides[current_principal] = lambda: scoped
        body = client.get("/api/v1/dispatch/units/GYE/board").json()
        assert [row["code"] for row in body] == ["C-01"]

    def test_the_crew_positions_map_honours_the_ambito(
        self, client, session: Session, unit: BusinessUnit
    ):
        crew = make_crew(session, unit, code="C-01", zone="norte")
        other_crew = make_crew(session, unit, code="C-02", zone="sur")
        order = make_order(session, unit, zone="norte", crew=crew, state=WorkOrderState.ASSIGNED)
        other_order = make_order(
            session, unit, zone="sur", crew=other_crew, state=WorkOrderState.ASSIGNED
        )
        mine, _ = enrol_device(session, unit, device_key="phone-mine", user_sub="tec.a")
        theirs, _ = enrol_device(session, unit, device_key="phone-theirs", user_sub="tec.b")
        record_delivery(session, mine, [order])
        record_delivery(session, theirs, [other_order])
        report(session, unit, mine, latitude=-2.17, longitude=-79.9)
        report(session, unit, theirs, latitude=-2.3, longitude=-80.0)
        session.flush()

        scoped = Principal(
            subject="dispatcher.norte",
            roles=frozenset({Role.SUPERVISOR.value}),
            business_units=frozenset({"GYE"}),
            zones=frozenset({"norte"}),
        )
        client.app.dependency_overrides[current_principal] = lambda: scoped
        body = client.get("/api/v1/dispatch/units/GYE/crews.geojson").json()
        device_keys = [f["properties"]["device_key"] for f in body["features"]]
        assert device_keys == ["phone-mine"]

    def test_an_unrestricted_corporate_account_sees_everything(
        self, client, session: Session, unit: BusinessUnit
    ):
        make_order(session, unit, form_code=APG_FORM, zone="norte")
        make_order(session, unit, form_code=MAINTENANCE_FORM, zone="sur")
        client.app.dependency_overrides[current_principal] = lambda: ADMIN
        body = client.get("/api/v1/review/units/GYE/queue").json()
        assert body["total"] == 2
