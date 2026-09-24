"""The lexicon generated from the profile and the work order (RF-331, RF-332, RF-304).

Every assertion here must hold under both data-model profiles, which is why nothing in the
file names a real class, field or domain: the lexicon is derived, and a test that hard-codes
one utility's wording would be testing the fixture.
"""

from __future__ import annotations

import copy

import pytest

from app.forms.generator import FormGenerator
from app.model_profile.metadata import GisMetadata
from app.model_profile.profile import load_profile
from app.model_profile.resolver import ModelResolver
from app.voice.lexicon import (
    SOURCE_VOLATILE_DOMAIN,
    SOURCE_WORK_ORDER,
    OrderContext,
    build_lexicon,
    load_spoken_vocabulary,
)
from app.voice.normalizer import strip_accents
from tests.conftest import ALL_PROFILE_IDS, build_metadata


@pytest.fixture(params=ALL_PROFILE_IDS)
def profile_id(request: pytest.FixtureRequest) -> str:
    return str(request.param)


@pytest.fixture
def parts(profile_id: str):
    resolver = ModelResolver(load_profile(profile_id))
    metadata = build_metadata(profile_id)
    generated = FormGenerator(resolver, metadata).generate("distribution_transformer")
    return resolver, metadata, generated


def _lexicon(parts, context: OrderContext | None = None):
    resolver, metadata, generated = parts
    return build_lexicon(
        resolver,
        metadata,
        form_code="F-MT-01",
        form_version="1.0.0",
        schema=generated.schema,
        asset_type_key="distribution_transformer",
        context=context,
    )


def test_rf_331_enum_fields_carry_spoken_forms_of_canonical_values(parts) -> None:
    lexicon = _lexicon(parts)
    aliases = lexicon.aliases_for("phases")
    assert aliases, "un campo de catálogo sin formas habladas no se puede dictar"
    # The canonical value is the key; what a technician says is the alias.
    assert any("trifasico" in forms for forms in aliases.values())


def test_rf_331_the_work_order_gets_the_highest_boost(parts) -> None:
    """The feeder of the order being worked is the phrase most likely to be said next."""
    lexicon = _lexicon(parts, OrderContext(asset_code="P-14522", feeder_code="04BH070T11"))
    order_words = [h for h in lexicon.hotwords if h.source == SOURCE_WORK_ORDER]
    assert {h.text for h in order_words} >= {"p-14522", "04bh070t11"}
    other = [h.boost for h in lexicon.hotwords if h.source != SOURCE_WORK_ORDER]
    assert min(h.boost for h in order_words) > max(other)


def test_rf_331_the_order_codes_reach_the_field_they_belong_to(parts) -> None:
    """Routed by semantic role, never by field name (ADR-004)."""
    lexicon = _lexicon(parts, OrderContext(asset_code="P-14522", feeder_code="04BH070T11"))
    assert "P-14522" in lexicon.codes_for("code")
    assert "04BH070T11" in lexicon.codes_for("feeder_code")


def test_rf_304_volatile_catalogues_are_named_and_boosted(parts) -> None:
    lexicon = _lexicon(parts)
    assert lexicon.volatile_fields, "el perfil declara un catálogo volátil que no se reflejó"
    volatile_hotwords = [h for h in lexicon.hotwords if h.source == SOURCE_VOLATILE_DOMAIN]
    assert volatile_hotwords
    domain_value_boost = load_spoken_vocabulary().boost("domain_value")
    assert all(h.boost > domain_value_boost for h in volatile_hotwords)


def test_rf_304_a_volatile_catalogue_that_did_not_arrive_is_reported(parts) -> None:
    """Silence about a missing catalogue is how a form ends up offering stale codes."""
    resolver, metadata, generated = parts
    without_domains = GisMetadata(
        profile_id=metadata.profile_id, domains=[], layers=metadata.layers
    )
    lexicon = build_lexicon(
        resolver,
        without_domains,
        form_code="F-MT-01",
        form_version="1.0.0",
        schema=generated.schema,
        asset_type_key="distribution_transformer",
    )
    assert any("volátil" in w for w in lexicon.warnings)


def test_rf_331_only_dictable_fields_get_cues(parts) -> None:
    """A repeatable table or an evidence URI in the lexicon is noise for the decoder.

    The two exclusions are injected rather than taken from the fixture, because not every
    profile maps a one-to-many relationship and the rule has to hold either way.
    """
    resolver, metadata, generated = parts
    schema = copy.deepcopy(generated.schema)
    schema["properties"]["installed_units"] = {
        "type": "array",
        "title": "Unidades instaladas",
        "x-repeatable-table": True,
        "items": {"type": "object"},
    }
    schema["properties"]["photos_before"] = {
        "type": "array",
        "title": "Fotos antes",
        "x-voice": False,
        "items": {"type": "string"},
    }
    lexicon = build_lexicon(
        resolver,
        metadata,
        form_code="F-MT-01",
        form_version="1.0.0",
        schema=schema,
        asset_type_key="distribution_transformer",
    )
    assert not {"installed_units", "photos_before"} & set(lexicon.field_cues)
    assert not any("unidades" in h.text or "fotos" in h.text for h in lexicon.hotwords)


def test_rf_331_generic_label_words_are_not_cues(parts) -> None:
    """ "tipo" appears in half the labels of any geodatabase; as a cue it matches nothing."""
    lexicon = _lexicon(parts)
    assert all("tipo" not in cues for cues in lexicon.field_cues.values())


def test_rf_331_the_hash_changes_with_the_content(parts) -> None:
    """The device re-downloads when the lexicon moved, and only then."""
    plain = _lexicon(parts)
    with_order = _lexicon(parts, OrderContext(feeder_code="04BH070T11"))
    assert plain.content_hash == _lexicon(parts).content_hash
    assert plain.content_hash != with_order.content_hash
    assert with_order.content_hash == with_order.compute_hash()


def test_rf_331_every_cue_is_derived_not_invented(parts) -> None:
    """A cue comes from the canonical vocabulary or from the unit's own field labels.

    That is the invariant behind "configure, don't program": nobody types a cue into the
    codebase for a particular utility. A word that coincides with a real field name — the
    Spanish for "code" is `codigo` in both — is not a leak; a cue with no source would be.
    """
    _, metadata, _ = parts
    lexicon = _lexicon(parts)
    canonical_cues = {
        cue for cues in load_spoken_vocabulary().attribute_cues.values() for cue in cues
    }
    label_words: set[str] = set()
    for layer in metadata.layers:
        for gis_field in layer.fields:
            folded = strip_accents(gis_field.label.lower())
            label_words.add(folded)
            label_words.update(folded.split())

    for field_key, cues in lexicon.field_cues.items():
        for cue in cues:
            assert cue in canonical_cues or cue in label_words, (
                f"la pista '{cue}' de '{field_key}' no viene ni del vocabulario canónico "
                "ni de una etiqueta sincronizada"
            )
