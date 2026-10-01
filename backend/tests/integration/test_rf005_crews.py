"""Crew administration: create, edit, deactivate, members and change history (RF-005).

Mirrors `test_rf152_zones.py`'s own `TestTrail`/`TestApi` split, because a crew roster is the same
kind of administrative record a zone boundary is: read broadly, written by one role, never deleted,
every change on the audit trail.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.audit.service import verify
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.workorders.service import (
    UnknownCrewError,
    crew_history,
    get_crew_by_code,
    list_crews,
    save_crew,
    set_crew_active,
)

pytestmark = pytest.mark.integration

ACTOR = "admin.funcional"


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


class TestService:
    def test_a_new_code_creates_a_crew(self, session: Session, unit: BusinessUnit):
        crew = save_crew(session, unit, code="C-01", name="Cuadrilla 1", actor=ACTOR)
        assert crew.code == "C-01"
        assert crew.active is True
        assert crew.created_by == ACTOR
        assert crew.members == []

    def test_an_existing_code_edits_instead_of_duplicating(self, session: Session, unit):
        first = save_crew(session, unit, code="C-01", name="Cuadrilla 1", actor=ACTOR)
        again = save_crew(
            session,
            unit,
            code="C-01",
            name="Cuadrilla Uno",
            actor="otra.persona",
            members=["Ana Pérez", "Luis Toro"],
        )
        assert again.id == first.id
        assert again.name == "Cuadrilla Uno"
        assert again.members == ["Ana Pérez", "Luis Toro"]
        assert again.updated_by == "otra.persona"
        assert len(list_crews(session, unit)) == 1

    def test_members_and_leader_and_competencies_round_trip(self, session: Session, unit):
        crew = save_crew(
            session,
            unit,
            code="C-01",
            name="Cuadrilla 1",
            leader_name="Jorge Salas",
            vehicle="Camioneta 12",
            competencies=["MV", "altura"],
            members=["Ana Pérez", "Luis Toro"],
            zone="norte",
            actor=ACTOR,
        )
        assert crew.leader_name == "Jorge Salas"
        assert crew.vehicle == "Camioneta 12"
        assert crew.competencies == ["MV", "altura"]
        assert crew.members == ["Ana Pérez", "Luis Toro"]
        assert crew.zone == "norte"

    def test_list_excludes_inactive_unless_asked(self, session: Session, unit):
        save_crew(session, unit, code="C-01", name="Activa", actor=ACTOR)
        inactive = save_crew(session, unit, code="C-02", name="Inactiva", actor=ACTOR)
        set_crew_active(session, unit, inactive, active=False, actor=ACTOR)
        assert [c.code for c in list_crews(session, unit)] == ["C-01"]
        assert [c.code for c in list_crews(session, unit, include_inactive=True)] == [
            "C-01",
            "C-02",
        ]

    def test_deactivating_never_deletes_the_row(self, session: Session, unit):
        crew = save_crew(session, unit, code="C-01", name="Cuadrilla 1", actor=ACTOR)
        set_crew_active(session, unit, crew, active=False, actor=ACTOR)
        assert get_crew_by_code(session, unit, "C-01").active is False

    def test_an_unknown_code_is_reported_by_name(self, session: Session, unit):
        with pytest.raises(UnknownCrewError, match="X-99"):
            get_crew_by_code(session, unit, "X-99")

    def test_crews_of_one_unit_never_leak_into_another(
        self, session: Session, units: dict[str, BusinessUnit]
    ):
        save_crew(session, units["GYE"], code="C-01", name="Guayaquil", actor=ACTOR)
        save_crew(session, units["MAN"], code="C-01", name="Manabí", actor=ACTOR)
        assert [c.name for c in list_crews(session, units["GYE"])] == ["Guayaquil"]
        assert [c.name for c in list_crews(session, units["MAN"])] == ["Manabí"]


class TestTrail:
    def test_every_change_lands_in_the_trail_and_the_chain_holds(
        self, session: Session, unit: BusinessUnit
    ):
        crew = save_crew(session, unit, code="C-01", name="Cuadrilla 1", actor=ACTOR)
        save_crew(session, unit, code="C-01", name="Cuadrilla Uno", actor="otra.persona")
        set_crew_active(session, unit, crew, active=False, actor="tercera.persona")

        events = [
            event
            for event in session.query(AuditEvent).order_by(AuditEvent.sequence)
            if event.subject_type == "cuadrilla"
        ]
        assert [event.actor for event in events] == [ACTOR, "otra.persona", "tercera.persona"]
        assert verify(session, unit.id).intact

    def test_crew_history_reads_only_that_crews_entries(self, session: Session, unit):
        one = save_crew(session, unit, code="C-01", name="Uno", actor=ACTOR)
        two = save_crew(session, unit, code="C-02", name="Dos", actor=ACTOR)
        save_crew(session, unit, code="C-01", name="Uno editada", actor=ACTOR)

        assert len(crew_history(session, unit, one)) == 2
        assert len(crew_history(session, unit, two)) == 1

    def test_reactivating_leaves_no_change_with_nothing_to_report(self, session: Session, unit):
        """`set_crew_active` is a no-op, and the trail should say so by staying silent."""
        crew = save_crew(session, unit, code="C-01", name="Cuadrilla 1", actor=ACTOR)
        set_crew_active(session, unit, crew, active=True, actor="otra.persona")
        assert len(crew_history(session, unit, crew)) == 1


#: The administrator these endpoint tests act as. Identity comes from the token in production;
#: here the dependency is overridden, because what this section tests is the endpoints.
ADMIN = Principal(
    subject="kc|admin.funcional",
    username="admin.funcional",
    display_name="Administradora Funcional",
    roles=frozenset({Role.FUNCTIONAL_ADMIN.value}),
    business_units=frozenset({"GYE", "MAN"}),
)

PLANNER = Principal(
    subject="kc|planner.a",
    username="planner.a",
    display_name="Planificador",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def client(session: Session):
    """A client sharing the test's transaction, so nothing it writes escapes the rollback."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: ADMIN
    with TestClient(app) as raw:
        yield raw


