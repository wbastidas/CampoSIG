"""The GBNF grammar for the extraction sub-schema (I7, plan §I7).

What is tested is what the grammar *accepts*, not how it is spelled: the grammar's job is
to make an invalid answer unreachable during sampling, and only matching real payloads
against it shows whether it does. `tests/support/gbnf.py` is the matcher.
"""

from __future__ import annotations

import json

import pytest

from app.voice.grammar import GrammarError, build_grammar, extractable_fields, grammar_fingerprint
from tests.support.gbnf import accepts, parse_grammar

SCHEMA = {
    "properties": {
        "code": {"type": "string", "title": "Código"},
        "material": {"type": "string", "enum": ["concrete", "wood"], "x-catalog-ref": "m"},
        "height_m": {"type": "number", "x-unit": "m"},
        "count": {"type": "integer"},
        "install_date": {"type": "string", "format": "date"},
        "signed": {"type": "boolean"},
        "photos_before": {"type": "array", "items": {}},
        "location": {"type": "string", "x-voice": False},
        "units": {"type": "array", "x-repeatable-table": True, "items": {}},
    }
}


def test_rf_332_only_dictable_scalar_fields_are_in_scope() -> None:
    """Arrays, repeatable tables and the fields the form marks non-dictable stay out."""
    assert list(extractable_fields(SCHEMA)) == [
        "code",
        "material",
        "height_m",
        "count",
        "install_date",
        "signed",
    ]


def test_rf_332_the_grammar_parses() -> None:
    rules = parse_grammar(build_grammar(SCHEMA))
    assert "root" in rules


def test_rf_332_a_well_formed_answer_is_accepted() -> None:
    grammar = build_grammar(SCHEMA)
    payload = json.dumps(
        {
            "code": "P-235",
            "material": "wood",
            "height_m": 9.5,
            "count": 3,
            "install_date": "2025-03-15",
            "signed": True,
        }
    )
    assert accepts(grammar, payload)


def test_rf_332_silence_is_expressible() -> None:
    """A model that heard nothing about a field must be able to say so.

    Without a null alternative the only grammatical answer is an invented value, which is
    the failure this increment exists to prevent.
    """
    grammar = build_grammar(SCHEMA)
    payload = json.dumps(dict.fromkeys(extractable_fields(SCHEMA), None))
    assert accepts(grammar, payload)


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("valor fuera del catálogo", {"material": "bamboo"}),
        ("fecha en formato local", {"install_date": "15/03/2025"}),
        ("número donde va un booleano", {"signed": 1}),
        ("texto donde va un número", {"height_m": "nueve"}),
    ],
)
def test_rf_332_invalid_answers_are_unreachable(name: str, payload: dict) -> None:
    grammar = build_grammar(SCHEMA)
    complete = dict.fromkeys(extractable_fields(SCHEMA), None)
    complete.update(payload)
    assert not accepts(grammar, json.dumps(complete)), name


def test_rf_332_an_unknown_field_cannot_be_invented() -> None:
    grammar = build_grammar(SCHEMA)
    complete = dict.fromkeys(extractable_fields(SCHEMA), None)
    complete["transformer_owner"] = "x"
    assert not accepts(grammar, json.dumps(complete))


def test_rf_332_a_missing_field_is_rejected() -> None:
    """Every field is present or explicitly null; a short object is not an answer."""
    assert not accepts(build_grammar(SCHEMA), json.dumps({"code": "P-1"}))


def test_rf_332_a_section_can_be_dictated_on_its_own() -> None:
    grammar = build_grammar(SCHEMA, fields=["material", "height_m"])
    assert accepts(grammar, json.dumps({"material": "concrete", "height_m": 12}))
    assert not accepts(grammar, json.dumps({"material": "concrete"}))


def test_rf_332_a_field_that_cannot_be_dictated_is_refused_loudly() -> None:
    with pytest.raises(GrammarError, match="location"):
        build_grammar(SCHEMA, fields=["location"])


def test_rf_332_a_form_with_nothing_dictable_is_refused() -> None:
    with pytest.raises(GrammarError):
        build_grammar({"properties": {"photo": {"type": "string", "x-voice": False}}})


def test_rf_332_the_fingerprint_follows_the_grammar() -> None:
    """The provenance record names the grammar a proposal was produced under."""
    first = grammar_fingerprint(build_grammar(SCHEMA))
    assert first == grammar_fingerprint(build_grammar(SCHEMA))
    assert first != grammar_fingerprint(build_grammar(SCHEMA, fields=["code"]))


def test_rf_332_whitespace_is_tolerated() -> None:
    """The model may pretty-print; rejecting a newline would be enforcing nothing useful."""
    grammar = build_grammar(SCHEMA, fields=["code"])
    assert accepts(grammar, '{\n  "code" : "P-1"\n}')
