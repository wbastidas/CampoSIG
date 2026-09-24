"""The operational dashboard (RF-130).

Four questions a supervisor asks before lunch: what is where, what is late, who is getting work
done, and how long the work is taking. The first three come from the work orders themselves. The
fourth comes from the audit trail, and could not be answered at all until the trail existed — the
state machine used to move a field and keep no record, so "how long from dispatch to arrival" had
nowhere to look.

Three decisions shape the numbers, and each one is a way the dashboard could otherwise mislead:

**Medians, not means.** Two orders left open over a weekend move a mean by hours and tell you
nothing about the ordinary day. The median says what a normal job takes; the 90th percentile says
what the bad ones take. A mean alone would hide both.

**An order in progress is not a zero.** A job dispatched an hour ago has not "taken zero minutes to
arrive": it has not arrived. Counting it would drag every average down exactly when the crews are
busy. So each leg reports what it measured, what is still running, and what it could not measure at
all — three different things that a single average silently merges.

**The clock starts at the first dispatch.** A reassignment does not reset it. The alternative reads
better and is false: the time a reassignment costs is time the work took, and a dashboard that hides
it is a dashboard nobody can use to find out why.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.workorders.models import Crew, WorkOrder, WorkOrderState

#: Below this many finished jobs, a duration is reported as a count and not as a median. Small
#: because an operation with eight closed orders still wants to see the shape, but not one: a single
#: job is an anecdote.
MIN_FOR_A_DURATION = 5

#: How far ahead "por vencer" looks. A shift: what a supervisor can still do something about today.
DUE_SOON = timedelta(hours=8)

#: States that mean the work is over, one way or another. An order in one of these that never
#: reached a milestone is missing a record; one still running is simply not there yet.
TERMINAL = (WorkOrderState.CLOSED, WorkOrderState.CANCELLED)

#: The three milestones of RF-130, and the state each one is.
DISPATCHED = WorkOrderState.ASSIGNED
ON_SITE = WorkOrderState.ON_SITE
CLOSED_IN_FIELD = WorkOrderState.CLOSED_FIELD

#: The legs the dashboard times, in the order a job lives them.
LEGS: tuple[tuple[str, str, str], ...] = (
    ("despacho_llegada", DISPATCHED, ON_SITE),
    ("llegada_cierre", ON_SITE, CLOSED_IN_FIELD),
    ("despacho_cierre", DISPATCHED, CLOSED_IN_FIELD),
)

LEG_LABEL: dict[str, str] = {
    "despacho_llegada": "Despacho → llegada",
    "llegada_cierre": "Llegada → cierre en campo",
    "despacho_cierre": "Despacho → cierre en campo",
}


def percentile(values: list[float], share: float) -> float | None:
    """The value below which `share` of the sample sits, by linear interpolation.

    Written out rather than pulled from numpy: it is six lines, the dependency is 30 MB, and a
    backend that must run on a CPU-only profile does not need another wheel for a median.
    """
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = share * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    weight = position - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


@dataclass(frozen=True)
class Leg:
    """How long one stretch of a job takes, and what the number does not cover."""

    key: str
    #: Durations in minutes, of the jobs that completed this leg in the period.
    samples: list[float]
    #: Jobs that started the leg and have not finished it. Not zeros: they are still running.
    in_progress: int
    #: Jobs that finished but have no record of one end. Counted, because an average computed over
    #: only the well-recorded jobs reports the best case.
    unrecorded: int

    @property
    def measured(self) -> int:
        return len(self.samples)

    @property
    def median_minutes(self) -> float | None:
        return percentile(self.samples, 0.5) if self.measured >= MIN_FOR_A_DURATION else None

    @property
    def p90_minutes(self) -> float | None:
        return percentile(self.samples, 0.9) if self.measured >= MIN_FOR_A_DURATION else None

    @property
    def worst_minutes(self) -> float | None:
        """The slowest job of the period.

        Reported beside the percentile because on a small sample the percentile hides it: with ten
        jobs, the interpolated p90 of nine at half an hour and one at five hours is under an hour,
        which is correct arithmetic and a useless answer to «¿cuál fue la peor?».
        """
        return max(self.samples) if self.samples else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": LEG_LABEL[self.key],
            "measured": self.measured,
            "in_progress": self.in_progress,
            "unrecorded": self.unrecorded,
            "median_minutes": self.median_minutes,
            "p90_minutes": self.p90_minutes,
            "worst_minutes": self.worst_minutes,
            "min_sample": MIN_FOR_A_DURATION,
        }


@dataclass(frozen=True)
class CrewProductivity:
    crew_id: str
    crew_name: str
    #: Orders the crew closed in the field during the period. The crew's own output: what happens
    #: afterwards in review is the office's work and not theirs.
    closed_in_field: int
    #: Of those, how many a supervisor later approved without returning them.
    approved: int
    #: Orders currently assigned to the crew and not finished. Load, not output.
    open_now: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "crew_id": self.crew_id,
            "crew_name": self.crew_name,
            "closed_in_field": self.closed_in_field,
            "approved": self.approved,
            "open_now": self.open_now,
        }


@dataclass
class Board:
    computed_at: datetime
    since: datetime
    by_state: dict[str, int] = field(default_factory=dict)
    overdue: int = 0
    due_soon: int = 0
    #: Orders with no SLA at all. Said out loud: a board reporting "0 vencidas" over a hundred
    #: orders that never had a date is reporting nothing.
    without_sla: int = 0
    legs: list[Leg] = field(default_factory=list)
    crews: list[CrewProductivity] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "computed_at": self.computed_at.isoformat(),
            "since": self.since.isoformat(),
            "by_state": self.by_state,
            "sla": {
                "overdue": self.overdue,
                "due_soon": self.due_soon,
                "due_soon_hours": int(DUE_SOON.total_seconds() // 3600),
                "without_sla": self.without_sla,
            },
            "legs": [leg.as_dict() for leg in self.legs],
            "crews": [crew.as_dict() for crew in self.crews],
        }


def _in_period(
    statement: Select[Any], unit_id: uuid.UUID, since: datetime, until: datetime
) -> Select[Any]:
    return statement.where(
        WorkOrder.business_unit_id == unit_id,
        WorkOrder.created_at >= since,
        WorkOrder.created_at <= until,
    )


def build(
    session: Session,
    unit_id: uuid.UUID,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    now: datetime | None = None,
) -> Board:
    """The whole board. Computed live, so «cada 5 min» is a refresh and never a stale cache."""
    moment = now or datetime.now(UTC)
    start = since or (moment - timedelta(days=30))
    end = until or moment

    by_state: dict[str, int] = dict(
        session.execute(
            _in_period(
                select(WorkOrder.state, func.count(WorkOrder.id)).group_by(WorkOrder.state),
                unit_id,
                start,
                end,
            )
        )
        .tuples()
        .all()
    )

    return Board(
        computed_at=moment,
        since=start,
        by_state=by_state,
        overdue=_sla_count(session, unit_id, start, end, before=moment),
        due_soon=_sla_count(session, unit_id, start, end, after=moment, before=moment + DUE_SOON),
        without_sla=_without_sla(session, unit_id, start, end),
        legs=_legs(session, unit_id, start, end),
        crews=_crews(session, unit_id, start, end),
    )


def _open_orders() -> Any:
    """Work that is still somebody's to do. An overdue SLA on a closed order is history."""
    return WorkOrder.state.notin_([*TERMINAL, WorkOrderState.APPROVED])