class TestApi:
    def test_the_list_comes_back_with_the_roster(self, client, session: Session, unit):
        save_crew(
            session, unit, code="C-01", name="Cuadrilla 1", members=["Ana Pérez"], actor=ACTOR
        )
        body = client.get("/api/v1/crews/units/GYE").json()
        assert body[0]["code"] == "C-01"
        assert body[0]["members"] == ["Ana Pérez"]

    def test_a_crew_is_created_with_the_author_from_the_token(self, client, session: Session, unit):
        response = client.put(
            "/api/v1/crews/units/GYE/C-01",
            json={"code": "C-01", "name": "Cuadrilla 1", "members": ["Ana Pérez"]},
        )
        assert response.status_code == 200
        assert get_crew_by_code(session, unit, "C-01").created_by == ADMIN.subject

    def test_putting_the_same_code_again_edits_it(self, client, session: Session, unit):
        client.put("/api/v1/crews/units/GYE/C-01", json={"code": "C-01", "name": "Cuadrilla 1"})
        response = client.put(
            "/api/v1/crews/units/GYE/C-01", json={"code": "C-01", "name": "Cuadrilla Uno"}
        )
        assert response.status_code == 200
        assert len(list_crews(session, unit)) == 1
        assert get_crew_by_code(session, unit, "C-01").name == "Cuadrilla Uno"

    def test_a_code_mismatch_between_route_and_body_is_refused(self, client, unit):
        response = client.put("/api/v1/crews/units/GYE/C-01", json={"code": "C-02", "name": "Otra"})
        assert response.status_code == 422

    def test_deactivate_then_reactivate_through_the_api(self, client, session: Session, unit):
        client.put("/api/v1/crews/units/GYE/C-01", json={"code": "C-01", "name": "Cuadrilla 1"})
        off = client.post("/api/v1/crews/units/GYE/C-01/active", json={"active": False})
        assert off.status_code == 200
        assert off.json()["active"] is False
        assert [c["code"] for c in client.get("/api/v1/crews/units/GYE").json()] == []

        on = client.post("/api/v1/crews/units/GYE/C-01/active", json={"active": True})
        assert on.status_code == 200
        assert [c["code"] for c in client.get("/api/v1/crews/units/GYE").json()] == ["C-01"]

    def test_deactivating_an_unknown_crew_is_404(self, client, unit):
        response = client.post("/api/v1/crews/units/GYE/X-99/active", json={"active": False})
        assert response.status_code == 404

    def test_the_history_endpoint_lists_every_change_in_order(self, client, session: Session, unit):
        client.put("/api/v1/crews/units/GYE/C-01", json={"code": "C-01", "name": "Cuadrilla 1"})
        client.put("/api/v1/crews/units/GYE/C-01", json={"code": "C-01", "name": "Cuadrilla Uno"})
        body = client.get("/api/v1/crews/units/GYE/C-01/history").json()
        assert len(body) == 2
        assert body[0]["payload"]["name"] == "Cuadrilla 1"
        assert body[1]["payload"]["name"] == "Cuadrilla Uno"

    def test_history_of_an_unknown_crew_is_404(self, client, unit):
        assert client.get("/api/v1/crews/units/GYE/X-99/history").status_code == 404

    def test_a_planner_may_look_and_may_not_write(self, session: Session, unit):
        """Managing the fleet is administrative; dispatching against it is everyone's job."""
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: PLANNER
        with TestClient(app) as planner_client:
            assert planner_client.get("/api/v1/crews/units/GYE").status_code == 200
            forbidden = planner_client.put(
                "/api/v1/crews/units/GYE/C-01", json={"code": "C-01", "name": "Cuadrilla 1"}
            )
            assert forbidden.status_code == 403

    def test_an_unknown_unit_is_rejected(self, client):
        response = client.get("/api/v1/crews/units/XX")
        assert response.status_code in (403, 404)
