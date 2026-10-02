"""El teléfono de la cuadrilla y lo que el pull le quita (RF-320, RF-321, RF-023).

Dos huecos del mismo contrato:

* **Una OT asignada solo a una cuadrilla no llegaba a ningún teléfono.** El lazo del mapa asigna a
  una cuadrilla y a nada más estrecho: sin persona, sin custodia, sin dispositivo. RF-320 dice que
  «aparece en el próximo sync/pull de los dispositivos de esa cuadrilla», y ningún dispositivo era
  de ninguna cuadrilla. `Device.crew_id` es esa pertenencia, y la fija la web.
* **El pull nunca decía que una OT se había ido.** Una OT reasignada dejaba de aparecer en el pull
  del teléfono anterior, y «dejar de aparecer» no es algo que un teléfono pueda observar: se quedaba
  en él indefinidamente, y el `ConflictResolver` del teléfono nunca recibía una reasignación.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.dispatch.service import device_readiness, dispatch_board
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.sync.models import Device
from app.sync.service import (
    CrossUnitError,
    assign_device_to_crew,
    enrol_device,
    pull_work_orders,
)
from app.workorders.models import Crew, WorkOrder, WorkOrderState
from app.workorders.service import assign, create_work_order, save_crew, set_crew_active

pytestmark = pytest.mark.integration

ACTOR = "kc|planificador.demo"

PLANNER = Principal(
    subject=ACTOR,
    username="planificador.demo",
    roles=frozenset({Role.PLANNER.value}),
    business_units=frozenset({"GYE"}),
)
TECHNICIAN = Principal(
    subject="kc|tecnico.demo",
    username="tecnico.demo",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)
TECHNICIAN_KEY = "phone-00000001"


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


@pytest.fixture
def crews(session: Session, unit: BusinessUnit) -> tuple[Crew, Crew]:
    return (
        save_crew(session, unit, code="C-01", name="Cuadrilla 1", zone="NORTE", actor=ACTOR),
        save_crew(session, unit, code="C-02", name="Cuadrilla 2", zone="SUR", actor=ACTOR),
    )


@pytest.fixture
def tablets(
    session: Session, unit: BusinessUnit, crews: tuple[Crew, Crew]
) -> tuple[Device, Device]:
    one, _ = enrol_device(session, unit, device_key="tablet-cuadrilla-1")
    two, _ = enrol_device(session, unit, device_key="tablet-cuadrilla-2")
    assign_device_to_crew(session, unit, one, crews[0], actor=ACTOR)
    assign_device_to_crew(session, unit, two, crews[1], actor=ACTOR)
    return one, two


def planned_order(session: Session, unit: BusinessUnit) -> WorkOrder:
    return create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        longitude=-79.9,
        latitude=-2.17,
        planner_id=ACTOR,
    )


def touch(session: Session, order: WorkOrder, *, seconds: int = 1) -> None:
    """Move the order past the cursor. PostgreSQL's now() is the transaction's, so a change made in
    the same test transaction as the pull carries the same `updated_at`; production gives each
    request its own transaction."""
    order.updated_at = datetime.now(UTC) + timedelta(seconds=seconds)
    session.flush()


class TestRf320CrewOnlyAssignment:
    def test_an_order_assigned_only_to_the_crew_reaches_its_declared_phone(
        self, session: Session, unit, crews, tablets
    ):
        order = planned_order(session, unit)
        assign(session, order, crew=crews[0])  # the map's lasso: a crew and nothing narrower
        assert order.assigned_user_sub is None

        page = pull_work_orders(session, tablets[0])
        assert [o.id for o in page.orders] == [order.id]
        assert page.withdrawn == []

    def test_another_crews_phone_does_not_receive_it(self, session: Session, unit, crews, tablets):
        order = planned_order(session, unit)
        assign(session, order, crew=crews[0])

        page = pull_work_orders(session, tablets[1])
        assert page.orders == []
        assert page.withdrawn == []

    def test_an_undeclared_phone_receives_nothing(self, session: Session, unit, crews, tablets):
        order = planned_order(session, unit)
        assign(session, order, crew=crews[0])
        loose, _ = enrol_device(session, unit, device_key="tablet-sin-cuadrilla")

        assert pull_work_orders(session, loose).orders == []

    def test_releasing_the_phone_stops_the_delivery(self, session: Session, unit, crews, tablets):
        order = planned_order(session, unit)
        assign(session, order, crew=crews[0])
        assign_device_to_crew(session, unit, tablets[0], None, actor=ACTOR)

        assert pull_work_orders(session, tablets[0]).orders == []


class TestRf023WithdrawnInThePull:
    def test_a_reassigned_order_is_withdrawn_from_the_old_phone(
        self, session: Session, unit, crews, tablets
    ):
        order = planned_order(session, unit)
        assign(session, order, crew=crews[0])
        _, cursor, _ = pull_work_orders(session, tablets[0])

        assign(session, order, crew=crews[1], reason="cambio de zona")
        touch(session, order)

        page = pull_work_orders(session, tablets[0], cursor=cursor)
        assert page.orders == []
        assert [o.id for o in page.withdrawn] == [order.id]
        # And the new phone has it.
        assert [o.id for o in pull_work_orders(session, tablets[1]).orders] == [order.id]

    def test_a_cancelled_order_is_withdrawn(self, session: Session, unit, crews, tablets):
        order = planned_order(session, unit)
        assign(session, order, crew=crews[0])
        _, cursor, _ = pull_work_orders(session, tablets[0])

        order.state = WorkOrderState.CANCELLED
        touch(session, order)

        page = pull_work_orders(session, tablets[0], cursor=cursor)
        assert [o.id for o in page.withdrawn] == [order.id]

    def test_a_phone_that_never_held_it_is_not_told_about_it(
        self, session: Session, unit, crews, tablets
    ):
        """A withdrawal only goes where the order went: a cancellation elsewhere in the unit is
        none of this phone's business, and listing it would leak that it exists."""
        order = planned_order(session, unit)
        assign(session, order, crew=crews[0])
        order.state = WorkOrderState.CANCELLED
        touch(session, order)

        page = pull_work_orders(session, tablets[1])
        assert page.orders == [] and page.withdrawn == []

    def test_the_cursor_advances_past_a_page_of_withdrawals(
        self, session: Session, unit, crews, tablets
    ):
        """Otherwise a phone whose only news is a withdrawal would be told it on every pull."""
        order = planned_order(session, unit)
        assign(session, order, crew=crews[0])
        _, cursor, _ = pull_work_orders(session, tablets[0])
        assign(session, order, crew=crews[1], reason="cambio")
        touch(session, order)

        withdrawn_page = pull_work_orders(session, tablets[0], cursor=cursor)
        assert withdrawn_page.next_cursor is not None
        after = pull_work_orders(session, tablets[0], cursor=withdrawn_page.next_cursor)
        assert after == ([], None, [])

    def test_a_page_boundary_skips_neither_kind(self, session: Session, unit, crews, tablets):
        """One ordering over both sets: page size one, one kept and one withdrawn, both seen."""
        kept = planned_order(session, unit)
        gone = planned_order(session, unit)
        assign(session, kept, crew=crews[0])
        assign(session, gone, crew=crews[0])
        _, cursor, _ = pull_work_orders(session, tablets[0])
        assign(session, gone, crew=crews[1], reason="cambio")
        touch(session, kept, seconds=1)
        touch(session, gone, seconds=2)

        first = pull_work_orders(session, tablets[0], cursor=cursor, limit=1)
        second = pull_work_orders(session, tablets[0], cursor=first.next_cursor, limit=1)
        assert [o.id for o in first.orders] == [kept.id]
        assert [o.id for o in second.withdrawn] == [gone.id]

    def test_a_personal_phone_gets_the_withdrawal_too(self, session: Session, unit, crews):
        phone, _ = enrol_device(session, unit, device_key="phone-a", user_sub="tecnico.a")
        order = planned_order(session, unit)
        assign(session, order, crew=crews[0], user_sub="tecnico.a")
        _, cursor, _ = pull_work_orders(session, phone)

        assign(session, order, crew=crews[0], user_sub="tecnico.b", reason="vacaciones")
        touch(session, order)

        assert [o.id for o in pull_work_orders(session, phone, cursor=cursor).withdrawn] == [
            order.id
        ]


