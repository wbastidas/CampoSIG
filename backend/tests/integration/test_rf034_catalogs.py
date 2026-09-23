"""Administrable catalogues, versioned, with a delta download (RF-034).

The gap this closes was not a missing feature but a dangling reference: the blocks already said
``x-catalog-ref: defect`` and ``x-catalog-ref: activity``, and **nothing served either list**. A
phone rendering the findings block had a code field and no values to choose from.

So the most valuable test in this file is the guard: every `x-catalog-ref` in `forms/` must be
servable by something — a catalogue here, the unit's synced GIS metadata, or the profile's enums. It
is what would have caught the gap, and it is what stops the next block from re-opening it.

The rest is about the delta being trustworthy:

* a retired value travels as a tombstone, or a phone offers a withdrawn code forever;
* the revision is monotonic and comes from the database, so «since» actually means something;
* a capped batch says it was capped, because a silent cap leaves a phone permanently missing a tail;
* and a device never receives another unit's additions (ADR-009).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal
from app.auth.principal import Principal, Role
from app.catalogs import service as catalogs
from app.catalogs.loader import apply_seeds, load_files, missing_for_forms, seeds_root, validate
from app.catalogs.models import Catalog, CatalogEntry, CatalogSource
from app.forms.catalog import forms_root
from app.infra.database import get_session
from app.main import create_app
from app.model_profile.amd import load_asset_model
from app.org.models import BusinessUnit, Organization
from app.sync.service import build_offline_package

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


@pytest.fixture
def seeded(session: Session) -> dict[str, int]:
    written = apply_seeds(session)
    session.flush()
    return written


def make_catalog(
    session: Session, code: str, *, source: str = CatalogSource.MANUAL, note: str | None = None
) -> Catalog:
    catalog = Catalog(code=code, title=f"Catálogo {code}", source=source, note=note)
    session.add(catalog)
    session.flush()
    return catalog


class TestTheGuardOverForms:
    """The test that would have caught the gap, and that stops it reopening."""

    def catalog_refs(self) -> set[str]:
        """Every `x-catalog-ref` written by hand in the block library.

        Read from the YAML rather than from a list in the test: a list would have to be kept in step
        with the blocks, and the whole point is that nothing needs keeping in step.
        """
        refs: set[str] = set()
        for path in sorted((forms_root() / "blocks").rglob("*.yaml")):
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            refs |= self._walk(document)
        return refs

    def _walk(self, node: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(node, dict):
            ref = node.get("x-catalog-ref")
            if isinstance(ref, str):
                found.add(ref)
            for value in node.values():
                found |= self._walk(value)
        elif isinstance(node, list):
            for item in node:
                found |= self._walk(item)
        return found

    def test_the_blocks_do_reference_catalogues(self):
        """A guard over an empty set proves nothing."""
        assert len(self.catalog_refs()) >= 10

    def test_every_reference_can_be_served(self, session: Session, seeded):
        """A reference nothing serves is a picker with no values."""
        profile_enums = set(load_asset_model().enums)
        missing = missing_for_forms(session, self.catalog_refs(), profile_enums)
        assert missing == [], f"referencias sin catálogo: {', '.join(missing)}"

    def test_the_guard_notices_a_new_dangling_reference(self, session: Session, seeded):
        """Negative test of the guard itself."""
        profile_enums = set(load_asset_model().enums)
        refs = self.catalog_refs() | {"catalogo.inventado"}
        assert missing_for_forms(session, refs, profile_enums) == ["catalogo.inventado"]

    def test_the_gis_backed_ones_are_not_expected_here(self, session: Session, seeded):
        """`feeder` and `substation` come from the unit's sync, not from this table (RF-304)."""
        assert "feeder" not in catalogs.known_codes(session)
        assert "feeder" in catalogs.GIS_BACKED


