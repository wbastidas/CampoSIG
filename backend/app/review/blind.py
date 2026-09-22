"""The blind sample that measures whether the supervisor is reading or agreeing (RF-111a).

The risk RF-111a names is anchoring: a supervisor who reads «riesgo bajo, sin observaciones» before
looking at the capture will find the capture fine. Once that happens habitually, the review is the
agent's, the kappa is 1.00, and nobody can tell — a metric computed over reviews that saw the report
first measures agreement with a suggestion, not agreement between two judgements.

So on a configurable share of work orders the report is **withheld** until the supervisor has
recorded their own decision, and then shown. Three properties make the number worth having:

* **The server draws the sample, not the client.** `blind_sample` used to be a boolean the browser
  sent — a field that looks authoritative and that the thing being measured gets to fill in.
* **The draw is stored, not recomputed.** A rate read at query time would silently rewrite the
  denominator of a quality metric whenever somebody changed the rate.
* **It is drawn when the report is stored, before any human is involved**, so no request path
  decides whether it is being measured.

What is withheld is the agent's *opinion* only. The deterministic findings — the compliance
verdicts, the blockers, the photographs — are not the agent's and are never hidden: they are what an
approval depends on, and RF-204 requires approving with no report at all.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from random import Random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.report import RiskLevel
from app.review.models import BlindReview, Decision

#: Share of work orders whose report is withheld until the supervisor decides. The SRS's own
#: example. A rate of zero disables the measurement, which is a decision an operator may make and
#: the dashboard says so by showing no sample.
DEFAULT_BLIND_RATE = 0.10

#: Below this, the kappa is not reported as a verdict (RNF-060 asks for ≥ 0,6 over the sample, and a
#: kappa over nine cases is noise with a decimal point).
MIN_SAMPLE_FOR_KAPPA = 10

#: RNF-060's gate for deploying a change to an agent or a server model.
KAPPA_FLOOR = 0.6


def verdict_of_decision(decision: str) -> str:
    """The supervisor's judgement, reduced to the two categories the agreement is about.

    Not «which button» — «did this capture have a problem». A returned order and an annulled one are
    both "yes"; only an approval is "no". Comparing three buttons against three risk levels would be
    comparing scales that do not mean the same thing.
    """
    return "sin_problema" if decision == Decision.APPROVED else "con_problema"


def verdict_of_risk(risk: RiskLevel | str) -> str:
    """The agent's judgement on the same two categories."""
    value = risk.value if isinstance(risk, RiskLevel) else risk
    return "sin_problema" if value == RiskLevel.LOW.value else "con_problema"


def draw(rng: Random | None = None, rate: float = DEFAULT_BLIND_RATE) -> bool:
    """Whether this order falls in the blind sample."""
    if rate <= 0:
        return False
    if rate >= 1:
        return True
    return (rng or Random()).random() < rate


def assign(
    session: Session,
    work_order_id: uuid.UUID,
    business_unit_id: uuid.UUID,
    *,
    rng: Random | None = None,
    rate: float = DEFAULT_BLIND_RATE,
) -> BlindReview | None:
    """Draw this order for the blind sample, at the moment its report is stored.

    Idempotent per work order: a re-run of the pre-review does not redraw. Otherwise an order that
    failed once and succeeded later would have two chances at being measured, and a supervisor who
    reloaded at the wrong moment could see a report that was meant to be withheld.
    """
    existing = session.scalars(
        select(BlindReview).where(BlindReview.work_order_id == work_order_id)
    ).first()
    if existing is not None:
        return existing
    if not draw(rng, rate):
        return None
    row = BlindReview(
        business_unit_id=business_unit_id,
        work_order_id=work_order_id,
        rate=rate,
    )
    session.add(row)
    session.flush()
    return row


def pending_for(session: Session, work_order_id: uuid.UUID) -> BlindReview | None:
    """The draw that is still withholding this order's report, if any."""
    return session.scalars(
        select(BlindReview).where(
            BlindReview.work_order_id == work_order_id,
            BlindReview.revealed_at.is_(None),
        )
    ).first()


