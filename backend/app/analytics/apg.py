"""The street-lighting board (RF-131), against the deadline the regulator sets.

Three numbers the APG area answers for: how long a failed luminaire takes to come back, how often
luminaires fail, and what technology the fleet is made of. The first is a regulatory obligation and
the other two are what tell the area where to spend next year's money.

The rule that shapes this module is ADR-007 and rule 16 of the project: **the deadline is never in
the code.** It lives in `regulatory_parameter` with its period of force, its norm reference and a
verification flag, and this board asks the same rule the approval gate asks. Two consequences that
are easy to get wrong and are the point of the module:

* **The verdict is re-derived, never stored.** Re-running this over a March period reproduces
  March's deadline, because the parameter carries its dates. A snapshot of the percentage would be
  a second copy of the truth, free to drift from the rule that produced it.
* **An unverified limit is reported as provisional.** Nobody has checked it against the official
  text yet, and a compliance percentage computed against a number somebody typed from memory —
  presented as if it cited the regulation — is worse than no percentage: it invites the reader to
  stop checking.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.operations import MIN_FOR_A_DURATION, percentile
from app.regulatory import rules as compliance
from app.responses.models import FormResponse
from app.review.service import compliance_findings
from app.workorders.models import WorkOrder

#: The form the APG area fills for a failed luminaire. Named once: a board that hunted for work
#: types by string in three places would disagree with itself the day a new form arrives.
FAILURE_FORM = "F-AP-01"

#: The rule whose verdict this board aggregates. The same one the approval gate runs.
RESTORATION_RULE = "plazo_reposicion_apg"

#: Answer keys this board reads. Canonical (ADR-004): no real GIS field name appears here.
KEY_TECHNOLOGY = "technology"
KEY_ASSET_CODE = "code"
KEY_CAUSE = "cause_found"
KEY_FAILURE = "reported_failure"


@dataclass(frozen=True)
class Restoration:
    """One attention, with what the rule said about its elapsed time."""

    work_order_id: str
    order_code: str | None
    asset_code: str | None
    hours: float | None
    limit_hours: float | None
    within_limit: bool | None
    #: False when the limit has not been checked against the official text (ADR-007).
    limit_verified: bool
    norm_ref: str | None
    article_ref: str | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": self.work_order_id,
            "order_code": self.order_code,
            "asset_code": self.asset_code,
            "hours": self.hours,
            "limit_hours": self.limit_hours,
            "within_limit": self.within_limit,
            "limit_verified": self.limit_verified,
            "norm_ref": self.norm_ref,
            "article_ref": self.article_ref,
            "message": self.message,
        }


@dataclass
class ApgBoard:
    computed_at: datetime
    since: datetime
    until: datetime
    #: Attentions the rule could judge, and how they came out.
    within: int = 0
    breached: int = 0
    #: Captured but not judgeable: no claim time, no restoration time, or no parameter loaded.
    not_measurable: int = 0
    #: Of the judged ones, how many were judged against a limit nobody has verified.
    against_unverified_limit: int = 0
    hours: list[float] = field(default_factory=list)
    by_technology: dict[str, int] = field(default_factory=dict)
    without_technology: int = 0
    by_cause: dict[str, int] = field(default_factory=dict)
    #: Luminaires that failed more than once in the period, worst first. Recurrence is the signal
    #: that the replacement did not fix it.
    repeat_offenders: list[tuple[str, int]] = field(default_factory=list)
    distinct_luminaires: int = 0
    attentions: int = 0
    breaches: list[Restoration] = field(default_factory=list)

    @property
    def judged(self) -> int:
        return self.within + self.breached

    @property
    def compliance(self) -> float | None:
        """Share inside the deadline, or None when too few to report.

        The threshold is the same as every other rate on these boards: a percentage over three
        attentions is a percentage somebody will quote in a meeting.
        """
        return self.within / self.judged if self.judged >= MIN_FOR_A_DURATION else None

    @property
    def failures_per_luminaire(self) -> float | None:
        """The failure rate RF-131 asks for, per luminaire that failed at all.

        Per luminaire with a failure and not per luminaire installed: the platform does not hold the
        fleet's inventory — that lives in the GIS — and dividing by a total it does not know would
        be inventing the denominator. Said in the payload so nobody reads it as the fleet's rate.
        """
        if self.distinct_luminaires == 0:
            return None
        return self.attentions / self.distinct_luminaires

    def as_dict(self) -> dict[str, Any]:
        return {
            "computed_at": self.computed_at.isoformat(),
            "since": self.since.isoformat(),
            "until": self.until.isoformat(),
            "attentions": self.attentions,
            "restoration": {
                "within": self.within,
                "breached": self.breached,
                "judged": self.judged,
                "not_measurable": self.not_measurable,
                "against_unverified_limit": self.against_unverified_limit,
                "compliance": self.compliance,
                "median_hours": percentile(self.hours, 0.5)
                if len(self.hours) >= MIN_FOR_A_DURATION
                else None,
                "p90_hours": percentile(self.hours, 0.9)
                if len(self.hours) >= MIN_FOR_A_DURATION
                else None,
                "worst_hours": max(self.hours) if self.hours else None,
                "min_sample": MIN_FOR_A_DURATION,
            },
            "fleet": {
                "by_technology": self.by_technology,
                "without_technology": self.without_technology,
            },
            "failures": {
                "by_cause": self.by_cause,
                "distinct_luminaires": self.distinct_luminaires,
                "failures_per_luminaire": self.failures_per_luminaire,
                "denominator": (
                    "luminarias con al menos una falla en el periodo, no el total instalado: "
                    "el inventario vive en el SIG y dividir por un total que la plataforma no "
                    "conoce sería inventar el denominador"
                ),
                "repeat_offenders": [
                    {"asset_code": code, "failures": times} for code, times in self.repeat_offenders
                ],
            },
            "breaches": [item.as_dict() for item in self.breaches],
        }


def _attentions(
    session: Session, unit_id: uuid.UUID, since: datetime, until: datetime
) -> list[tuple[WorkOrder, FormResponse]]:
    """The APG attentions of the period, with their captures.

    Dated by submission: a luminaire fixed on Friday and synchronised on Monday belongs to Friday's
    numbers, which is the week the regulator's clock was running.
    """
    rows = session.execute(
        select(WorkOrder, FormResponse)
        .join(FormResponse, FormResponse.work_order_id == WorkOrder.id)
        .where(
            WorkOrder.business_unit_id == unit_id,
            FormResponse.form_code == FAILURE_FORM,
            FormResponse.submitted_at.is_not(None),
            FormResponse.submitted_at >= since,
            FormResponse.submitted_at <= until,
        )
        .order_by(FormResponse.submitted_at)
    )
    return [(order, response) for order, response in rows]


def build(
    session: Session,
    unit_id: uuid.UUID,
    *,
    since: datetime,
    until: datetime,
    now: datetime | None = None,
) -> ApgBoard:
    """The whole board, judged by the same rule the approval gate runs."""
    board = ApgBoard(computed_at=now or datetime.now(tz=since.tzinfo), since=since, until=until)
    per_asset: Counter[str] = Counter()
    technologies: Counter[str] = Counter()
    causes: Counter[str] = Counter()

    for order, response in _attentions(session, unit_id, since, until):
        board.attentions += 1
        answers = response.answers or {}

        technology = answers.get(KEY_TECHNOLOGY)
        if isinstance(technology, str) and technology.strip():
            technologies[technology] += 1
        else:
            # Counted rather than dropped: a fleet composition computed over the captures that
            # happened to record a technology reports the shape of the well-filled forms.
            board.without_technology += 1

        cause = answers.get(KEY_CAUSE)
        if isinstance(cause, str) and cause.strip():
            causes[cause] += 1

        asset = answers.get(KEY_ASSET_CODE) or order.asset_code
        if isinstance(asset, str) and asset.strip():
            per_asset[asset] += 1

        verdict = _restoration_verdict(session, order, response)
        if verdict.within_limit is None:
            board.not_measurable += 1
            continue
        if verdict.hours is not None:
            board.hours.append(verdict.hours)
        if not verdict.limit_verified:
            board.against_unverified_limit += 1
        if verdict.within_limit:
            board.within += 1
        else:
            board.breached += 1
            board.breaches.append(verdict)

    board.by_technology = dict(technologies.most_common())
    board.by_cause = dict(causes.most_common())
    board.distinct_luminaires = len(per_asset)
    board.repeat_offenders = [(code, times) for code, times in per_asset.most_common() if times > 1]
    return board


def _restoration_verdict(session: Session, order: WorkOrder, response: FormResponse) -> Restoration:
    """What the deterministic rule says about one attention.

    Asked of `compliance_findings`, which is what the approval gate asks. A second implementation
    here could disagree with the decision it is reporting on, and then the board and the gate would
    be telling the area two different things about the same work order.
    """
    findings = [
        finding
        for finding in compliance_findings(session, order, response)
        if finding.rule == RESTORATION_RULE
    ]
    finding = findings[0] if findings else None
    if finding is None or finding.outcome not in (
        compliance.Outcome.COMPLIES,
        compliance.Outcome.BREACHES,
    ):
        return Restoration(
            work_order_id=str(order.id),
            order_code=order.code,
            asset_code=(response.answers or {}).get(KEY_ASSET_CODE) or order.asset_code,
            hours=None,
            limit_hours=None,
            within_limit=None,
            limit_verified=False,
            norm_ref=finding.norm_ref if finding else None,
            article_ref=finding.article_ref if finding else None,
            message=finding.message if finding else "la regla de plazo no produjo veredicto",
        )
    return Restoration(
        work_order_id=str(order.id),
        order_code=order.code,
        asset_code=(response.answers or {}).get(KEY_ASSET_CODE) or order.asset_code,
        hours=float(finding.measured) if finding.measured is not None else None,
        limit_hours=float(finding.limit) if isinstance(finding.limit, int | float) else None,
        within_limit=finding.outcome is compliance.Outcome.COMPLIES,
        limit_verified=finding.limit_verified,
        norm_ref=finding.norm_ref,
        article_ref=finding.article_ref,
        message=finding.message,
    )


# --- the export --------------------------------------------------------------------------

#: Columns of the CSV RF-131 asks to be exportable. Named here so the header and the rows cannot
#: drift apart.
CSV_COLUMNS = (
    "ot",
    "luminaria",
    "horas_reposicion",
    "plazo_h",
    "cumple",
    "limite_verificado",
    "norma",
    "articulo",
    "observacion",
)


def as_csv(board: ApgBoard) -> str:
    """The breach list as a CSV that opens correctly in a Spanish-locale Excel.

    Semicolons and comma decimals, with a byte-order mark. Not a preference: an Excel configured for
    Ecuador reads a comma-separated file as one column and «1.5» as fifteen, so the "exportable a
    Excel" of the requirement means this and not a technically valid RFC 4180 file that arrives
    unreadable.
    """
    lines = [";".join(CSV_COLUMNS)]
    for item in board.breaches:
        lines.append(
            ";".join(
                (
                    _cell(item.order_code or item.work_order_id),
                    _cell(item.asset_code),
                    _number(item.hours),
                    _number(item.limit_hours),
                    "no" if item.within_limit is False else "sí",
                    "sí" if item.limit_verified else "no",
                    _cell(item.norm_ref),
                    _cell(item.article_ref),
                    _cell(item.message),
                )
            )
        )
    return "﻿" + "\r\n".join(lines) + "\r\n"


def _cell(value: str | None) -> str:
    """One field, with the separator and the newlines taken out rather than quoted.

    Stripped and not escaped because these cells are codes and short messages: a quoting bug that
    shifts every column of one row is harder to notice than a message missing a semicolon.
    """
    if value is None:
        return ""
    return value.replace(";", ",").replace("\r", " ").replace("\n", " ").strip()


def _number(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}".replace(".", ",")