class TestTheSeeds:
    def test_the_seed_directory_validates(self):
        assert validate(load_files()) == []

    def test_loading_is_idempotent(self, session: Session):
        first = apply_seeds(session)
        before = len(list(session.query(CatalogEntry)))
        second = apply_seeds(session)
        after = len(list(session.query(CatalogEntry)))
        assert first == second
        assert before == after

    def test_an_empty_catalogue_must_explain_itself(self, tmp_path: Path):
        """An empty picker with no explanation reads as a broken form."""
        (tmp_path / "x.yaml").write_text(
            "catalog:\n  code: vacio\n  title: Vacío\nentries: []\n", encoding="utf-8"
        )
        problems = validate(load_files(tmp_path))
        assert any("sin `note`" in problem for problem in problems)

    def test_an_empty_catalogue_with_a_note_is_accepted(self, tmp_path: Path):
        """The political division is deliberately empty: inventing it would be worse."""
        (tmp_path / "x.yaml").write_text(
            "catalog:\n  code: vacio\n  title: V\n  note: falta la lista oficial\nentries: []\n",
            encoding="utf-8",
        )
        assert validate(load_files(tmp_path)) == []

    def test_two_catalogues_with_one_code_are_refused(self, tmp_path: Path):
        (tmp_path / "a.yaml").write_text(
            "catalog: {code: dup, title: A}\nentries: [{code: x, label: X}]\n", encoding="utf-8"
        )
        (tmp_path / "b.yaml").write_text(
            "catalog: {code: dup, title: B}\nentries: [{code: y, label: Y}]\n", encoding="utf-8"
        )
        assert any("ya venía" in problem for problem in validate(load_files(tmp_path)))

    def test_a_repeated_value_is_refused(self, tmp_path: Path):
        (tmp_path / "a.yaml").write_text(
            "catalog: {code: c, title: C}\nentries: [{code: x, label: X}, {code: x, label: Y}]\n",
            encoding="utf-8",
        )
        assert any("repite el valor" in problem for problem in validate(load_files(tmp_path)))

    def test_nothing_is_written_when_the_seeds_are_invalid(self, session: Session, tmp_path: Path):
        """Half a catalogue is worse than none: the missing half looks retired on purpose."""
        (tmp_path / "a.yaml").write_text(
            "catalog: {code: bueno, title: Bueno}\nentries: [{code: x, label: X}]\n",
            encoding="utf-8",
        )
        (tmp_path / "b.yaml").write_text("catalog: {code: malo}\nentries: []\n", encoding="utf-8")
        with pytest.raises(catalogs.CatalogError):
            apply_seeds(session, root=tmp_path)
        assert session.query(Catalog).filter(Catalog.code == "bueno").one_or_none() is None

    def test_reloading_does_not_retire_what_the_file_omits(self, session: Session, tmp_path: Path):
        """An incomplete file must not be able to empty a catalogue in production."""
        path = tmp_path / "a.yaml"
        path.write_text(
            "catalog: {code: c, title: C}\nentries: [{code: x, label: X}, {code: y, label: Y}]\n",
            encoding="utf-8",
        )
        apply_seeds(session, root=tmp_path)
        path.write_text(
            "catalog: {code: c, title: C}\nentries: [{code: x, label: X}]\n", encoding="utf-8"
        )
        apply_seeds(session, root=tmp_path)
        assert {item.code for item in catalogs.resolve(session, "c").entries} == {"x", "y"}

    def test_retiring_the_missing_ones_is_explicit(self, session: Session, tmp_path: Path):
        path = tmp_path / "a.yaml"
        path.write_text(
            "catalog: {code: c, title: C}\nentries: [{code: x, label: X}, {code: y, label: Y}]\n",
            encoding="utf-8",
        )
        apply_seeds(session, root=tmp_path)
        path.write_text(
            "catalog: {code: c, title: C}\nentries: [{code: x, label: X}]\n", encoding="utf-8"
        )
        apply_seeds(session, root=tmp_path, retire_missing=True)
        assert {item.code for item in catalogs.resolve(session, "c").entries} == {"x"}

    def test_the_seed_files_carry_synonyms_for_the_lexicon(self, session: Session, seeded):
        """They feed the ASR (ADR-011): that is why they are data and not a table in the code."""
        found = catalogs.resolve(session, "defect")
        assert any(entry.synonyms for entry in found.entries)

    def test_a_defect_suggests_a_criticality_and_does_not_decide_it(self, session: Session, seeded):
        """The form asks and the person confirms: a criticality nobody chose is not a decision."""
        found = catalogs.resolve(session, "defect")
        suggested = [
            entry for entry in found.entries if "suggested_criticality" in entry.attributes
        ]
        assert suggested
        assert all("criticality" not in entry.attributes for entry in found.entries)