def reveal(
    session: Session,
    work_order_id: uuid.UUID,
    *,
    decision: str,
    risk: RiskLevel | str | None,
) -> BlindReview | None:
    """Record the agreement and release the report (RF-111a).

    Called from `decide`, in the decision's own transaction: the supervisor's verdict and the
    agent's are written together or not at all, and a pair with one half missing is a row that
    would quietly bias the kappa.

    `risk` of None means there was no report to compare against — the draw is closed with no pair,
    because an order the agents never rated cannot measure agreement with them.
    """
    row = pending_for(session, work_order_id)
    if row is None:
        return None
    row.revealed_at = datetime.now(UTC)
    row.supervisor_verdict = verdict_of_decision(decision)
    row.agent_verdict = verdict_of_risk(risk) if risk is not None else None
    session.flush()
    return row


@dataclass(frozen=True)
class Agreement:
    """The two-by-two table and what it says (RF-111a, RNF-060)."""

    #: Both said there was no problem.
    both_clear: int
    #: Both said there was one.
    both_flagged: int
    #: The supervisor found something the agent did not. The expensive cell: the agent missed it.
    supervisor_only: int
    #: The agent flagged what the supervisor approved. Cheap by comparison — a false alarm.
    agent_only: int
    #: Drawn but not yet decided.
    pending: int
    #: Decided, but with no report to compare against.
    unpaired: int

    @property
    def paired(self) -> int:
        return self.both_clear + self.both_flagged + self.supervisor_only + self.agent_only

    @property
    def observed(self) -> float | None:
        """Plain agreement. Reported beside the kappa because it is the number people expect."""
        return (self.both_clear + self.both_flagged) / self.paired if self.paired else None

    @property
    def kappa(self) -> float | None:
        """Cohen's kappa, or None when there is not enough sample to mean anything.

        Kappa and not plain agreement because the marginals are lopsided: most captures are fine, so
        two raters who both say "fine" almost always agree by arithmetic. Ninety-two per cent
        agreement on a population that is ninety per cent clean is barely better than a rater who
        never looks.
        """
        total = self.paired
        if total < MIN_SAMPLE_FOR_KAPPA:
            return None
        observed = (self.both_clear + self.both_flagged) / total
        supervisor_flagged = (self.both_flagged + self.supervisor_only) / total
        agent_flagged = (self.both_flagged + self.agent_only) / total
        expected = supervisor_flagged * agent_flagged + (1 - supervisor_flagged) * (
            1 - agent_flagged
        )
        if expected >= 1:
            # Both raters used one category for everything. Kappa is undefined there — 0/0 — and
            # reporting 1.00 would be reporting perfect agreement between two raters who never
            # distinguished anything.
            return None
        return (observed - expected) / (1 - expected)

    @property
    def meets_floor(self) -> bool | None:
        value = self.kappa
        return None if value is None else value >= KAPPA_FLOOR

    def as_dict(self) -> dict[str, object]:
        return {
            "both_clear": self.both_clear,
            "both_flagged": self.both_flagged,
            "supervisor_only": self.supervisor_only,
            "agent_only": self.agent_only,
            "pending": self.pending,
            "unpaired": self.unpaired,
            "paired": self.paired,
            "observed_agreement": self.observed,
            "kappa": self.kappa,
            "kappa_floor": KAPPA_FLOOR,
            "meets_floor": self.meets_floor,
            "min_sample": MIN_SAMPLE_FOR_KAPPA,
        }


def agreement(session: Session, business_unit_id: uuid.UUID) -> Agreement:
    """The unit's agreement with the agent over its blind sample."""
    rows = session.scalars(
        select(BlindReview).where(BlindReview.business_unit_id == business_unit_id)
    ).all()
    counts = {"both_clear": 0, "both_flagged": 0, "supervisor_only": 0, "agent_only": 0}
    pending = 0
    unpaired = 0
    for row in rows:
        if row.revealed_at is None:
            pending += 1
            continue
        if row.agent_verdict is None or row.supervisor_verdict is None:
            unpaired += 1
            continue
        supervisor_flagged = row.supervisor_verdict == "con_problema"
        agent_flagged = row.agent_verdict == "con_problema"
        if supervisor_flagged and agent_flagged:
            counts["both_flagged"] += 1
        elif supervisor_flagged:
            counts["supervisor_only"] += 1
        elif agent_flagged:
            counts["agent_only"] += 1
        else:
            counts["both_clear"] += 1
    return Agreement(pending=pending, unpaired=unpaired, **counts)
