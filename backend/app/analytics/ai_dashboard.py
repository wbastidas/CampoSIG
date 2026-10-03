"""The AI dashboard (RF-134), and the arithmetic that keeps its numbers honest.

Five things the requirement asks for: acceptance rate per field, corrections per visual class, an
estimated word error rate, voice adoption per user, and the model versions in the fleet. All five
come from `field_provenance`, which exists precisely so they can be derived rather than counted by
somebody with a spreadsheet.

Three rules run through the whole module, and they are what separate a dashboard from a decoration:

**A rate without its denominator is not a measurement.** "100 % acceptance" over two proposals is
noise with a percent sign, and the decision it invites — ship the model — is the expensive one. So
every rate travels with the count it came from, and below :data:`MIN_FOR_A_RATE` the rate is `None`
rather than a number somebody will quote.

**The word error rate is named for what it measures.** A true WER compares a transcript against a
reference transcription of the same audio, and nobody transcribes these recordings twice. What can
be measured is the distance between what the pipeline proposed for a field and what the person
submitted — ASR *and* extraction together, over the words that reached a field. That is a useful
estimate and it is not WER, so the payload says so and counts what it could not measure.

**Corrections are the signal, not the failures.** A high correction rate on a visual class is where
the next labelling batch goes (guía 11.1), not a verdict on the crew. The wording follows RF-174's
rule for the agents: it marks for review, it does not accuse.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.responses.models import FieldProvenance, FormResponse, ValueOrigin

#: Below this many proposals, a rate is not reported. The number is small on purpose — a pilot has
#: few captures and an analyst still needs to see the shape — but not one, because a single
#: correction should never read as "50 % error".
MIN_FOR_A_RATE = 5

#: Origins the dashboard is about. Manual, computed and prefilled values are not proposals and
#: including them would dilute every rate with fields no model ever touched.
AI_ORIGINS = (ValueOrigin.VOICE.value, ValueOrigin.VISION.value)


def rate(part: int, whole: int) -> float | None:
    """A share, or None when the denominator is too small to mean anything."""
    if whole < MIN_FOR_A_RATE:
        return None
    return part / whole


@dataclass(frozen=True)
class FieldAcceptance:
    field_key: str
    proposals: int
    accepted: int
    corrected: int
    #: Mean confidence of the proposals, which is what makes a low acceptance rate interpretable:
    #: a model that is wrong *and* confident is a different problem from one that is unsure.
    mean_confidence: float | None

    @property
    def acceptance(self) -> float | None:
        return rate(self.accepted, self.proposals)

    def as_dict(self) -> dict[str, Any]:
        return {
            "field_key": self.field_key,
            "proposals": self.proposals,
            "accepted": self.accepted,
            "corrected": self.corrected,
            "acceptance": self.acceptance,
            "mean_confidence": self.mean_confidence,
        }


@dataclass(frozen=True)
class ClassCorrections:
    """What a vision model proposed, and what people changed it to."""

    proposed_class: str
    proposals: int
    corrected: int
    #: The correction people actually made, most frequent first. A class that is always corrected to
    #: the same other class is a confusion to fix in the taxonomy or the training set; one corrected
    #: to five different classes is a detector that is guessing.
    became: list[tuple[str, int]]

    @property
    def correction_rate(self) -> float | None:
        return rate(self.corrected, self.proposals)

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposed_class": self.proposed_class,
            "proposals": self.proposals,
            "corrected": self.corrected,
            "correction_rate": self.correction_rate,
            "became": [{"value": value, "times": times} for value, times in self.became],
        }


@dataclass(frozen=True)
class WordErrors:
    """The estimate, and what it is an estimate of."""

    reference_words: int
    errors: int
    measured_fields: int
    #: Fields whose value is not text — a number, a code, a list — so no word distance applies.
    unmeasurable_fields: int

    @property
    def error_rate(self) -> float | None:
        if self.measured_fields < MIN_FOR_A_RATE or self.reference_words == 0:
            return None
        return self.errors / self.reference_words

    def as_dict(self) -> dict[str, Any]:
        return {
            "reference_words": self.reference_words,
            "errors": self.errors,
            "measured_fields": self.measured_fields,
            "unmeasurable_fields": self.unmeasurable_fields,
            "error_rate": self.error_rate,
            # Said in the payload, not only in the docs: whoever reads this number will quote it,
            # and they should quote what it measures.
            "measures": (
                "distancia de palabras entre lo que la voz propuso para un campo y lo que la "
                "persona envió: mide la cadena completa (reconocimiento y extracción), no el "
                "reconocimiento solo. No es un WER contra una transcripción de referencia."
            ),
        }


@dataclass(frozen=True)
class VoiceAdoption:
    user: str
    responses: int
    responses_with_voice: int
    voice_fields: int

    @property
    def adoption(self) -> float | None:
        return rate(self.responses_with_voice, self.responses)

    def as_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "responses": self.responses,
            "responses_with_voice": self.responses_with_voice,
            "voice_fields": self.voice_fields,
            "adoption": self.adoption,
        }


@dataclass(frozen=True)
class ModelInFleet:
    model_name: str
    model_version: str
    origin: str
    proposals: int
    accepted: int
    first_seen: datetime | None
    last_seen: datetime | None

    @property
    def acceptance(self) -> float | None:
        return rate(self.accepted, self.proposals)

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "origin": self.origin,
            "proposals": self.proposals,
            "accepted": self.accepted,
            "acceptance": self.acceptance,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


@dataclass
class Dashboard:
    """Everything RF-134 asks for, in one payload.

    One call rather than five, for the same reason the review detail is assembled server-side: a
    screen that makes five calls is a screen where one failure quietly removes a panel, and the
    panel that vanishes is the one nobody notices was supposed to be there.
    """

    since: datetime | None = None
    until: datetime | None = None
    fields: list[FieldAcceptance] = field(default_factory=list)
    visual_classes: list[ClassCorrections] = field(default_factory=list)
    word_errors: WordErrors | None = None
    voice_adoption: list[VoiceAdoption] = field(default_factory=list)
    fleet: list[ModelInFleet] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "since": self.since.isoformat() if self.since else None,
            "until": self.until.isoformat() if self.until else None,
            "min_for_a_rate": MIN_FOR_A_RATE,
            "fields": [item.as_dict() for item in self.fields],
            "visual_classes": [item.as_dict() for item in self.visual_classes],
            "word_errors": self.word_errors.as_dict() if self.word_errors else None,
            "voice_adoption": [item.as_dict() for item in self.voice_adoption],
            "fleet": [item.as_dict() for item in self.fleet],
        }


# --- the word distance -------------------------------------------------------------------


def words_of(value: Any) -> list[str] | None:
    """The words of a text value, or None when it is not text.

    Case and surrounding punctuation are folded away: «Hormigón.» and «hormigón» are the same
    answer, and counting them as an error would inflate the estimate with a difference no person
    would call one.
    """
    if not isinstance(value, str):
        return None
    cleaned = value.replace("\n", " ").strip().lower()
    if not cleaned:
        return None
    words = [token.strip(".,;:()«»\"'¿?¡!") for token in cleaned.split()]
    kept = [word for word in words if word]
    return kept or None


def word_distance(reference: list[str], said: list[str]) -> int:
    """Levenshtein distance over words: substitutions, insertions and deletions.

    Over words rather than characters because that is the unit a WER counts, and because a
    character distance would score «hormigon» against «hormigón» as an error worth a tenth of a
    word when it is a diacritic the extractor should handle.
    """
    if not reference:
        return len(said)
    previous = list(range(len(said) + 1))
    for i, want in enumerate(reference, start=1):
        current = [i]
        for j, got in enumerate(said, start=1):
            current.append(
                min(
                    previous[j] + 1,  # deletion
                    current[j - 1] + 1,  # insertion
                    previous[j - 1] + (0 if want == got else 1),  # substitution
                )
            )
        previous = current
    return previous[-1]


# --- the queries -------------------------------------------------------------------------


def _rows(
    unit_id: uuid.UUID,
    *,
    since: datetime | None,
    until: datetime | None,
    origins: tuple[str, ...] = AI_ORIGINS,
) -> Select[tuple[FieldProvenance, FormResponse]]:
    """Provenance rows of one unit's captures, within the period.

    Scoped to the unit at the query, not filtered afterwards (ADR-009), and dated by the
    submission: a capture taken offline on Monday and synchronised on Wednesday belongs to the week
    the crew did the work, not the week the phone found signal.
    """
    statement = (
        select(FieldProvenance, FormResponse)
        .join(FormResponse, FieldProvenance.response_id == FormResponse.id)
        .where(
            FormResponse.business_unit_id == unit_id,
            FieldProvenance.origin.in_(list(origins)),
        )
    )
    if since is not None:
        statement = statement.where(FormResponse.submitted_at >= since)
    if until is not None:
        statement = statement.where(FormResponse.submitted_at <= until)
    return statement


def _responses(
    unit_id: uuid.UUID, *, since: datetime | None, until: datetime | None
) -> Select[tuple[FormResponse]]:
    """Every submitted capture of the unit in the period.

    The denominator of voice adoption, and it has to be this and not "captures that had an AI
    proposal": measuring adoption over the captures where a model already proposed something would
    count a technician who never dictates as having no captures at all, and the number would read
    high precisely where adoption is lowest.
    """
    statement = select(FormResponse).where(
        FormResponse.business_unit_id == unit_id,
        FormResponse.submitted_at.is_not(None),
    )
    if since is not None:
        statement = statement.where(FormResponse.submitted_at >= since)
    if until is not None:
        statement = statement.where(FormResponse.submitted_at <= until)
    return statement


def _value(payload: dict[str, Any] | None) -> Any:
    return None if payload is None else payload.get("v")


def _label(value: Any) -> str | None:
    """A class value as a label. Only scalars: a list or an object is not a class."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, bool | int | float):
        return str(value)
    return None


