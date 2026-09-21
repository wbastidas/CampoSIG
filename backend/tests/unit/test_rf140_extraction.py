"""Dictation → proposals (RF-140, RF-331).

Most of these are refusals. The extractor's value is not how many fields it fills — it is
that the fields it fills are the ones that were said, because every proposal costs a
technician a confirmation and a wrong one that looks right costs a wrong capture.
"""

from __future__ import annotations

import pytest

from app.forms.generator import FormGenerator
from app.model_profile.profile import load_profile
from app.model_profile.resolver import ModelResolver
from app.voice.extractor import (
    MAX_HEURISTIC_CONFIDENCE,
    RuleBasedExtractor,
    build_extraction_request,
)
from app.voice.lexicon import OrderContext, build_lexicon
from tests.conftest import ALL_PROFILE_IDS, build_metadata
from tests.support.gbnf import accepts

FEEDER = "04BH070T11"
ASSET = "P-14522"


@pytest.fixture(params=ALL_PROFILE_IDS)
def setup(request: pytest.FixtureRequest):
    profile_id = str(request.param)
    resolver = ModelResolver(load_profile(profile_id))
    metadata = build_metadata(profile_id)
    generated = FormGenerator(resolver, metadata).generate("distribution_transformer")
    lexicon = build_lexicon(
        resolver,
        metadata,
        form_code="F-MT-01",
        form_version="1.0.0",
        schema=generated.schema,
        asset_type_key="distribution_transformer",
        context=OrderContext(asset_code=ASSET, feeder_code=FEEDER),
    )
    return generated.schema, lexicon


def extract(setup, transcript: str):
    schema, lexicon = setup
    return RuleBasedExtractor().extract(transcript, lexicon, schema)


def test_rf_140_a_full_dictation_fills_what_was_said(setup) -> None:
    result = extract(
        setup,
        "el transformador es trifásico, montado en poste, la capacidad es de "
        "cincuenta kilovoltamperios",
    )
    assert result.values["phases"] == "three"
    assert result.values["mounting"] == "pole"
    assert result.values["rated_kva"] == 50


def test_rf_140_nothing_is_ever_certain(setup) -> None:
    result = extract(
        setup, "el transformador es trifásico, la capacidad cincuenta kilovoltamperios"
    )
    assert result.proposals
    assert all(0 < p.confidence <= MAX_HEURISTIC_CONFIDENCE for p in result.proposals)


def test_rf_140_every_proposal_points_at_the_words_it_came_from(setup) -> None:
    """A correction without its context teaches nothing, so the span travels with it."""
    result = extract(setup, "la capacidad es de cincuenta kilovoltamperios")
    proposal = result.proposal("rated_kva")
    assert proposal is not None
    assert "50" in proposal.transcript_span
    assert proposal.rationale


def test_rf_140_silence_about_a_field_leaves_it_empty(setup) -> None:
    result = extract(setup, "el transformador es trifásico")
    assert "rated_kva" in result.unfilled
    assert result.proposal("rated_kva") is None


def test_rf_140_a_quantity_in_the_wrong_unit_is_refused(setup) -> None:
    """ "cincuenta kilovoltios" is not fifty kVA. Converting it would be inventing data."""
    result = extract(setup, "la capacidad es de cincuenta kilovoltios")
    assert result.proposal("rated_kva") is None


def test_rf_140_a_quantity_with_the_right_unit_is_trusted_more(setup) -> None:
    with_unit = extract(setup, "la capacidad es de cincuenta kilovoltamperios").proposal(
        "rated_kva"
    )
    bare = extract(setup, "la capacidad es de cincuenta").proposal("rated_kva")
    assert with_unit is not None and bare is not None
    assert with_unit.confidence > bare.confidence


def test_rf_331_a_code_is_matched_against_the_real_catalogue(setup) -> None:
    result = extract(setup, f"el alimentador es {FEEDER}")
    assert result.values["feeder_code"] == FEEDER


def test_rf_331_a_code_spelled_out_is_understood(setup) -> None:
    """Technicians spell feeders on the radio; the decoder returns words, not a code."""
    result = extract(setup, "el alimentador es cero cuatro be hache cero siete cero te once")
    assert result.values["feeder_code"] == FEEDER


def test_rf_331_a_b_heard_as_a_v_still_matches_but_with_less_confidence(setup) -> None:
    exact = extract(setup, f"el alimentador es {FEEDER}").proposal("feeder_code")
    folded = extract(
        setup, "el alimentador es cero cuatro ve hache cero siete cero te once"
    ).proposal("feeder_code")
    assert exact is not None and folded is not None
    assert folded.value == exact.value
    assert folded.confidence < exact.confidence


def test_rf_331_a_code_outside_the_catalogue_is_refused_and_reported(setup) -> None:
    """The fragment "04" for a ten-character feeder is the value that gets confirmed blind."""
    result = extract(setup, "el alimentador es 99ZZ999")
    assert result.proposal("feeder_code") is None
    assert any("catálogo" in w for w in result.warnings)


def test_rf_140_an_unambiguous_catalogue_word_needs_no_cue(setup) -> None:
    """Nothing but the phase field can claim "trifásico", so requiring a cue would only
    reject a clear dictation."""
    result = extract(setup, "llegamos y el equipo es trifásico")
    assert result.values["phases"] == "three"


def test_rf_140_a_longer_catalogue_phrase_wins_over_a_shorter_one() -> None:
    """ "sodio de alta presión" must not lose to "sodio"."""
    profile_id = ALL_PROFILE_IDS[0]
    resolver = ModelResolver(load_profile(profile_id))
    metadata = build_metadata(profile_id)
    generated = FormGenerator(resolver, metadata).generate("street_light")
    lexicon = build_lexicon(
        resolver,
        metadata,
        form_code="F-AP-01",
        form_version="1.0.0",
        schema=generated.schema,
        asset_type_key="street_light",
    )
    result = RuleBasedExtractor().extract(
        "la luminaria es de sodio de alta presión", lexicon, generated.schema
    )
    assert result.values["technology"] == "sodium_hp"


def test_rf_304_a_value_from_a_volatile_catalogue_is_flagged_for_review(setup) -> None:
    result = extract(setup, f"el alimentador es {FEEDER}")
    assert any("unidad de negocio" in w for w in result.warnings)


def test_rf_140_the_gateway_request_carries_a_grammar_that_binds(setup) -> None:
    """The contract with the model gateway (CLAUDE.md 13), asserted on the payload."""
    schema, lexicon = setup
    request = build_extraction_request("la capacidad es de cincuenta kVA", lexicon, schema)
    assert request["model"] == "form-extractor"
    assert request["temperature"] == 0
    grammar = request["extra_body"]["grammar"]
    assert accepts(
        grammar,
        '{"code": null, "rated_kva": 50, "phases": null, "mounting": null, "feeder_code": null}',
    )
    assert not accepts(
        grammar,
        '{"code": null, "rated_kva": 50, "phases": "cuatro", '
        '"mounting": null, "feeder_code": null}',
    )
    assert request["metadata"]["lexicon_hash"] == lexicon.content_hash


def test_rf_140_the_gateway_prompt_forbids_inventing_values(setup) -> None:
    schema, lexicon = setup
    request = build_extraction_request("nada que extraer", lexicon, schema)
    system = request["messages"][0]["content"]
    assert "No inventes" in system or "no inventes" in system
