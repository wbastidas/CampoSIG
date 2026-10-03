"""Running and storing the pre-review (RF-170, RF-180, RF-204).

The orchestration half: it reads the database, hands the agents plain facts, and stores what they
returned. The agents themselves never see a session — that is rule 14, and the package split is what
makes it structural rather than remembered.

RF-170's acceptance criterion drives the shape: **every synced work order has a run in a terminal
state, failures retry, and nothing blocks human review.** So a failure is a stored state with its
reason, not an exception that escapes; a retry is a new attempt on the same run; and no caller of
this module is on a request path a supervisor waits on.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.facts import (
    AiValueFact,
    OtherOrderFact,
    PhotoFact,
    PreReviewFacts,
    RegulatoryFact,
)
from app.agents.graph import GRAPH_VERSION, run_pre_review
from app.agents.guardrails import Validation, with_reask
from app.agents.report import AgentReport, RunStatus
from app.org.models import BusinessUnit
from app.prereview.models import AgentRun, AgentStepTrace, RunState, StoredReport
from app.responses.models import Evidence, FormResponse, ValueOrigin
from app.review.blind import assign as assign_blind
from app.review.service import compliance_findings
from app.settings import get_settings
from app.workorders.models import WorkOrder

#: How many other work orders the cross-order rules compare against. Bounded because the rules are
#: about neighbours in time, not about the unit's whole history, and an unbounded comparison would
#: turn a night batch into a full table scan per order.
CROSS_ORDER_WINDOW = 200

#: How many times a failed run is retried before it stays failed. A run that keeps failing is a bug
#: to fix, not a queue to grow — and the supervisor is not waiting on it either way (RF-204).
MAX_ATTEMPTS = 3


def build_facts(session: Session, unit: BusinessUnit, order: WorkOrder) -> PreReviewFacts:
    """Everything the deterministic nodes need, read once."""
    response = session.scalars(
        select(FormResponse).where(FormResponse.work_order_id == order.id)
    ).first()

    photos = [
        PhotoFact(
            evidence_id=str(item.id),
            stage=item.stage,
            content_hash=item.content_hash,
            integrity_verified=item.integrity_verified,
        )
        for item in (response.evidence if response else [])
    ]

    ai_values = [
        AiValueFact(
            field_key=entry.field_key,
            origin=entry.origin,
            confidence=entry.confidence,
            model_name=entry.model_name,
            model_version=entry.model_version,
            accepted_unchanged=entry.accepted_unchanged,
            confirmed_by=entry.confirmed_by,
            transcript=entry.source_transcript,
        )
        for entry in (response.provenance if response else [])
        if entry.origin in (ValueOrigin.VOICE, ValueOrigin.VISION)
    ]

    regulatory = [
        RegulatoryFact(
            rule=finding.rule,
            outcome=finding.outcome.value,
            severity=finding.severity.value,
            message=finding.message,
            norm_ref=finding.norm_ref,
            article_ref=finding.article_ref,
            limit_verified=finding.limit_verified,
        )
        for finding in compliance_findings(session, order, response)
    ]

    return PreReviewFacts(
        work_order_id=str(order.id),
        work_order_code=order.code,
        asset_code=order.asset_code,
        asset_latitude=_latitude(session, order),
        asset_longitude=_longitude(session, order),
        answers=dict(response.answers) if response else {},
        photos=photos,
        ai_values=ai_values,
        regulatory=regulatory,
        other_orders=_other_orders(session, unit, order),
        submitted_at=response.submitted_at if response else None,
    )


def _coordinates(session: Session, order: WorkOrder) -> tuple[float, float] | None:
    """The asset's point, read through PostGIS rather than parsed from WKB here."""
    if order.location is None:
        return None
    from geoalchemy2.functions import ST_X, ST_Y

    row = session.execute(
        select(ST_Y(WorkOrder.location), ST_X(WorkOrder.location)).where(WorkOrder.id == order.id)
    ).first()
    if row is None or row[0] is None or row[1] is None:
        return None
    return float(row[0]), float(row[1])


def _latitude(session: Session, order: WorkOrder) -> float | None:
    found = _coordinates(session, order)
    return found[0] if found else None


def _longitude(session: Session, order: WorkOrder) -> float | None:
    found = _coordinates(session, order)
    return found[1] if found else None


