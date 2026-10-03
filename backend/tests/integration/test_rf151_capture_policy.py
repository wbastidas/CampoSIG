"""Capture policy per area (RF-151), and the two places it has to bite.

The requirement's acceptance criterion is «cambiar la política se refleja en el móvil en el
siguiente sync», so the test that matters most is not the write: it is that the resolved policy
travels inside the offline package manifest and that changing a policy changes the manifest's
content hash. That hash is the device's staleness check, so if it did not move the policy would
never arrive.

The rest is about not lying to an administrator:

* every effective value names its origin, or a unit-level change that a zone overrides looks like
  a broken sync;
* a zone overrides field by field and inherits the rest, so changing the unit's figure reaches the
  zone for everything the zone did not state;
* an absent key leaves a field alone and an explicit null clears it — a screen that posted every
  field would otherwise turn «I did not touch this» into «set this to null»;
* and `store_audio` is enforced on the server, not only on the phone (RF-058).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.audit.service import verify
from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.policy import service as policy
from app.policy.models import CapturePolicy
from app.responses.models import EvidenceKind
from app.responses.service import AudioNotAllowedError, register_evidence, save_answers
from app.sync.service import build_offline_package
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

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


class TestDefaults:
    def test_a_unit_with_no_policy_still_resolves_and_names_the_default(
        self, session: Session, unit: BusinessUnit
    ):
        """A field nobody set must not show a number with no author."""
        found = policy.effective(session, unit)
        assert found.value("min_photos") == policy.DEFAULTS["min_photos"]
        assert found.source("min_photos") == policy.SOURCE_DEFAULT

    def test_the_defaults_are_the_conservative_reading_and_not_the_convenient_one(
        self, session: Session, unit: BusinessUnit
    ):
        """Keeping a customer's voice and spending a technician's data plan are both opt-in."""
        found = policy.effective(session, unit)
        assert found.value("store_audio") is False
        assert found.value("require_audio_consent") is True
        assert found.value("upload_on_metered") is False

    def test_every_field_of_the_model_has_a_default(self, session: Session, unit: BusinessUnit):
        """Otherwise adding a column would make the resolver raise for a unit that set nothing."""
        assert set(policy.FIELDS) == set(policy.DEFAULTS)
        found = policy.effective(session, unit)
        assert set(found.values) == set(policy.FIELDS)


class TestResolution:
    def test_the_unit_overrides_the_default_and_says_so(self, session: Session, unit: BusinessUnit):
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        found = policy.effective(session, unit)
        assert found.value("min_photos") == 3
        assert found.source("min_photos") == policy.SOURCE_UNIT

    def test_the_zone_overrides_the_unit_and_says_so(self, session: Session, unit: BusinessUnit):
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        policy.set_policy(session, unit, zone_code="NORTE", changes={"min_photos": 5}, actor=ACTOR)
        found = policy.effective(session, unit, "NORTE")
        assert found.value("min_photos") == 5
        assert found.source("min_photos") == policy.SOURCE_ZONE

    def test_a_zone_inherits_every_field_it_did_not_state(
        self, session: Session, unit: BusinessUnit
    ):
        """The reason the columns are nullable: a zone that differs in one thing says one thing."""
        policy.set_policy(
            session, unit, changes={"min_photos": 3, "store_audio": True}, actor=ACTOR
        )
        policy.set_policy(
            session, unit, zone_code="NORTE", changes={"upload_on_metered": True}, actor=ACTOR
        )
        found = policy.effective(session, unit, "NORTE")
        assert (found.value("upload_on_metered"), found.source("upload_on_metered")) == (
            True,
            policy.SOURCE_ZONE,
        )
        assert (found.value("min_photos"), found.source("min_photos")) == (3, policy.SOURCE_UNIT)

    def test_changing_the_unit_reaches_a_zone_that_never_stated_that_field(
        self, session: Session, unit: BusinessUnit
    ):
        """The failure whole-row overrides would cause: the zone keeping yesterday's figure."""
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        policy.set_policy(
            session, unit, zone_code="NORTE", changes={"upload_on_metered": True}, actor=ACTOR
        )
        policy.set_policy(session, unit, changes={"min_photos": 6}, actor=ACTOR)
        assert policy.effective(session, unit, "NORTE").value("min_photos") == 6

    def test_a_zone_nobody_configured_resolves_to_its_unit(
        self, session: Session, unit: BusinessUnit
    ):
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        assert policy.effective(session, unit, "SIN-CONFIGURAR").value("min_photos") == 3

    def test_false_is_a_value_and_not_an_absence(self, session: Session, unit: BusinessUnit):
        """The bug a truthiness check would cause: a unit that turns audio off is ignored."""
        policy.set_policy(session, unit, changes={"store_audio": True}, actor=ACTOR)
        policy.set_policy(
            session, unit, zone_code="SUR", changes={"store_audio": False}, actor=ACTOR
        )
        found = policy.effective(session, unit, "SUR")
        assert found.value("store_audio") is False
        assert found.source("store_audio") == policy.SOURCE_ZONE

    def test_nothing_crosses_between_units(self, session: Session, units: dict[str, BusinessUnit]):
        policy.set_policy(session, units["GYE"], changes={"min_photos": 9}, actor=ACTOR)
        assert (
            policy.effective(session, units["MAN"]).value("min_photos")
            == (policy.DEFAULTS["min_photos"])
        )

    def test_the_device_payload_carries_no_provenance(self, session: Session, unit: BusinessUnit):
        """The origins are for the administrator. A policy is to be obeyed, not interpreted."""
        flat = policy.effective(session, unit).for_device()
        assert set(flat) == set(policy.FIELDS)
        assert all(not isinstance(value, dict) for value in flat.values())