def _sla_count(
    session: Session,
    unit_id: uuid.UUID,
    since: datetime,
    until: datetime,
    *,
    before: datetime,
    after: datetime | None = None,
) -> int:
    statement = _in_period(select(func.count(WorkOrder.id)), unit_id, since, until).where(
        WorkOrder.sla_due_at.is_not(None),
        WorkOrder.sla_due_at < before,
        _open_orders(),
    )
    if after is not None:
        statement = statement.where(WorkOrder.sla_due_at >= after)
    return int(session.scalar(statement) or 0)


def _without_sla(session: Session, unit_id: uuid.UUID, since: datetime, until: datetime) -> int:
    return int(
        session.scalar(
            _in_period(select(func.count(WorkOrder.id)), unit_id, since, until).where(
                WorkOrder.sla_due_at.is_(None), _open_orders()
            )
        )
        or 0
    )


def _milestones(
    session: Session, unit_id: uuid.UUID, since: datetime, until: datetime
) -> dict[uuid.UUID, dict[str, datetime]]:
    """When each order first reached each milestone, from the trail.

    Matched on the event's payload rather than on its kind, because a state change arrives as a
    transition for most moves and as a field change for an assignment — the two write the same
    `from`/`to`, and a query that only read transitions would silently lose every dispatch.

    The **first** time, and not the last: a reassignment does not restart the clock. The time it
    costs is time the work took.
    """
    reached = AuditEvent.payload["to"].astext.label("reached")
    rows = session.execute(
        select(
            AuditEvent.work_order_id,
            reached,
            func.min(AuditEvent.occurred_at),
        )
        .where(
            AuditEvent.business_unit_id == unit_id,
            AuditEvent.work_order_id.is_not(None),
            AuditEvent.occurred_at >= since,
            AuditEvent.occurred_at <= until,
            reached.in_([DISPATCHED, ON_SITE, CLOSED_IN_FIELD]),
        )
        .group_by(AuditEvent.work_order_id, reached)
    )
    found: dict[uuid.UUID, dict[str, datetime]] = {}
    for order_id, state, when in rows:
        found.setdefault(order_id, {})[state] = when
    return found