class TestResolution:
    def test_only_the_active_values_come_back(self, session: Session):
        make_catalog(session, "c")
        catalogs.upsert_entry(session, "c", entry_code="x", label="X", actor=ACTOR)
        catalogs.upsert_entry(session, "c", entry_code="y", label="Y", actor=ACTOR)
        catalogs.retire_entry(session, "c", "y", actor=ACTOR)
        assert [item.code for item in catalogs.resolve(session, "c").entries] == ["x"]

    def test_the_order_is_the_declared_one(self, session: Session):
        make_catalog(session, "c")
        catalogs.upsert_entry(session, "c", entry_code="b", label="B", sort_order=2, actor=ACTOR)
        catalogs.upsert_entry(session, "c", entry_code="a", label="A", sort_order=1, actor=ACTOR)
        assert [item.code for item in catalogs.resolve(session, "c").entries] == ["a", "b"]

    def test_a_units_value_is_added_to_the_national_list(self, session: Session, unit):
        make_catalog(session, "c")
        catalogs.upsert_entry(session, "c", entry_code="nacional", label="Nacional", actor=ACTOR)
        catalogs.upsert_entry(
            session, "c", entry_code="propio", label="Propio", unit=unit, actor=ACTOR
        )
        found = catalogs.resolve(session, "c", unit)
        assert {item.code for item in found.entries} == {"nacional", "propio"}
        assert next(item for item in found.entries if item.code == "propio").local is True

    def test_a_units_value_overrides_the_national_one_of_the_same_code(
        self, session: Session, unit
    ):
        """Two rows with one code in a picker is a bug a technician sees."""
        make_catalog(session, "c")
        catalogs.upsert_entry(session, "c", entry_code="x", label="Nacional", actor=ACTOR)
        catalogs.upsert_entry(
            session, "c", entry_code="x", label="Como lo llamamos aquí", unit=unit, actor=ACTOR
        )
        found = catalogs.resolve(session, "c", unit)
        assert len(found.entries) == 1
        assert found.entries[0].label == "Como lo llamamos aquí"
        assert found.entries[0].local is True

    def test_another_units_value_is_not_visible(self, session: Session, units):
        make_catalog(session, "c")
        catalogs.upsert_entry(
            session, "c", entry_code="ajeno", label="Ajeno", unit=units["MAN"], actor=ACTOR
        )
        assert catalogs.resolve(session, "c", units["GYE"]).entries == []

    def test_without_a_unit_only_the_national_list_answers(self, session: Session, unit):
        make_catalog(session, "c")
        catalogs.upsert_entry(session, "c", entry_code="n", label="N", actor=ACTOR)
        catalogs.upsert_entry(session, "c", entry_code="p", label="P", unit=unit, actor=ACTOR)
        assert [item.code for item in catalogs.resolve(session, "c").entries] == ["n"]

    def test_an_unknown_catalogue_raises(self, session: Session):
        with pytest.raises(catalogs.UnknownCatalogError):
            catalogs.resolve(session, "no-existe")

    def test_an_empty_catalogue_says_it_is_empty_and_why(self, session: Session, seeded):
        found = catalogs.resolve(session, "administrative.canton")
        assert found.is_empty
        assert found.note and "INEC" in found.note

    def test_two_national_rows_with_one_code_are_refused_by_the_database(self, session: Session):
        """The unique constraint does not cover them: PostgreSQL treats nulls as distinct."""
        make_catalog(session, "c")
        catalogs.upsert_entry(session, "c", entry_code="x", label="X", actor=ACTOR)
        session.add(CatalogEntry(catalog_code="c", code="x", label="Otra"))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