class TestWriting:
    def test_an_absent_key_leaves_the_field_alone(self, session: Session, unit: BusinessUnit):
        policy.set_policy(
            session, unit, changes={"min_photos": 3, "photo_quality": 60}, actor=ACTOR
        )
        policy.set_policy(session, unit, changes={"photo_quality": 70}, actor=ACTOR)
        assert policy.effective(session, unit).value("min_photos") == 3

    def test_an_explicit_null_clears_the_field_so_it_inherits_again(
        self, session: Session, unit: BusinessUnit
    ):
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        policy.set_policy(session, unit, zone_code="NORTE", changes={"min_photos": 5}, actor=ACTOR)
        policy.set_policy(
            session, unit, zone_code="NORTE", changes={"min_photos": None}, actor=ACTOR
        )
        found = policy.effective(session, unit, "NORTE")
        assert (found.value("min_photos"), found.source("min_photos")) == (3, policy.SOURCE_UNIT)

    def test_removing_a_zone_row_makes_it_inherit_everything(
        self, session: Session, unit: BusinessUnit
    ):
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        policy.set_policy(session, unit, zone_code="NORTE", changes={"min_photos": 5}, actor=ACTOR)
        assert policy.clear_policy(session, unit, zone_code="NORTE", actor=ACTOR) is True
        assert policy.effective(session, unit, "NORTE").value("min_photos") == 3

    def test_removing_a_zone_row_that_does_not_exist_says_so(
        self, session: Session, unit: BusinessUnit
    ):
        assert policy.clear_policy(session, unit, zone_code="NO-HAY", actor=ACTOR) is False

    def test_a_field_that_is_not_a_policy_field_is_refused(
        self, session: Session, unit: BusinessUnit
    ):
        with pytest.raises(policy.PolicyError):
            policy.set_policy(session, unit, changes={"aprobar_todo": True}, actor=ACTOR)

    def test_a_retention_of_zero_days_is_refused_as_a_typo(
        self, session: Session, unit: BusinessUnit
    ):
        """Zero days is not a retention policy, it is a deletion rule, and it arrives as a typo."""
        with pytest.raises(policy.PolicyError):
            policy.set_policy(session, unit, changes={"audio_retention_days": 0}, actor=ACTOR)

    def test_a_quality_outside_one_to_a_hundred_is_refused(
        self, session: Session, unit: BusinessUnit
    ):
        with pytest.raises(policy.PolicyError):
            policy.set_policy(session, unit, changes={"photo_quality": 140}, actor=ACTOR)

    def test_the_unit_can_only_have_one_row(self, session: Session, unit: BusinessUnit):
        """Two unit rows would make resolution depend on which one the query happened to see."""
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        session.add(CapturePolicy(business_unit_id=unit.id, zone_code=None, min_photos=9))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_the_rows_come_back_with_the_unit_first(self, session: Session, unit: BusinessUnit):
        policy.set_policy(session, unit, zone_code="SUR", changes={"min_photos": 5}, actor=ACTOR)
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        policy.set_policy(session, unit, zone_code="NORTE", changes={"min_photos": 4}, actor=ACTOR)
        assert [row.zone_code for row in policy.list_policies(session, unit)] == [
            None,
            "NORTE",
            "SUR",
        ]


