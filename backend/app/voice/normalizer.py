"""Ecuadorian-Spanish transcript normalizer (I7, guía 4.3).

An ASR model transcribes what was said, not what a form needs: a technician says
"veinticinco kilovoltamperios" and the field wants ``25`` with the unit ``kVA``. This
module does that conversion **deterministically**, before any model sees the text, which
is why it can be tested exhaustively without a single weight on disk.

Two decisions here are deliberate and worth knowing:

* **A run of bare digit words is not a number.** "dos tres cinco" is how a technician
  dictates the code *235* character by character, and reading it as the quantity 235 is
  a different claim. Quantities come from :func:`normalize`; code-shaped dictation goes
  through :func:`digit_sequence`, which the extractor only uses on string fields.
* **The decimal separator becomes a point.** Ecuador writes the comma and dictates both
  ("tres punto cinco", "tres coma cinco"); the form stores a JSON number, so the point
  wins. The original phrasing survives in the transcript kept for provenance.

Filler removal is deliberately timid. Dropping "bueno" would eat the answer to "¿en qué
estado está?", so only unambiguous hesitation markers are removed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

#: Bare units, rank 1. "un"/"uno"/"una" all appear in dictation.
_UNITS: dict[str, int] = {
    "cero": 0,
    "un": 1,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
}

#: 10 through 29, which Spanish says as single words. Rank 2: they occupy the tens slot.
_TEENS: dict[str, int] = {
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiuno": 21,
    "veintiun": 21,
    "veintiuna": 21,
    "veintidos": 22,
    "veintitres": 23,
    "veinticuatro": 24,
    "veinticinco": 25,
    "veintiseis": 26,
    "veintisiete": 27,
    "veintiocho": 28,
    "veintinueve": 29,
}

_TENS: dict[str, int] = {
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
}

_HUNDREDS: dict[str, int] = {
    "cien": 100,
    "ciento": 100,
    "doscientos": 200,
    "doscientas": 200,
    "trescientos": 300,
    "trescientas": 300,
    "cuatrocientos": 400,
    "cuatrocientas": 400,
    "quinientos": 500,
    "quinientas": 500,
    "seiscientos": 600,
    "seiscientas": 600,
    "setecientos": 700,
    "setecientas": 700,
    "ochocientos": 800,
    "ochocientas": 800,
    "novecientos": 900,
    "novecientas": 900,
}

_THOUSAND = {"mil"}
_MILLION = {"millon", "millones"}

#: Every token a number run may contain. "y" joins tens and units ("treinta y cinco").
_NUMBER_TOKENS = (
    set(_UNITS) | set(_TEENS) | set(_TENS) | set(_HUNDREDS) | _THOUSAND | _MILLION | {"y"}
)

#: Digit names only, for code dictation. No "y", no scales.
_DIGIT_NAMES: dict[str, str] = {
    "cero": "0",
    "un": "1",
    "uno": "1",
    "una": "1",
    "dos": "2",
    "tres": "3",
    "cuatro": "4",
    "cinco": "5",
    "seis": "6",
    "siete": "7",
    "ocho": "8",
    "nueve": "9",
}

#: Spoken unit phrases → the symbol the geodatabase and the forms use. Longest phrase
#: wins, so "kilo voltios amperios" is not read as "kilo voltios" followed by junk.
_UNIT_PHRASES: dict[tuple[str, ...], str] = {
    ("kilovoltamperios",): "kVA",
    ("kilovoltamperio",): "kVA",
    ("kilo", "voltamperios"): "kVA",
    ("kilovoltios", "amperios"): "kVA",
    ("kilo", "voltios", "amperios"): "kVA",
    ("ka", "ve", "a"): "kVA",
    ("kilovoltios",): "kV",
    ("kilovoltio",): "kV",
    ("kilo", "voltios"): "kV",
    ("kilovatios",): "kW",
    ("kilovatio",): "kW",
    ("kilowatts",): "kW",
    ("voltios",): "V",
    ("voltio",): "V",
    ("amperios",): "A",
    ("amperio",): "A",
    ("vatios",): "W",
    ("vatio",): "W",
    ("metros",): "m",
    ("metro",): "m",
    ("centimetros",): "cm",
    ("centimetro",): "cm",
    ("milimetros",): "mm",
    ("milimetro",): "mm",
    ("kilometros",): "km",
    ("kilometro",): "km",
    ("grados",): "deg",
    ("grado",): "deg",
    ("por", "ciento"): "%",
    ("lumenes",): "lm",
    ("lumen",): "lm",
    ("hertz",): "Hz",
    ("hertzios",): "Hz",
}

_MONTHS: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

#: Hesitation markers only. Anything that could be an answer stays.
_FILLERS: frozenset[str] = frozenset(
    {"eh", "ehh", "ehm", "em", "mmm", "mm", "aja", "ajam", "este_", "esteee"}
)

_TOKEN_RE = re.compile(r"[0-9]+(?:[.,][0-9]+)?|[^\W\d_]+|[^\s\w]", re.UNICODE)


def strip_accents(text: str) -> str:
    """Fold accents for matching. Never used on text shown to a person."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def tokenize(text: str) -> list[str]:
    """Words, numbers and punctuation, accent-folded and lowercased."""
    return _TOKEN_RE.findall(strip_accents(text.lower()))


