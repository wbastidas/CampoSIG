"""The consolidator: one report, with a risk level (RF-175).

Annex D says the risk level is «el máximo ponderado de las severidades (regla configurable)». Two
things follow, and both matter more than the arithmetic.

**A single high finding makes the whole work order high risk.** Averaging would let nine harmless
observations dilute one that says the earth resistance is out of limit, and a supervisor scanning a
queue by risk would never reach it.

**Volume raises risk on its own.** Enough medium findings on one capture is a capture worth
opening, even when none is individually serious — the pattern a person notices and a maximum does
not. The count that does it is declared here, not buried in a comparison.

And the summary is deterministic prose (SRS 7.7 rule 1: rules first, the LLM after). The optional
LLM polish of I12 replaces the wording, never the risk level: a model that could change a risk level
would be a model that decides what a supervisor looks at.
"""

from __future__ import annotations

from app.agents.report import (
    AgentReport,
    Budget,
    Category,
    Observation,
    RiskLevel,
    RunStatus,
    Severity,
)

#: How many mediums add up to a high. Declared rather than inlined because it is the one number in
#: this module a supervisor might reasonably want changed after a month of use.
MEDIUMS_THAT_MAKE_A_HIGH = 4

#: Order for reading: the worst first, and within a severity the categories a person can act on.
CATEGORY_ORDER = (
    Category.SAFETY,
    Category.REGULATORY,
    Category.EVIDENCE,
    Category.COHERENCE,
    Category.CATALOG,
    Category.ANOMALY,
)

_SEVERITY_RANK = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}


def sort_observations(observations: list[Observation]) -> list[Observation]:
    """Worst first, then by category, then by id so two runs read identically."""
    return sorted(
        observations,
        key=lambda item: (
            _SEVERITY_RANK[item.severity],
            CATEGORY_ORDER.index(item.category) if item.category in CATEGORY_ORDER else 99,
            item.id,
        ),
    )


def risk_level(observations: list[Observation]) -> RiskLevel:
    """The weighted maximum of the severities (Annex D)."""
    if any(item.severity is Severity.HIGH for item in observations):
        return RiskLevel.HIGH
    mediums = sum(1 for item in observations if item.severity is Severity.MEDIUM)
    if mediums >= MEDIUMS_THAT_MAKE_A_HIGH:
        return RiskLevel.HIGH
    if mediums:
        return RiskLevel.MEDIUM
    if observations:
        return RiskLevel.LOW
    return RiskLevel.LOW


def summarise(observations: list[Observation], skipped: list[str]) -> str:
    """Deterministic prose. The same capture produces the same sentence.

    Which is what makes RF-180 checkable — «la reproducción de una ejecución con la misma versión da
    el mismo informe» — and what lets a supervisor compare two reports without wondering whether the
    model was in a different mood.
    """
    if not observations:
        base = "Sin observaciones: las reglas deterministas no encontraron nada que revisar."
    else:
        counts: dict[Severity, int] = {}
        for item in observations:
            counts[item.severity] = counts.get(item.severity, 0) + 1
        parts = [
            f"{counts[severity]} {label}"
            for severity, label in (
                (Severity.HIGH, "de severidad alta"),
                (Severity.MEDIUM, "de severidad media"),
                (Severity.LOW, "de severidad baja"),
            )
            if counts.get(severity)
        ]
        leading = sort_observations(observations)[0]
        base = (
            f"{len(observations)} observaciones ({', '.join(parts)}). "
            f"La principal: {leading.message}"
        )

    if skipped:
        # Said in the summary and not only in a field: the first line is what a supervisor reads
        # before deciding how much of the report to trust.
        base += f" No se ejecutó: {', '.join(skipped)}."
    return base


def consolidate(
    work_order_id: str,
    graph_version: str,
    hardware_profile: str,
    observations: list[Observation],
    *,
    skipped: list[str] | None = None,
    discarded: int = 0,
    models: dict[str, str] | None = None,
    budget: Budget | None = None,
) -> AgentReport:
    """Assemble the report. Adds no findings of its own."""
    ordered = sort_observations(observations)
    missing = skipped or []
    return AgentReport(
        work_order_id=work_order_id,
        graph_version=graph_version,
        hardware_profile=hardware_profile,
        risk_level=risk_level(ordered),
        # Partial whenever a node did not run, whatever the reason. A report that ran four nodes out
        # of five and called itself complete is the failure mode RF-204 exists to prevent.
        status=RunStatus.PARTIAL if missing else RunStatus.COMPLETE,
        summary=summarise(ordered, missing),
        observations=ordered,
        models=models or {},
        budget=budget or Budget(),
        skipped=missing,
        discarded=discarded,
    )