class TestTrail:
    def test_a_change_records_who_and_what_moved(self, session: Session, unit: BusinessUnit):
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        policy.set_policy(session, unit, changes={"min_photos": 6}, actor="otra.persona")
        events = [
            event
            for event in session.query(AuditEvent).order_by(AuditEvent.sequence)
            if event.subject_type == "capture_policy"
        ]
        assert [event.actor for event in events] == [ACTOR, "otra.persona"]
        assert events[1].payload["changed"]["min_photos"] == {"from": 3, "to": 6}
        assert verify(session, unit.id).intact

    def test_a_save_that_changes_nothing_records_no_field(
        self, session: Session, unit: BusinessUnit
    ):
        """Otherwise the trail fills with «min_photos: 3 → 3» and hides the real changes."""
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        events = [
            event
            for event in session.query(AuditEvent).order_by(AuditEvent.sequence)
            if event.subject_type == "capture_policy"
        ]
        assert events[1].payload["changed"] == {}


class TestTheManifest:
    def build(self, session: Session, unit: BusinessUnit, zone: str = "NORTE"):
        return build_offline_package(
            session, unit, zone=zone, tile_url="/tiles/norte.pmtiles", asset_count=10
        )

    def test_the_policy_travels_inside_the_package(self, session: Session, unit: BusinessUnit):
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        package = self.build(session, unit)
        assert package.manifest["capture_policy"]["min_photos"] == 3

    def test_changing_the_policy_changes_the_content_hash(
        self, session: Session, unit: BusinessUnit
    ):
        """This is RF-151's acceptance criterion: the hash is the device's staleness check, so if it
        did not move, the new policy would never reach a phone."""
        first = self.build(session, unit)
        before = first.content_hash
        policy.set_policy(session, unit, changes={"min_photos": 4}, actor=ACTOR)
        second = self.build(session, unit)
        assert second.content_hash != before
        assert second.version == first.version + 1
        assert first.superseded_at is not None

    def test_a_zone_policy_only_changes_that_zone_package(
        self, session: Session, unit: BusinessUnit
    ):
        north = self.build(session, unit, "NORTE")
        south = self.build(session, unit, "SUR")
        policy.set_policy(session, unit, zone_code="NORTE", changes={"min_photos": 7}, actor=ACTOR)
        assert self.build(session, unit, "NORTE").content_hash != north.content_hash
        assert self.build(session, unit, "SUR").content_hash == south.content_hash

    def test_rebuilding_without_changes_reuses_the_package(
        self, session: Session, unit: BusinessUnit
    ):
        """Otherwise every rebuild would make every device re-download for nothing."""
        first = self.build(session, unit)
        assert self.build(session, unit).id == first.id

    def test_every_policy_field_reaches_the_manifest(self, session: Session, unit: BusinessUnit):
        """A field added to the model and forgotten here would be a policy the phone never sees."""
        package = self.build(session, unit)
        assert set(package.manifest["capture_policy"]) == set(policy.FIELDS)


class TestAudioIsEnforcedOnTheServer:
    @pytest.fixture
    def response(self, session: Session, unit: BusinessUnit):
        ingest_metadata(session, unit, build_metadata("cnel-gye"))
        order = create_work_order(
            session,
            unit,
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
            longitude=-79.9,
            latitude=-2.17,
            planner_id="planner.a",
            zone="NORTE",
        )
        return save_answers(session, unit, order, answers={}, device_key="dev-1")

    def audio(self, session: Session, response):
        return register_evidence(
            session,
            response,
            kind=EvidenceKind.AUDIO,
            storage_key="audio/1.ogg",
            content_hash="a" * 64,
        )

    def test_audio_is_refused_when_the_area_does_not_keep_it(
        self, session: Session, unit: BusinessUnit, response
    ):
        """The default. Refused rather than stored-and-forgotten: an evidence row pointing at a file
        nobody keeps reads as kept audio in an audit."""
        with pytest.raises(AudioNotAllowedError):
            self.audio(session, response)

    def test_the_refusal_names_the_scope_that_decided(
        self, session: Session, unit: BusinessUnit, response
    ):
        policy.set_policy(session, unit, changes={"store_audio": True}, actor=ACTOR)
        policy.set_policy(
            session, unit, zone_code="NORTE", changes={"store_audio": False}, actor=ACTOR
        )
        with pytest.raises(AudioNotAllowedError) as raised:
            self.audio(session, response)
        assert policy.SOURCE_ZONE in str(raised.value)

    def test_audio_is_stored_when_the_area_keeps_it(
        self, session: Session, unit: BusinessUnit, response
    ):
        policy.set_policy(session, unit, changes={"store_audio": True}, actor=ACTOR)
        assert self.audio(session, response).kind == EvidenceKind.AUDIO

    def test_a_zone_may_allow_what_its_unit_refuses(
        self, session: Session, unit: BusinessUnit, response
    ):
        policy.set_policy(
            session, unit, zone_code="NORTE", changes={"store_audio": True}, actor=ACTOR
        )
        assert self.audio(session, response) is not None

    def test_a_photograph_is_never_held_back_by_the_audio_policy(
        self, session: Session, unit: BusinessUnit, response
    ):
        evidence = register_evidence(
            session,
            response,
            kind=EvidenceKind.PHOTO,
            storage_key="foto/1.jpg",
            content_hash="b" * 64,
        )
        assert evidence.kind == EvidenceKind.PHOTO


