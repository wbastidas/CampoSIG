"""Deterministic compliance rules (ADR-007, plan I12, SRS 10.4).

This is what replaced the normative RAG. Every rule here does arithmetic: it takes a measured
value from the capture, the limit in force from :mod:`app.regulatory.service`, and compares
them. No model is involved, the result is reproducible, and it cites the norm — because an
observation without a citation is an opinion.

Three properties each rule has, and each one exists because of a way this goes wrong:

* **A missing fact is not a pass.** A rule with nothing to measure returns *not applicable*
  and says why. Treating absence as compliance is how a form with an empty field gets
  approved as compliant.
* **A missing limit is not a pass either.** ``UnknownParameterError`` propagates as a finding
  that says the platform cannot judge, not as a silent success.
* **An unverified limit gives a provisional verdict.** The comparison still runs — it is
  useful — but the finding is marked so nobody cites it as if it came from the official text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.regulatory.models import RegulatoryParameter
from app.regulatory.service import (
    UnknownParameterError,
    UnverifiedParameterError,
    parameter_in_force,
)

#: Parameter codes the shipped rules read. Listed so the admin screen can show which limits
#: the platform needs loaded, and so a test can assert none is hard-coded elsewhere.
#: The form catalogue already declares this code on its computed field; the rule reads
#: the same one, so a form annotation and a rule can never drift apart.
APG_RESTORATION_HOURS = "apg.max_restoration_hours"
NON_COMPUTABLE_INTERRUPTION_SECONDS = "interruption.non_computable_seconds"
MAX_EARTH_RESISTANCE_OHM = "grounding.max_resistance_ohm"

REQUIRED_PARAMETER_CODES = (
    APG_RESTORATION_HOURS,
    NON_COMPUTABLE_INTERRUPTION_SECONDS,
    MAX_EARTH_RESISTANCE_OHM,
)


class Outcome(StrEnum):
    COMPLIES = "cumple"
    BREACHES = "incumple"
    #: The capture has nothing to measure. Not a pass.
    NOT_APPLICABLE = "no_aplica"
    #: The platform cannot judge: no limit in force, or a strict limit unverified.
    UNDETERMINED = "no_determinable"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Facts:
    """What a capture offers a rule, all optional.

    Built by :func:`facts_from` out of the work order and the submitted answers. A rule reads
    only what it needs and reports ``NOT_APPLICABLE`` for the rest, which is what lets one
    form type be evaluated by the same set of rules as another.
    """

    #: When the claim or the outage was reported.
    reported_at: datetime | None = None
    #: When the crew restored service or replaced the lamp.
    restored_at: datetime | None = None
    #: Zone class the limit is keyed by (urban, rural...). Canonical, from the order.
    zone_class: str | None = None
    interruption_seconds: float | None = None
    earth_resistance_ohm: float | None = None
    #: Canonical context for the resistance limit (a substation and a pole differ).
    grounding_context: str | None = None
    #: The date the compliance is judged as of — normally the capture date, never today, so
    #: re-running the rules on an old order gives the same answer it gave then.
    evaluated_on: date = field(default_factory=lambda: datetime.now(UTC).date())


@dataclass
class Finding:
    """One rule's result, with everything needed to cite it."""

    rule: str
    outcome: Outcome
    message: str
    severity: Severity = Severity.MEDIUM
    measured: float | None = None
    limit: Any = None
    unit: str | None = None
    norm_ref: str | None = None
    article_ref: str | None = None
    #: False when the limit has not been checked against the official text: the comparison
    #: stands, the citation does not.
    limit_verified: bool = True
    parameter_code: str | None = None
    evaluated_on: date | None = None

    @property
    def blocking(self) -> bool:
        """Whether this should stop an approval.

        Only a confirmed high-severity breach against a verified limit. An undetermined
        finding is a gap in configuration, and blocking approvals over a parameter nobody
        loaded would punish the crew for the office's omission.
        """
        return (
            self.outcome is Outcome.BREACHES
            and self.severity is Severity.HIGH
            and self.limit_verified
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "outcome": self.outcome.value,
            "message": self.message,
            "severity": self.severity.value,
            "measured": self.measured,
            "limit": self.limit,
            "unit": self.unit,
            "norm_ref": self.norm_ref,
            "article_ref": self.article_ref,
            "limit_verified": self.limit_verified,
            "parameter_code": self.parameter_code,
            "evaluated_on": self.evaluated_on.isoformat() if self.evaluated_on else None,
            "blocking": self.blocking,
        }