@dataclass(frozen=True)
class NormalizedText:
    """The normalized transcript plus what was changed, for auditability."""

    text: str
    tokens: tuple[str, ...]
    original: str
    replacements: tuple[str, ...] = field(default_factory=tuple)

    def __contains__(self, needle: str) -> bool:
        return strip_accents(needle.lower()) in self.text


# -- numbers ---------------------------------------------------------------------------
def _parse_under_thousand(tokens: list[str]) -> int | None:
    """Parse 0 to 999 written as words, rejecting impossible orders.

    Rank enforcement is what makes "dos tres" fail: two rank-1 tokens in a row is not a
    quantity in Spanish, it is someone spelling out a code.
    """
    if not tokens:
        return None
    total = 0
    last_rank = 99
    consumed = False
    for token in tokens:
        if token == "y":
            continue
        if token in _HUNDREDS:
            rank, value = 3, _HUNDREDS[token]
        elif token in _TENS:
            rank, value = 2, _TENS[token]
        elif token in _TEENS:
            rank, value = 2, _TEENS[token]
        elif token in _UNITS:
            rank, value = 1, _UNITS[token]
        else:
            return None
        if rank >= last_rank:
            return None
        total += value
        last_rank = rank
        consumed = True
    return total if consumed else None


def _parse_under_million(tokens: list[str]) -> int | None:
    if "mil" not in tokens:
        return _parse_under_thousand(tokens)
    index = tokens.index("mil")
    left, right = tokens[:index], tokens[index + 1 :]
    # "mil quinientos": nothing before the scale means one thousand.
    multiplier = 1 if not [t for t in left if t != "y"] else _parse_under_thousand(left)
    if multiplier is None:
        return None
    remainder = 0
    if [t for t in right if t != "y"]:
        parsed = _parse_under_thousand(right)
        if parsed is None:
            return None
        remainder = parsed
    return multiplier * 1000 + remainder


def parse_number_words(tokens: list[str]) -> int | None:
    """Parse a run of Spanish number words, or return None if it is not a quantity.

    Supports 0 through 999999999. Beyond that the phrasing is not something a field
    technician dictates, and guessing would be worse than declining.
    """
    million_index = next((i for i, t in enumerate(tokens) if t in _MILLION), None)
    if million_index is None:
        return _parse_under_million(tokens)
    left, right = tokens[:million_index], tokens[million_index + 1 :]
    multiplier = 1 if not [t for t in left if t != "y"] else _parse_under_million(left)
    if multiplier is None:
        return None
    remainder = 0
    if [t for t in right if t != "y"]:
        parsed = _parse_under_million(right)
        if parsed is None:
            return None
        remainder = parsed
    return multiplier * 1_000_000 + remainder


def digit_sequence(tokens: list[str]) -> str | None:
    """Read a run of digit words as the characters of a code, not as a quantity.

    "pe dos tres cinco" is asset *P235*. Only the digits are returned; the letters are
    the caller's problem, because letter dictation is not reliable enough to guess at.
    """
    digits = [_DIGIT_NAMES[t] for t in tokens if t in _DIGIT_NAMES]
    if len(digits) != len([t for t in tokens if t not in {"y"}]):
        return None
    return "".join(digits) or None


