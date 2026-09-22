"""The pre-review report, and the guardrail that decides what is allowed into it (RF-175).

The schema is Annex D of the SRS. What matters more than the shape is the rule from design note 3
of section 7.7: **one observation = evidence + source.** An observation with nothing to point at is
an opinion, and an opinion in a document a supervisor uses to approve field work is worse than
silence — it spends the reader's attention and cannot be checked.

So the guardrail drops them, and says how many it dropped. Dropping rather than refusing
construction is deliberate: an LLM node that returns one bad observation should cost that
observation, not the whole report. And counting the discards keeps the drop from being silent,
which is what would let a node quietly produce nothing useful for a month.

Regulatory observations are held to a second bar (RF-172): they must cite a document, version and
section. "Ninguna observación sin fuente se muestra como normativa" — so one without a source is not
rendered harmless by relabelling it, it is discarded like the rest.

Nothing here approves, closes or integrates anything (rule 14). The report is the agents' only
output, and a structural test proves this package has no path to a work order's state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field


class Category(StrEnum):
    """Annex D's categories."""

    COHERENCE = "coherence"
    REGULATORY = "regulatory"
    CATALOG = "catalog"
    EVIDENCE = "evidence"
    ANOMALY = "anomaly"
    SAFETY = "safety"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


#: How a risk level is said to a person. The enum values are English because identifiers are
#: (rule 11), and interpolating one into a Spanish sentence produces «riesgo medium», which is what
#: a supervisor would actually have read on the screen. Kept beside the enum so that a third
#: consumer of this text does not invent a fourth spelling.
RISK_IN_SPANISH: dict[RiskLevel, str] = {
    RiskLevel.LOW: "bajo",
    RiskLevel.MEDIUM: "medio",
    RiskLevel.HIGH: "alto",
}


class RunStatus(StrEnum):
    #: Every node ran.
    COMPLETE = "complete"
    #: Some node was skipped — no hardware for it, the gateway was down, or the budget ran out.
    #: The report is still delivered, and says so (RF-204, SRS 7.7 note 5).
    PARTIAL = "partial"
    FAILED = "failed"


class EvidenceType(StrEnum):
    TRANSCRIPT = "transcript"
    FIELD = "field"
    PHOTO = "photo"
    #: A deterministic rule's own output — a computed distance, a duration, a hash comparison.
    COMPUTED = "computed"


class EvidenceRef(BaseModel):
    """What an observation points at. One of these is what makes it checkable."""

    type: EvidenceType
    #: Character span of the transcript, for a dictated claim.
    span: tuple[int, int] | None = None
    #: JSON path into the answers, for a field.
    json_path: str | None = None
    #: The evidence row, for a photograph.
    evidence_id: str | None = None
    #: For COMPUTED: the rule and the numbers it compared, so a reader can redo the arithmetic.
    detail: str | None = None

    @property
    def is_locatable(self) -> bool:
        """Whether this reference actually points somewhere.

        An `EvidenceRef` with a type and nothing else is the shape of evidence without the
        substance, and it is exactly what a model produces when it is guessing.
        """
        return any((self.span, self.json_path, self.evidence_id, self.detail))


class Source(BaseModel):
    """The citation a regulatory observation must carry (RF-172)."""

    document: str
    version: str | None = None
    section: str | None = None
    #: False when nobody has checked the cited limit against the official text (ADR-007). A report
    #: that presented an unverified figure as a citation would be handing somebody a verdict with
    #: an official-looking reference under it.
    verified: bool = True

    def describe(self) -> str:
        parts = [self.document]
        if self.version:
            parts.append(f"v{self.version}")
        if self.section:
            parts.append(self.section)
        return " · ".join(parts)


class Observation(BaseModel):
    """One finding. Neutral in tone: it marks for verification, it does not accuse (RF-174)."""

    id: str
    category: Category
    severity: Severity
    message: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    source: Source | None = None
    suggested_action: str | None = None
    confidence: float | None = None
    #: Which node produced it, for traceability (RF-180).
    node: str | None = None

    @property
    def is_supported(self) -> bool:
        """Whether the guardrail lets this through.

        Two bars: something to point at, and — for a regulatory finding — a citation (RF-172).
        """
        if not any(ref.is_locatable for ref in self.evidence):
            return False
        return not (self.category is Category.REGULATORY and self.source is None)


@dataclass(frozen=True)
class Discard:
    """An observation the guardrail refused, and why. Counted so the drop is not silent."""

    observation_id: str
    node: str | None
    reason: str


def guardrail(observations: list[Observation]) -> tuple[list[Observation], list[Discard]]:
    """Keep what can be checked; report what could not.

    Returns both halves rather than logging the discards: a node that starts producing unsupported
    observations is a regression, and a count in the report is what makes it visible on the next
    run instead of in six months.
    """
    kept: list[Observation] = []
    dropped: list[Discard] = []
    for observation in observations:
        if not any(ref.is_locatable for ref in observation.evidence):
            dropped.append(
                Discard(
                    observation.id,
                    observation.node,
                    "sin evidencia que señalar: una observación sin evidencia es una opinión",
                )
            )
            continue
        if observation.category is Category.REGULATORY and observation.source is None:
            dropped.append(
                Discard(
                    observation.id,
                    observation.node,
                    "normativa sin cita: ninguna observación sin fuente se presenta como normativa",
                )
            )
            continue
        kept.append(observation)
    return kept, dropped


class Budget(BaseModel):
    """What the run cost. A run that exceeds its allowance is marked partial, not killed."""

    llm_calls: int = 0
    tokens: int = 0
    duration_s: float = 0.0


class AgentReport(BaseModel):
    """Annex D, typed. The agents' only output (rule 14)."""

    work_order_id: str
    graph_version: str
    hardware_profile: str
    risk_level: RiskLevel
    status: RunStatus
    summary: str
    observations: list[Observation] = Field(default_factory=list)
    #: Alias → model@version, so a report can be traced to what produced it (RF-180).
    models: dict[str, str] = Field(default_factory=dict)
    budget: Budget = Field(default_factory=Budget)
    #: Nodes that did not run, with the reason. This is RF-204 arriving on the supervisor's screen:
    #: a report with a section quietly missing looks complete, which is worse than one that says
    #: what it could not do.
    skipped: list[str] = Field(default_factory=list)
    #: How many observations the guardrail refused. Zero is the expected value.
    discarded: int = 0

    @property
    def is_partial(self) -> bool:
        return self.status is RunStatus.PARTIAL

    def by_category(self, category: Category) -> list[Observation]:
        return [item for item in self.observations if item.category is category]