class ComplianceRule(Protocol):
    name: str

    def evaluate(self, session: Session, facts: Facts) -> Finding: ...


def _resolve(
    session: Session, base_code: str, key: str | None, facts: Facts
) -> tuple[RegulatoryParameter | None, Finding | None]:
    """Fetch the parameter in force, or the finding explaining why it cannot be fetched.

    Tries the keyed code first (``grounding.max_resistance_ohm.substation``) and falls back
    to the base code, because a regulator sometimes publishes one number for everything and
    sometimes a table. The fallback is a real behaviour, not a convenience: a platform that
    demanded the keyed form would refuse to evaluate a perfectly well-specified single limit.
    """
    candidates = [f"{base_code}.{key}"] if key else []
    candidates.append(base_code)
    problems: list[str] = []
    for code in candidates:
        try:
            return parameter_in_force(session, code, on=facts.evaluated_on), None
        except UnknownParameterError as exc:
            problems.append(str(exc))
        except UnverifiedParameterError as exc:
            return None, Finding(
                rule=base_code,
                outcome=Outcome.UNDETERMINED,
                message=str(exc),
                severity=Severity.HIGH,
                parameter_code=code,
                evaluated_on=facts.evaluated_on,
            )
    return None, Finding(
        rule=base_code,
        outcome=Outcome.UNDETERMINED,
        message=(
            f"no hay un límite vigente para '{base_code}' el {facts.evaluated_on}; "
            "hasta cargarlo, la plataforma no puede juzgar este punto"
        ),
        severity=Severity.MEDIUM,
        parameter_code=candidates[0],
        evaluated_on=facts.evaluated_on,
    )


class ApgRestorationRule:
    """Street-light restoration inside the deadline the regulator sets (SRS 4.8, RF-350)."""

    name = "plazo_reposicion_apg"

    def evaluate(self, session: Session, facts: Facts) -> Finding:
        if facts.reported_at is None or facts.restored_at is None:
            return Finding(
                rule=self.name,
                outcome=Outcome.NOT_APPLICABLE,
                message=(
                    "la captura no tiene fecha de reclamo y de reposición, así que el plazo "
                    "no se puede medir"
                ),
                severity=Severity.LOW,
                evaluated_on=facts.evaluated_on,
            )

        parameter, problem = _resolve(session, APG_RESTORATION_HOURS, facts.zone_class, facts)
        if problem is not None:
            return problem
        assert parameter is not None

        limit_hours = float(_scalar(parameter.value))
        elapsed_hours = (facts.restored_at - facts.reported_at).total_seconds() / 3600
        complies = elapsed_hours <= limit_hours
        return Finding(
            rule=self.name,
            outcome=Outcome.COMPLIES if complies else Outcome.BREACHES,
            message=(
                f"la reposición tomó {elapsed_hours:.1f} h "
                f"{'dentro del' if complies else 'por encima del'} plazo de {limit_hours:g} h"
            ),
            severity=Severity.HIGH,
            measured=round(elapsed_hours, 2),
            limit=limit_hours,
            unit=parameter.unit or "h",
            norm_ref=parameter.norm_ref,
            article_ref=parameter.article_ref,
            limit_verified=parameter.is_verified,
            parameter_code=parameter.code,
            evaluated_on=facts.evaluated_on,
        )


