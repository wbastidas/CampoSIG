"""The living technical dictionary, and that it actually reaches the decoder (RF-147).

The criterion is «un término añadido llega al móvil en el siguiente sync de catálogos», and the gap
was a disconnection rather than an absence: the catalogue entries of RF-034 already carried
`synonyms`, and the lexicon builder never read them. A field whose values live in a platform
catalogue — a defect, an activity — produced **no hotwords at all**, so a technician dictating
«cruceta podrida» had nothing to be pushed towards.

So the tests follow the whole path: a synonym added in the catalogue becomes a hotword and an alias
in the lexicon, changes the lexicon's content hash, and rides the catalogue delta and the package
hash to the phone. And the failure mode is named out loud: a field pointing at an empty catalogue
warns, because otherwise the symptom is «the decoder is broken» rather than «the list is empty».
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.catalogs import service as catalogs
from app.catalogs.loader import apply_seeds
from app.forms.composer import FormComposer
from app.gis_gateway.ingest import ingest_metadata
from app.model_profile.metadata import GisMetadata
from app.model_profile.resolver import ModelResolver
from app.org.models import BusinessUnit, Organization
from app.org.service import context_for_unit
from app.sync.service import build_offline_package
from app.voice.lexicon import VoiceLexicon, build_lexicon
from app.voice.service import build_lexicon_for, lexicon_for_order
from app.voice.vocabulary import VOCABULARY_CATALOG, VocabularyTerms, collect
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
    for unit in created.values():
        ingest_metadata(session, unit, build_metadata("cnel-gye"))
    return created


@pytest.fixture
def unit(units: dict[str, BusinessUnit]) -> BusinessUnit:
    return units["GYE"]


@pytest.fixture
def seeded(session: Session) -> None:
    apply_seeds(session)
    session.flush()


def context_of(session: Session, unit: BusinessUnit) -> tuple[ModelResolver, GisMetadata | None]:
    return context_for_unit(session, unit)


def compose(session: Session, unit: BusinessUnit, code: str = "F-MT-01"):
    resolver, metadata = context_of(session, unit)
    return FormComposer(resolver, metadata).compose(code, "support_structure")


def lexicon_of(
    session: Session, unit: BusinessUnit, *, with_terms: bool = True, code: str = "F-MT-01"
) -> VoiceLexicon:
    resolver, metadata = context_of(session, unit)
    form = compose(session, unit, code)
    return build_lexicon_for(
        resolver,
        metadata,
        form,
        terms=collect(session, unit) if with_terms else None,
    )


def make_order(session: Session, unit: BusinessUnit):
    return create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        longitude=-79.9,
        latitude=-2.17,
        planner_id="planner.a",
    )


def hotword_texts(lexicon: VoiceLexicon) -> set[str]:
    return {item.text for item in lexicon.hotwords}


class TestCollecting:
    def test_a_values_synonyms_become_its_spoken_forms(self, session: Session, seeded):
        terms = collect(session)
        aliases = terms.aliases_for("defect")
        assert "cruceta_podrida" in aliases
        # The label leads because it is what the utility calls the thing; the synonyms follow.
        assert aliases["cruceta_podrida"][0] == "cruceta deteriorada"
        assert "cruceta podrida" in aliases["cruceta_podrida"]

    def test_a_vocabulary_entry_with_a_field_is_a_cue(self, session: Session, seeded):
        terms = collect(session)
        assert "condicion general" in terms.field_cues["general_condition"]

    def test_a_vocabulary_entry_without_a_field_is_a_plain_term(self, session: Session, seeded):
        terms = collect(session)
        assert "bushing" in terms.terms
        assert all("bushing" not in cues for cues in terms.field_cues.values())

    def test_the_vocabulary_catalogue_is_not_an_alias_source(self, session: Session, seeded):
        """Its entries are cues and terms, not values of a form field."""
        assert collect(session).aliases_for(VOCABULARY_CATALOG) == {}

    def test_a_units_own_word_is_collected_for_that_unit_only(
        self, session: Session, units, seeded
    ):
        """A word only one unit uses is exactly the one a national list would never carry."""
        catalogs.upsert_entry(
            session,
            "defect",
            entry_code="cruceta_podrida",
            label="Cruceta deteriorada",
            synonyms=["cruceta jodida"],
            unit=units["GYE"],
            actor=ACTOR,
        )
        assert (
            "cruceta jodida"
            in collect(session, units["GYE"]).aliases_for("defect")["cruceta_podrida"]
        )
        assert (
            "cruceta jodida"
            not in collect(session, units["MAN"]).aliases_for("defect")["cruceta_podrida"]
        )

    def test_nothing_loaded_means_an_empty_dictionary_and_not_an_error(self, session: Session):
        assert collect(session).is_empty


class TestTheLexiconUsesIt:
    def test_a_catalogue_backed_field_had_no_hotwords_and_now_has_them(
        self, session: Session, unit, seeded
    ):
        """The gap, stated as a test: without the dictionary the field is undictatable."""
        without = lexicon_of(session, unit, with_terms=False)
        with_terms = lexicon_of(session, unit)
        assert "delay_reason" not in without.value_aliases
        assert "delay_reason" in with_terms.value_aliases
        assert "habia trafico" in hotword_texts(with_terms)

    def test_the_codes_travel_so_a_proposal_can_name_one(self, session: Session, unit, seeded):
        found = lexicon_of(session, unit)
        assert "trafico" in found.codes_for("delay_reason")

    def test_a_value_inside_a_repeatable_table_is_a_hotword_and_not_an_alias(
        self, session: Session, unit, seeded
    ):
        """Two different needs, deliberately kept apart.

        `value_aliases` is the extractor's contract and covers what one dictation can fill; a table
        is filled entry by entry, so a defect does not belong there. The **decoder** still has to
        have heard «cruceta podrida», and before RF-147 it had not — which left the whole findings
        block undictatable while looking like a decoder problem.
        """
        found = lexicon_of(session, unit)
        assert "cruceta podrida" in hotword_texts(found)
        assert "defect_code" not in found.value_aliases
        assert "defects" not in found.value_aliases

    def test_an_administrable_cue_extends_the_canonical_ones(self, session: Session, unit, seeded):
        """It extends rather than displaces: the canonical layer defines what «canonical» means."""
        found = lexicon_of(session, unit)
        cues = found.field_cues.get("material", [])
        assert "material" in cues  # canonical, from profiles/amd/voice-es-EC.yaml
        catalogs.upsert_entry(
            session,
            VOCABULARY_CATALOG,
            entry_code="cue.material.local",
            label="de que esta hecho",
            synonyms=["con que lo hicieron"],
            attributes={"field": "material"},
            actor=ACTOR,
        )
        after = lexicon_of(session, unit)
        assert "material" in after.field_cues["material"]
        assert "de que esta hecho" in after.field_cues["material"]

    def test_a_plain_term_is_boosted_even_though_it_fills_nothing(
        self, session: Session, unit, seeded
    ):
        assert "tirafusible" in hotword_texts(lexicon_of(session, unit))

    def test_adding_a_synonym_changes_the_lexicon_hash(self, session: Session, unit, seeded):
        """What makes the download cheap is also what proves the term arrived."""
        before = lexicon_of(session, unit).content_hash
        catalogs.upsert_entry(
            session,
            "defect",
            entry_code="cruceta_podrida",
            label="Cruceta deteriorada",
            synonyms=["cruceta podrida", "cruceta hecha polvo"],
            actor=ACTOR,
        )
        assert lexicon_of(session, unit).content_hash != before

    def test_a_field_pointing_at_an_empty_catalogue_warns(self, session: Session, unit, seeded):
        """Otherwise the symptom is «the decoder is broken», not «the list is empty»."""
        for entry in list(catalogs.resolve(session, "defect").entries):
            catalogs.retire_entry(session, "defect", entry.code, actor=ACTOR)
        found = lexicon_of(session, unit)
        assert any("'defect'" in warning for warning in found.warnings)

    def test_the_empty_political_division_is_reported_too(self, session: Session, unit, seeded):
        """It is deliberately empty, and the lexicon still has to say the field cannot be heard."""
        found = lexicon_of(session, unit)
        assert any("administrative." in warning for warning in found.warnings)

    def test_the_order_lexicon_collects_the_dictionary_by_itself(
        self, session: Session, unit, seeded
    ):
        """`lexicon_for_order` is the one place with both a session and a unit."""
        order = make_order(session, unit)
        found = lexicon_for_order(session, unit, order)
        assert "cruceta podrida" in hotword_texts(found)

    def test_a_retired_value_stops_being_a_hotword(self, session: Session, unit, seeded):
        catalogs.retire_entry(session, "defect", "cruceta_podrida", actor=ACTOR)
        assert "cruceta podrida" not in hotword_texts(lexicon_of(session, unit))

    def test_building_without_a_session_still_works(self, session: Session, unit, seeded):
        """The offline-package builder and the mobile contract tests have no dictionary."""
        resolver, metadata = context_of(session, unit)
        form = compose(session, unit)
        found = build_lexicon(
            resolver,
            metadata,
            form_code=form.code,
            form_version=form.version,
            schema=form.schema,
            asset_type_key="support_structure",
        )
        assert found.hotwords

    def test_an_empty_dictionary_behaves_like_none(self, session: Session, unit, seeded):
        resolver, metadata = context_of(session, unit)
        form = compose(session, unit)
        empty = build_lexicon(
            resolver,
            metadata,
            form_code=form.code,
            form_version=form.version,
            schema=form.schema,
            terms=VocabularyTerms(),
        )
        none = build_lexicon(
            resolver,
            metadata,
            form_code=form.code,
            form_version=form.version,
            schema=form.schema,
        )
        assert empty.content_hash == none.content_hash


class TestItReachesTheDevice:
    def test_a_new_term_changes_the_package_hash(self, session: Session, unit, seeded):
        """«Llega al móvil en el siguiente sync de catálogos», made checkable."""
        first = build_offline_package(
            session, unit, zone="NORTE", tile_url="/tiles/n.pmtiles", asset_count=1
        )
        before = first.content_hash
        catalogs.upsert_entry(
            session,
            VOCABULARY_CATALOG,
            entry_code="term.nuevo",
            label="palabra nueva del sector",
            actor=ACTOR,
        )
        second = build_offline_package(
            session, unit, zone="NORTE", tile_url="/tiles/n.pmtiles", asset_count=1
        )
        assert second.content_hash != before

    def test_a_new_term_travels_in_the_delta(self, session: Session, unit, seeded):
        mark = catalogs.delta(session, since=0, unit=unit).revision
        catalogs.upsert_entry(
            session,
            VOCABULARY_CATALOG,
            entry_code="term.nuevo",
            label="palabra nueva",
            synonyms=["como la dicen aquí"],
            actor=ACTOR,
        )
        found = catalogs.delta(session, since=mark, unit=unit)
        assert [item["code"] for item in found.changes] == ["term.nuevo"]
        assert "como la dicen aquí" in found.changes[0]["synonyms"]

    def test_the_vocabulary_catalogue_has_its_own_version(self, session: Session, seeded):
        assert catalogs.versions(session)[VOCABULARY_CATALOG] >= 1
