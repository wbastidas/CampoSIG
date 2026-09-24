"""The pre-review graph (RF-170), deterministic half.

Plain function composition, not LangGraph. The framework earns its place when there are checkpoints
to resume and LLM nodes to retry; today every node is a pure function over
:class:`PreReviewFacts`, and wrapping five of those in a state machine would add a dependency, a
serialisation format and a failure mode in exchange for nothing. LangGraph enters with the LLM
nodes of I12, and the deterministic nodes below are what it will orchestrate.

The order is the one SRS 7.7 draws: coherence → catalogues and regulation → visual evidence →
anomalies → consolidation. The visual-evidence node needs a VLM, so on most deployments it does not
run; what this module guarantees is that **not running is recorded, not skipped silently**. A report
that ran four nodes out of five and called itself complete is exactly the failure RF-204 exists to
prevent, and it is worse than no report because it looks finished.

Rule 14 holds structurally: `run_pre_review` takes facts and returns a report. It receives no
session, imports nothing that writes a work order's state, and has no branch that approves, closes
or integrates anything. A test walks this package's imports to keep it that way.
"""

from __future__ import annotations

import time
from datetime import datetime

from app.agents import anomalies, coherence
from app.agents.consolidator import consolidate
from app.agents.facts import PreReviewFacts
from app.agents.report import AgentReport, Budget, Observation, guardrail
from app.inference.admission import Placement, admit
from app.inference.registry import InferenceRegistry, load_registry

#: Bumped when a node's rules change, so two reports can be compared knowing whether they came from
#: the same graph (RF-180). Not the application's version: the graph changes on its own rhythm.
GRAPH_VERSION = "prereview-0.1.0"

#: Nodes that need a model, with the alias they need. Their absence is the normal case on a CPU-only
#: deployment, and the report says so rather than omitting a section.
MODEL_NODES: dict[str, str] = {
    "visual_evidence": "vlm-audit",
    "narrative": "llm-judge",
}

#: How each model node is named in the report's `skipped` list, in words a supervisor reads.
NODE_LABELS = {
    "visual_evidence": "auditoría de evidencia visual",
    "narrative": "redacción de observaciones de texto libre",
}


def run_pre_review(
    facts: PreReviewFacts,
    hardware_profile: str,
    *,
    gateway_reachable: bool = True,
    now: datetime | None = None,
    registry: InferenceRegistry | None = None,
) -> AgentReport:
    """Run the deterministic nodes and report what the model nodes could not do.

    :param gateway_reachable: whether the model gateway answers. False is a first-class case, not an
        error: the report is still produced and a supervisor still decides (RF-204).
    """
    started = time.monotonic()
    known = registry or load_registry()

    observations: list[Observation] = []
    observations.extend(coherence.run(facts, now))
    observations.extend(anomalies.run(facts))

    skipped: list[str] = []
    models: dict[str, str] = {}
    for node, alias_name in MODEL_NODES.items():
        decision = admit(
            alias_name, hardware_profile, gateway_reachable=gateway_reachable, registry=known
        )
        if decision.placement is Placement.INTERACTIVE:
            # The node would run here. It is not implemented yet (I12), so it is still recorded as
            # not run — claiming a section exists because the hardware could host it would be the
            # same lie from the other direction.
            skipped.append(f"{NODE_LABELS[node]} (pendiente de I12)")
            continue
        alias = known.alias(alias_name)
        models[alias_name] = f"{alias.model}@{alias.runtime}"
        skipped.append(f"{NODE_LABELS[node]}: {decision.reason}")

    kept, dropped = guardrail(observations)
    return consolidate(
        work_order_id=facts.work_order_id,
        graph_version=GRAPH_VERSION,
        hardware_profile=hardware_profile,
        observations=kept,
        skipped=skipped,
        discarded=len(dropped),
        models=models,
        budget=Budget(duration_s=round(time.monotonic() - started, 4)),
    )
