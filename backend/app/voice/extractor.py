"""Transcript → field proposals (I7, RF-140, RF-331).

Two extractors live behind one interface, on purpose.

:class:`RuleBasedExtractor` is deterministic: it matches the lexicon's phrases against the
normalized transcript and proposes nothing it cannot point at. It needs no weights, so it
runs on the cheapest phone, it is the baseline every model version has to beat, and it is
the offline fallback when a device has no model package yet. It is also the logic that gets
ported to Kotlin, which is why it holds no server-side state.

:func:`build_extraction_request` is the other half: the request a 1.5B instruct model gets
through the model gateway, with the GBNF grammar attached so its answer is JSON by
construction. The call itself is M19's job — this module stops at the payload, so the
contract can be tested without a model.

**Nothing here decides anything.** Every proposal comes back with a confidence and a
transcript span and is stored as an unconfirmed AI value; a human confirms or corrects it
before it is part of the response (SRS rule 0.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.voice.grammar import build_grammar, extractable_fields, grammar_fingerprint
from app.voice.lexicon import VoiceLexicon
from app.voice.normalizer import (
    NormalizedText,
    code_key,
    digit_sequence,
    normalize,
    sound_fold,
    spell_out,
    strip_accents,
)

#: How far after a field cue the value may sit, in tokens. Six covers "la capacidad del
#: transformador es de 50 kVA" and stops before the next sentence.
CUE_WINDOW = 6

#: The window for a code field, which is longer because a technician spelling a code out
#: spends one token per character: "cero cuatro be hache cero siete cero te once" is nine
#: tokens for a ten-character feeder.
CODE_WINDOW = 18

#: Ceiling on any heuristic confidence. The rule-based extractor is never certain, and a
#: 1.0 would let a proposal look confirmed when nobody confirmed it.
MAX_HEURISTIC_CONFIDENCE = 0.95

RULE_BASED_MODEL_NAME = "rule-based-es-ec"
RULE_BASED_MODEL_VERSION = "0.1.0"

#: Gateway alias for the on-server extractor (CLAUDE.md rule 13).
EXTRACTOR_ALIAS = "form-extractor"


@dataclass(frozen=True)
class FieldProposal:
    """One value the extractor believes was dictated."""

    field_key: str
    value: Any
    confidence: float
    #: The fragment of the normalized transcript the value came from. Stored with the
    #: proposal because a correction without its audio context teaches nothing.
    transcript_span: str
    #: Why this field, in the platform's own words, for the review screen.
    rationale: str


@dataclass
class ExtractionResult:
    proposals: list[FieldProposal] = field(default_factory=list)
    #: Fields that were in scope and stayed empty. Shown to the technician so a silence
    #: is visible as a silence, not as a field nobody asked about.
    unfilled: list[str] = field(default_factory=list)
    normalized: NormalizedText | None = None
    model_name: str = RULE_BASED_MODEL_NAME
    model_version: str = RULE_BASED_MODEL_VERSION
    grammar_fingerprint: str | None = None
    warnings: list[str] = field(default_factory=list)

    def proposal(self, field_key: str) -> FieldProposal | None:
        return next((p for p in self.proposals if p.field_key == field_key), None)

    @property
    def values(self) -> dict[str, Any]:
        return {p.field_key: p.value for p in self.proposals}


class FormExtractor(Protocol):
    """The seam the mobile app and the server both program against (CLAUDE.md rule 12)."""

    def extract(
        self,
        transcript: str,
        lexicon: VoiceLexicon,
        schema: dict[str, Any],
        *,
        fields: list[str] | None = None,
    ) -> ExtractionResult: ...


def _unique_alias_owners(
    lexicon: VoiceLexicon, candidates: dict[str, dict[str, Any]]
) -> dict[str, tuple[str, str]]:
    """Aliases that can only belong to one field, mapped to (field, canonical value).

    "trifásico" is not ambiguous in any form the platform generates, so requiring a cue
    before accepting it would reject a perfectly clear dictation. An alias that two fields
    share is left out: there, the cue is the only thing that disambiguates.
    """
    owners: dict[str, set[tuple[str, str]]] = {}
    for field_key in candidates:
        for canonical, aliases in lexicon.aliases_for(field_key).items():
            for alias in aliases:
                owners.setdefault(strip_accents(alias.lower()), set()).add((field_key, canonical))
    return {alias: next(iter(pair)) for alias, pair in owners.items() if len(pair) == 1}


def _find_phrase(tokens: tuple[str, ...], phrase: str) -> int | None:
    """Index of the first token of ``phrase`` in ``tokens``, or None."""
    needle = strip_accents(phrase.lower()).split()
    if not needle:
        return None
    for index in range(len(tokens) - len(needle) + 1):
        if list(tokens[index : index + len(needle)]) == needle:
            return index
    return None


def _cue_position(tokens: tuple[str, ...], cues: list[str]) -> tuple[int, str] | None:
    """The earliest cue for a field, with the cue that matched."""
    best: tuple[int, str] | None = None
    for cue in cues:
        found = _find_phrase(tokens, cue)
        if found is not None and (best is None or found < best[0]):
            best = (found + len(strip_accents(cue).split()), cue)
    return best


#: Words that sit between a cue and its value and carry no information: "el código ES DE
#: 235". Skipped when looking for the value, never when matching a cue.
_CONNECTORS = frozenset(
    {
        "es",
        "son",
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "un",
        "una",
        "esta",
        "quedo",
        "fue",
        ":",
        ",",
        "numero",
        "nro",
        "n",
    }
)


def _skip_connectors(tokens: tuple[str, ...], start: int) -> int:
    index = start
    while index < len(tokens) and tokens[index] in _CONNECTORS:
        index += 1
    return index


def _is_number(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def _span(tokens: tuple[str, ...], start: int, end: int) -> str:
    return " ".join(tokens[max(0, start) : min(len(tokens), end)])


#: Unit symbols the normalizer can produce. Used to tell "a unit that does not match" from
#: "an ordinary word after the number".
_KNOWN_UNIT_SYMBOLS = frozenset(
    {"kVA", "kV", "kW", "V", "A", "W", "m", "cm", "mm", "km", "deg", "%", "lm", "Hz"}
)


class RuleBasedExtractor:
    """Deterministic extraction from the lexicon. The baseline, and the offline fallback."""

    model_name = RULE_BASED_MODEL_NAME
    model_version = RULE_BASED_MODEL_VERSION

    def extract(
        self,
        transcript: str,
        lexicon: VoiceLexicon,
        schema: dict[str, Any],
        *,
        fields: list[str] | None = None,
    ) -> ExtractionResult:
        candidates = extractable_fields(schema)
        if fields is not None:
            candidates = {k: v for k, v in candidates.items() if k in fields}

        normalized = normalize(transcript)
        tokens = normalized.tokens
        result = ExtractionResult(normalized=normalized)
        unique_aliases = _unique_alias_owners(lexicon, candidates)

        for field_key, prop in candidates.items():
            proposal = self._propose(
                field_key, prop, tokens, lexicon, unique_aliases, result.warnings
            )
            if proposal is not None:
                result.proposals.append(proposal)
            else:
                result.unfilled.append(field_key)

        if lexicon.volatile_fields:
            filled_volatile = [
                key for key in lexicon.volatile_fields if result.proposal(key) is not None
            ]
            if filled_volatile:
                # The value came from a catalogue that changes per business unit, so a
                # stale lexicon can propose a code that no longer exists (RF-304).
                result.warnings.append(
                    "estos campos vienen de catálogos que cambian por unidad de negocio y "
                    "deben revisarse contra el catálogo vigente: " + ", ".join(filled_volatile)
                )
        return result

    # -- per field ---------------------------------------------------------------------
    def _propose(
        self,
        field_key: str,
        prop: dict[str, Any],
        tokens: tuple[str, ...],
        lexicon: VoiceLexicon,
        unique_aliases: dict[str, tuple[str, str]],
        warnings: list[str],
    ) -> FieldProposal | None:
        cues = lexicon.field_cues.get(field_key, [])
        cue = _cue_position(tokens, cues)

        if prop.get("enum"):
            return self._propose_enum(field_key, tokens, lexicon, unique_aliases, cue)
        declared = prop.get("type")
        if declared == "boolean":
            return self._propose_boolean(field_key, tokens, lexicon, cue)
        if declared in {"number", "integer"}:
            return self._propose_number(field_key, prop, tokens, cue)
        if declared == "string":
            if prop.get("format") == "date":
                return self._propose_date(field_key, tokens, cue)
            return self._propose_string(field_key, tokens, lexicon, cue, warnings)
        return None

    def _propose_enum(
        self,
        field_key: str,
        tokens: tuple[str, ...],
        lexicon: VoiceLexicon,
        unique_aliases: dict[str, tuple[str, str]],
        cue: tuple[int, str] | None,
    ) -> FieldProposal | None:
        # Longest alias first: "sodio de alta presion" must not lose to "sodio".
        aliases = sorted(
            (
                (alias, canonical)
                for canonical, forms in lexicon.aliases_for(field_key).items()
                for alias in forms
            ),
            key=lambda pair: len(pair[0].split()),
            reverse=True,
        )
        for alias, canonical in aliases:
            position = _find_phrase(tokens, alias)
            if position is None:
                continue
            owned = unique_aliases.get(strip_accents(alias.lower()))
            near_cue = cue is not None and 0 <= position - cue[0] <= CUE_WINDOW
            if not near_cue and owned != (field_key, canonical):
                # Ambiguous alias with no cue nearby: two fields could claim it, so
                # proposing one of them would be a coin toss dressed as a suggestion.
                continue
            confidence = 0.9 if near_cue else 0.8
            if len(alias.split()) == 1:
                confidence -= 0.05
            return FieldProposal(
                field_key=field_key,
                value=canonical,
                confidence=min(confidence, MAX_HEURISTIC_CONFIDENCE),
                transcript_span=_span(tokens, position - 2, position + len(alias.split()) + 1),
                rationale=(
                    f"se escuchó «{alias}»"
                    + (f" después de «{cue[1]}»" if near_cue and cue else "")
                ),
            )
        return None

    def _propose_boolean(
        self,
        field_key: str,
        tokens: tuple[str, ...],
        lexicon: VoiceLexicon,
        cue: tuple[int, str] | None,
    ) -> FieldProposal | None:
        # A yes or a no on its own belongs to no field in particular, so a boolean is only
        # filled when its cue was said.
        if cue is None:
            return None
        window = tokens[cue[0] : cue[0] + CUE_WINDOW]
        for offset, token in enumerate(window):
            if token in {strip_accents(w) for w in lexicon.negative}:
                value = False
            elif token in {strip_accents(w) for w in lexicon.affirmative}:
                value = True
            else:
                continue
            return FieldProposal(
                field_key=field_key,
                value=value,
                confidence=min(0.85 - 0.05 * offset, MAX_HEURISTIC_CONFIDENCE),
                transcript_span=_span(tokens, cue[0] - 2, cue[0] + offset + 2),
                rationale=f"«{cue[1]}» seguido de «{token}»",
            )
        return None

    def _propose_number(
        self,
        field_key: str,
        prop: dict[str, Any],
        tokens: tuple[str, ...],
        cue: tuple[int, str] | None,
    ) -> FieldProposal | None:
        if cue is None:
            return None
        expected_unit = prop.get("x-unit")
        window_end = min(len(tokens), cue[0] + CUE_WINDOW)
        for index in range(cue[0], window_end):
            if not _is_number(tokens[index]):
                continue
            raw = float(tokens[index])
            value: Any = int(raw) if prop.get("type") == "integer" or raw.is_integer() else raw
            unit_next = tokens[index + 1] if index + 1 < len(tokens) else None
            unit_matches = expected_unit is not None and unit_next == expected_unit
            wrong_unit = (
                expected_unit is not None
                and unit_next in _KNOWN_UNIT_SYMBOLS
                and unit_next != expected_unit
            )
            if wrong_unit:
                # "50 kV" offered for a field measured in kVA is not a transcription
                # detail; it is a different quantity. Refuse rather than convert.
                continue
            confidence = 0.9 if unit_matches else 0.7
            minimum, maximum = prop.get("minimum"), prop.get("maximum")
            if (minimum is not None and raw < minimum) or (maximum is not None and raw > maximum):
                # Out of the domain's own range. Still proposed — a technician may be
                # reporting something genuinely out of range — but not with confidence.
                confidence = 0.4
            return FieldProposal(
                field_key=field_key,
                value=value,
                confidence=min(confidence, MAX_HEURISTIC_CONFIDENCE),
                transcript_span=_span(tokens, cue[0] - 2, index + 2),
                rationale=(
                    f"«{cue[1]}» seguido de {tokens[index]}"
                    + (f" {expected_unit}" if unit_matches else "")
                ),
            )
        return None

    def _propose_date(
        self, field_key: str, tokens: tuple[str, ...], cue: tuple[int, str] | None
    ) -> FieldProposal | None:
        if cue is None:
            return None
        for index in range(cue[0], min(len(tokens), cue[0] + CUE_WINDOW)):
            token = tokens[index]
            if len(token) == 10 and token[4] == "-" and token[7] == "-":
                return FieldProposal(
                    field_key=field_key,
                    value=token,
                    confidence=0.85,
                    transcript_span=_span(tokens, cue[0] - 2, index + 2),
                    rationale=f"«{cue[1]}» seguido de la fecha {token}",
                )
        return None

    def _propose_string(
        self,
        field_key: str,
        tokens: tuple[str, ...],
        lexicon: VoiceLexicon,
        cue: tuple[int, str] | None,
        warnings: list[str],
    ) -> FieldProposal | None:
        """Codes and free text.

        Three paths, in decreasing order of how much can be trusted:

        1. The field has a **catalogue of codes** (a feeder, a substation). Then the only
           acceptable value is one of them, matched against the dictated characters after
           the cue. Nothing else is proposed: a feeder code is not partially right, and
           offering the fragment "04" for "04BH070T11" is the kind of plausible-looking
           value that gets confirmed by a tired technician at five in the afternoon.
        2. **Digits dictated one by one** — "el código dos tres cinco" is 235 as characters,
           which the normalizer deliberately refuses to read as a quantity.
        3. A single alphanumeric token right after the cue, the usual shape of a plate.

        Free prose is never guessed: a narrative field is filled with the transcript by the
        caller, not inferred here.
        """
        if cue is None:
            return None
        start = _skip_connectors(tokens, cue[0])
        window = tokens[start : start + CUE_WINDOW]
        if not window:
            return None

        codes = lexicon.codes_for(field_key)
        if codes:
            return self._propose_code(
                field_key, tokens, start, tokens[start : start + CODE_WINDOW], codes, cue, warnings
            )

        digits = digit_sequence(list(window))
        if digits:
            return FieldProposal(
                field_key=field_key,
                value=digits,
                confidence=0.7,
                transcript_span=_span(tokens, cue[0] - 2, start + len(window)),
                rationale=f"«{cue[1]}» seguido de dígitos dictados uno por uno",
            )

        # A single alphanumeric token right after the cue is the usual shape of a code.
        first = window[0]
        if any(ch.isdigit() for ch in first) and first.isalnum():
            return FieldProposal(
                field_key=field_key,
                value=first.upper(),
                confidence=0.75,
                transcript_span=_span(tokens, cue[0] - 2, start + 2),
                rationale=f"«{cue[1]}» seguido de «{first}»",
            )
        return None

    @staticmethod
    def _propose_code(
        field_key: str,
        tokens: tuple[str, ...],
        start: int,
        window: tuple[str, ...],
        codes: list[str],
        cue: tuple[int, str],
        warnings: list[str],
    ) -> FieldProposal | None:
        """Match the dictated characters after a cue against the field's real catalogue.

        The decoder splits a code into whatever pieces sound like words — "04BH070T11"
        arrives as "04 bh 070 t 11", and a technician spelling it out produces "cero cuatro
        be hache…". So every contiguous slice of the window is tried, longest first, under
        three readings: the characters as transcribed, the same slice read as letter and
        digit names, and finally with the sounds Spanish does not distinguish collapsed.

        The last reading is the interesting one: "04VH070T11" is not a different feeder, it
        is the same feeder with a *v* heard for a *b*. Matching it is what the boost in the
        lexicon cannot do on its own.

        When nothing matches, nothing is proposed, and what was heard is reported. A code
        is not partially right, and offering the fragment "04" for "04BH070T11" produces
        exactly the plausible-looking value that gets confirmed without being read.
        """
        exact = {code_key(code): code for code in codes}
        by_sound = {sound_fold(code): code for code in codes}

        for length in range(len(window), 0, -1):
            for offset in range(0, len(window) - length + 1):
                slice_ = window[offset : offset + length]
                readings = [code_key("".join(slice_))]
                spelled = spell_out(list(slice_))
                if spelled:
                    readings.append(code_key(spelled))
                for reading in readings:
                    if not reading:
                        continue
                    match = exact.get(reading)
                    confidence = 0.9
                    if match is None:
                        match = by_sound.get(sound_fold(reading))
                        confidence = 0.75
                    if match is None:
                        continue
                    return FieldProposal(
                        field_key=field_key,
                        value=match,
                        confidence=confidence,
                        transcript_span=_span(
                            tokens, start + offset - 2, start + offset + length + 1
                        ),
                        rationale=(
                            f"«{cue[1]}» seguido de «{' '.join(slice_)}», "
                            "que corresponde a un valor del catálogo vigente"
                        ),
                    )

        heard = " ".join(window)
        warnings.append(
            f"se escuchó «{heard}» después de «{cue[1]}» y no corresponde a ningún valor "
            f"del catálogo de '{field_key}'; el campo quedó vacío para que lo revise una persona"
        )
        return None


_SYSTEM_PROMPT = (
    "Eres un asistente que extrae datos de un formulario de campo de una distribuidora "
    "eléctrica del Ecuador. Recibes la transcripción de lo que dictó el técnico y devuelves "
    "únicamente los valores que el técnico dijo. Si no lo dijo, devuelve null. No inventes "
    "valores, no completes por contexto y no conviertas unidades."
)


def build_extraction_request(
    transcript: str,
    lexicon: VoiceLexicon,
    schema: dict[str, Any],
    *,
    fields: list[str] | None = None,
    alias: str = EXTRACTOR_ALIAS,
) -> dict[str, Any]:
    """The OpenAI-compatible request for the grammar-constrained extractor (CLAUDE.md 13).

    Returned rather than sent: the gateway is M19, and a payload that can be asserted on
    is worth more than a mock of an HTTP client.
    """
    grammar = build_grammar(schema, fields=fields)
    normalized = normalize(transcript)

    catalogue_lines: list[str] = []
    for field_key in fields or list(extractable_fields(schema)):
        aliases = lexicon.aliases_for(field_key)
        if not aliases:
            continue
        rendered = "; ".join(
            f"{canonical} = {', '.join(forms)}" for canonical, forms in sorted(aliases.items())
        )
        catalogue_lines.append(f"- {field_key}: {rendered}")

    user_content = [f"Transcripción normalizada: {normalized.text}"]
    if catalogue_lines:
        user_content.append(
            "Catálogos válidos (usa el valor de la izquierda):\n" + "\n".join(catalogue_lines)
        )
    if lexicon.volatile_fields:
        user_content.append(
            "Campos de catálogo variable: " + ", ".join(sorted(lexicon.volatile_fields))
        )

    return {
        "model": alias,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(user_content)},
        ],
        # llama.cpp's OpenAI-compatible server takes the grammar here; it is what makes
        # the answer valid JSON by construction rather than by hope.
        "extra_body": {"grammar": grammar},
        "metadata": {
            "grammar_fingerprint": grammar_fingerprint(grammar),
            "lexicon_hash": lexicon.content_hash,
            "form_code": lexicon.form_code,
            "form_version": lexicon.form_version,
        },
    }