def _other_orders(session: Session, unit: BusinessUnit, order: WorkOrder) -> list[OtherOrderFact]:
    """The unit's other recent orders, for the cross-order rules.

    Scoped to the unit, always: a pattern that spanned two business units would be a finding nobody
    in either unit could act on, and reading another unit's captures is what ADR-009 forbids.
    """
    recent = session.scalars(
        select(WorkOrder)
        .where(
            WorkOrder.business_unit_id == unit.id,
            WorkOrder.id != order.id,
        )
        .order_by(WorkOrder.updated_at.desc())
        .limit(CROSS_ORDER_WINDOW)
    ).all()
    if not recent:
        return []

    by_order = {item.id: item for item in recent}
    hashes: dict[uuid.UUID, set[str]] = {identifier: set() for identifier in by_order}
    rows = session.execute(
        select(FormResponse.work_order_id, Evidence.content_hash)
        .join(Evidence, Evidence.response_id == FormResponse.id)
        .where(FormResponse.work_order_id.in_(list(by_order)))
    ).all()
    for work_order_id, content_hash in rows:
        hashes.setdefault(work_order_id, set()).add(content_hash)

    facts: list[OtherOrderFact] = []
    for other in recent:
        point = _coordinates(session, other)
        facts.append(
            OtherOrderFact(
                work_order_id=str(other.id),
                code=other.code,
                photo_hashes=frozenset(hashes.get(other.id, set())),
                latitude=point[0] if point else None,
                longitude=point[1] if point else None,
            )
        )
    return facts


def execute(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    gateway_reachable: bool = True,
) -> AgentRun:
    """Run the pre-review and store the result, whatever it is.

    Never raises for a modelling failure: a run that ends `fallido` with its reason is a run a
    supervisor can see and a worker can retry, and an exception escaping here would leave the order
    with no run at all — which is the one state RF-170 forbids.
    """
    run = AgentRun(
        business_unit_id=unit.id,
        work_order_id=order.id,
        graph_version=GRAPH_VERSION,
        hardware_profile=get_settings().inference_profile,
        state=RunState.RUNNING,
        started_at=datetime.now(UTC),
        attempts=1,
    )
    session.add(run)
    session.flush()

    try:
        facts = build_facts(session, unit, order)
        # Through the guardrail, always (RF-182). Nothing is stored unvalidated: a report with a
        # customer's phone number in it is a report that has already been read by the time anybody
        # notices, and the golden sets of RNF-060 measure a corpus, not this run.
        report, validation, attempts = with_reask(
            lambda _attempt: run_pre_review(
                facts, run.hardware_profile, gateway_reachable=gateway_reachable
            )
        )
    except Exception as cause:  # a failed run is a state, not an escape
        run.state = RunState.FAILED
        run.error = f"{type(cause).__name__}: {cause}"
        run.finished_at = datetime.now(UTC)
        session.flush()
        return run

    _store(session, run, report, validation=validation, attempts=attempts)
    # Drawn here, before any human is involved: RF-111a measures whether a supervisor read the
    # capture or agreed with the report, and a draw made on a request path would be a draw the thing
    # being measured takes part in.
    assign_blind(session, order.id, unit.id, rate=get_settings().blind_sample_rate)
    return run


def _store(
    session: Session,
    run: AgentRun,
    report: AgentReport,
    *,
    validation: Validation | None = None,
    attempts: int = 1,
) -> None:
    document = report.model_dump(mode="json")
    run.state = RunState.PARTIAL if report.status is RunStatus.PARTIAL else RunState.DONE
    run.tokens = report.budget.tokens
    run.compute_seconds = report.budget.duration_s
    run.finished_at = datetime.now(UTC)
    session.add(
        StoredReport(
            agent_run_id=run.id,
            risk_level=report.risk_level.value,
            summary=report.summary,
            document=document,
            observation_count=len(report.observations),
            discarded=report.discarded,
        )
    )
    # One trace per deterministic node that contributed, plus one per node that did not run. The
    # second kind is the one RF-180 makes auditable: "why is there no visual section" has an answer
    # on record instead of in somebody's memory of the deployment.
    for node in sorted({item.node for item in report.observations if item.node}):
        session.add(
            AgentStepTrace(
                agent_run_id=run.id,
                node=node,
                output={
                    "observations": [item.id for item in report.observations if item.node == node]
                },
                duration_ms=0,
            )
        )
    # The guardrail's own trace (RF-180, RF-182). Written even when it changed nothing, because
    # «the guardrail ran and found nothing» and «the guardrail did not run» are different answers to
    # the question an auditor asks, and only one of them is reassuring.
    if validation is not None:
        session.add(
            AgentStepTrace(
                agent_run_id=run.id,
                node="guardrails",
                output={**validation.as_dict(), "attempts": attempts},
                duration_ms=0,
            )
        )

    for reason in report.skipped:
        node, _, detail = reason.partition(":")
        session.add(
            AgentStepTrace(
                agent_run_id=run.id,
                node=node.strip()[:48],
                skipped_reason=detail.strip() or reason,
                output={},
            )
        )
    session.flush()


