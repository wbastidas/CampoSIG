"""Priority classes and day/night windows (RF-202).

The requirement in one sentence: during working hours no training task occupies the GPU, and the
queues can say how long they will wait. So this module is a policy and a clock, with no queue of
its own — the queue is Celery's, and a scheduling rule that lived inside a worker would be a rule
nobody could test against a Tuesday at three in the afternoon.

Why training is special. Everything else competes for the GPU in a way a person eventually
notices as slowness; a training run holds it for hours and turns the interactive path into a
timeout. So it is the one class refused outright by the clock rather than merely ranked last, and
it releases the GPU when its window closes — with a checkpoint, which is the worker's job, not
this module's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

from app.inference.registry import InferenceRegistry, Priority, Windows, load_registry

#: Saturday and Sunday, as `date.weekday()` numbers them.
WEEKEND = (5, 6)

#: Classes that only ever run in the night window. Training is here because it holds the GPU for
#: hours rather than seconds: ranking it last would still let it start at nine in the morning.
NIGHT_ONLY = frozenset({Priority.TRAINING})


@dataclass(frozen=True)
class Slot:
    """Whether a class may run at a given moment, and when it may if not."""

    priority: Priority
    may_run: bool
    reason: str
    #: When the next night window opens. Present only when the answer is no, so a queue can say
    #: how long the wait is instead of showing a task stuck with no explanation.
    waits_until: datetime | None = None


def is_night(moment: datetime, windows: Windows) -> bool:
    """Whether a moment falls in the batch-and-training window."""
    if windows.weekend_is_night and moment.date().weekday() in WEEKEND:
        return True
    return not (windows.day_starts_at <= moment.time() < windows.day_ends_at)


def next_night_start(moment: datetime, windows: Windows) -> datetime:
    """When the next night window opens — now, if it is already open.

    Walks day by day rather than doing modular arithmetic on the calendar: a weekend that is
    entirely night makes the closed form fiddly, and this is called once per queued task.
    """
    if is_night(moment, windows):
        return moment

    candidate = datetime.combine(moment.date(), windows.day_ends_at, tzinfo=moment.tzinfo)
    if candidate > moment:
        return candidate

    day: date = moment.date() + timedelta(days=1)
    for _ in range(8):
        start = _night_start_on(day, windows, moment.tzinfo)
        if start > moment:
            return start
        day += timedelta(days=1)
    # Unreachable while a day window has a length, which the registry validates at load.
    raise RuntimeError("no se encontró una ventana nocturna en los próximos ocho días")


def _night_start_on(day: date, windows: Windows, zone: tzinfo | None = None) -> datetime:
    """The moment the night window opens on a given day.

    The zone travels because the caller's moment may be aware: comparing an aware moment with a
    naive one raises, and it would raise in the one branch that only runs after eleven at night.
    """
    if windows.weekend_is_night and day.weekday() in WEEKEND:
        return datetime.combine(day, time(0, 0), tzinfo=zone)
    return datetime.combine(day, windows.day_ends_at, tzinfo=zone)


def slot_for(
    priority: Priority, moment: datetime, registry: InferenceRegistry | None = None
) -> Slot:
    """Whether this priority class may run at this moment."""
    known = registry or load_registry()
    windows = known.windows
    night = is_night(moment, windows)

    if priority in NIGHT_ONLY and not night:
        return Slot(
            priority,
            False,
            "el entrenamiento no toma la GPU en horario laboral (RF-202)",
            waits_until=next_night_start(moment, windows),
        )

    return Slot(priority, True, "dentro de su ventana" if night else "horario de inferencia")


def order_queue(
    tasks: list[tuple[str, Priority]], registry: InferenceRegistry | None = None
) -> list[str]:
    """Task ids in the order they should be served.

    Stable within a class, so two pre-review runs queued a minute apart are served in that order —
    a queue that reshuffled equals would make a supervisor's wait unpredictable for no gain. The
    ranking comes from the registry's own list, so reordering it in configuration reorders this.
    """
    known = registry or load_registry()
    ranked = sorted(
        (known.rank(priority), position, task_id)
        for position, (task_id, priority) in enumerate(tasks)
    )
    return [task_id for _, _, task_id in ranked]