class TestAssignDeviceToCrew:
    def test_the_declaration_is_on_the_trail(self, session: Session, unit, crews, tablets):
        events = session.scalars(
            select(AuditEvent).where(
                AuditEvent.subject_type == "dispositivo",
                AuditEvent.subject_id == "tablet-cuadrilla-1",
            )
        ).all()
        assert len(events) == 1
        assert events[0].payload["to"] == "C-01"
        assert events[0].actor == ACTOR

    def test_declaring_the_same_crew_twice_records_once(
        self, session: Session, unit, crews, tablets
    ):
        assign_device_to_crew(session, unit, tablets[0], crews[0], actor=ACTOR)
        count = len(
            session.scalars(
                select(AuditEvent).where(AuditEvent.subject_id == "tablet-cuadrilla-1")
            ).all()
        )
        assert count == 1

    def test_a_crew_of_another_unit_is_refused(self, session: Session, units, tablets):
        foreign = save_crew(session, units["MAN"], code="M-01", name="Manabí 1", actor=ACTOR)
        with pytest.raises(CrossUnitError):
            assign_device_to_crew(session, units["GYE"], tablets[0], foreign, actor=ACTOR)

    def test_a_device_of_another_unit_is_refused(self, session: Session, units, crews):
        foreign, _ = enrol_device(session, units["MAN"], device_key="tablet-manabi")
        with pytest.raises(CrossUnitError):
            assign_device_to_crew(session, units["GYE"], foreign, crews[0], actor=ACTOR)

    def test_the_board_shows_a_declared_phone_before_its_first_pull(
        self, session: Session, unit, crews, tablets
    ):
        rows = {row.code: row for row in dispatch_board(session, unit)}
        assert rows["C-01"].devices == ["tablet-cuadrilla-1"]
        assert rows["C-02"].devices == ["tablet-cuadrilla-2"]

    def test_readiness_names_the_declared_crew(self, session: Session, unit, crews, tablets):
        enrol_device(session, unit, device_key="tablet-sin-cuadrilla")
        rows = {row.device_key: row.as_dict() for row in device_readiness(session, unit)}
        assert rows["tablet-cuadrilla-1"]["crew_code"] == "C-01"
        assert rows["tablet-sin-cuadrilla"]["crew_code"] is None


