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
from app.workers.plan_generation import run_once as run_plan_generation
from app.workers.pre_review import run_once as run_pre_review_pass

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
        },
        # Cada cinco minutos, no cada minuto: la pre-revisión de una OT recién sincronizada no es
        # urgente —el supervisor la abre cuando llega a ella— y un grafo por OT cuesta más que
        # empujar un evento. Lo que sí importa es que la cola se vacíe, y eso lo comprueba
        # `orders_without_a_terminal_run`.
        "pre-revisar-ot": {
            "task": "sigec.prereview.run",
            "schedule": crontab(minute="*/5"),
        },
        # Una vez al día, de madrugada: un plan preventivo se mide en meses, y las OT que emite
        # tienen que estar en el tablero antes de que el planificador abra la bandeja. A las 04:30
        # de Guayaquil, que es antes del primer turno y después de cualquier corte nocturno.
        #
        # Que el job corra dos veces —un reintento, dos beats, un operador impaciente— es inocuo:
        # la etiqueta de periodo en `plan_issue` es la guarda, y es un índice de la base.
        "emitir-planes-preventivos": {
            "task": "sigec.plans.generate",
            "schedule": crontab(hour=4, minute=30),
        },
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


@celery_app.task(name="sigec.prereview.run")  # type: ignore[untyped-decorator]
def run_pre_reviews() -> dict[str, Any]:
    """One pre-review pass over every business unit (RF-170).

    No `autoretry_for` here either, and for a sharper reason than the integration task: a failed
    run is recorded with its reason and retried by the next pass, bounded by `MAX_ATTEMPTS`. A task
    retry would multiply that, and a graph that fails deterministically would be run until the queue
    gave up rather than until somebody fixed it.
    """
    with get_session_factory()() as session:
        return run_pre_review_pass(session).as_dict()


@celery_app.task(name="sigec.plans.generate")  # type: ignore[untyped-decorator]
def generate_preventive_plans() -> dict[str, Any]:
    """One pass over every business unit's due preventive plans (RF-012).

    No `autoretry_for`: a retry would re-run every unit, and the ones that succeeded would find
    their period already issued and do nothing — harmless but noisy. The failures are named in the
    report, and the next night's pass picks up a period that is still unissued.
    """
    with get_session_factory()() as session:
        return run_plan_generation(session).as_dict()