class TestTheDelta:
    def test_a_device_with_nothing_gets_everything(self, session: Session, seeded, unit):
        found = catalogs.delta(session, since=0, unit=unit)
        assert len(found.changes) > 50
        assert found.revision > 0

    def test_asking_from_the_last_revision_returns_nothing(self, session: Session, seeded, unit):
        first = catalogs.delta(session, since=0, unit=unit)
        second = catalogs.delta(session, since=first.revision, unit=unit)
        assert second.changes == []
        assert second.revision == first.revision

    def test_a_retired_value_travels_as_a_tombstone(self, session: Session, unit):
        """Without it a phone keeps offering a code the utility withdrew, and nobody notices."""
        make_catalog(session, "c")
        catalogs.upsert_entry(session, "c", entry_code="x", label="X", actor=ACTOR)
        mark = catalogs.delta(session, since=0, unit=unit).revision
        catalogs.retire_entry(session, "c", "x", actor=ACTOR)
        found = catalogs.delta(session, since=mark, unit=unit)
        assert [(item["code"], item["active"]) for item in found.changes] == [("x", False)]

    def test_an_edited_label_travels_too(self, session: Session, unit):
        make_catalog(session, "c")
        catalogs.upsert_entry(session, "c", entry_code="x", label="Antes", actor=ACTOR)
        mark = catalogs.delta(session, since=0, unit=unit).revision
        catalogs.upsert_entry(session, "c", entry_code="x", label="Después", actor=ACTOR)
        found = catalogs.delta(session, since=mark, unit=unit)
        assert [item["label"] for item in found.changes] == ["Después"]

    def test_the_revision_is_monotonic_across_edits(self, session: Session, unit):
        """The trigger, not the service: an entry written by the ERP connector needs one too."""
        make_catalog(session, "c")
        first = catalogs.upsert_entry(session, "c", entry_code="x", label="X", actor=ACTOR)
        firstrev = first.revision
        session.expire(first)
        catalogs.upsert_entry(session, "c", entry_code="x", label="X2", actor=ACTOR)
        session.refresh(first)
        assert first.revision > firstrev

    def test_a_capped_batch_says_so(self, session: Session, unit):
        """A silent cap leaves a phone permanently missing the tail of a catalogue."""
        make_catalog(session, "c")
        for index in range(5):
            catalogs.upsert_entry(
                session, "c", entry_code=f"x{index}", label=f"X{index}", actor=ACTOR
            )
        found = catalogs.delta(session, since=0, unit=unit, limit=2)
        assert len(found.changes) == 2
        assert found.more is True
        rest = catalogs.delta(session, since=found.revision, unit=unit, limit=10)
        assert rest.more is False

    def test_a_device_never_receives_another_units_additions(self, session: Session, units):
        make_catalog(session, "c")
        catalogs.upsert_entry(
            session, "c", entry_code="ajeno", label="Ajeno", unit=units["MAN"], actor=ACTOR
        )
        found = catalogs.delta(session, since=0, unit=units["GYE"])
        assert found.changes == []

    def test_the_delta_can_be_limited_to_the_catalogues_that_moved(self, session: Session, unit):
        make_catalog(session, "a")
        make_catalog(session, "b")
        catalogs.upsert_entry(session, "a", entry_code="x", label="X", actor=ACTOR)
        catalogs.upsert_entry(session, "b", entry_code="y", label="Y", actor=ACTOR)
        found = catalogs.delta(session, since=0, unit=unit, codes=["a"])
        assert {item["catalog"] for item in found.changes} == {"a"}


class TestVersions:
    def test_a_change_bumps_the_catalogues_version(self, session: Session):
        catalog = make_catalog(session, "c")
        before = catalog.version
        catalogs.upsert_entry(session, "c", entry_code="x", label="X", actor=ACTOR)
        session.refresh(catalog)
        assert catalog.version > before

    def test_retiring_bumps_it_too(self, session: Session):
        catalog = make_catalog(session, "c")
        catalogs.upsert_entry(session, "c", entry_code="x", label="X", actor=ACTOR)
        session.refresh(catalog)
        before = catalog.version
        catalogs.retire_entry(session, "c", "x", actor=ACTOR)
        session.refresh(catalog)
        assert catalog.version > before

    def test_retiring_something_already_retired_changes_nothing(self, session: Session):
        catalog = make_catalog(session, "c")
        catalogs.upsert_entry(session, "c", entry_code="x", label="X", actor=ACTOR)
        catalogs.retire_entry(session, "c", "x", actor=ACTOR)
        session.refresh(catalog)
        before = catalog.version
        catalogs.retire_entry(session, "c", "x", actor=ACTOR)
        session.refresh(catalog)
        assert catalog.version == before

    def test_the_manifest_carries_one_version_per_catalogue(self, session: Session, seeded, unit):
        package = build_offline_package(
            session, unit, zone="NORTE", tile_url="/tiles/n.pmtiles", asset_count=1
        )
        carried = package.manifest["catalog_versions"]
        assert carried["defect"] >= 1
        assert set(carried) == catalogs.known_codes(session)

    def test_a_catalogue_change_changes_the_package_hash(self, session: Session, seeded, unit):
        first = build_offline_package(
            session, unit, zone="NORTE", tile_url="/tiles/n.pmtiles", asset_count=1
        )
        before = first.content_hash
        catalogs.upsert_entry(session, "defect", entry_code="nuevo", label="Nuevo", actor=ACTOR)
        second = build_offline_package(
            session, unit, zone="NORTE", tile_url="/tiles/n.pmtiles", asset_count=1
        )
        assert second.content_hash != before