def _replace_number_runs(tokens: list[str], replacements: list[str]) -> list[str]:
    """Rewrite every run of number words as digits, longest run first."""
    out: list[str] = []
    index = 0
    while index < len(tokens):
        if tokens[index] not in _NUMBER_TOKENS or tokens[index] == "y":
            out.append(tokens[index])
            index += 1
            continue
        end = index
        while end < len(tokens) and tokens[end] in _NUMBER_TOKENS:
            end += 1
        # A trailing "y" belongs to the sentence ("quince y luego revisamos"), not to the
        # number, so it is dropped before parsing. Nothing else is: the run either parses
        # whole or stays as words. Parsing a prefix of it would silently turn the first
        # word of dictated code "dos tres cinco" into the quantity 2 and leave the rest
        # as text, which is the one outcome worse than not normalizing at all.
        run_end = end
        while run_end > index and tokens[run_end - 1] == "y":
            run_end -= 1
        run = tokens[index:run_end]
        value = parse_number_words(run) if run else None
        if value is None:
            out.extend(tokens[index:end])
            index = end
            continue
        out.append(str(value))
        replacements.append(f"{' '.join(run)} → {value}")
        out.extend(tokens[run_end:end])
        index = end
    return out


_DIGITS_RE = re.compile(r"^\d+$")


def _join_decimals(tokens: list[str], replacements: list[str]) -> list[str]:
    """Turn "3 punto 5", "3 coma 5" and "3 y medio" into a single decimal token."""
    out: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if _DIGITS_RE.match(token):
            if (
                index + 2 < len(tokens)
                and tokens[index + 1] in {"punto", "coma"}
                and _DIGITS_RE.match(tokens[index + 2])
            ):
                joined = f"{token}.{tokens[index + 2]}"
                replacements.append(f"{token} {tokens[index + 1]} {tokens[index + 2]} → {joined}")
                out.append(joined)
                index += 3
                continue
            half = index + 1
            if half < len(tokens) and tokens[half] == "y":
                half += 1
            if half < len(tokens) and tokens[half] in {"medio", "media"}:
                joined = f"{token}.5"
                replacements.append(f"{' '.join(tokens[index : half + 1])} → {joined}")
                out.append(joined)
                index = half + 1
                continue
        out.append(token)
        index += 1
    return out


def _apply_units(
    tokens: list[str], replacements: list[str], *, only: set[tuple[str, ...]] | None = None
) -> list[str]:
    """Replace spoken unit phrases with their symbols, longest phrase first.

    :param only: restrict to these phrases, for the pre-pass that has to run before
        numbers are converted.
    """
    selected = {k: v for k, v in _UNIT_PHRASES.items() if only is None or k in only}
    phrases = sorted(selected.items(), key=lambda item: len(item[0]), reverse=True)
    out: list[str] = []
    index = 0
    while index < len(tokens):
        matched = False
        for phrase, symbol in phrases:
            if tuple(tokens[index : index + len(phrase)]) == phrase:
                out.append(symbol)
                replacements.append(f"{' '.join(phrase)} → {symbol}")
                index += len(phrase)
                matched = True
                break
        if not matched:
            out.append(tokens[index])
            index += 1
    return out


def _apply_dates(tokens: list[str], replacements: list[str]) -> list[str]:
    """ "15 de marzo de 2025" → "2025-03-15". Numbers are already digits by now."""
    out: list[str] = []
    index = 0
    while index < len(tokens):
        if (
            index + 4 < len(tokens)
            and _DIGITS_RE.match(tokens[index])
            and tokens[index + 1] == "de"
            and tokens[index + 2] in _MONTHS
            and tokens[index + 3] == "de"
            and _DIGITS_RE.match(tokens[index + 4])
        ):
            day, month, year = (
                int(tokens[index]),
                _MONTHS[tokens[index + 2]],
                int(tokens[index + 4]),
            )
            if 1 <= day <= 31 and 1900 <= year <= 2999:
                iso = f"{year:04d}-{month:02d}-{day:02d}"
                replacements.append(f"{' '.join(tokens[index : index + 5])} → {iso}")
                out.append(iso)
                index += 5
                continue
        out.append(tokens[index])
        index += 1
    return out