def latest_run(session: Session, order_id: uuid.UUID) -> AgentRun | None:
    """The most recent run for a work order, whatever state it ended in."""
    return session.scalars(
        select(AgentRun)
        .where(AgentRun.work_order_id == order_id)
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    ).first()


def latest_report(session: Session, order_id: uuid.UUID) -> AgentReport | None:
    """The report a supervisor should read, or None when there is none yet.

    None is an ordinary answer, not an error: an order may be waiting for the night batch, or the
    deployment may have no model service at all. The review screen already says so (RF-204).
    """
    run = latest_run(session, order_id)
    if run is None or run.report is None:
        return None
    return AgentReport.model_validate(run.report.document)


def retry(session: Session, run: AgentRun, unit: BusinessUnit, order: WorkOrder) -> AgentRun:
    """Run it again, counting the attempt.

    Bounded: a run that keeps failing is a bug to fix rather than a queue to grow, and nobody is
    waiting on it (RF-204).
    """
    if run.attempts >= MAX_ATTEMPTS:
        return run
    fresh = execute(session, unit, order)
    fresh.attempts = run.attempts + 1
    session.flush()
    return fresh


def orders_without_a_terminal_run(
    session: Session, unit: BusinessUnit, limit: int = 50
) -> list[WorkOrder]:
    """Synced orders with no finished run — what the worker picks up (RF-170).

    Its acceptance criterion is that this list empties: every synced order ends with a run in a
    terminal state. An order that stays here is visible rather than forgotten.
    """
    from app.workorders.models import WorkOrderState

    latest = select(AgentRun.work_order_id).where(AgentRun.state.in_(RunState.TERMINAL)).subquery()
    return list(
        session.scalars(
            select(WorkOrder)
            .where(
                WorkOrder.business_unit_id == unit.id,
                WorkOrder.state.in_((WorkOrderState.SYNCED, WorkOrderState.IN_REVIEW)),
                WorkOrder.id.not_in(select(latest.c.work_order_id)),
            )
            .order_by(WorkOrder.updated_at)
            .limit(limit)
        )
    )


def risk_levels_for(
    session: Session, order_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, tuple[str, str | None]]:
    """Run state and risk level of the latest run of each named order, in one query.

    For the queue, which shows a page of orders and has two seconds to do it (RNF). Calling
    :func:`latest_report` per row would be two queries and a full document validation each, and the
    queue needs one word per order, not the report.

    The value is a pair — run state and risk level — because "no risk yet" has two meanings the
    supervisor should be able to tell apart: it failed, or it has not run.
    """
    if not order_ids:
        return {}
    ranked = (
        select(
            AgentRun.work_order_id.label("work_order_id"),
            AgentRun.state.label("state"),
            StoredReport.risk_level.label("risk_level"),
            func.row_number()
            .over(partition_by=AgentRun.work_order_id, order_by=AgentRun.created_at.desc())
            .label("position"),
        )
        .join(StoredReport, StoredReport.agent_run_id == AgentRun.id, isouter=True)
        .where(AgentRun.work_order_id.in_(list(order_ids)))
        .subquery()
    )
    rows = session.execute(
        select(ranked.c.work_order_id, ranked.c.state, ranked.c.risk_level).where(
            ranked.c.position == 1
        )
    )
    return {row.work_order_id: (row.state, row.risk_level) for row in rows}