ADMIN = Principal(
    subject="kc|admin.funcional",
    username="admin.funcional",
    display_name="Administradora Funcional",
    roles=frozenset({Role.FUNCTIONAL_ADMIN.value}),
    business_units=frozenset({"GYE", "MAN"}),
)

SUPERVISOR = Principal(
    subject="kc|supervisor.demo",
    username="supervisor.demo",
    display_name="Supervisor Demo",
    roles=frozenset({Role.SUPERVISOR.value}),
    business_units=frozenset({"GYE"}),
)


@pytest.fixture
def client(session: Session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: ADMIN
    with TestClient(app) as raw:
        yield raw


class TestApi:
    def test_the_effective_view_names_the_origin_of_every_value(
        self, client, session: Session, unit: BusinessUnit
    ):
        policy.set_policy(session, unit, changes={"min_photos": 3}, actor=ACTOR)
        policy.set_policy(
            session, unit, zone_code="NORTE", changes={"photo_quality": 55}, actor=ACTOR
        )
        body = client.get("/api/v1/policies/units/GYE/effective?zone=NORTE").json()
        assert body["values"]["photo_quality"] == {"value": 55, "source": policy.SOURCE_ZONE}
        assert body["values"]["min_photos"] == {"value": 3, "source": policy.SOURCE_UNIT}
        assert body["values"]["downscale_on_metered"]["source"] == policy.SOURCE_DEFAULT

    def test_the_list_carries_the_defaults_so_the_screen_can_show_what_is_inherited(
        self, client, unit: BusinessUnit
    ):
        body = client.get("/api/v1/policies/units/GYE").json()
        assert body["defaults"]["store_audio"] is False
        assert body["fields"] == list(policy.FIELDS)

    def test_a_put_only_touches_the_fields_it_sends(
        self, client, session: Session, unit: BusinessUnit
    ):
        client.put("/api/v1/policies/units/GYE", json={"min_photos": 3, "photo_quality": 60})
        client.put("/api/v1/policies/units/GYE", json={"photo_quality": 70})
        body = client.get("/api/v1/policies/units/GYE/effective").json()
        assert body["values"]["min_photos"]["value"] == 3
        assert body["values"]["photo_quality"]["value"] == 70

    def test_an_explicit_null_over_the_wire_clears_the_field(
        self, client, session: Session, unit: BusinessUnit
    ):
        client.put("/api/v1/policies/units/GYE", json={"min_photos": 3})
        client.put("/api/v1/policies/units/GYE/zones/NORTE", json={"min_photos": 5})
        client.put("/api/v1/policies/units/GYE/zones/NORTE", json={"min_photos": None})
        body = client.get("/api/v1/policies/units/GYE/effective?zone=NORTE").json()
        assert body["values"]["min_photos"] == {"value": 3, "source": policy.SOURCE_UNIT}

    def test_an_invalid_value_comes_back_as_422_with_the_reason(self, client, unit: BusinessUnit):
        response = client.put("/api/v1/policies/units/GYE", json={"photo_quality": 140})
        assert response.status_code == 422
        assert "photo_quality" in str(response.json()["detail"])

    def test_deleting_a_zone_row_that_does_not_exist_is_404(self, client, unit: BusinessUnit):
        assert client.delete("/api/v1/policies/units/GYE/zones/NO-HAY").status_code == 404

    def test_the_unit_row_has_no_delete_endpoint(self, client, unit: BusinessUnit):
        """Removing it would move ten values to the defaults at once, unseen."""
        assert client.delete("/api/v1/policies/units/GYE").status_code == 405

    def test_a_supervisor_may_read_and_may_not_write(self, session: Session, unit: BusinessUnit):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: SUPERVISOR
        with TestClient(app) as supervisor:
            assert supervisor.get("/api/v1/policies/units/GYE/effective").status_code == 200
            refused = supervisor.put("/api/v1/policies/units/GYE", json={"min_photos": 9})
            assert refused.status_code == 403

    def test_another_units_policy_is_out_of_scope(self, session: Session, unit: BusinessUnit):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: SUPERVISOR
        with TestClient(app) as supervisor:
            assert supervisor.get("/api/v1/policies/units/MAN/effective").status_code == 403