#: Unit phrases built out of number words. They have to be replaced *before* the number
#: pass, or "por ciento" becomes "por 100" and the percentage is gone.
_NUMBER_WORD_UNITS = {phrase for phrase in _UNIT_PHRASES if set(phrase) & _NUMBER_TOKENS}


def normalize(text: str) -> NormalizedText:
    """Normalize a dictated fragment for field extraction.

    Order matters: unit phrases that contain number words first (otherwise "por ciento"
    loses to the number pass), then numbers, then decimals (so "tres punto cinco" has
    digits to join), then the remaining units, and dates last because they consume
    already-normalized digits.
    """
    replacements: list[str] = []
    tokens = [t for t in tokenize(text) if t not in _FILLERS]
    tokens = _apply_units(tokens, replacements, only=_NUMBER_WORD_UNITS)
    tokens = _replace_number_runs(tokens, replacements)
    tokens = _join_decimals(tokens, replacements)
    tokens = _apply_units(tokens, replacements)
    tokens = _apply_dates(tokens, replacements)
    rendered = " ".join(tokens)
    # Punctuation should not carry a leading space when the text is read back.
    rendered = re.sub(r"\s+([,.;:])", r"\1", rendered)
    return NormalizedText(
        text=rendered,
        tokens=tuple(tokens),
        original=text,
        replacements=tuple(replacements),
    )


# -- codes dictated character by character ---------------------------------------------
#: Spanish letter names as a technician says them on the radio. "be"/"ve" and "ce"/"se"
#: are genuinely the same sound in Ecuadorian Spanish, which :func:`sound_fold` handles;
#: this map only turns a spoken name into the letter it is meant to be.
_LETTER_NAMES: dict[str, str] = {
    "a": "a",
    "be": "b",
    "be larga": "b",
    "ce": "c",
    "de": "d",
    "e": "e",
    "efe": "f",
    "ge": "g",
    "hache": "h",
    "i": "i",
    "i latina": "i",
    "jota": "j",
    "ka": "k",
    "ele": "l",
    "eme": "m",
    "ene": "n",
    "enie": "n",
    "o": "o",
    "pe": "p",
    "cu": "q",
    "que": "q",
    "ere": "r",
    "erre": "r",
    "ese": "s",
    "te": "t",
    "u": "u",
    "ve": "v",
    "uve": "v",
    "ve corta": "v",
    "doble ve": "w",
    "doble u": "w",
    "equis": "x",
    "ye": "y",
    "i griega": "y",
    "zeta": "z",
}

#: Sounds Ecuadorian Spanish does not distinguish. Folding them lets a dictated code be
#: matched against a real catalogue even when the letter heard was the other one of a
#: pair — which is a transcription artefact, not a different code.
_SOUND_FOLDS = (
    ("v", "b"),
    ("z", "s"),
    ("c", "s"),
    ("k", "s"),
    ("q", "s"),
    ("ll", "y"),
    ("h", ""),
)


def spell_out(tokens: list[str]) -> str | None:
    """Read a run of letter and digit names as the characters of a code.

    Returns None unless *every* token is one: a partial reading would produce a code that
    looks plausible and is not the one that was said.
    """
    out: list[str] = []
    for token in tokens:
        if token in _DIGIT_NAMES:
            out.append(_DIGIT_NAMES[token])
        elif token in _LETTER_NAMES:
            out.append(_LETTER_NAMES[token])
        elif token.isdigit():
            out.append(token)
        else:
            return None
    return "".join(out) or None


def code_key(text: str) -> str:
    """Comparison key for a code: accent-folded, alphanumeric only, lowercase."""
    return "".join(ch for ch in strip_accents(text.lower()) if ch.isalnum())


def sound_fold(text: str) -> str:
    """Comparison key that also collapses the sounds Spanish keeps apart only in writing."""
    folded = code_key(text)
    for source, target in _SOUND_FOLDS:
        folded = folded.replace(source, target)
    return folded
