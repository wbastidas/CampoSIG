"""Celery application and the schedule (RF-125, ADR-012).

Thin on purpose. The work lives in :mod:`app.workers.integration_delivery`, which takes a
session and returns a report, so it can be called from a test, from a management command, or
from here. What Celery adds is only the schedule and the retry of the *task*, and the task's
retry is deliberately absent: the events carry their own retry state in the ledger, and a task
that also retried would multiply the attempts of every event in its batch.

`beat` runs the pass every minute. Not every second: the outbox exists so that a delayed
delivery is harmless, and a minute of latency on closing a claim costs nothing while a worker
hammering a corporate API every second costs goodwill.
"""

from __future__ import annotations

from typing import Any

from celery import Celery
from celery.schedules import crontab

from app.infra.database import get_session_factory
from app.settings import get_settings
from app.workers.integration_delivery import run_once

settings = get_settings()

celery_app = Celery("sigec", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Guayaquil",
    enable_utc=True,
    # A task that outlives its schedule interval would pile up. The pass is bounded by
    # `integration_batch_size`, so a minute is generous.
    task_time_limit=120,
    task_soft_time_limit=100,
    beat_schedule={
        "entregar-integraciones": {
            "task": "sigec.integrations.deliver",
            "schedule": crontab(minute="*"),
        }
    },
)


# Celery ships no type information, so its decorator erases the signature under
# `mypy --strict`. Ignored narrowly here rather than by relaxing the setting for the package:
# the function's own types are checked, only the decorator is opaque.
@celery_app.task(name="sigec.integrations.deliver")  # type: ignore[untyped-decorator]
def deliver_integrations() -> dict[str, Any]:
    """One delivery pass over every business unit's outbox.

    No `autoretry_for`: the events retry themselves through the ledger, with their own backoff
    and their own limit. A task retry on top would multiply every event's attempts by the
    task's, and a connector that is down would be hit far harder than the backoff intends.
    """
    with get_session_factory()() as session:
        return run_once(session).as_dict()
