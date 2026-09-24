"""Period labels and due dates for a preventive plan (RF-012).

Separated from the service because this is the part with no database in it and the part most worth
testing on its own: every idempotence guarantee of RF-012 rests on two plans runs on different days
producing the **same label**, and on a plan firing on the day the area expects.

The label is deliberately human: a planner reading `plan_issue` sees `2026-T3`, not a timestamp. It
is also the only thing that decides whether a second run issues anything, which is why it is a pure
function of a date and a cadence and nothing else — no «last run», no clock.
"""

from __future__ import annotations

from datetime import date

from app.plans.models import Cadence

#: The most a calendar plan's day of month can be.
#:
#: 28 and not 31 on purpose: «el 31 de cada mes» does not exist in February, and the two ways to
#: cope are both wrong. Firing on the 28th in February makes the period shorter than the cadence;
#: skipping February makes the plan issue eleven times a year while the area reports twelve. So the
#: platform refuses to accept 29, 30 or 31, and says why, which is a conversation with the planner
#: instead of a discrepancy in an audit.
MAX_DAY_OF_MONTH = 28

#: Months each calendar cadence spans.
MONTHS: dict[str, int] = {
    Cadence.MONTHLY.value: 1,
    Cadence.QUARTERLY.value: 3,
    Cadence.SEMIANNUAL.value: 6,
    Cadence.ANNUAL.value: 12,
}


def period_of(cadence: str, cadence_days: int | None, on: date, *, anchor: date) -> str:
    """The label of the period `on` falls in.

    :param anchor: the plan's start date. Only used by the day-based cadence, where periods are
        counted from the start and not from the calendar: «cada 45 días» has no calendar meaning, so
        the only honest anchor is the day the area said the plan begins.
    """
    if cadence == Cadence.CUSTOM_DAYS:
        days = cadence_days or 1
        elapsed = (on - anchor).days
        index = elapsed // days if elapsed >= 0 else 0
        start = anchor.toordinal() + index * days
        return date.fromordinal(start).isoformat()
    if cadence == Cadence.MONTHLY:
        return f"{on.year:04d}-{on.month:02d}"
    if cadence == Cadence.QUARTERLY:
        return f"{on.year:04d}-T{(on.month - 1) // 3 + 1}"
    if cadence == Cadence.SEMIANNUAL:
        return f"{on.year:04d}-S{(on.month - 1) // 6 + 1}"
    return f"{on.year:04d}"


def is_due(
    cadence: str,
    cadence_days: int | None,
    day_of_month: int,
    on: date,
    *,
    anchor: date,
) -> bool:
    """Whether a plan fires on this date.

    A calendar plan fires on its day of month, in the first month of its period — so a quarterly
    plan with `day_of_month=5` fires on 5 January, 5 April, 5 July and 5 October, and not on the 5th
    of every month.

    **On or after** rather than exactly on, for the calendar cadences: a worker that did not run on
    the 5th (a machine down, a deployment) must still issue that period's orders on the 6th. The
    period label is what stops it issuing them twice, so being generous here is safe and being
    strict here would silently lose a month of preventive work.
    """
    if on < anchor:
        return False
    if cadence == Cadence.CUSTOM_DAYS:
        # Always due once the plan has started, and the period label is what decides whether
        # anything is issued. Written this way rather than «exactly every N days» because the two
        # differ only when the worker missed its day, and then the strict version silently waits
        # another N days — a plan «cada 45 días» losing a month and a half of preventive work.
        return True
    months = MONTHS.get(cadence, 1)
    start_month = _period_start_month(months, anchor.month)
    if (on.month - start_month) % months != 0:
        return False
    return on.day >= min(day_of_month, MAX_DAY_OF_MONTH)


def _period_start_month(months: int, anchor_month: int) -> int:
    """The month a period starts in, aligned to the calendar and anchored by the plan's start.

    A quarterly plan that starts in February runs in February, May, August and November: the area's
    quarter, not the platform's. Aligning every plan to January would move its first run by up to
    two months without telling anybody.
    """
    return ((anchor_month - 1) % months) + 1
