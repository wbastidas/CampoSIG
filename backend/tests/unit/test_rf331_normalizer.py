"""The es-EC transcript normalizer (I7, guía 4.3).

These are the cases a field recording actually contains. Two of them encode decisions that
are easy to get wrong in the opposite direction, and both have a negative test: a run of
bare digit words must not become a quantity, and a partially parseable run must not be
half-converted.
"""

from __future__ import annotations

import pytest

from app.voice.normalizer import (
    code_key,
    digit_sequence,
    normalize,
    parse_number_words,
    sound_fold,
    spell_out,
    strip_accents,
    tokenize,
)


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        ("cero", 0),
        ("siete", 7),
        ("quince", 15),
        ("veintiuno", 21),
        ("veinticinco", 25),
        ("treinta y cinco", 35),
        ("cien", 100),
        ("ciento veinte", 120),
        ("doscientos cincuenta y tres", 253),
        ("mil", 1000),
        ("mil quinientos", 1500),
        ("dos mil veinticinco", 2025),
        ("quince mil", 15000),
        ("un millon", 1_000_000),
        ("dos millones trescientos mil", 2_300_000),
    ],
)
def test_rf_331_spanish_number_words_parse(words: str, expected: int) -> None:
    assert parse_number_words(words.split()) == expected


@pytest.mark.parametrize("words", ["dos tres", "cinco cinco cinco", "veinte treinta", "mil mil"])
def test_rf_331_juxtaposed_digit_words_are_not_a_quantity(words: str) -> None:
    """ "dos tres" is someone spelling a code, not the number 23."""
    assert parse_number_words(words.split()) is None


def test_rf_331_a_run_that_does_not_parse_stays_as_words() -> None:
    """The dangerous outcome is a *partial* conversion, so there is a test for it.

    Reading "dos tres cinco" as "2 tres cinco" would turn one dictated code into a
    quantity plus noise, and the quantity would look like a perfectly good value.
    """
    assert normalize("el codigo es dos tres cinco").text == "el codigo es dos tres cinco"


def test_rf_331_a_trailing_conjunction_is_not_part_of_the_number() -> None:
    assert normalize("quince y luego revisamos").text == "15 y luego revisamos"


@pytest.mark.parametrize(
    ("said", "expected"),
    [
        ("veinticinco kilovoltamperios", "25 kVA"),
        ("cincuenta kilo voltios amperios", "50 kVA"),
        ("ciento veinte voltios", "120 V"),
        ("trece punto ocho kilovoltios", "13.8 kV"),
        ("tres coma cinco metros", "3.5 m"),
        ("dos y medio metros", "2.5 m"),
        ("noventa por ciento", "90 %"),
        ("doscientos cincuenta vatios", "250 W"),
    ],
)
def test_rf_331_quantities_and_units(said: str, expected: str) -> None:
    assert normalize(said).text == expected


def test_rf_331_dates_become_iso() -> None:
    assert normalize("instalado el quince de marzo de dos mil veinticinco").text == (
        "instalado el 2025-03-15"
    )


def test_rf_331_an_impossible_date_is_left_alone() -> None:
    """A day of 45 is a transcription error; rewriting it as a date would hide it."""
    assert "2025-03-45" not in normalize("el cuarenta y cinco de marzo de dos mil veinticinco").text


def test_rf_331_only_hesitation_fillers_are_removed() -> None:
    """ "bueno" is the answer to "¿cómo está el poste?" and must survive."""
    result = normalize("eh, el estado es bueno")
    assert "bueno" in result.text
    assert not result.text.startswith("eh")


def test_rf_331_replacements_are_reported_for_audit() -> None:
    result = normalize("cincuenta kilovoltamperios")
    assert any("50" in r for r in result.replacements)
    assert result.original == "cincuenta kilovoltamperios"


def test_rf_331_accents_are_folded_for_matching_only() -> None:
    assert strip_accents("Tecnología") == "Tecnologia"
    assert tokenize("Tecnología LED") == ["tecnologia", "led"]


def test_rf_331_digit_dictation_reads_characters() -> None:
    assert digit_sequence(["dos", "tres", "cinco"]) == "235"
    assert digit_sequence(["dos", "postes"]) is None


def test_rf_331_spelled_codes_read_letters_and_digits() -> None:
    assert spell_out(["cero", "cuatro", "be", "hache", "cero", "siete"]) == "04bh07"
    assert spell_out(["cero", "cuatro", "postes"]) is None


def test_rf_331_sound_folding_collapses_what_spanish_does_not_distinguish() -> None:
    """A *v* heard for a *b* is a transcription artefact, not a different code."""
    assert sound_fold("04BH070T11") == sound_fold("04VH070T11")
    assert code_key("04BH070T11") != code_key("04VH070T11")
    # It must not collapse everything: two genuinely different codes stay different.
    assert sound_fold("04BH070T11") != sound_fold("04BH070T12")
