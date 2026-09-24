"""Assisted batch approval (RF-176).

The requirement in one line: a supervisor may approve low-risk work orders in bulk, **always with
an explicit human action** and **always with a mandatory verification sample**. Its acceptance
criterion is a security test — «no existe ningún camino de aprobación automática sin clic humano» —
so the shape of this module is dictated by what must remain impossible:

* **Every approval goes through the same `decide`.** Not a faster path that skips the blockers: a
  second, weaker approval route is how a gate stops meaning anything, and the whole point of I6's
  blockers is that they hold on every approval.
* **The sample is drawn before anything is approved, and rounded up.** Five per cent of three is
  0.15, and a sample size that rounds to zero is a sampling policy a supervisor learns to defeat by
  approving in threes. So the floor is one, always: a batch with no sample is not a batch.
* **Low risk means a report said so.** No report is not low risk. An order nobody pre-reviewed is
  exactly the one a bulk approval should not swallow.

Nothing here runs on a schedule, and nothing calls it but a request carrying a supervisor's token.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from random import Random

from sqlalchemy.orm import Session

from app.agents.report import RISK_IN_SPANISH
from app.org.models import BusinessUnit
from app.prereview.service import latest_report
from app.review.models import Decision
from app.review.service import ApprovalBlockedError, NotReviewableError, decide
from app.workorders.models import WorkOrder

#: Share of a batch held back for one-by-one verification. The parameter RF-176 names, with the
#: example it gives.
SAMPLE_RATE = 0.05

#: However small the batch, at least this many are sampled. One, because zero is a policy with a
#: hole in it and everybody finds the hole eventually.
MIN_SAMPLE = 1

#: The risk level a batch may contain. Only one, deliberately: «OT de riesgo bajo» is the
#: requirement's own wording, and widening it here would be widening it without anybody deciding to.
BATCHABLE_RISK = "low"


@dataclass
class Refusal:
    work_order_id: str
    code: str | None
    reason: str


@dataclass
class BatchOutcome:
    """What a batch approval did and did not do."""

    approved: list[str] = field(default_factory=list)
    #: Held back for individual review. Not a failure: it is the point.
    sampled: list[str] = field(default_factory=list)
    refused: list[Refusal] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "approved": self.approved,
            "sampled": self.sampled,
            "refused": [
                {"work_order_id": item.work_order_id, "code": item.code, "reason": item.reason}
                for item in self.refused
            ],
        }


def sample_size(batch: int, rate: float = SAMPLE_RATE) -> int:
    """How many of a batch are held back.

    Rounded **up**, and never below :data:`MIN_SAMPLE` for a non-empty batch. The alternative —
    rounding to nearest — means a batch of three samples nobody, which is a rule with a hole that
    somebody will find.
    """
    if batch <= 0:
        return 0
    return max(MIN_SAMPLE, math.ceil(batch * rate))


def eligible(session: Session, order: WorkOrder) -> str | None:
    """None when the order may be batch-approved; otherwise why not."""
    report = latest_report(session, order.id)
    if report is None:
        # No report is not low risk. An order nobody pre-reviewed is exactly the one a bulk
        # approval should not swallow.
        return "sin informe de pre-revisión: no se puede aprobar en lote lo que nadie revisó"
    if report.risk_level.value != BATCHABLE_RISK:
        said = RISK_IN_SPANISH[report.risk_level]
        return f"riesgo {said}: solo se aprueban en lote las de riesgo bajo"
    return None


def approve_batch(
    session: Session,
    unit: BusinessUnit,
    orders: list[WorkOrder],
    *,
    reviewer_sub: str,
    note: str | None = None,
    rate: float = SAMPLE_RATE,
    rng: Random | None = None,
) -> BatchOutcome:
    """Approve the eligible low-risk orders, holding a sample back.

    :param reviewer_sub: the supervisor, from their token. There is no parameter for "no reviewer":
        an approval without a person is the thing this module exists to make unrepresentable.
    :param rng: injected so a test can assert on which orders were sampled. Production uses the
        default, and the sample is drawn from the eligible set only — sampling an order that was
        going to be refused anyway would waste the sample.
    """
    outcome = BatchOutcome()
    candidates: list[WorkOrder] = []

    for order in orders:
        reason = eligible(session, order)
        if reason is not None:
            outcome.refused.append(Refusal(str(order.id), order.code, reason))
            continue
        candidates.append(order)

    if not candidates:
        return outcome

    chooser = rng or Random()
    held = set(
        chooser.sample(
            [str(order.id) for order in candidates],
            k=min(sample_size(len(candidates), rate), len(candidates)),
        )
    )

    for order in candidates:
        if str(order.id) in held:
            outcome.sampled.append(str(order.id))
            continue
        try:
            decide(
                session,
                unit,
                order,
                decision=Decision.APPROVED,
                reviewer_sub=reviewer_sub,
                note=note or "aprobada en lote de riesgo bajo (RF-176)",
            )
        except ApprovalBlockedError as blocked:
            # The blockers of I6 hold identically here. A batch that could approve past them would
            # be a second, weaker approval path.
            outcome.refused.append(Refusal(str(order.id), order.code, "; ".join(blocked.reasons)))
        except NotReviewableError as wrong_state:
            outcome.refused.append(Refusal(str(order.id), order.code, str(wrong_state)))
        else:
            outcome.approved.append(str(order.id))

    return outcome


def orders_for_batch(
    session: Session, unit: BusinessUnit, order_ids: list[uuid.UUID]
) -> tuple[list[WorkOrder], list[Refusal]]:
    """Load the named orders, refusing anything that is not this unit's.

    A cross-unit id is refused rather than ignored: silently dropping it would let a caller believe
    a batch covered an order it never touched (ADR-009).
    """
    found: list[WorkOrder] = []
    refused: list[Refusal] = []
    for order_id in order_ids:
        order = session.get(WorkOrder, order_id)
        if order is None or order.business_unit_id != unit.id:
            refused.append(Refusal(str(order_id), None, "la OT no existe en esta unidad"))
            continue
        found.append(order)
    return found, refused
