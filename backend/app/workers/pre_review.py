"""The process that runs the pre-review (RF-170, RF-202, RF-204).

RF-170's acceptance criterion is what this module is for: **every synced work order ends with a
run in a terminal state, failures retry, and nothing blocks human review.** So the pass picks up
orders with no finished run, runs one at a time, and commits each — a worker killed mid-pass leaves
the runs it finished on record and the rest exactly as they were.

Two rules it inherits rather than invents:

* **Never on a request path.** A supervisor opening a work order must not wait for a graph; the
  report is there or it is not, and the screen says which (RF-204).
* **The window belongs to the scheduler.** On a CPU-only deployment the model nodes are night work,
  and the deterministic nodes are cheap enough to run whenever. So the pass runs on its schedule and
  the placement of each node is M19's decision, not this module's.

One commit per run, for the same reason the integration worker commits per event: a batch-wide
transaction would re-run everything after a crash, and a graph run is not free.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.org.models import BusinessUnit
from app.org.service import active_units
from app.prereview.models import RunState
from app.prereview.service import execute, orders_without_a_terminal_run
from app.settings import get_settings

logger = logging.getLogger(__name__)

#: How many orders one pass takes per unit. Bounded so a backlog drains in visible chunks rather
#: than in one pass that either finishes or dies holding everything.
BATCH_SIZE = 25


@dataclass
class PassReport:
    """What one pass did, for the log and for a test to assert on."""

    considered: int = 0
    completed: int = 0
    partial: int = 0
    failed: int = 0
    units: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "considered": self.considered,
            "completed": self.completed,
            "partial": self.partial,
            "failed": self.failed,
            "units": self.units,
        }


def run_once(session: Session, limit: int = BATCH_SIZE) -> PassReport:
    """One pass over every active unit's pending pre-reviews."""
    report = PassReport()
    settings = get_settings()
    # Whether the gateway is configured is a deployment fact, and the admission policy turns it
    # into a placement per alias. A probe here would cost a timeout per pass to learn what a
    # setting already says.
    reachable = bool(settings.model_gateway_url)

    for unit in active_units(session):
        pending = orders_without_a_terminal_run(session, unit, limit=limit)
        if not pending:
            continue
        report.units.append(unit.code)
        for order in pending:
            report.considered += 1
            run = execute(session, unit, order, gateway_reachable=reachable)
            if run.state == RunState.DONE:
                report.completed += 1
            elif run.state == RunState.PARTIAL:
                report.partial += 1
            else:
                report.failed += 1
                logger.warning(
                    "pre-revisión fallida para la OT %s: %s", order.code or order.id, run.error
                )
            # Per run: a worker that dies here keeps what it finished.
            session.commit()
    return report


def run_for_unit(session: Session, unit: BusinessUnit, limit: int = BATCH_SIZE) -> PassReport:
    """One unit's pass, for a management command or a test that wants one unit."""
    report = PassReport()
    reachable = bool(get_settings().model_gateway_url)
    for order in orders_without_a_terminal_run(session, unit, limit=limit):
        report.considered += 1
        run = execute(session, unit, order, gateway_reachable=reachable)
        if run.state == RunState.DONE:
            report.completed += 1
        elif run.state == RunState.PARTIAL:
            report.partial += 1
        else:
            report.failed += 1
        session.commit()
    if report.considered:
        report.units.append(unit.code)
    return report
