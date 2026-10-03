"""The coherence node (RF-171). Deterministic rules only.

Design rule 1 of SRS 7.7: **deterministic rules first, the LLM afterwards.** Everything verifiable
with code — times, distances, hashes, catalogue values — is a function, and the LLM is left to read
free text and write prose. That halves the cost on small hardware and, more importantly, makes the
findings reproducible: a rule that fired yesterday fires today on the same capture.

Every rule here points at what it compared. An observation that said "the times look wrong" without
the two timestamps would make a supervisor go and find them, which is the work the report exists to
save.

The tone is neutral throughout (RF-174 sets it for anomalies; there is no reason for coherence to be
harsher). These are things to check with the crew, not accusations: a technician who dictated the
wrong hour and a technician who did something wrong produce the same observation, and only one of
them is a problem.
"""

from __future__ import annotations

from datetime import datetime
from itertools import pairwise

from app.agents.facts import PreReviewFacts
from app.agents.geo import distance_m, format_distance
from app.agents.report import (
    Category,
    EvidenceRef,
    EvidenceType,
    Observation,
    Severity,
    Source,
)

NODE = "coherence"

#: The order the times block declares (B03). Any pair out of this order is an inconsistency.
TIME_SEQUENCE = ("dispatched_at", "departed_at", "arrived_at", "started_at", "finished_at")

#: How far the capture may sit from the asset before it is worth asking about. Generous on purpose:
#: a phone's GPS under a canopy of trees or beside a substation wall is routinely off by tens of
#: metres, and a rule that fired on that would be ignored within a week.
GPS_TOLERANCE_M = 250.0

#: Below this, an AI-proposed value accepted without a change is worth a second look. Not wrong —
#: worth checking, which is a different claim and the one the message makes.
LOW_CONFIDENCE = 0.6


def _time_label(key: str) -> str:
    return {
        "dispatched_at": "despacho",
        "departed_at": "salida",
        "arrived_at": "llegada",
        "started_at": "inicio",
        "finished_at": "fin",
    }.get(key, key)


def check_time_order(facts: PreReviewFacts) -> list[Observation]:
    """Times that run backwards (RF-171).

    Compares consecutive declared times rather than all pairs: reporting six observations for one
    mistyped hour buries the one that matters.
    """
    found: list[Observation] = []
    declared = [(key, facts.time(key)) for key in TIME_SEQUENCE]
    present = [(key, when) for key, when in declared if when is not None]

    for (earlier_key, earlier), (later_key, later) in pairwise(present):
        if later >= earlier:
            continue
        found.append(
            Observation(
                id=f"coh-time-{earlier_key}-{later_key}",
                category=Category.COHERENCE,
                severity=Severity.MEDIUM,
                node=NODE,
                message=(
                    f"La hora de {_time_label(later_key)} ({later.isoformat(timespec='minutes')}) "
                    f"es anterior a la de {_time_label(earlier_key)} "
                    f"({earlier.isoformat(timespec='minutes')})."
                ),
                evidence=[
                    EvidenceRef(type=EvidenceType.FIELD, json_path=f"$.{earlier_key}"),
                    EvidenceRef(type=EvidenceType.FIELD, json_path=f"$.{later_key}"),
                ],
                suggested_action="Confirmar la secuencia de horas con el jefe de cuadrilla.",
            )
        )
    return found


def check_times_are_not_in_the_future(
    facts: PreReviewFacts, now: datetime | None = None
) -> list[Observation]:
    """A time after the moment the capture arrived.

    Compared against the submission, not against the clock of whoever runs the report: a night batch
    that ran twelve hours later would otherwise find nothing, and a run in a different timezone
    would find everything.

    That ordering is the whole rule, and it used to be the other way round: `now` took precedence,
    so any caller that passed one — the night batch, the golden-set evaluation — silently compared
    against the wrong moment and the rule went quiet. The clock is only the fallback for a capture
    that carries no submission time, where there is nothing else to compare against.
    """
    reference = facts.submitted_at or now
    if reference is None:
        return []
    found: list[Observation] = []
    for key in TIME_SEQUENCE:
        when = facts.time(key)
        if when is None or when <= reference:
            continue
        found.append(
            Observation(
                id=f"coh-future-{key}",
                category=Category.COHERENCE,
                severity=Severity.MEDIUM,
                node=NODE,
                message=(
                    f"La hora de {_time_label(key)} ({when.isoformat(timespec='minutes')}) es "
                    f"posterior al envío de la captura "
                    f"({reference.isoformat(timespec='minutes')})."
                ),
                evidence=[EvidenceRef(type=EvidenceType.FIELD, json_path=f"$.{key}")],
                suggested_action="Verificar la hora del dispositivo y la hora declarada.",
            )
        )
    return found


