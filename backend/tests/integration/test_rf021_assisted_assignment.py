"""Assisted assignment: the top three with an explainable score (RF-021).

The properties under test are the ones that make a suggestion worth following:

* **A missing competency excludes, and no amount of proximity buys it back.** The crew next door
  without the APG competency must never be suggested for an APG form.
* **An excluded crew comes back with its reason.** A planner who cannot see why C-03 is absent will
  assign it by hand.
* **Every point carries a sentence**, and what could not be measured is said rather than scored as
  zero — a suggestion computed for an order with no location should not look confident.
* **The order is stable.** A ranking that reshuffles on refresh is one nobody trusts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.assignment.suggest import (
    DISTANCE_CEILING_KM,
    LOAD_CEILING,
    POINTS_LOAD,
    POINTS_SLA,
    POINTS_ZONE,
    required_competencies,
    suggest_crews,
)
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.workorders.models import Crew, WorkOrder
from app.workorders.service import assign, create_work_order
from app.zones import service as zones

pytestmark = pytest.mark.integration

#: Guayaquil, roughly.
LON, LAT = -79.90, -2.17
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def square(west: float, south: float, size: float = 0.20) -> dict[str, object]:
    east, north = west + size, south + size
    return {
        "type": "Polygon",
        "coordinates": [
            [[west, south], [east, south], [east, north], [west, north], [west, south]]
        ],
    }


def zone_feature(code: str, geometry: dict[str, object]) -> dict[str, object]:
    return {"type": "Feature", "geometry": geometry, "properties": {"code": code}}


@pytest.fixture
def units(session: Session) -> dict[str, BusinessUnit]:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created = {}
    for code, name in (("GYE", "Unidad Guayaquil"), ("MAN", "Unidad Manabí")):
        unit = BusinessUnit(organization_id=org.id, code=code, name=name, profile_id="cnel-gye")
        session.add(unit)
        created[code] = unit
    session.flush()
    return created


@pytest.fixture
def unit(units: dict[str, BusinessUnit]) -> BusinessUnit:
    return units["GYE"]


def make_crew(
    session: Session,
    unit: BusinessUnit,
    code: str,
    *,
    competencies: list[str] | None = None,
    zone: str | None = None,
    active: bool = True,
) -> Crew:
    crew = Crew(
        business_unit_id=unit.id,
        code=code,
        name=f"Cuadrilla {code}",
        competencies=competencies if competencies is not None else ["MT", "BT", "APG"],
        zone=zone,
        active=active,
    )
    session.add(crew)
    session.flush()
    return crew


def make_order(
    session: Session,
    unit: BusinessUnit,
    *,
    form_code: str = "F-MT-01",
    lon: float | None = LON,
    lat: float | None = LAT,
    sla_due_at: datetime | None = None,
) -> WorkOrder:
    return create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code=form_code,
        longitude=lon,
        latitude=lat,
        planner_id="planner.a",
        sla_due_at=sla_due_at,
    )


def carry(
    session: Session,
    unit: BusinessUnit,
    crew: Crew,
    *,
    lon: float = LON,
    lat: float = LAT,
    sla_due_at: datetime | None = None,
) -> WorkOrder:
    """Give a crew one open order, which is what «carga» and the distance proxy read."""
    order = make_order(session, unit, lon=lon, lat=lat, sla_due_at=sla_due_at)
    assign(session, order, crew=crew)
    session.flush()
    return order


class TestCompetenciesAreAHardRequirement:
    def test_the_form_declares_them_as_data(self):
        """From `forms/definitions/`, not from a table in the code (rule 3)."""
        assert required_competencies("F-AP-01") == ["APG"]
        assert required_competencies("F-MT-01") == []

    def test_a_crew_without_the_competency_is_never_suggested(
        self, session: Session, unit: BusinessUnit
    ):
        """Not even the one standing next to the luminaire."""
        near = make_crew(session, unit, "SIN-APG", competencies=["MT"])
        carry(session, unit, near, lon=LON, lat=LAT)
        far = make_crew(session, unit, "CON-APG", competencies=["APG"])
        carry(session, unit, far, lon=LON + 0.5, lat=LAT + 0.5)
        order = make_order(session, unit, form_code="F-AP-01")

        found = suggest_crews(session, unit, order, now=NOW)
        assert [item.code for item in found.candidates] == ["CON-APG"]
        assert [item.code for item in found.excluded] == ["SIN-APG"]

    def test_the_exclusion_names_the_competency_and_the_form(
        self, session: Session, unit: BusinessUnit
    ):
        make_crew(session, unit, "C-01", competencies=["MT"])
        order = make_order(session, unit, form_code="F-AP-01")
        found = suggest_crews(session, unit, order, now=NOW)
        assert "APG" in found.excluded[0].reason
        assert "F-AP-01" in found.excluded[0].reason

    def test_when_nobody_qualifies_it_says_so_instead_of_returning_an_empty_list(
        self, session: Session, unit: BusinessUnit
    ):
        make_crew(session, unit, "C-01", competencies=["MT"])
        order = make_order(session, unit, form_code="F-AP-01")
        found = suggest_crews(session, unit, order, now=NOW)
        assert found.candidates == []
        assert any("competencias" in line for line in found.caveats)

    def test_an_unknown_form_does_not_suggest_nobody(self, session: Session, unit: BusinessUnit):
        """The order exists and somebody has to do it; the caveat says what was not checked."""
        crew = make_crew(session, unit, "C-01", competencies=[])
        order = make_order(session, unit)
        order.form_code = "F-XX-99"
        session.flush()
        found = suggest_crews(session, unit, order, now=NOW)
        assert [item.code for item in found.candidates] == [crew.code]
        assert any("F-XX-99" in line for line in found.caveats)


class TestTheZone:
    def test_a_crew_whose_zone_contains_the_order_scores_for_it(
        self, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session,
            unit,
            {"type": "Feature", **zone_feature("NORTE", square(-80.0, -2.30))},
            actor="admin",
        )
        crew = make_crew(session, unit, "C-01", zone="NORTE")
        order = make_order(session, unit)
        found = suggest_crews(session, unit, order, now=NOW)
        zone_reason = next(r for r in found.candidates[0].reasons if r.factor == "zona")
        assert zone_reason.points == POINTS_ZONE
        assert "NORTE" in zone_reason.detail
        assert crew.zone == "NORTE"

    def test_a_crew_of_another_zone_scores_zero_and_the_reason_says_which(
        self, session: Session, unit: BusinessUnit
    ):
        zones.import_geojson(
            session,
            unit,
            {"type": "Feature", **zone_feature("NORTE", square(-80.0, -2.30))},
            actor="admin",
        )
        make_crew(session, unit, "C-01", zone="SUR")
        order = make_order(session, unit)
        found = suggest_crews(session, unit, order, now=NOW)
        zone_reason = next(r for r in found.candidates[0].reasons if r.factor == "zona")
        assert zone_reason.points == 0
        assert "SUR" in zone_reason.detail and "NORTE" in zone_reason.detail

    def test_an_order_outside_every_zone_says_the_zone_does_not_count(
        self, session: Session, unit: BusinessUnit
    ):
        make_crew(session, unit, "C-01", zone="NORTE")
        order = make_order(session, unit)
        found = suggest_crews(session, unit, order, now=NOW)
        assert any("no cae en ninguna zona" in line for line in found.caveats)
        assert all(r.factor != "zona" for r in found.candidates[0].reasons)


class TestDistance:
    def test_the_nearer_crew_scores_higher(self, session: Session, unit: BusinessUnit):
        near = make_crew(session, unit, "CERCA")
        carry(session, unit, near, lon=LON + 0.01, lat=LAT)
        far = make_crew(session, unit, "LEJOS")
        carry(session, unit, far, lon=LON + 0.15, lat=LAT)
        order = make_order(session, unit)

        found = suggest_crews(session, unit, order, now=NOW)
        by_code = {item.code: item for item in found.candidates}
        near_points = next(r.points for r in by_code["CERCA"].reasons if r.factor == "cercanía")
        far_points = next(r.points for r in by_code["LEJOS"].reasons if r.factor == "cercanía")
        assert near_points > far_points

    def test_a_crew_with_no_open_work_says_the_distance_cannot_be_measured(
        self, session: Session, unit: BusinessUnit
    ):
        """The platform holds no crew GPS, so silence here would look like a bad fit."""
        make_crew(session, unit, "C-01")
        order = make_order(session, unit)
        found = suggest_crews(session, unit, order, now=NOW)
        reason = next(r for r in found.candidates[0].reasons if r.factor == "cercanía")
        assert reason.points == 0
        assert "no se puede medir" in reason.detail

    def test_beyond_the_ceiling_distance_stops_counting(self, session: Session, unit: BusinessUnit):
        crew = make_crew(session, unit, "C-01")
        # Roughly 55 km east, well past the ceiling.
        carry(session, unit, crew, lon=LON + 0.5, lat=LAT)
        order = make_order(session, unit)
        found = suggest_crews(session, unit, order, now=NOW)
        reason = next(r for r in found.candidates[0].reasons if r.factor == "cercanía")
        assert reason.points == 0
        assert f"{DISTANCE_CEILING_KM:.0f}" in reason.detail

    def test_an_order_without_a_location_says_so_and_scores_no_geography(
        self, session: Session, unit: BusinessUnit
    ):
        crew = make_crew(session, unit, "C-01")
        carry(session, unit, crew)
        order = make_order(session, unit, lon=None, lat=None)
        found = suggest_crews(session, unit, order, now=NOW)
        assert any("no tiene ubicación" in line for line in found.caveats)
        reason = next(r for r in found.candidates[0].reasons if r.factor == "cercanía")
        assert reason.points == 0


class TestLoadAndSla:
    def test_an_idle_crew_gets_the_full_load_points(self, session: Session, unit: BusinessUnit):
        make_crew(session, unit, "C-01")
        order = make_order(session, unit)
        found = suggest_crews(session, unit, order, now=NOW)
        reason = next(r for r in found.candidates[0].reasons if r.factor == "carga")
        assert reason.points == POINTS_LOAD
        assert "no tiene OT abiertas" in reason.detail

    def test_load_points_fall_as_the_crew_fills_up(self, session: Session, unit: BusinessUnit):
        light = make_crew(session, unit, "LIVIANA")
        carry(session, unit, light)
        heavy = make_crew(session, unit, "CARGADA")
        for _ in range(4):
            carry(session, unit, heavy)
        order = make_order(session, unit)

        found = suggest_crews(session, unit, order, now=NOW)
        by_code = {item.code: item for item in found.candidates}
        light_points = next(r.points for r in by_code["LIVIANA"].reasons if r.factor == "carga")
        heavy_points = next(r.points for r in by_code["CARGADA"].reasons if r.factor == "carga")
        assert light_points > heavy_points

    def test_at_the_ceiling_load_earns_nothing_but_the_crew_is_still_suggestible(
        self, session: Session, unit: BusinessUnit
    ):
        """Not a hard cap: a planner may want to give a ninth order to the crew already there."""
        crew = make_crew(session, unit, "C-01")
        for _ in range(LOAD_CEILING):
            carry(session, unit, crew)
        order = make_order(session, unit)
        found = suggest_crews(session, unit, order, now=NOW)
        assert [item.code for item in found.candidates] == ["C-01"]
        reason = next(r for r in found.candidates[0].reasons if r.factor == "carga")
        assert reason.points == 0

    def test_a_crew_with_urgent_work_loses_the_sla_points(
        self, session: Session, unit: BusinessUnit
    ):
        calm = make_crew(session, unit, "TRANQUILA")
        carry(session, unit, calm, sla_due_at=NOW + timedelta(days=5))
        pressed = make_crew(session, unit, "APURADA")
        carry(session, unit, pressed, sla_due_at=NOW + timedelta(hours=2))
        order = make_order(session, unit)

        found = suggest_crews(session, unit, order, now=NOW)
        by_code = {item.code: item for item in found.candidates}
        calm_points = next(
            r.points for r in by_code["TRANQUILA"].reasons if r.factor == "presión de SLA"
        )
        pressed_reason = next(r for r in by_code["APURADA"].reasons if r.factor == "presión de SLA")
        assert calm_points == POINTS_SLA
        assert pressed_reason.points == 0
        assert "menos margen" in pressed_reason.detail


class TestTheRanking:
    def test_only_the_top_three_come_back(self, session: Session, unit: BusinessUnit):
        for index in range(5):
            make_crew(session, unit, f"C-{index:02d}")
        order = make_order(session, unit)
        assert len(suggest_crews(session, unit, order, now=NOW).candidates) == 3

    def test_the_top_can_be_widened_when_a_caller_asks(self, session: Session, unit: BusinessUnit):
        for index in range(5):
            make_crew(session, unit, f"C-{index:02d}")
        order = make_order(session, unit)
        assert len(suggest_crews(session, unit, order, top=5, now=NOW).candidates) == 5

    def test_ties_break_by_code_so_two_runs_agree(self, session: Session, unit: BusinessUnit):
        for code in ("C-03", "C-01", "C-02"):
            make_crew(session, unit, code)
        order = make_order(session, unit)
        first = [item.code for item in suggest_crews(session, unit, order, now=NOW).candidates]
        second = [item.code for item in suggest_crews(session, unit, order, now=NOW).candidates]
        assert first == second == ["C-01", "C-02", "C-03"]

    def test_the_score_is_the_sum_of_its_reasons(self, session: Session, unit: BusinessUnit):
        """Otherwise a planner could not tell which factor made the difference."""
        make_crew(session, unit, "C-01", zone="NORTE")
        order = make_order(session, unit)
        candidate = suggest_crews(session, unit, order, now=NOW).candidates[0]
        assert candidate.score == sum(reason.points for reason in candidate.reasons)

    def test_an_inactive_crew_is_not_suggested_at_all(self, session: Session, unit: BusinessUnit):
        make_crew(session, unit, "ACTIVA")
        make_crew(session, unit, "RETIRADA", active=False)
        order = make_order(session, unit)
        found = suggest_crews(session, unit, order, now=NOW)
        assert [item.code for item in found.candidates] == ["ACTIVA"]
        assert found.excluded == []

    def test_a_unit_with_no_crews_says_so(self, session: Session, unit: BusinessUnit):
        order = make_order(session, unit)
        found = suggest_crews(session, unit, order, now=NOW)
        assert found.candidates == []
        assert any("no tiene cuadrillas activas" in line for line in found.caveats)

    def test_another_units_crews_are_never_suggested(
        self, session: Session, units: dict[str, BusinessUnit]
    ):
        make_crew(session, units["MAN"], "AJENA")
        make_crew(session, units["GYE"], "PROPIA")
        order = make_order(session, units["GYE"])
        found = suggest_crews(session, units["GYE"], order, now=NOW)
        assert [item.code for item in found.candidates] == ["PROPIA"]

    def test_the_order_being_assigned_does_not_count_as_its_own_load(
        self, session: Session, unit: BusinessUnit
    ):
        """A reassignment asks about an order the crew may already hold."""
        crew = make_crew(session, unit, "C-01")
        order = carry(session, unit, crew)
        found = suggest_crews(session, unit, order, now=NOW)
        reason = next(r for r in found.candidates[0].reasons if r.factor == "carga")
        assert reason.detail == "no tiene OT abiertas"


PLANNER = Principal(
    subject="kc|planner.a",
    username="planner.a",
    display_name="Planificador",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
)

TECHNICIAN = Principal(
    subject="kc|tecnico.1",
    username="tecnico.1",
    display_name="Técnico",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def client(session: Session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: PLANNER
    with TestClient(app) as raw:
        yield raw


class TestApi:
    def test_the_suggestion_comes_back_with_its_reasons(
        self, client, session: Session, unit: BusinessUnit
    ):
        make_crew(session, unit, "C-01")
        order = make_order(session, unit)
        session.flush()
        body = client.get(
            f"/api/v1/planning/work-orders/{order.id}/suggested-crews?business_unit=GYE"
        ).json()
        assert body["candidates"][0]["code"] == "C-01"
        assert body["candidates"][0]["reasons"]
        assert "factor" in body["candidates"][0]["reasons"][0]

    def test_the_required_competencies_travel_so_the_screen_can_show_them(
        self, client, session: Session, unit: BusinessUnit
    ):
        make_crew(session, unit, "C-01", competencies=["APG"])
        order = make_order(session, unit, form_code="F-AP-01")
        session.flush()
        body = client.get(
            f"/api/v1/planning/work-orders/{order.id}/suggested-crews?business_unit=GYE"
        ).json()
        assert body["required_competencies"] == ["APG"]

    def test_an_order_of_another_unit_is_404(
        self, client, session: Session, units: dict[str, BusinessUnit]
    ):
        order = make_order(session, units["MAN"])
        session.flush()
        response = client.get(
            f"/api/v1/planning/work-orders/{order.id}/suggested-crews?business_unit=GYE"
        )
        assert response.status_code == 404

    def test_a_technician_cannot_ask(self, session: Session, unit: BusinessUnit):
        order = make_order(session, unit)
        session.flush()
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: TECHNICIAN
        with TestClient(app) as technician:
            response = technician.get(
                f"/api/v1/planning/work-orders/{order.id}/suggested-crews?business_unit=GYE"
            )
            assert response.status_code == 403

    def test_nothing_is_assigned_by_asking(self, client, session: Session, unit: BusinessUnit):
        """It is a suggestion: the planner still clicks."""
        make_crew(session, unit, "C-01")
        order = make_order(session, unit)
        session.flush()
        client.get(f"/api/v1/planning/work-orders/{order.id}/suggested-crews?business_unit=GYE")
        assert order.assigned_crew_id is None