@pytest.fixture
def client(session: Session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: PLANNER
    with TestClient(app) as raw:
        yield raw


class TestApi:
    URL = "/api/v1/dispatch/units/GYE/devices/{key}/crew"

    def test_a_planner_declares_the_crew_phone(self, client, session: Session, unit, crews):
        enrol_device(session, unit, device_key="tablet-nueva")
        response = client.put(self.URL.format(key="tablet-nueva"), json={"crew_code": "C-01"})
        assert response.status_code == 200
        assert response.json() == {"device_key": "tablet-nueva", "crew_code": "C-01"}
        device = session.scalars(select(Device).where(Device.device_key == "tablet-nueva")).one()
        assert device.crew_id == crews[0].id

    def test_a_null_crew_releases_it(self, client, session: Session, unit, crews, tablets):
        response = client.put(self.URL.format(key="tablet-cuadrilla-1"), json={"crew_code": None})
        assert response.status_code == 200
        assert tablets[0].crew_id is None

    def test_an_unknown_device_is_404(self, client, unit, crews):
        response = client.put(self.URL.format(key="no-existe"), json={"crew_code": "C-01"})
        assert response.status_code == 404

    def test_another_units_device_is_404(self, client, session: Session, units, crews):
        enrol_device(session, units["MAN"], device_key="tablet-manabi")
        response = client.put(self.URL.format(key="tablet-manabi"), json={"crew_code": "C-01"})
        assert response.status_code == 404

    def test_an_unknown_crew_is_404(self, client, session: Session, unit, crews, tablets):
        response = client.put(self.URL.format(key="tablet-cuadrilla-1"), json={"crew_code": "X-99"})
        assert response.status_code == 404

    def test_a_deactivated_crew_receives_no_phone(
        self, client, session: Session, unit, crews, tablets
    ):
        set_crew_active(session, unit, crews[1], active=False, actor=ACTOR)
        response = client.put(self.URL.format(key="tablet-cuadrilla-1"), json={"crew_code": "C-02"})
        assert response.status_code == 409

    def test_a_crew_outside_the_planners_zone_is_404(self, session: Session, unit, crews, tablets):
        """RF-002: out of ámbito reads as «does not exist», here as everywhere else."""
        scoped = Principal(
            subject="kc|planificador.norte",
            username="planificador.norte",
            roles=frozenset({Role.PLANNER.value}),
            business_units=frozenset({"GYE"}),
            zones=frozenset({"NORTE"}),
        )
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: scoped
        with TestClient(app) as raw:
            response = raw.put(
                self.URL.format(key="tablet-cuadrilla-1"), json={"crew_code": "C-02"}
            )
        assert response.status_code == 404

    def test_a_technician_cannot_declare_their_own_crew(self, session: Session, unit, crews):
        """The whole point: a phone that chose its own crew could read another crew's work."""
        enrol_device(session, unit, device_key=TECHNICIAN_KEY, user_sub=TECHNICIAN.subject)
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: TECHNICIAN
        with TestClient(app) as raw:
            response = raw.put(self.URL.format(key=TECHNICIAN_KEY), json={"crew_code": "C-01"})
        assert response.status_code == 403


class TestPullApiCarriesWithdrawals:
    def test_the_withdrawn_list_has_what_the_phone_resolver_needs(
        self, session: Session, unit, crews
    ):
        phone, _ = enrol_device(
            session, unit, device_key=TECHNICIAN_KEY, user_sub=TECHNICIAN.subject
        )
        order = planned_order(session, unit)
        assign(session, order, crew=crews[0], user_sub=TECHNICIAN.subject)
        _, cursor, _ = pull_work_orders(session, phone)
        assign(session, order, crew=crews[1], user_sub="kc|otro", reason="cambio")
        touch(session, order)

        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: TECHNICIAN
        with TestClient(app) as raw:
            body = raw.get(
                "/api/v1/sync/units/GYE/pull",
                params={"device_key": TECHNICIAN_KEY, "cursor": cursor},
            ).json()
        assert body["work_orders"] == []
        assert body["withdrawn"] == [
            {
                "work_order_id": str(order.id),
                "state": WorkOrderState.ASSIGNED,
                "assigned_user_sub": "kc|otro",
                "version": order.version,
                "reason": "reasignada",
            }
        ]