def check_capture_is_near_the_asset(facts: PreReviewFacts) -> list[Observation]:
    """The capture's GPS against where the asset is (RF-171)."""
    if (
        facts.capture_latitude is None
        or facts.capture_longitude is None
        or facts.asset_latitude is None
        or facts.asset_longitude is None
    ):
        return []
    metres = distance_m(
        facts.capture_latitude,
        facts.capture_longitude,
        facts.asset_latitude,
        facts.asset_longitude,
    )
    if metres <= GPS_TOLERANCE_M:
        return []
    return [
        Observation(
            id="coh-gps-distance",
            category=Category.COHERENCE,
            severity=Severity.MEDIUM if metres < 1_000 else Severity.HIGH,
            node=NODE,
            message=(
                f"La captura se registró a {format_distance(metres)} del activo "
                f"{facts.asset_code or 'declarado'}."
            ),
            evidence=[
                EvidenceRef(type=EvidenceType.FIELD, json_path="$.gps"),
                EvidenceRef(
                    type=EvidenceType.COMPUTED,
                    detail=(
                        "distancia haversine entre la captura y el activo: "
                        f"{format_distance(metres)}, tolerancia "
                        f"{format_distance(GPS_TOLERANCE_M)}"
                    ),
                ),
            ],
            suggested_action="Confirmar que se trabajó en el activo de la OT.",
        )
    ]


def check_evidence_integrity(facts: PreReviewFacts) -> list[Observation]:
    """A photograph whose stored hash does not match its file.

    High severity without hedging: either the file changed after capture or the record is wrong, and
    both mean the evidence cannot support an approval.
    """
    return [
        Observation(
            id=f"coh-hash-{photo.evidence_id}",
            category=Category.EVIDENCE,
            severity=Severity.HIGH,
            node=NODE,
            message=(
                f"La evidencia {photo.stage} no coincide con el hash registrado al capturarla."
            ),
            evidence=[
                EvidenceRef(type=EvidenceType.PHOTO, evidence_id=photo.evidence_id),
                EvidenceRef(
                    type=EvidenceType.COMPUTED,
                    detail=f"hash registrado {photo.content_hash[:16]}…, verificación fallida",
                ),
            ],
            suggested_action="Pedir nuevamente la evidencia antes de aprobar.",
        )
        for photo in facts.photos
        if not photo.integrity_verified
    ]


def check_low_confidence_accepted_unchanged(facts: PreReviewFacts) -> list[Observation]:
    """An AI proposal accepted without a change and without much confidence (rule 8).

    The failure this looks for is a person tapping through a form: the value came from a model, the
    model was not sure, and nobody altered it. That is not evidence of anything wrong — it is the
    place a supervisor's attention is worth most.
    """
    found: list[Observation] = []
    for value in facts.ai_values:
        if not value.accepted_unchanged or value.confidence is None:
            continue
        if value.confidence >= LOW_CONFIDENCE:
            continue
        found.append(
            Observation(
                id=f"coh-lowconf-{value.field_key}",
                category=Category.COHERENCE,
                severity=Severity.LOW,
                node=NODE,
                confidence=value.confidence,
                message=(
                    f"El campo '{value.field_key}' se aceptó sin cambios con una confianza de "
                    f"{value.confidence:.0%} ({value.origin}, "
                    f"{value.model_name or 'modelo sin identificar'})."
                ),
                evidence=[
                    EvidenceRef(type=EvidenceType.FIELD, json_path=f"$.{value.field_key}"),
                    EvidenceRef(
                        type=EvidenceType.COMPUTED,
                        detail=(
                            f"confianza {value.confidence:.2f} por debajo del umbral "
                            f"{LOW_CONFIDENCE:.2f}; confirmado por "
                            f"{value.confirmed_by or 'nadie'}"
                        ),
                    ),
                ],
                suggested_action="Verificar el valor con la evidencia.",
            )
        )
    return found


def carry_regulatory_findings(facts: PreReviewFacts) -> list[Observation]:
    """The deterministic compliance findings, as observations with their citation (RF-172).

    Carried, not recomputed: the report must agree with the approval gate, and a node that evaluated
    the rules again could contradict the decision it documents. A finding whose limit nobody
    verified travels with `verified=False`, so the reader sees a provisional result rather than a
    citation of the official text (ADR-007).
    """
    found: list[Observation] = []
    for finding in facts.regulatory:
        if finding.outcome not in ("incumple", "no_determinable"):
            continue
        document = finding.norm_ref or "norma no identificada"
        found.append(
            Observation(
                id=f"reg-{finding.rule}",
                category=Category.REGULATORY,
                severity=Severity(finding.severity),
                node=NODE,
                message=finding.message,
                source=Source(
                    document=document,
                    section=finding.article_ref,
                    verified=finding.limit_verified,
                ),
                evidence=[
                    EvidenceRef(
                        type=EvidenceType.COMPUTED,
                        detail=f"regla determinista '{finding.rule}', resultado {finding.outcome}",
                    )
                ],
                suggested_action="Revisar el incumplimiento antes de aprobar.",
            )
        )
    return found


def run(facts: PreReviewFacts, now: datetime | None = None) -> list[Observation]:
    """Every deterministic coherence rule, in a stable order."""
    return [
        *check_time_order(facts),
        *check_times_are_not_in_the_future(facts, now),
        *check_capture_is_near_the_asset(facts),
        *check_evidence_integrity(facts),
        *check_low_confidence_accepted_unchanged(facts),
        *carry_regulatory_findings(facts),
    ]