def _legs(session: Session, unit_id: uuid.UUID, since: datetime, until: datetime) -> list[Leg]:
    milestones = _milestones(session, unit_id, since, until)
    states: dict[uuid.UUID, str] = dict(
        session.execute(_in_period(select(WorkOrder.id, WorkOrder.state), unit_id, since, until))
        .tuples()
        .all()
    )

    legs: list[Leg] = []
    for key, start_state, end_state in LEGS:
        samples: list[float] = []
        in_progress = 0
        unrecorded = 0
        for order_id, state in states.items():
            reached = milestones.get(order_id, {})
            started = reached.get(start_state)
            finished = reached.get(end_state)
            if started is not None and finished is not None:
                # Negative durations would mean the trail recorded the end before the start, which
                # the chain makes impossible. Clamped anyway rather than trusted: a negative in an
                # average is worse than a missing one.
                minutes = max((finished - started).total_seconds() / 60, 0.0)
                samples.append(minutes)
            elif started is not None:
                in_progress += 1
            elif state in TERMINAL or finished is not None:
                # It finished — or is over — without a record of having started. That is a gap in
                # the trail, usually an order that predates it, and it is counted rather than
                # ignored: an average over only the well-recorded jobs reports the best case.
                unrecorded += 1
        legs.append(Leg(key=key, samples=samples, in_progress=in_progress, unrecorded=unrecorded))
    return legs


def _crews(
    session: Session, unit_id: uuid.UUID, since: datetime, until: datetime
) -> list[CrewProductivity]:
    """What each crew finished, and what it is carrying now.

    Finished means closed in the field: that is the crew's own output. What happens afterwards in
    review is the office's work, and counting it here would make a crew's number move because
    somebody else was on holiday.
    """
    crews = list(session.scalars(select(Crew).where(Crew.business_unit_id == unit_id)))
    if not crews:
        return []

    milestones = _milestones(session, unit_id, since, until)
    rows = session.execute(
        _in_period(
            select(WorkOrder.id, WorkOrder.assigned_crew_id, WorkOrder.state),
            unit_id,
            since,
            until,
        )
    ).all()

    closed: dict[uuid.UUID, int] = {}
    approved: dict[uuid.UUID, int] = {}
    open_now: dict[uuid.UUID, int] = {}
    for order_id, crew_id, state in rows:
        if crew_id is None:
            continue
        if CLOSED_IN_FIELD in milestones.get(order_id, {}):
            closed[crew_id] = closed.get(crew_id, 0) + 1
        if state in (WorkOrderState.APPROVED, WorkOrderState.CLOSED):
            approved[crew_id] = approved.get(crew_id, 0) + 1
        if state not in (*TERMINAL, WorkOrderState.APPROVED):
            open_now[crew_id] = open_now.get(crew_id, 0) + 1

    return sorted(
        (
            CrewProductivity(
                crew_id=str(crew.id),
                crew_name=crew.name,
                closed_in_field=closed.get(crew.id, 0),
                approved=approved.get(crew.id, 0),
                open_now=open_now.get(crew.id, 0),
            )
            for crew in crews
        ),
        key=lambda item: (-item.closed_in_field, item.crew_name),
    )
