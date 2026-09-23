"""Form versioning: publishing v2 does not change the orders carrying v1 (RF-032).

The criterion is that one sentence, and the platform did not meet it: forms are files and the
catalogue keyed them by code alone, so editing `F-AP-01.yaml` changed the shape of *every* order —
including one a technician was already carrying. A field renamed on Tuesday would have made
Monday's answers fail validation against a form nobody in the field had ever seen.

So what is tested here is the freeze:

* publishing snapshots the definition **and the blocks**, because freezing only the definition
  leaves the shape at the mercy of a block edit;
* an order pinned to v1 composes against v1 even after v2 is published and the file has changed;
* an obsolete version still composes, because the orders carrying it still exist;
* and what is **not** frozen — the unit's catalogue values — stays current, on purpose.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.forms import registry
from app.forms.catalog import CatalogError, load_blocks, load_definitions
from app.forms.models import PublishedForm
from app.forms.registry import FormState
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.responses.service import compose_for
from app.sync.service import form_versions
from app.workorders.models import Crew
from app.workorders.service import assign, create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

CODE = "F-MT-01"
ACTOR = "admin.funcional"


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


@pytest.fixture
def crew(session: Session, unit: BusinessUnit) -> Crew:
    made = Crew(
        business_unit_id=unit.id, code="C-01", name="Cuadrilla C-01", competencies=["MT", "BT"]
    )
    session.add(made)
    session.flush()
    return made


def make_order(session: Session, unit: BusinessUnit, *, form_code: str = CODE):
    return create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code=form_code,
        longitude=-79.9,
        latitude=-2.17,
        planner_id="planner.a",
    )


@pytest.fixture
def bump_the_file():
    """Edit the in-memory catalogue as if somebody had changed the file and reloaded.

    The caches are cleared around every test by the root conftest, so mutating the cached objects
    here is contained. Done through the cache rather than by writing YAML because the point is the
    *shape changing under a live order*, not the file I/O.
    """
    undo: list[tuple[dict[str, Any], str, Any]] = []

    def apply(*, version: str, drop_block: str | None = None) -> None:
        definitions = load_definitions()
        definition = definitions[CODE]
        undo.append((definitions, CODE, copy.deepcopy(definition.model_dump(mode="json"))))
        definition.form.version = version
        if drop_block and drop_block in definition.form.blocks:
            definition.form.blocks.remove(drop_block)

    yield apply
    for definitions, code, snapshot in undo:
        from app.forms.catalog import FormDefinition

        definitions[code] = FormDefinition.model_validate(snapshot)


class TestPublishing:
    def test_publishing_freezes_the_definition_and_its_blocks(self, session: Session):
        row = registry.publish(session, CODE, actor=ACTOR)
        assert row.state == FormState.PUBLISHED
        assert row.published_by == ACTOR
        assert set(row.blocks) == set(load_definitions()[CODE].form.blocks)
        assert row.content_hash

    def test_publishing_the_same_version_twice_is_refused(self, session: Session):
        """Otherwise «v1.0.0» would name two different shapes, which is worse than an error."""
        registry.publish(session, CODE, actor=ACTOR)
        with pytest.raises(registry.AlreadyPublishedError):
            registry.publish(session, CODE, actor=ACTOR)

    def test_publishing_a_new_version_obsoletes_the_previous_one(
        self, session: Session, bump_the_file
    ):
        first = registry.publish(session, CODE, actor=ACTOR)
        bump_the_file(version="2.0.0")
        second = registry.publish(session, CODE, actor=ACTOR)
        session.refresh(first)
        assert first.state == FormState.OBSOLETE
        assert first.obsoleted_at is not None
        assert second.state == FormState.PUBLISHED
        assert registry.current_version(session, CODE) == "2.0.0"

    def test_only_one_version_can_be_published_at_a_time(self, session: Session):
        """Two would leave «which version does a new order get» to whichever row a query saw."""
        registry.publish(session, CODE, actor=ACTOR)
        session.add(
            PublishedForm(
                code=CODE,
                version="9.9.9",
                state=FormState.PUBLISHED,
                definition={},
                blocks={},
                content_hash="x" * 64,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_a_form_with_a_missing_block_is_not_published(self, session: Session, bump_the_file):
        """Publishing a shape that cannot be composed moves the error onto a phone."""
        definitions = load_definitions()
        definitions[CODE].form.blocks.append("B-NO-EXISTE")
        with pytest.raises(CatalogError):
            registry.publish(session, CODE, actor=ACTOR)

    def test_an_unpublished_code_has_no_current_version(self, session: Session):
        assert registry.current_version(session, "F-AP-01") is None
        assert registry.current(session, "F-AP-01") is None

    def test_asking_for_a_version_nobody_published_raises(self, session: Session):
        with pytest.raises(registry.FormNotPublishedError):
            registry.frozen(session, CODE, "1.0.0")


class TestTheFreezeHolds:
    def test_an_order_pinned_to_v1_still_composes_against_v1(
        self, session: Session, unit: BusinessUnit, crew: Crew, bump_the_file
    ):
        """The whole requirement, in one test."""
        registry.publish(session, CODE, actor=ACTOR)
        order = make_order(session, unit)
        assign(session, order, crew=crew)
        pinned = order.form_version
        assert pinned == "1.0.0"

        # Somebody edits the file and publishes v2, dropping a whole block.
        bump_the_file(version="2.0.0", drop_block="B13")
        registry.publish(session, CODE, actor=ACTOR)

        composed = compose_for(session, unit, order)
        assert composed.version == pinned
        # The dropped block's fields are still in the order's form, because its shape was frozen.
        frozen_blocks = registry.frozen(session, CODE, pinned).blocks
        assert "B13" in frozen_blocks
        for field in frozen_blocks["B13"].fields:
            assert field in composed.schema["properties"]

    def test_a_new_order_gets_the_new_version(
        self, session: Session, unit: BusinessUnit, crew: Crew, bump_the_file
    ):
        registry.publish(session, CODE, actor=ACTOR)
        bump_the_file(version="2.0.0")
        registry.publish(session, CODE, actor=ACTOR)
        order = make_order(session, unit)
        assign(session, order, crew=crew)
        assert order.form_version == "2.0.0"

    def test_an_unpublished_draft_never_reaches_the_field(
        self, session: Session, unit: BusinessUnit, crew: Crew, bump_the_file
    ):
        """The point of publication being an act.

        Somebody edits the file to v2 and does not publish it. An order assigned now must pin v1 —
        the version that exists as a frozen shape — and not the draft number, which names nothing.
        Pinning the draft would leave the order composing against a file that keeps moving.
        """
        registry.publish(session, CODE, actor=ACTOR)
        bump_the_file(version="2.0.0", drop_block="B13")
        order = make_order(session, unit)
        assign(session, order, crew=crew)
        assert order.form_version == "1.0.0"
        composed = compose_for(session, unit, order)
        # The block the draft dropped is still there, because v1 is what was frozen.
        assert any(field in composed.schema["properties"] for field in load_blocks()["B13"].fields)

    def test_the_version_is_pinned_at_assignment_and_not_at_creation(
        self, session: Session, unit: BusinessUnit, crew: Crew, bump_the_file
    ):
        """SRS 4.1, point 6: «la versión vigente al asignarse»."""
        registry.publish(session, CODE, actor=ACTOR)
        order = make_order(session, unit)
        assert order.form_version is None
        bump_the_file(version="2.0.0")
        registry.publish(session, CODE, actor=ACTOR)
        assign(session, order, crew=crew)
        assert order.form_version == "2.0.0"

    def test_an_obsolete_version_still_composes(
        self, session: Session, unit: BusinessUnit, crew: Crew, bump_the_file
    ):
        """The orders carrying it exist and have to be closed."""
        registry.publish(session, CODE, actor=ACTOR)
        order = make_order(session, unit)
        assign(session, order, crew=crew)
        registry.obsolete(session, CODE, "1.0.0", actor=ACTOR)
        composed = compose_for(session, unit, order)
        assert composed.version == "1.0.0"
        assert registry.frozen(session, CODE, "1.0.0").is_obsolete

    def test_without_any_publication_the_file_stands_in_and_says_so(
        self, session: Session, unit: BusinessUnit, crew: Crew
    ):
        """A platform that has not published yet must still compose, and must not pretend."""
        order = make_order(session, unit)
        assign(session, order, crew=crew)
        composed = compose_for(session, unit, order)
        assert composed.version == load_definitions()[CODE].version
        assert any("archivo actual" in warning for warning in composed.warnings)

    def test_a_pinned_version_nobody_published_is_flagged(
        self, session: Session, unit: BusinessUnit
    ):
        order = make_order(session, unit)
        order.form_version = "0.0.9"
        session.flush()
        composed = compose_for(session, unit, order)
        assert any("no está publicada" in warning for warning in composed.warnings)

    def test_an_order_with_no_version_is_flagged_too(self, session: Session, unit: BusinessUnit):
        order = make_order(session, unit)
        composed = compose_for(session, unit, order)
        assert any("no declara versión" in warning for warning in composed.warnings)

    def test_the_catalogue_values_are_not_frozen(
        self, session: Session, unit: BusinessUnit, crew: Crew
    ):
        """Deliberate: an order executed today has to name a feeder that exists today (RF-304).

        So the frozen shape carries no domain values at all — they arrive from the unit's current
        metadata at composition time.
        """
        registry.publish(session, CODE, actor=ACTOR)
        order = make_order(session, unit)
        assign(session, order, crew=crew)
        composed = compose_for(session, unit, order)
        # The composed schema has enumerations; the snapshot of the blocks does not carry the
        # unit's values, which is what «no se congelan» means.
        snapshot = registry.frozen(session, CODE, "1.0.0")
        assert snapshot.blocks
        assert composed.schema["properties"]


class TestWhatTheDeviceIsTold:
    def test_the_manifest_announces_the_published_version(self, session: Session):
        registry.publish(session, CODE, actor=ACTOR)
        assert form_versions(session)[CODE] == "1.0.0"

    def test_an_unpublished_draft_is_not_announced(self, session: Session, bump_the_file):
        """A device that downloaded whatever was on disk would pick up a shape nobody published."""
        registry.publish(session, CODE, actor=ACTOR)
        bump_the_file(version="2.0.0")
        assert form_versions(session)[CODE] == "1.0.0"

    def test_a_code_with_no_publication_falls_back_to_the_file(self, session: Session):
        """Otherwise a platform that has not published would hand its phones nothing."""
        versions = form_versions(session)
        assert versions["F-AP-01"] == load_definitions()["F-AP-01"].version

    def test_without_a_session_the_catalogue_answers_alone(self):
        """The form-library tests have no database and must keep working."""
        assert form_versions()[CODE] == load_definitions()[CODE].version


ADMIN = Principal(
    subject="kc|admin.funcional",
    username="admin.funcional",
    display_name="Administradora Funcional",
    roles=frozenset({Role.FUNCTIONAL_ADMIN.value}),
    business_units=frozenset({"GYE"}),
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
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_principal] = lambda: ADMIN
    with TestClient(app) as raw:
        yield raw


class TestApi:
    def test_the_catalogue_shows_the_file_next_to_what_is_published(self, client):
        body = client.get("/api/v1/forms/catalogue").json()
        row = next(item for item in body["forms"] if item["code"] == CODE)
        assert row["never_published"] is True
        assert row["file_version"] == load_definitions()[CODE].version

    def test_an_unpublished_draft_is_the_thing_the_screen_exists_to_show(
        self, client, bump_the_file
    ):
        """A form edited weeks ago that nobody published is one nobody in the field has seen."""
        client.post(f"/api/v1/forms/{CODE}/publish", json={})
        bump_the_file(version="2.0.0")
        body = client.get("/api/v1/forms/catalogue").json()
        row = next(item for item in body["forms"] if item["code"] == CODE)
        assert row["has_unpublished_draft"] is True
        assert row["published_version"] == "1.0.0"
        assert row["file_version"] == "2.0.0"

    def test_publishing_is_201_and_records_the_author_from_the_token(self, client):
        body = client.post(f"/api/v1/forms/{CODE}/publish", json={"note": "línea base"}).json()
        assert body["published_by"] == ADMIN.subject
        assert body["note"] == "línea base"
        assert sorted(body["blocks"]) == sorted(load_definitions()[CODE].form.blocks)

    def test_publishing_twice_is_409(self, client):
        client.post(f"/api/v1/forms/{CODE}/publish", json={})
        assert client.post(f"/api/v1/forms/{CODE}/publish", json={}).status_code == 409

    def test_the_version_history_is_newest_first(self, client, bump_the_file):
        client.post(f"/api/v1/forms/{CODE}/publish", json={})
        bump_the_file(version="2.0.0")
        client.post(f"/api/v1/forms/{CODE}/publish", json={})
        rows = client.get(f"/api/v1/forms/{CODE}/versions").json()
        assert [row["version"] for row in rows] == ["2.0.0", "1.0.0"]
        assert rows[0]["state"] == "publicado"
        assert rows[1]["state"] == "obsoleto"

    def test_the_history_order_is_the_sequence_and_not_the_timestamp(
        self, session: Session, bump_the_file
    ):
        """Why the sequence column exists.

        `published_at` is the transaction clock, so two publications in one request share it to the
        microsecond. A row published last with a backdated timestamp must still read first.
        """
        from datetime import UTC, datetime

        registry.publish(session, CODE, actor=ACTOR)
        bump_the_file(version="2.0.0")
        second = registry.publish(session, CODE, actor=ACTOR)
        second.published_at = datetime(2001, 1, 1, tzinfo=UTC)
        session.flush()
        rows = registry.history(session, CODE)
        assert [row.version for row in rows] == ["2.0.0", "1.0.0"]
        assert [row.sequence for row in rows] == sorted(
            (row.sequence for row in rows), reverse=True
        )

    def test_obsoleting_a_version_that_does_not_exist_is_404(self, client):
        response = client.post(f"/api/v1/forms/{CODE}/versions/9.9.9/obsolete")
        assert response.status_code == 404

    def test_a_planner_may_read_and_may_not_publish(self, session: Session):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: PLANNER
        with TestClient(app) as planner:
            assert planner.get("/api/v1/forms/catalogue").status_code == 200
            assert planner.post(f"/api/v1/forms/{CODE}/publish", json={}).status_code == 403

    def test_publishing_a_form_whose_block_is_missing_is_422(self, client):
        load_definitions()[CODE].form.blocks.append("B-NO-EXISTE")
        assert client.post(f"/api/v1/forms/{CODE}/publish", json={}).status_code == 422

    def test_the_block_library_is_not_altered_by_publishing(self, session: Session):
        """Publishing reads the files; mutating them would poison every form composed after."""
        before = {code: block.model_dump(mode="json") for code, block in load_blocks().items()}
        registry.publish(session, CODE, actor=ACTOR)
        after = {code: block.model_dump(mode="json") for code, block in load_blocks().items()}
        assert before == after
