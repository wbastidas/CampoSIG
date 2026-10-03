"""The criticality matrix of Annex C, as a function of data (RF-013).

    Criticidad = Severidad del defecto (1 a 5) por Consecuencia (1 a 5)

with «un ajuste por exposición (zona urbana o escolar, vía principal: +1 nivel)», and a score that
maps to P1..P4 with a suggested deadline.

Every input is data and none of it is in this file:

* **Severity** is an attribute of the defect catalogue. The annex defines it by examples of defect,
  and each area has to be able to adjust it without a deployment.
* **Consequence** is an attribute of a catalogue keyed by asset type — and it is an *approximation*
  the platform declares rather than a fact it computes. The annex defines consequence by impact on
  service: an MV trunk with critical loads is 5 and a branch is 4, and the platform cannot tell them
  apart, because client counts and trunk-versus-branch live in the GIS and the commercial systems.
  So the catalogue says 4 for a line segment and carries the caveat, and the caveat travels with
  every proposal that used it.
* **The deadline** is an attribute of the priority catalogue: the annex's «plazo sugerido
  (parametrizable)».

What this module refuses to do is guess quietly. A defect with no severity, an asset type with no
consequence, a zone nobody marked: each of those produces a proposal that **says** what it could
not know, next to the number. A priority presented as a computation when half its inputs were
defaults is how a supervisor learns to ignore the whole tray.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.workorders.models import Priority

#: Used when the defect catalogue does not say. The middle of the scale, so the proposal lands in
#: the middle of the tray rather than at either end: a default that produced P1 would flood the
#: supervisor, and one that produced P4 would bury real findings.
DEFAULT_SEVERITY = 3

#: Used when no consequence is known for the asset type. Same reasoning.
DEFAULT_CONSEQUENCE = 3

#: The annex's bands. Read as «score ≥ threshold → this priority», worst first.
BANDS: tuple[tuple[int, str], ...] = (
    (20, Priority.CRITICAL.value),
    (12, Priority.HIGH.value),
    (6, Priority.MEDIUM.value),
    (0, Priority.LOW.value),
)

#: What the annex calls each band, kept so a screen can show «P2» next to «alta» — the areas speak
#: in P-numbers and the platform stores its own enum.
ANNEX_LABEL: dict[str, str] = {
    Priority.CRITICAL.value: "P1",
    Priority.HIGH.value: "P2",
    Priority.MEDIUM.value: "P3",
    Priority.LOW.value: "P4",
}

#: The most the exposure adjustment can add to a factor. «+1 nivel» applied to the consequence, not
#: to the score: raising the score directly would move a P3 to P1 in one step on a single defect,
#: and the annex says «nivel».
MAX_FACTOR = 5


@dataclass
class Criticality:
    """A computed priority, with everything needed to argue with it."""

    severity: int
    consequence: int
    score: int
    priority: str
    #: True when the zone's exposure raised the consequence.
    exposed: bool
    #: What the computation could not know, in Spanish. Shown, never paraphrased: a number whose
    #: inputs were defaults has to look different from one whose inputs were known.
    caveats: list[str] = field(default_factory=list)

    @property
    def annex_band(self) -> str:
        return ANNEX_LABEL.get(self.priority, "—")

    @property
    def is_estimated(self) -> bool:
        """Whether any input was a default or an approximation.

        The single flag a screen sorts by: «these ones the platform actually knew».
        """
        return bool(self.caveats)

    def explain(self) -> str:
        """The arithmetic, so a supervisor can redo it."""
        adjustment = " (consecuencia +1 por exposición de la zona)" if self.exposed else ""
        return (
            # El signo de multiplicacion de la frase es el del anexo C y lo lee un supervisor, no
            # un programador: es la frase del documento, tal cual.
            f"severidad {self.severity} × consecuencia {self.consequence} = {self.score}"  # noqa: RUF001
            f"{adjustment} → {self.annex_band} {self.priority}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "consequence": self.consequence,
            "score": self.score,
            "priority": self.priority,
            "annex_band": self.annex_band,
            "exposed": self.exposed,
            "estimated": self.is_estimated,
            "caveats": self.caveats,
            "explanation": self.explain(),
        }


def priority_for(score: int) -> str:
    for threshold, priority in BANDS:
        if score >= threshold:
            return priority
    return Priority.LOW.value


def compute(
    *,
    defect_attributes: dict[str, Any] | None,
    asset_attributes: dict[str, Any] | None,
    defect_code: str | None = None,
    asset_type_key: str | None = None,
    exposed: bool = False,
) -> Criticality:
    """The annex's matrix over the catalogue attributes it is given.

    :param defect_attributes: the `defect` catalogue entry's attributes, or None when the defect is
        not in the catalogue at all.
    :param asset_attributes: the `consequence_by_asset` entry's attributes, or None.
    :param exposed: the zone is urban, near a school or on a main road (RF-152's `exposure`).
    """
    caveats: list[str] = []

    severity = _as_level((defect_attributes or {}).get("severity"))
    if severity is None:
        severity = DEFAULT_SEVERITY
        named = f"«{defect_code}»" if defect_code else "el defecto"
        caveats.append(
            f"{named} no declara severidad en el catálogo; se usó {DEFAULT_SEVERITY} por omisión"
        )

    consequence = _as_level((asset_attributes or {}).get("consequence"))
    if consequence is None:
        consequence = DEFAULT_CONSEQUENCE
        named = f"«{asset_type_key}»" if asset_type_key else "el tipo de activo"
        caveats.append(
            f"no hay consecuencia declarada para {named}; se usó {DEFAULT_CONSEQUENCE} por omisión"
        )
    else:
        caveat = (asset_attributes or {}).get("caveat")
        if isinstance(caveat, str) and caveat.strip():
            # The approximation the catalogue itself declares — «se asume ramal de media tensión» —
            # travels with the number. Otherwise a 4 reads as a measurement.
            caveats.append(caveat.strip())

    if exposed:
        consequence = min(MAX_FACTOR, consequence + 1)

    score = severity * consequence
    return Criticality(
        severity=severity,
        consequence=consequence,
        score=score,
        priority=priority_for(score),
        exposed=exposed,
        caveats=caveats,
    )


def _as_level(value: Any) -> int | None:
    """A level from 1 to 5, or None. Anything outside the scale is treated as absent.

    Deliberately strict: a `severity: 9` in a hand-edited catalogue would silently produce a score
    of 45 and flood the tray with emergencies, so it is refused and reported as missing instead.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 1 <= value <= MAX_FACTOR else None


def suggested_deadline_hours(priority_attributes: dict[str, Any] | None) -> int | None:
    """The annex's «plazo sugerido», from the priority catalogue, or None when there is none.

    None is a real answer for P4: the annex says «plan de mantenimiento», which is not a deadline,
    and inventing hours for it would put maintenance work on a clock nobody agreed to.
    """
    hours = (priority_attributes or {}).get("sla_hours")
    if isinstance(hours, bool) or not isinstance(hours, int):
        return None
    return hours if hours >= 0 else None
