"""Position reporting with consent, inside working hours, every N minutes (RF-107).

«Reporte de posición de la cuadrilla (cada N minutos durante la jornada, parámetro, con
consentimiento y solo en horario laboral). Criterio: respeta el horario configurado; se puede
auditar.»

RF-020 built the position itself and stored only the last one. What it did not have was any rule
about **when** a phone may report: a fix sent at 23:00 on a Sunday was stored like one sent at
10:00 on a Tuesday, and nobody had ever been asked. The rules live in the capture policy (RF-151)
so they travel to the phone in its package and are judged on the server by the same values.
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
from app.dispatch import positions
from app.dispatch.models import DevicePosition
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.policy.service import (
    DEFAULTS,
    PolicyError,
    effective,
    parse_workdays,
    policy_for_package,
    set_policy,
    within_workday,
)
from app.sync.models import Device
from app.sync.service import enrol_device

pytestmark = pytest.mark.integration

#: Thursday 24 September 2026. Ecuador is UTC-5 all year, so 15:00 UTC is 10:00 in Guayaquil.
THURSDAY_10AM = datetime(2026, 9, 24, 15, 0, tzinfo=UTC)
THURSDAY_8PM = datetime(2026, 9, 25, 1, 0, tzinfo=UTC)
SATURDAY_10AM = datetime(2026, 9, 26, 15, 0, tzinfo=UTC)

DEVICE_KEY = "phone-00000001"
TECHNICIAN = Principal(
    subject="kc|tecnico.demo",
    username="tecnico.demo",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)
COLLEAGUE = Principal(
    subject="kc|tecnico.colega",
    username="tecnico.colega",
    roles=frozenset({Role.TECHNICIAN.value}),
    business_units=frozenset({"GYE"}),
)


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


@pytest.fixture
def device(session: Session, unit: BusinessUnit) -> Device:
    created, _ = enrol_device(session, unit, device_key=DEVICE_KEY, user_sub=TECHNICIAN.subject)
    return created


@pytest.fixture
def api(session: Session):
    def build(who: Principal = TECHNICIAN) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: who
        return TestClient(app)

    return build


def post_position(client: TestClient, at: datetime, **extra: object) -> dict:
    response = client.post(
        "/api/v1/sync/units/GYE/position",
        json={
            "device_key": DEVICE_KEY,
            "latitude": -2.17,
            "longitude": -79.9,
            "reported_at": at.isoformat(),
            **extra,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


class TestTheWorkday:
    def test_the_defaults_are_a_weekday_office_day_with_consent(self):
        assert DEFAULTS["workday_start"] == "07:00"
        assert DEFAULTS["workday_end"] == "17:00"
        assert DEFAULTS["workdays"] == "1,2,3,4,5"
        assert DEFAULTS["require_position_consent"] is True
        assert DEFAULTS["position_report_minutes"] == 15

    def test_it_is_judged_in_ecuadors_time_not_utc(self, session: Session, unit):
        policy = effective(session, unit)
        assert within_workday(policy, THURSDAY_10AM) is True
        # 20:00 in Guayaquil is 01:00 UTC on Friday — inside a naive UTC reading of "Friday", and
        # outside the working day where the crew actually is.
        assert within_workday(policy, THURSDAY_8PM) is False

    def test_a_non_working_day_is_outside(self, session: Session, unit):
        assert within_workday(effective(session, unit), SATURDAY_10AM) is False

    def test_the_end_is_exclusive_and_the_start_inclusive(self, session: Session, unit):
        policy = effective(session, unit)
        seven = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)  # 07:00 local
        five_pm = datetime(2026, 9, 24, 22, 0, tzinfo=UTC)  # 17:00 local
        assert within_workday(policy, seven) is True
        assert within_workday(policy, seven - timedelta(minutes=1)) is False
        assert within_workday(policy, five_pm) is False
        assert within_workday(policy, five_pm - timedelta(minutes=1)) is True

    def test_a_night_shift_crosses_midnight_and_belongs_to_the_day_it_started(
        self, session: Session, unit
    ):
        set_policy(
            session,
            unit,
            changes={"workday_start": "22:00", "workday_end": "06:00", "workdays": "5"},
            actor="admin",
        )
        policy = effective(session, unit)
        friday_23 = datetime(2026, 9, 26, 4, 0, tzinfo=UTC)  # Friday 23:00 local
        saturday_03 = datetime(2026, 9, 26, 8, 0, tzinfo=UTC)  # Saturday 03:00 local
        saturday_23 = datetime(2026, 9, 27, 4, 0, tzinfo=UTC)  # Saturday 23:00 local
        thursday_03 = datetime(2026, 9, 24, 8, 0, tzinfo=UTC)  # Thursday 03:00 local
        assert within_workday(policy, friday_23) is True
        assert within_workday(policy, saturday_03) is True
        assert within_workday(policy, saturday_23) is False
        assert within_workday(policy, thursday_03) is False

    def test_twenty_four_hundred_closes_the_day(self, session: Session, unit):
        set_policy(
            session,
            unit,
            changes={"workday_start": "00:00", "workday_end": "24:00", "workdays": "1,2,3,4,5,6,7"},
            actor="admin",
        )
        policy = effective(session, unit)
        assert within_workday(policy, THURSDAY_8PM) is True
        assert within_workday(policy, SATURDAY_10AM) is True

    def test_a_zone_can_lengthen_its_day(self, session: Session, unit):
        set_policy(session, unit, zone_code="RURAL", changes={"workday_end": "21:00"}, actor="a")
        assert within_workday(effective(session, unit, "RURAL"), THURSDAY_8PM) is True
        assert within_workday(effective(session, unit), THURSDAY_8PM) is False


class TestValidation:
    @pytest.mark.parametrize(
        "changes",
        [
            {"position_report_minutes": 0},
            {"position_report_minutes": 241},
            {"position_report_minutes": "15"},
            {"workday_start": "7:00"},
            {"workday_start": "25:00"},
            {"workday_start": "24:00"},
            {"workday_end": "17:60"},
            {"workday_start": "08:00", "workday_end": "08:00"},
            {"workdays": ""},
            {"workdays": "0,1"},
            {"workdays": "8"},
            {"workdays": "lunes"},
        ],
    )
    def test_a_malformed_value_is_refused(self, session: Session, unit, changes):
        with pytest.raises(PolicyError):
            set_policy(session, unit, changes=changes, actor="admin")

    def test_workdays_parse_to_iso_weekdays(self):
        assert parse_workdays("1, 2,3") == frozenset({1, 2, 3})

    def test_the_policy_travels_in_the_package(self, session: Session, unit):
        set_policy(session, unit, changes={"position_report_minutes": 30}, actor="admin")
        package = policy_for_package(session, unit, "NORTE")
        assert package["position_report_minutes"] == 30
        assert package["workday_start"] == "07:00"
        assert package["require_position_consent"] is True

    def test_the_change_is_on_the_trail(self, session: Session, unit):
        set_policy(session, unit, changes={"workday_end": "18:00"}, actor="admin.funcional")
        event = session.scalars(
            select(AuditEvent).where(AuditEvent.subject_type == "capture_policy")
        ).one()
        assert event.actor == "admin.funcional"
        assert event.payload["changed"]["workday_end"] == {"from": None, "to": "18:00"}

    def test_the_api_accepts_the_new_fields(self, session: Session, unit):
        admin = Principal(
            subject="kc|admin",
            username="admin",
            roles=frozenset({Role.FUNCTIONAL_ADMIN.value}),
            business_units=frozenset({"GYE"}),
        )
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: admin
        with TestClient(app) as client:
            response = client.put(
                "/api/v1/policies/units/GYE",
                json={"workdays": "1,2,3,4,5,6", "position_report_minutes": 10},
            )
        assert response.status_code == 200, response.text
        policy = effective(session, unit)
        assert policy.value("workdays") == "1,2,3,4,5,6"
        assert policy.value("position_report_minutes") == 10


class TestConsent:
    def test_without_consent_nothing_is_stored(self, api, session: Session, device):
        with api() as client:
            body = post_position(client, THURSDAY_10AM)
        assert body["stored"] is False
        assert body["reason"] == positions.REFUSED_NO_CONSENT
        assert session.get(DevicePosition, device.id) is None

    def test_with_consent_inside_hours_it_is_stored(self, api, session: Session, device):
        with api() as client:
            client.post(
                "/api/v1/sync/units/GYE/position-consent",
                json={"device_key": DEVICE_KEY, "granted": True},
            )
            body = post_position(client, THURSDAY_10AM)
        assert body["stored"] is True
        assert session.get(DevicePosition, device.id) is not None

    def test_with_consent_outside_hours_it_is_refused(self, api, session: Session, unit, device):
        positions.set_consent(session, unit, device, subject=TECHNICIAN.subject, granted=True)
        with api() as client:
            evening = post_position(client, THURSDAY_8PM)
            saturday = post_position(client, SATURDAY_10AM)
        assert evening["reason"] == saturday["reason"] == positions.REFUSED_OFF_HOURS
        assert session.get(DevicePosition, device.id) is None

    def test_the_phone_declared_zone_decides_the_hours(self, api, session: Session, unit, device):
        positions.set_consent(session, unit, device, subject=TECHNICIAN.subject, granted=True)
        set_policy(session, unit, zone_code="RURAL", changes={"workday_end": "21:00"}, actor="a")
        with api() as client:
            body = post_position(client, THURSDAY_8PM, zone_code="RURAL")
        assert body["stored"] is True

    def test_consent_is_not_needed_when_the_policy_says_so(
        self, api, session: Session, unit, device
    ):
        set_policy(session, unit, changes={"require_position_consent": False}, actor="admin")
        with api() as client:
            assert post_position(client, THURSDAY_10AM)["stored"] is True

    def test_consent_is_the_persons_not_the_phones(self, session: Session, unit, device):
        positions.set_consent(session, unit, device, subject=TECHNICIAN.subject, granted=True)
        assert positions.has_consent(device, TECHNICIAN.subject) is True
        assert positions.has_consent(device, COLLEAGUE.subject) is False
        assert (
            positions.refusal(session, unit, device, subject=COLLEAGUE.subject, at=THURSDAY_10AM)
            == positions.REFUSED_NO_CONSENT
        )

    def test_withdrawing_deletes_the_stored_position(self, api, session: Session, unit, device):
        positions.set_consent(session, unit, device, subject=TECHNICIAN.subject, granted=True)
        positions.report(session, unit, device, latitude=-2.17, longitude=-79.9)
        with api() as client:
            response = client.post(
                "/api/v1/sync/units/GYE/position-consent",
                json={"device_key": DEVICE_KEY, "granted": False},
            )
        assert response.json()["granted"] is False
        assert session.get(DevicePosition, device.id) is None
        assert device.position_consent_sub is None

    def test_every_grant_and_withdrawal_is_on_the_trail(self, session: Session, unit, device):
        positions.set_consent(session, unit, device, subject=TECHNICIAN.subject, granted=True)
        positions.set_consent(session, unit, device, subject=TECHNICIAN.subject, granted=True)
        positions.set_consent(session, unit, device, subject=TECHNICIAN.subject, granted=False)
        events = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.subject_type == "consentimiento_posicion")
            .order_by(AuditEvent.sequence)
        ).all()
        # The repeated grant changed nothing and is not recorded twice.
        assert [event.payload["granted"] for event in events] == [True, False]
        assert {event.actor for event in events} == {TECHNICIAN.subject}
        assert {event.device_key for event in events} == {DEVICE_KEY}

    def test_the_trail_answers_by_device(self, api, session: Session, unit, device):
        positions.set_consent(session, unit, device, subject=TECHNICIAN.subject, granted=True)
        auditor = Principal(
            subject="kc|auditor",
            username="auditor",
            roles=frozenset({Role.AUDITOR.value}),
            business_units=frozenset({"GYE"}),
        )
        with api(auditor) as client:
            body = client.get(
                "/api/v1/audit/units/GYE/trail", params={"device_key": DEVICE_KEY}
            ).json()
        assert [e["subject_type"] for e in body["events"]] == ["consentimiento_posicion"]

    def test_nobody_consents_for_somebody_elses_phone(self, api, device):
        with api(COLLEAGUE) as client:
            response = client.post(
                "/api/v1/sync/units/GYE/position-consent",
                json={"device_key": DEVICE_KEY, "granted": True},
            )
        assert response.status_code == 403
        assert device.position_consent_sub is None
