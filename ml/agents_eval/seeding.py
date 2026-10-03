"""Labelled perturbations and benign variations (guía 11.2, RNF-060).

The golden set is built the way the guide prescribes: take clean captures and **plant** labelled
inconsistencies. Hand-writing two hundred cases would produce two hundred cases somebody wrote to
pass, and the interesting failure is not the case you imagined — it is the legitimate capture that
looks like a problem.

Hence two catalogues, and the second one is the one that earns its keep:

* :data:`PERTURBATIONS` plant a defect and say which rule must catch it. They measure **recall**.
* :data:`VARIATIONS` change a capture in ways a crew legitimately does — a different hour, one more
  photograph, a GPS reading at the edge of tolerance. They must produce **no** observation, and they
  are what measures **precision**. Without them precision is unmeasurable: a false positive only
  shows up on a capture that was fine.

Every function takes and returns a plain dict, so a case is data and the corpus can be read by
somebody who does not read Python.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

Capture = dict[str, Any]


@dataclass(frozen=True)
class Perturbation:
    """One planted defect and the observation that must catch it."""

    id: str
    #: Prefix of the observation id the rules must produce. A prefix rather than the whole id
    #: because several carry the field or the evidence in them.
    expects: str
    #: Why this defect matters, for the report a person reads.
    note: str
    apply: Callable[[Capture], Capture]
    #: Some defects cannot be planted on every base (a capture with no times has no time to swap).
    applies_when: Callable[[Capture], bool] = lambda capture: True


@dataclass(frozen=True)
class Variation:
    """A legitimate change. Anything the rules say about it is a false positive."""

    id: str
    note: str
    apply: Callable[[Capture], Capture]
    applies_when: Callable[[Capture], bool] = lambda capture: True


def _shift(when: str, delta: timedelta) -> str:
    return (datetime.fromisoformat(when) + delta).isoformat()


def _has(capture: Capture, *keys: str) -> bool:
    return all(capture["answers"].get(key) for key in keys)


def _photos(capture: Capture) -> list[dict[str, Any]]:
    return capture.get("photos") or []


# --- planted defects ---------------------------------------------------------------------


def _swap_times(capture: Capture) -> Capture:
    """Finish before start. The plainest incoherence there is."""
    answers = capture["answers"]
    answers["started_at"], answers["finished_at"] = answers["finished_at"], answers["started_at"]
    return capture


def _arrive_after_starting(capture: Capture) -> Capture:
    answers = capture["answers"]
    answers["arrived_at"] = _shift(answers["started_at"], timedelta(hours=1))
    return capture


def _finish_in_the_future(capture: Capture) -> Capture:
    """Finished after the capture reached the server."""
    answers = capture["answers"]
    answers["finished_at"] = _shift(capture["submitted_at"], timedelta(hours=2))
    return capture


def _move_the_capture_far_away(capture: Capture) -> Capture:
    """Six kilometres from the asset: a photograph taken somewhere else."""
    asset = capture["asset"]
    capture["answers"]["gps"] = {
        "latitude": asset["latitude"] + 0.058,
        "longitude": asset["longitude"],
    }
    return capture


def _break_a_hash(capture: Capture) -> Capture:
    """Evidence whose hash does not match what the device recorded."""
    _photos(capture)[0]["verified"] = False
    return capture


def _accept_a_weak_proposal(capture: Capture) -> Capture:
    """An AI value accepted unchanged with low confidence (SRS rule 0.5)."""
    capture["ai_values"] = [
        {
            "field": "material",
            "origin": "voz",
            "confidence": 0.34,
            "accepted_unchanged": True,
            "confirmed_by": "kc|tecnico.9",
        }
    ]
    return capture


def _shorten_the_execution(capture: Capture) -> Capture:
    """Two minutes between start and finish."""
    answers = capture["answers"]
    answers["finished_at"] = _shift(answers["started_at"], timedelta(minutes=2))
    return capture


def _duplicate_a_photo(capture: Capture) -> Capture:
    """The same file sent twice inside one work order."""
    photos = _photos(capture)
    twin = copy.deepcopy(photos[0])
    twin["id"] = f"{twin['id']}-bis"
    twin["stage"] = "despues"
    photos.append(twin)
    return capture


def _share_a_photo_with_another_order(capture: Capture) -> Capture:
    """The same photograph closing two different work orders. The pattern nothing looks at today."""
    shared = _photos(capture)[0]["hash"]
    capture.setdefault("other_orders", []).append(
        {
            "id": "wo-sembrada",
            "code": "OT-000500",
            "hashes": [shared],
            "latitude": capture["asset"]["latitude"] + 0.5,
            "longitude": capture["asset"]["longitude"] + 0.5,
        }
    )
    return capture


def _share_the_spot_with_another_order(capture: Capture) -> Capture:
    """Two orders closed from the same point, with different photographs."""
    gps = capture["answers"]["gps"]
    capture.setdefault("other_orders", []).append(
        {
            "id": "wo-mismo-punto",
            "code": "OT-000501",
            "hashes": ["ffff"],
            "latitude": gps["latitude"],
            "longitude": gps["longitude"],
        }
    )
    return capture


PERTURBATIONS: tuple[Perturbation, ...] = (
    Perturbation(
        id="tiempos-invertidos",
        expects="coh-time-",
        note="Terminó antes de empezar.",
        apply=_swap_times,
        applies_when=lambda capture: _has(capture, "started_at", "finished_at"),
    ),
    Perturbation(
        id="llegada-despues-del-inicio",
        expects="coh-time-",
        note="Llegó después de haber empezado.",
        apply=_arrive_after_starting,
        applies_when=lambda capture: _has(capture, "arrived_at", "started_at"),
    ),
    Perturbation(
        id="fin-en-el-futuro",
        expects="coh-future-",
        note="Terminó después de que la captura llegó al servidor.",
        apply=_finish_in_the_future,
        applies_when=lambda capture: _has(capture, "finished_at"),
    ),
    Perturbation(
        id="captura-lejos-del-activo",
        expects="coh-gps-distance",
        note="La captura está a kilómetros del activo.",
        apply=_move_the_capture_far_away,
        applies_when=lambda capture: bool(capture["answers"].get("gps")),
    ),
    Perturbation(
        id="hash-que-no-cuadra",
        expects="coh-hash-",
        note="La evidencia no coincide con lo que registró el dispositivo.",
        apply=_break_a_hash,
        applies_when=lambda capture: bool(_photos(capture)),
    ),
    Perturbation(
        id="propuesta-debil-aceptada",
        expects="coh-lowconf-",
        note="Valor de IA con poca confianza aceptado sin cambios.",
        apply=_accept_a_weak_proposal,
    ),
    Perturbation(
        id="ejecucion-de-dos-minutos",
        expects="ano-duration",
        note="Ejecución implausiblemente corta.",
        apply=_shorten_the_execution,
        applies_when=lambda capture: _has(capture, "started_at", "finished_at"),
    ),
    Perturbation(
        id="foto-repetida-en-la-ot",
        expects="ano-photo-duplicate",
        note="El mismo archivo enviado dos veces.",
        apply=_duplicate_a_photo,
        applies_when=lambda capture: bool(_photos(capture)),
    ),
    Perturbation(
        id="foto-compartida-entre-ot",
        expects="ano-photo-shared-",
        note="La misma fotografía cerrando dos OT distintas.",
        apply=_share_a_photo_with_another_order,
        applies_when=lambda capture: bool(_photos(capture)),
    ),
    Perturbation(
        id="mismo-punto-en-dos-ot",
        expects="ano-gps-shared-",
        note="Dos OT cerradas desde el mismo punto.",
        apply=_share_the_spot_with_another_order,
        applies_when=lambda capture: bool(capture["answers"].get("gps")),
    ),
)


# --- legitimate variations ---------------------------------------------------------------


def _another_day(capture: Capture) -> Capture:
    """The same work, a week later. Nothing about a date is a finding."""
    answers = capture["answers"]
    for key in ("dispatched_at", "departed_at", "arrived_at", "started_at", "finished_at"):
        if answers.get(key):
            answers[key] = _shift(answers[key], timedelta(days=7))
    capture["submitted_at"] = _shift(capture["submitted_at"], timedelta(days=7))
    return capture


def _one_more_photo(capture: Capture) -> Capture:
    photos = _photos(capture)
    photos.append(
        {
            "id": f"{capture['id']}-extra",
            "stage": "despues",
            "hash": f"e{abs(hash(capture['id'])) % 10000:04d}",
            "verified": True,
        }
    )
    return capture


def _a_longer_job(capture: Capture) -> Capture:
    answers = capture["answers"]
    if answers.get("finished_at"):
        answers["finished_at"] = _shift(answers["finished_at"], timedelta(hours=2))
        capture["submitted_at"] = _shift(capture["submitted_at"], timedelta(hours=3))
    return capture


def _gps_at_the_edge(capture: Capture) -> Capture:
    """Two hundred metres out: within tolerance, and routine under a canopy of trees."""
    asset = capture["asset"]
    capture["answers"]["gps"] = {
        "latitude": asset["latitude"] + 0.0018,
        "longitude": asset["longitude"],
    }
    return capture


def _a_confirmed_proposal(capture: Capture) -> Capture:
    """Low confidence, but a person corrected it. Confidence stops mattering there."""
    capture["ai_values"] = [
        {
            "field": "material",
            "origin": "vision",
            "confidence": 0.22,
            "accepted_unchanged": False,
            "confirmed_by": "kc|tecnico.4",
        }
    ]
    return capture


def _a_strong_proposal_accepted(capture: Capture) -> Capture:
    capture["ai_values"] = [
        {
            "field": "material",
            "origin": "voz",
            "confidence": 0.94,
            "accepted_unchanged": True,
            "confirmed_by": "kc|tecnico.4",
        }
    ]
    return capture


def _a_neighbour_up_the_street(capture: Capture) -> Capture:
    """Another order fifty metres away with its own photographs: an ordinary day on a feeder."""
    gps = capture["answers"].get("gps") or capture["asset"]
    capture.setdefault("other_orders", []).append(
        {
            "id": "wo-al-lado",
            "code": "OT-000700",
            "hashes": ["aaaa"],
            "latitude": gps["latitude"] + 0.00045,
            "longitude": gps["longitude"],
        }
    )
    return capture


def _a_compliant_regulatory_finding(capture: Capture) -> Capture:
    capture.setdefault("regulatory", []).append(
        {
            "rule": "resistencia_tierra",
            "outcome": "cumple",
            "severity": "low",
            "message": "Resistencia de puesta a tierra dentro del límite.",
            "norm_ref": "ARCERNNR 002/20",
            "article_ref": "Art. 20",
            "limit_verified": True,
        }
    )
    return capture


def _a_worse_condition(capture: Capture) -> Capture:
    """A capture may report a bad asset. Bad condition is the job, not an inconsistency."""
    capture["answers"]["general_condition"] = "malo"
    return capture


def _a_different_priority(capture: Capture) -> Capture:
    capture["answers"]["priority"] = "alta"
    return capture


VARIATIONS: tuple[Variation, ...] = (
    Variation(id="otro-dia", note="La misma faena una semana después.", apply=_another_day),
    Variation(id="una-foto-mas", note="Una fotografía adicional.", apply=_one_more_photo),
    Variation(id="faena-mas-larga", note="Dos horas más de trabajo.", apply=_a_longer_job),
    Variation(
        id="gps-en-el-borde",
        note="Doscientos metros: dentro de la tolerancia.",
        apply=_gps_at_the_edge,
        applies_when=lambda capture: bool(capture["answers"].get("gps")),
    ),
    Variation(
        id="propuesta-corregida",
        note="Poca confianza, pero la persona la corrigió.",
        apply=_a_confirmed_proposal,
    ),
    Variation(
        id="propuesta-fuerte-aceptada",
        note="Alta confianza aceptada sin cambios.",
        apply=_a_strong_proposal_accepted,
    ),
    Variation(
        id="vecina-a-cincuenta-metros",
        note="Otra OT calle arriba, con sus propias fotos.",
        apply=_a_neighbour_up_the_street,
    ),
    Variation(
        id="normativa-que-cumple",
        note="Un hallazgo normativo que cumple.",
        apply=_a_compliant_regulatory_finding,
    ),
    Variation(id="peor-estado", note="El activo está en mal estado.", apply=_a_worse_condition),
    Variation(id="otra-prioridad", note="Prioridad alta.", apply=_a_different_priority),
)