class TestOwnership:
    def test_a_catalogue_the_erp_owns_refuses_a_hand_edit(self, session: Session, seeded):
        """A value typed over one the connector overwrites tonight vanishes unexplained."""
        with pytest.raises(catalogs.NotEditableError):
            catalogs.upsert_entry(
                session, "material", entry_code="x", label="Inventado", actor=ACTOR
            )

    def test_the_connector_may_write_it(self, session: Session, seeded):
        row = catalogs.upsert_entry(
            session,
            "material",
            entry_code="POSTE-HC-9",
            label="Poste de hormigón 9 m",
            actor="conector.erp",
            from_integration=True,
        )
        assert row.code == "POSTE-HC-9"

    def test_the_seed_may_create_an_integration_catalogue(self, session: Session, seeded):
        """It is how the catalogue exists before the connector's first delivery."""
        assert "material" in catalogs.known_codes(session)
        assert catalogs.resolve(session, "material").source == CatalogSource.INTEGRATION


ADMIN = Principal(
    subject="kc|admin.funcional",
    username="admin.funcional",
    display_name="Administradora Funcional",
    roles=frozenset({Role.FUNCTIONAL_ADMIN.value}),
    business_units=frozenset({"GYE", "MAN"}),
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
    app.dependency_overrides[current_principal] = lambda: ADMIN
    with TestClient(app) as raw:
        yield raw


class TestApi:
    def test_the_index_shows_the_version_and_whether_it_is_empty(self, client, session, seeded):
        body = client.get("/api/v1/catalogs/").json()
        by_code = {row["code"]: row for row in body["catalogs"]}
        assert by_code["defect"]["active_entries"] > 10
        assert by_code["administrative.canton"]["empty"] is True
        assert by_code["administrative.canton"]["note"]
        assert "feeder" in body["gis_backed"]

    def test_a_technician_may_read_the_resolved_list(self, session: Session, unit, seeded):
        """It is what the phone's picker needs."""
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: TECHNICIAN
        with TestClient(app) as technician:
            response = technician.get("/api/v1/catalogs/units/GYE/catalog/defect")
            assert response.status_code == 200
            assert response.json()["entries"]

    def test_a_technician_may_not_write(self, session: Session, unit, seeded):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: TECHNICIAN
        with TestClient(app) as technician:
            response = technician.put(
                "/api/v1/catalogs/catalog/defect/entries/x", json={"code": "x", "label": "X"}
            )
            assert response.status_code == 403

    def test_the_delta_endpoint_carries_the_next_revision(self, client, unit, seeded):
        body = client.get("/api/v1/catalogs/units/GYE/delta?since=0&limit=5").json()
        assert len(body["changes"]) == 5
        assert body["more"] is True
        assert body["revision"] > 0

    def test_the_delta_path_cannot_be_shadowed_by_a_catalogue_code(
        self, client, session, unit, seeded
    ):
        """Why the routes carry a literal `catalog/` segment.

        Without it, `/units/GYE/delta` matched `/units/{unit_code}/{catalog_code}` and a device's
        delta resolved to the non-existent catalogue «delta». Ordering the routes would have hidden
        it until somebody created a catalogue called that.
        """
        make_catalog(session, "delta", note="un catálogo llamado como un verbo")
        session.flush()
        body = client.get("/api/v1/catalogs/units/GYE/delta?since=0").json()
        assert "changes" in body
        assert client.get("/api/v1/catalogs/units/GYE/catalog/delta").json()["code"] == "delta"

    def test_a_code_mismatch_between_route_and_body_is_refused(self, client, seeded):
        response = client.put(
            "/api/v1/catalogs/catalog/defect/entries/uno", json={"code": "otro", "label": "X"}
        )
        assert response.status_code == 422

    def test_editing_an_integration_catalogue_is_409(self, client, seeded):
        response = client.put(
            "/api/v1/catalogs/catalog/material/entries/x", json={"code": "x", "label": "X"}
        )
        assert response.status_code == 409

    def test_retiring_a_value_that_does_not_exist_is_404(self, client, seeded):
        assert client.delete("/api/v1/catalogs/catalog/defect/entries/no-hay").status_code == 404

    def test_an_unknown_catalogue_is_404(self, client, unit, seeded):
        assert client.get("/api/v1/catalogs/units/GYE/catalog/no-existe").status_code == 404

    def test_another_units_catalogue_is_out_of_scope(self, session: Session, units, seeded):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[current_principal] = lambda: TECHNICIAN
        with TestClient(app) as technician:
            assert technician.get("/api/v1/catalogs/units/MAN/catalog/defect").status_code == 403


def test_the_seed_readme_names_the_command_it_documents():
    """A README naming a command that did not exist happened once already, in the seeds."""
    text = (seeds_root() / "README.md").read_text(encoding="utf-8")
    assert "app.catalogs.cli" in text
    assert re.search(r"--dry-run", text)