def build(
    session: Session,
    unit_id: uuid.UUID,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> Dashboard:
    """The whole dashboard, from one pass over the period's provenance rows.

    One pass because the five panels are five groupings of the same rows, and five queries over the
    same table would be five chances for the panels to disagree about the period they cover.
    """
    pairs = list(session.execute(_rows(unit_id, since=since, until=until)))
    submitted = list(session.scalars(_responses(unit_id, since=since, until=until)))

    per_field: dict[str, list[FieldProvenance]] = defaultdict(list)
    per_class: dict[str, list[FieldProvenance]] = defaultdict(list)
    per_model: dict[tuple[str, str, str], list[FieldProvenance]] = defaultdict(list)
    per_model_seen: dict[tuple[str, str, str], list[datetime]] = defaultdict(list)
    voice_rows: list[FieldProvenance] = []

    for row, response in pairs:
        per_field[row.field_key].append(row)
        if row.origin == ValueOrigin.VISION.value:
            proposed = _label(_value(row.proposed_value))
            if proposed is not None:
                per_class[proposed].append(row)
        if row.origin == ValueOrigin.VOICE.value:
            voice_rows.append(row)
        if row.model_name and row.model_version:
            key = (row.model_name, row.model_version, row.origin)
            per_model[key].append(row)
            when = response.submitted_at or response.captured_at or response.created_at
            if when is not None:
                per_model_seen[key].append(when)

    fields = [
        FieldAcceptance(
            field_key=key,
            proposals=len(rows),
            accepted=sum(1 for row in rows if row.accepted_unchanged),
            corrected=sum(1 for row in rows if not row.accepted_unchanged),
            mean_confidence=_mean([row.confidence for row in rows]),
        )
        for key, rows in sorted(per_field.items())
    ]
    # Worst acceptance first, and never a rate we refused to report: a panel sorted by "None" would
    # put the least measured field at the top, which is the opposite of useful.
    fields.sort(key=lambda item: (item.acceptance is None, item.acceptance or 0.0, item.field_key))

    visual = []
    for proposed, rows in sorted(per_class.items()):
        became = Counter(
            _label(_value(row.final_value)) or "(vacío)"
            for row in rows
            if not row.accepted_unchanged
        )
        visual.append(
            ClassCorrections(
                proposed_class=proposed,
                proposals=len(rows),
                corrected=sum(1 for row in rows if not row.accepted_unchanged),
                became=became.most_common(3),
            )
        )
    visual.sort(
        key=lambda item: (
            item.correction_rate is None,
            -(item.correction_rate or 0.0),
            item.proposed_class,
        )
    )

    fleet = [
        ModelInFleet(
            model_name=name,
            model_version=version,
            origin=origin,
            proposals=len(rows),
            accepted=sum(1 for row in rows if row.accepted_unchanged),
            first_seen=min(per_model_seen[(name, version, origin)], default=None),
            last_seen=max(per_model_seen[(name, version, origin)], default=None),
        )
        for (name, version, origin), rows in sorted(per_model.items())
    ]

    return Dashboard(
        since=since,
        until=until,
        fields=fields,
        visual_classes=visual,
        word_errors=_word_errors(voice_rows),
        voice_adoption=_voice_adoption(submitted, pairs),
        fleet=fleet,
    )


def _mean(values: list[float | None]) -> float | None:
    known = [value for value in values if value is not None]
    return sum(known) / len(known) if known else None


def _word_errors(rows: list[FieldProvenance]) -> WordErrors:
    reference = 0
    errors = 0
    measured = 0
    unmeasurable = 0
    for row in rows:
        final = words_of(_value(row.final_value))
        proposed = words_of(_value(row.proposed_value))
        if final is None or proposed is None:
            # A number, a code, a list or an empty answer. Counted rather than dropped: a rate
            # computed over three of four hundred fields is not the pipeline's error rate, and the
            # only way a reader can tell is if the payload says how little it covered.
            unmeasurable += 1
            continue
        measured += 1
        reference += len(final)
        errors += word_distance(final, proposed)
    return WordErrors(
        reference_words=reference,
        errors=errors,
        measured_fields=measured,
        unmeasurable_fields=unmeasurable,
    )


def _voice_adoption(submitted: list[FormResponse], pairs: list[Any]) -> list[VoiceAdoption]:
    """Adoption per person, over **every** capture that person submitted.

    Per response and not per field: the question RF-134 asks is whether a technician uses the voice
    feature at all, and a field count would rank whoever happens to fill the longer forms.

    The denominator is all of their submitted captures, including the ones with no AI value at all.
    Those are exactly the captures that show non-adoption, so leaving them out would make the metric
    report its best case.
    """
    responses: dict[str, set[uuid.UUID]] = defaultdict(set)
    for response in submitted:
        responses[response.captured_by or "(sin registrar)"].add(response.id)

    with_voice: dict[str, set[uuid.UUID]] = defaultdict(set)
    voice_fields: Counter[str] = Counter()
    for row, response in pairs:
        if row.origin != ValueOrigin.VOICE.value:
            continue
        who = response.captured_by or "(sin registrar)"
        # A draft with a dictated value and no submission is not a capture yet, and it is not in the
        # denominator either: counting it only in the numerator could put adoption above 100 %.
        if response.id not in responses[who]:
            continue
        with_voice[who].add(response.id)
        voice_fields[who] += 1

    return sorted(
        (
            VoiceAdoption(
                user=who,
                responses=len(seen),
                responses_with_voice=len(with_voice.get(who, set())),
                voice_fields=voice_fields.get(who, 0),
            )
            for who, seen in responses.items()
        ),
        key=lambda item: (-item.voice_fields, item.user),
    )
