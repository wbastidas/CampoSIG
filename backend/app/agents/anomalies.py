"""The anomaly node (RF-174). Rules and arithmetic, never an accusation.

The requirement is explicit about tone: «No acusa: marca para revisión», and every alert must show
the rule or the statistic behind it. That is not politeness. A report that reads as an accusation
gets argued with instead of checked, and the crew it names stops cooperating with the platform — at
which point the anomaly agent has cost more than it found.

The rules here are **cross-order** on purpose. Reused evidence inside one work order is already
highlighted on the review screen; the same photograph closing two different orders, or one GPS
reading closing orders in two parishes, is the pattern nothing looks at today, and it is the one
this node is for.
"""

from __future__ import annotations

from datetime import timedelta

from app.agents.facts import PreReviewFacts
from app.agents.geo import distance_m
from app.agents.report import (
    Category,
    EvidenceRef,
    EvidenceType,
    Observation,
    Severity,
)

NODE = "anomalies"

#: Below this, the execution is worth a look. Not proof of anything: a lamp swap on an accessible
#: pole genuinely takes minutes. It is the shortest duration that stops being ordinary.
MIN_PLAUSIBLE_EXECUTION = timedelta(minutes=4)

#: Two captures closer than this are, for practical purposes, the same spot.
SAME_PLACE_M = 25.0


def check_execution_duration(facts: PreReviewFacts) -> list[Observation]:
    """A job that started and finished implausibly close together."""
    started = facts.time("started_at")
    finished = facts.time("finished_at")
    if started is None or finished is None or finished < started:
        # Backwards times are the coherence node's finding; reporting them twice in two voices
        # would make a supervisor read the same mistake in two places.
        return []
    duration = finished - started
    if duration >= MIN_PLAUSIBLE_EXECUTION:
        return []
    minutes = duration.total_seconds() / 60
    return [
        Observation(
            id="ano-duration",
            category=Category.ANOMALY,
            severity=Severity.LOW,
            node=NODE,
            message=(
                f"La ejecución duró {minutes:.0f} min. Requiere verificación: no es imposible, "
                "pero está por debajo de lo habitual para este tipo de trabajo."
            ),
            evidence=[
                EvidenceRef(type=EvidenceType.FIELD, json_path="$.started_at"),
                EvidenceRef(type=EvidenceType.FIELD, json_path="$.finished_at"),
                EvidenceRef(
                    type=EvidenceType.COMPUTED,
                    detail=(
                        f"duración {minutes:.1f} min, umbral "
                        f"{MIN_PLAUSIBLE_EXECUTION.total_seconds() / 60:.0f} min"
                    ),
                ),
            ],
            suggested_action="Confirmar el alcance ejecutado con el jefe de cuadrilla.",
        )
    ]


def check_photos_shared_with_another_order(facts: PreReviewFacts) -> list[Observation]:
    """The same photograph closing two work orders.

    The cross-order case, which nothing else looks at. Inside one order the review screen already
    shows a file sent twice; across orders it is invisible, and it is the cheaper way to close work
    that was not done.
    """
    mine = set(facts.photo_hashes)
    if not mine:
        return []

    found: list[Observation] = []
    for other in facts.other_orders:
        shared = sorted(mine & other.photo_hashes)
        if not shared:
            continue
        label = other.code or other.work_order_id
        found.append(
            Observation(
                id=f"ano-photo-shared-{other.work_order_id}",
                category=Category.ANOMALY,
                severity=Severity.MEDIUM,
                node=NODE,
                message=(
                    f"{len(shared)} fotografía(s) de esta OT tienen el mismo contenido que las de "
                    f"la OT {label}. Requiere verificación."
                ),
                evidence=[
                    *[
                        EvidenceRef(
                            type=EvidenceType.PHOTO,
                            evidence_id=photo.evidence_id,
                        )
                        for photo in facts.photos
                        if photo.content_hash in shared
                    ],
                    EvidenceRef(
                        type=EvidenceType.COMPUTED,
                        detail=(
                            f"hashes compartidos: {', '.join(item[:12] + '…' for item in shared)}"
                        ),
                    ),
                ],
                suggested_action=f"Comparar la evidencia de esta OT con la de {label}.",
            )
        )
    return found


def check_gps_shared_with_another_order(facts: PreReviewFacts) -> list[Observation]:
    """One GPS reading closing orders that should be in different places."""
    if facts.capture_latitude is None or facts.capture_longitude is None:
        return []

    found: list[Observation] = []
    for other in facts.other_orders:
        if other.latitude is None or other.longitude is None:
            continue
        metres = distance_m(
            facts.capture_latitude, facts.capture_longitude, other.latitude, other.longitude
        )
        if metres > SAME_PLACE_M:
            continue
        label = other.code or other.work_order_id
        found.append(
            Observation(
                id=f"ano-gps-shared-{other.work_order_id}",
                category=Category.ANOMALY,
                severity=Severity.LOW,
                node=NODE,
                message=(
                    f"Esta OT y la {label} se cerraron desde prácticamente el mismo punto "
                    f"({metres:.0f} m de separación). Requiere verificación."
                ),
                evidence=[
                    EvidenceRef(type=EvidenceType.FIELD, json_path="$.gps"),
                    EvidenceRef(
                        type=EvidenceType.COMPUTED,
                        detail=(
                            f"separación {metres:.1f} m frente al umbral {SAME_PLACE_M:.0f} m "
                            f"respecto de la OT {label}"
                        ),
                    ),
                ],
                suggested_action=(
                    "Confirmar si las dos OT corresponden a activos en el mismo sitio."
                ),
            )
        )
    return found


def check_duplicate_photos_within_the_order(facts: PreReviewFacts) -> list[Observation]:
    """The same file registered twice in one order, as a pattern rather than a display detail.

    The review screen highlights it for the person looking at the photographs; here it belongs to
    the report so the pattern is counted over time, which is what makes it actionable at all.
    """
    seen: dict[str, list[str]] = {}
    for photo in facts.photos:
        seen.setdefault(photo.content_hash, []).append(photo.evidence_id)
    repeated = {digest: ids for digest, ids in seen.items() if len(ids) > 1}
    if not repeated:
        return []
    return [
        Observation(
            id="ano-photo-duplicate",
            category=Category.ANOMALY,
            severity=Severity.LOW,
            node=NODE,
            message=(
                f"{len(repeated)} archivo(s) de evidencia se registraron más de una vez en esta "
                "OT. Requiere verificación."
            ),
            evidence=[
                *[
                    EvidenceRef(type=EvidenceType.PHOTO, evidence_id=identifier)
                    for ids in repeated.values()
                    for identifier in ids
                ],
                EvidenceRef(
                    type=EvidenceType.COMPUTED,
                    detail=(
                        "hashes repetidos: "
                        + ", ".join(digest[:12] + "…" for digest in sorted(repeated))
                    ),
                ),
            ],
            suggested_action="Verificar que el antes y el después no sean la misma fotografía.",
        )
    ]


def run(facts: PreReviewFacts) -> list[Observation]:
    """Every anomaly rule, in a stable order."""
    return [
        *check_execution_duration(facts),
        *check_duplicate_photos_within_the_order(facts),
        *check_photos_shared_with_another_order(facts),
        *check_gps_shared_with_another_order(facts),
    ]
