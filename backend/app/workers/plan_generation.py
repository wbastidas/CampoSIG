"""The nightly pass that fires preventive plans (RF-012).

«Un plan mensual genera N OT en la fecha programada (job programado)» — this is the job. It takes a
session and returns a report, like every other pass in this package, so the same code runs from
Celery, from the CLI and from a test.

Two properties:

* **A plan that fails does not stop the others.** Each plan's run is committed on its own. A form
  that was retired under a plan's feet should cost that plan its period, not the whole unit's
  preventive maintenance.
* **Running twice in one night is harmless.** The period label in `plan_issue` is the guard, and it
  is a database index, so a retry, a second beat or an operator pressing «generar» while the job
  runs all end with the same orders.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.org.models import BusinessUnit
from app.plans import service as plans

logger = logging.getLogger(__name__)


@dataclass
class GenerationPass:
    """What one pass over every business unit did."""

    on: date
    issued: int = 0
    units: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: Units whose pass raised, with the error. Named rather than counted: an operator needs to know
    #: which area's preventive work did not get issued tonight.
    failed: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "on": self.on.isoformat(),
            "issued": self.issued,
            "units": self.units,
            "failed": self.failed,
        }


def run_once(session: Session, *, on: date | None = None) -> GenerationPass:
    """Fire every due plan of every business unit."""
    today = on or datetime.now(UTC).date()
    result = GenerationPass(on=today)
    for unit in session.execute(select(BusinessUnit).order_by(BusinessUnit.code)).scalars():
        try:
            report = plans.run_due(session, unit, on=today)
            session.commit()
        # Deliberately broad: one unit's failure must not stop the rest of the country's
        # preventive maintenance, and what failed is named in the report.
        except Exception as exc:
            session.rollback()
            logger.exception("falló la generación de planes de %s", unit.code)
            result.failed[unit.code] = f"{type(exc).__name__}: {exc}"
            continue
        result.units[unit.code] = report.as_dict()
        result.issued += report.issued
    return result