class NonComputableInterruptionRule:
    """Whether an interruption counts towards the quality indices (SRS 4.x, RF-351).

    Not a breach either way: the outcome is a *classification*, and the regulator's threshold
    is what decides it. Reported as a finding so a supervisor sees the reasoning instead of a
    number appearing in a report.
    """

    name = "interrupcion_no_computable"

    def evaluate(self, session: Session, facts: Facts) -> Finding:
        if facts.interruption_seconds is None:
            return Finding(
                rule=self.name,
                outcome=Outcome.NOT_APPLICABLE,
                message="la captura no registra duración de interrupción",
                severity=Severity.LOW,
                evaluated_on=facts.evaluated_on,
            )

        parameter, problem = _resolve(session, NON_COMPUTABLE_INTERRUPTION_SECONDS, None, facts)
        if problem is not None:
            return problem
        assert parameter is not None

        threshold = float(_scalar(parameter.value))
        computable = facts.interruption_seconds >= threshold
        return Finding(
            rule=self.name,
            outcome=Outcome.COMPLIES,
            message=(
                f"interrupción de {facts.interruption_seconds:g} s: "
                f"{'computable' if computable else 'no computable'} frente al umbral de "
                f"{threshold:g} s"
            ),
            severity=Severity.LOW,
            measured=facts.interruption_seconds,
            limit=threshold,
            unit=parameter.unit or "s",
            norm_ref=parameter.norm_ref,
            article_ref=parameter.article_ref,
            limit_verified=parameter.is_verified,
            parameter_code=parameter.code,
            evaluated_on=facts.evaluated_on,
        )


class EarthResistanceRule:
    """Measured earth resistance against the admissible maximum (RF-350)."""

    name = "resistencia_puesta_a_tierra"

    def evaluate(self, session: Session, facts: Facts) -> Finding:
        if facts.earth_resistance_ohm is None:
            return Finding(
                rule=self.name,
                outcome=Outcome.NOT_APPLICABLE,
                message="la captura no registra medición de resistencia de puesta a tierra",
                severity=Severity.LOW,
                evaluated_on=facts.evaluated_on,
            )

        parameter, problem = _resolve(
            session, MAX_EARTH_RESISTANCE_OHM, facts.grounding_context, facts
        )
        if problem is not None:
            return problem
        assert parameter is not None

        limit = float(_scalar(parameter.value))
        complies = facts.earth_resistance_ohm <= limit
        return Finding(
            rule=self.name,
            outcome=Outcome.COMPLIES if complies else Outcome.BREACHES,
            message=(
                f"resistencia medida de {facts.earth_resistance_ohm:g} Ω "
                f"{'dentro del' if complies else 'por encima del'} máximo admisible de "
                f"{limit:g} Ω"
            ),
            severity=Severity.HIGH,
            measured=facts.earth_resistance_ohm,
            limit=limit,
            unit=parameter.unit or "ohm",
            norm_ref=parameter.norm_ref,
            article_ref=parameter.article_ref,
            limit_verified=parameter.is_verified,
            parameter_code=parameter.code,
            evaluated_on=facts.evaluated_on,
        )


#: The rules the platform ships. Order is the order a supervisor reads them in.
RULES: tuple[ComplianceRule, ...] = (
    ApgRestorationRule(),
    NonComputableInterruptionRule(),
    EarthResistanceRule(),
)


def evaluate(session: Session, facts: Facts) -> list[Finding]:
    """Run every rule. Findings that do not apply are kept, not dropped.

    Keeping them is the point: a supervisor should be able to see that the platform looked at
    the earth resistance and found nothing recorded, which is different from not having
    looked.
    """
    return [rule.evaluate(session, facts) for rule in RULES]


def blocking_findings(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.blocking]


def _scalar(stored: dict[str, Any]) -> Any:
    """Pull the number out of a stored value, whatever shape it was stored in."""
    if set(stored) == {"v"}:
        return stored["v"]
    for key in ("value", "max", "limit", "hours", "seconds", "ohm"):
        if key in stored:
            return stored[key]
    raise ValueError(
        f"el valor del parámetro no tiene una forma escalar reconocible: {sorted(stored)}"
    )
