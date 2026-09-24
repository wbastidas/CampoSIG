"""Writing preventive plans and firing them (RF-012).

The acceptance criterion is a count — «un plan mensual genera N OT en la fecha programada» — so this
module is organised around being able to defend that count afterwards. Four decisions shape it:

* **The period, not the clock, decides.** A run asks «has this plan already issued this period?» and
  the answer is a row in `plan_issue`. The uniqueness is a database index, so the nightly job and a
  planner pressing «generar ahora» cannot both issue September.
* **Every refusal is recorded with its reason.** An asset skipped because a crew is already on its
  way, or because it was inspected last week, becomes a row saying so. A plan that issued 4 of 11
  and explained nothing is a plan nobody can trust with the 4.
* **An expanded scope declares what it could not know.** The asset inventory is in the GIS, not here
  (ADR-006). «Todos los postes del alimentador 04BH07T11» is a question this platform cannot answer;
  what it can answer is «los activos de ese alimentador en los que hemos trabajado», which is a
  subset, and it says so in the words the planner reads next to the count. An explicit asset list —
  typed or imported by the area, which is also how a route is expressed — has no caveat.
* **Nothing here is clever about the work order.** Issuing goes through `create_work_order` with
  `source=plan_preventivo`, so the boards, the SLA and the audit trail treat a preventive order like
  any other. A second creation path would be a second set of invariants to keep.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analytics.maintenance import _last_attended
from app.audit.models import ActorKind, EventKind
from app.audit.service import record
from app.forms.catalog import CatalogError, get_definition
from app.org.models import BusinessUnit
from app.plans.models import (
    Cadence,
    IssueOutcome,
    MaintenancePlan,
    PlanIssue,
    PlanScope,
    PlanTarget,
)
from app.plans.periods import MAX_DAY_OF_MONTH, is_due, period_of
from app.responses.models import FormResponse
from app.workorders.models import Priority, WorkOrder, WorkOrderSource
from app.workorders.service import create_work_order, pending_field_work

#: What an expanded scope cannot know, in the words a planner reads. One sentence, defined once, so
#: the screen and the stored issue cannot drift.
EXPANSION_CAVEAT = (
    "El inventario de activos vive en el SIG, no en esta plataforma: la expansión cubre solo los "
    "activos de ese alcance en los que la plataforma ya registró trabajo. Puede faltar el activo "
    "que nunca se ha intervenido, y ese es justamente el que más falta hace inspeccionar"
)


class PlanError(Exception):
    pass


class UnknownPlanError(PlanError):
    pass


@dataclass
class PlanRun:
    """What one plan did in one period."""

    plan_code: str
    period: str
    issued: list[uuid.UUID] = field(default_factory=list)
    #: Asset codes skipped because there is already work pending in the field on them.
    skipped_pending: list[str] = field(default_factory=list)
    #: Asset codes skipped by the plan's own «atendido hace poco» guard.
    skipped_recent: list[str] = field(default_factory=list)
    #: Assets this period had already been issued for. Zero on a first run; the whole report on a
    #: second one, which is what makes «volver a correrlo no duplica» visible rather than assumed.
    already_issued: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    #: Why the run produced nothing, when it produced nothing. A plan that fired and issued zero
    #: orders in silence is indistinguishable from a plan that never fired.
    note: str | None = None

    @property
    def targets(self) -> int:
        return (
            len(self.issued)
            + len(self.skipped_pending)
            + len(self.skipped_recent)
            + len(self.already_issued)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_code": self.plan_code,
            "period": self.period,
            "targets": self.targets,
            "issued": [str(item) for item in self.issued],
            "skipped_pending": self.skipped_pending,
            "skipped_recent": self.skipped_recent,
            "already_issued": self.already_issued,
            "caveats": self.caveats,
            "note": self.note,
        }


@dataclass
class PassReport:
    """What one pass over every plan of a business unit did."""

    on: date
    runs: list[PlanRun] = field(default_factory=list)
    #: Plans that were not due today. Counted so an operator reading the log can tell «nothing was
    #: due» from «the pass did not run».
    not_due: list[str] = field(default_factory=list)

    @property
    def issued(self) -> int:
        return sum(len(run.issued) for run in self.runs)

    def as_dict(self) -> dict[str, Any]:
        return {
            "on": self.on.isoformat(),
            "issued": self.issued,
            "runs": [run.as_dict() for run in self.runs],
            "not_due": self.not_due,
        }


# --- writing plans ------------------------------------------------------------------------


def save_plan(
    session: Session,
    unit: BusinessUnit,
    *,
    code: str,
    name: str,
    work_type: str,
    form_code: str,
    cadence: str,
    scope: str,
    actor: str,
    priority: str = Priority.MEDIUM.value,
    asset_type_key: str | None = None,
    cadence_days: int | None = None,
    day_of_month: int = 1,
    scope_value: str | None = None,
    skip_if_attended_within_days: int | None = None,
    starts_on: date | None = None,
    ends_on: date | None = None,
    description: str | None = None,
    targets: list[dict[str, Any]] | None = None,
    active: bool = True,
) -> MaintenancePlan:
    """Create or replace one plan, validating everything that would otherwise fail at 05:00.

    The form, the cadence and the day of month are checked here rather than at fire time on purpose:
    a plan is written by a person who is present, and a worker that discovered the problem three
    weeks later would report it to a log nobody reads.
    """
    _validate(
        cadence=cadence,
        cadence_days=cadence_days,
        day_of_month=day_of_month,
        scope=scope,
        scope_value=scope_value,
        form_code=form_code,
        targets=targets,
        skip_if_attended_within_days=skip_if_attended_within_days,
    )

    plan = session.execute(
        select(MaintenancePlan).where(
            MaintenancePlan.business_unit_id == unit.id, MaintenancePlan.code == code
        )
    ).scalar_one_or_none()
    created = plan is None
    if plan is None:
        plan = MaintenancePlan(business_unit_id=unit.id, code=code, created_by=actor)
        session.add(plan)

    plan.name = name
    plan.description = description
    plan.work_type = work_type
    plan.form_code = form_code
    plan.priority = priority
    plan.asset_type_key = asset_type_key
    plan.cadence = cadence
    plan.cadence_days = cadence_days if cadence == Cadence.CUSTOM_DAYS else None
    plan.day_of_month = day_of_month
    plan.scope = scope
    plan.scope_value = scope_value if scope != PlanScope.ASSETS else None
    plan.skip_if_attended_within_days = skip_if_attended_within_days
    plan.starts_on = starts_on or datetime.now(UTC).date()
    plan.ends_on = ends_on
    plan.active = active
    plan.updated_by = actor
    session.flush()

    if targets is not None:
        _replace_targets(session, plan, targets)

    record(
        session,
        unit.id,
        kind=EventKind.CREATED if created else EventKind.FIELD_CHANGED,
        subject_type="maintenance_plan",
        subject_id=str(plan.id),
        actor=actor,
        payload={
            "code": code,
            "cadence": cadence,
            "scope": scope,
            "scope_value": plan.scope_value,
            "form_code": form_code,
            "active": active,
        },
    )
    return plan


def _validate(
    *,
    cadence: str,
    cadence_days: int | None,
    day_of_month: int,
    scope: str,
    scope_value: str | None,
    form_code: str,
    targets: list[dict[str, Any]] | None,
    skip_if_attended_within_days: int | None,
) -> None:
    if cadence not in tuple(Cadence):
        raise PlanError(f"la frecuencia «{cadence}» no existe")
    if cadence == Cadence.CUSTOM_DAYS and (not cadence_days or cadence_days < 1):
        raise PlanError("una frecuencia en días necesita cuántos días, y al menos uno")
    if not 1 <= day_of_month <= MAX_DAY_OF_MONTH:
        raise PlanError(
            f"el día del mes tiene que estar entre 1 y {MAX_DAY_OF_MONTH}: el 29, 30 y 31 no "
            "existen todos los meses, y un plan que se saltara febrero emitiría once veces al año "
            "mientras el área reporta doce"
        )
    if scope not in tuple(PlanScope):
        raise PlanError(f"el alcance «{scope}» no existe")
    if scope != PlanScope.ASSETS and not scope_value:
        raise PlanError(f"un plan por «{scope}» necesita el código del alcance")
    if scope == PlanScope.ASSETS and not targets:
        raise PlanError(
            "un plan por activos necesita al menos un activo: la lista es el alcance, y un plan "
            "sin ella no emitiría nada sin decir por qué"
        )
    if skip_if_attended_within_days is not None and skip_if_attended_within_days < 0:
        raise PlanError("los días de la guarda de «atendido hace poco» no pueden ser negativos")
    try:
        get_definition(form_code)
    except CatalogError as exc:
        raise PlanError(f"el formulario «{form_code}» no está en el catálogo") from exc


def _replace_targets(
    session: Session, plan: MaintenancePlan, targets: list[dict[str, Any]]
) -> None:
    """Replace a plan's target list wholesale.

    Wholesale because the list *is* the route: a partial update would leave the visit order as a mix
    of two versions, and the crew would drive it.
    """
    for existing in session.execute(
        select(PlanTarget).where(PlanTarget.plan_id == plan.id)
    ).scalars():
        session.delete(existing)
    session.flush()
    seen: set[str] = set()
    for position, target in enumerate(targets):
        code = str(target.get("asset_code") or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        session.add(
            PlanTarget(
                plan_id=plan.id,
                asset_code=code,
                asset_type_key=target.get("asset_type_key") or plan.asset_type_key,
                feeder_code=target.get("feeder_code"),
                zone=target.get("zone"),
                sort_order=int(target.get("sort_order", position)),
            )
        )
    session.flush()


def plans_of(
    session: Session, unit: BusinessUnit, *, only_active: bool = False
) -> list[MaintenancePlan]:
    query = select(MaintenancePlan).where(MaintenancePlan.business_unit_id == unit.id)
    if only_active:
        query = query.where(MaintenancePlan.active.is_(True))
    return list(session.execute(query.order_by(MaintenancePlan.code)).scalars())


def get_plan(session: Session, unit: BusinessUnit, code: str) -> MaintenancePlan:
    plan = session.execute(
        select(MaintenancePlan).where(
            MaintenancePlan.business_unit_id == unit.id, MaintenancePlan.code == code
        )
    ).scalar_one_or_none()
    if plan is None:
        raise UnknownPlanError(f"no existe el plan «{code}» en esta unidad de negocio")
    return plan


def targets_of(session: Session, plan: MaintenancePlan) -> list[PlanTarget]:
    return list(
        session.execute(
            select(PlanTarget)
            .where(PlanTarget.plan_id == plan.id)
            .order_by(PlanTarget.sort_order, PlanTarget.asset_code)
        ).scalars()
    )


def history(session: Session, plan: MaintenancePlan, *, limit: int = 500) -> list[PlanIssue]:
    return list(
        session.execute(
            select(PlanIssue)
            .where(PlanIssue.plan_id == plan.id)
            .order_by(PlanIssue.issued_at.desc())
            .limit(limit)
        ).scalars()
    )


# --- expanding the scope ------------------------------------------------------------------


@dataclass
class Expansion:
    """The assets a plan covers, and what finding them could not know."""

    assets: list[tuple[str, str | None, str | None, str | None]] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    note: str | None = None


def expand(session: Session, unit: BusinessUnit, plan: MaintenancePlan) -> Expansion:
    """The assets this plan issues work for, in visit order where there is one."""
    if plan.scope == PlanScope.ASSETS:
        rows = targets_of(session, plan)
        expansion = Expansion(
            assets=[(row.asset_code, row.asset_type_key, row.feeder_code, row.zone) for row in rows]
        )
        if not expansion.assets:
            expansion.note = "el plan no tiene ningún activo en su lista"
        return expansion

    column = WorkOrder.feeder_code if plan.scope == PlanScope.FEEDER else WorkOrder.zone
    seen = session.execute(
        select(
            WorkOrder.asset_code,
            func.min(WorkOrder.asset_type_key),
            func.min(WorkOrder.feeder_code),
            func.min(WorkOrder.zone),
        )
        .where(
            WorkOrder.business_unit_id == unit.id,
            column == plan.scope_value,
            WorkOrder.asset_code.is_not(None),
        )
        .group_by(WorkOrder.asset_code)
        .order_by(WorkOrder.asset_code)
    ).all()
    if plan.asset_type_key:
        seen = [row for row in seen if row[1] == plan.asset_type_key]

    expansion = Expansion(
        assets=[(str(row[0]), row[1], row[2], row[3]) for row in seen],
        caveats=[EXPANSION_CAVEAT],
    )
    if not expansion.assets:
        expansion.note = (
            f"la plataforma no ha registrado trabajo en ningún activo de «{plan.scope_value}», "
            "así que no hay nada que expandir todavía"
        )
    return expansion


# --- firing -------------------------------------------------------------------------------


def run_plan(
    session: Session,
    unit: BusinessUnit,
    plan: MaintenancePlan,
    *,
    on: date,
    actor: str = "sistema:plan-preventivo",
) -> PlanRun:
    """Issue this plan's orders for the period `on` falls in.

    Safe to call twice: the second call finds the period's issues already recorded and reports them
    as `already_issued` rather than creating anything.
    """
    period = period_of(plan.cadence, plan.cadence_days, on, anchor=plan.starts_on)
    run = PlanRun(plan_code=plan.code, period=period)

    expansion = expand(session, unit, plan)
    run.caveats = list(expansion.caveats)
    if not expansion.assets:
        run.note = expansion.note
        return run

    assets = {code for code, _type, _feeder, _zone in expansion.assets}
    issued_before = {
        str(code)
        for code in session.execute(
            select(PlanIssue.asset_code).where(
                PlanIssue.plan_id == plan.id,
                PlanIssue.period == period,
                PlanIssue.asset_code.is_not(None),
            )
        ).scalars()
    }
    pending = pending_field_work(session, unit, assets)
    attended = (
        _last_attended(session, unit.id, assets)
        if plan.skip_if_attended_within_days is not None
        else {}
    )
    cutoff = (
        datetime.now(UTC) - timedelta(days=plan.skip_if_attended_within_days)
        if plan.skip_if_attended_within_days is not None
        else None
    )

    for code, asset_type, feeder, zone in expansion.assets:
        if code in issued_before:
            run.already_issued.append(code)
            continue
        if pending.get(code):
            run.skipped_pending.append(code)
            _record_issue(
                session,
                plan,
                period,
                code,
                outcome=IssueOutcome.PENDING_WORK,
                reason="ya hay trabajo pendiente en campo sobre este activo",
                caveats=expansion.caveats,
            )
            continue
        last = attended.get(code)
        if cutoff is not None and last is not None and last >= cutoff:
            run.skipped_recent.append(code)
            _record_issue(
                session,
                plan,
                period,
                code,
                outcome=IssueOutcome.RECENTLY_ATTENDED,
                reason=(
                    f"se atendió el {last.date().isoformat()}, dentro de los "
                    f"{plan.skip_if_attended_within_days} días de la guarda del plan"
                ),
                caveats=expansion.caveats,
            )
            continue

        order = create_work_order(
            session,
            unit,
            work_type=plan.work_type,
            form_code=plan.form_code,
            priority=plan.priority,
            source=WorkOrderSource.PREVENTIVE_PLAN,
            description=f"{plan.name} ({plan.code}), periodo {period}",
            asset_type_key=asset_type or plan.asset_type_key,
            asset_code=code,
            feeder_code=feeder,
            zone=zone,
            planner_id=actor,
        )
        issue = _record_issue(
            session,
            plan,
            period,
            code,
            outcome=IssueOutcome.ISSUED,
            reason=None,
            caveats=expansion.caveats,
            work_order_id=order.id,
        )
        if issue is None:
            # Another writer took this asset and period first. Its order stands; ours would be the
            # duplicate, so it is cancelled rather than left for a crew to drive to.
            order.state = "anulada"
            session.flush()
            run.already_issued.append(code)
            continue
        run.issued.append(order.id)

    record(
        session,
        unit.id,
        kind=EventKind.CREATED,
        subject_type="plan_run",
        subject_id=str(plan.id),
        actor=actor,
        actor_kind=ActorKind.SYSTEM,
        payload={
            "plan_code": plan.code,
            "period": period,
            "issued": len(run.issued),
            "skipped_pending": len(run.skipped_pending),
            "skipped_recent": len(run.skipped_recent),
            "already_issued": len(run.already_issued),
        },
    )
    return run


def _record_issue(
    session: Session,
    plan: MaintenancePlan,
    period: str,
    asset_code: str | None,
    *,
    outcome: str,
    reason: str | None,
    caveats: list[str],
    work_order_id: uuid.UUID | None = None,
) -> PlanIssue | None:
    """Record one outcome, or None when this asset and period were already recorded.

    The SAVEPOINT is what makes the database index usable as the guard rather than as a crash: a
    losing race rolls back this row and leaves the rest of the pass intact.
    """
    issue = PlanIssue(
        plan_id=plan.id,
        period=period,
        asset_code=asset_code,
        outcome=outcome,
        reason=reason,
        caveats=list(caveats),
        work_order_id=work_order_id,
    )
    try:
        with session.begin_nested():
            session.add(issue)
            session.flush()
    except IntegrityError:
        return None
    return issue


def run_due(
    session: Session,
    unit: BusinessUnit,
    *,
    on: date | None = None,
    actor: str = "sistema:plan-preventivo",
) -> PassReport:
    """Every active plan of this unit that is due today."""
    today = on or datetime.now(UTC).date()
    report = PassReport(on=today)
    for plan in plans_of(session, unit, only_active=True):
        if plan.ends_on is not None and today > plan.ends_on:
            report.not_due.append(plan.code)
            continue
        if not is_due(
            plan.cadence, plan.cadence_days, plan.day_of_month, today, anchor=plan.starts_on
        ):
            report.not_due.append(plan.code)
            continue
        report.runs.append(run_plan(session, unit, plan, on=today, actor=actor))
    return report


def coverage(session: Session, unit: BusinessUnit, plan: MaintenancePlan) -> dict[str, Any]:
    """How the plan's current period is going, for the screen.

    Reported as a fraction with its denominator, like every other rate in this platform: «8 de 11»
    says something «73 %» does not, which is that three assets are unaccounted for.
    """
    period = period_of(
        plan.cadence, plan.cadence_days, datetime.now(UTC).date(), anchor=plan.starts_on
    )
    rows = session.execute(
        select(PlanIssue.outcome, func.count())
        .where(PlanIssue.plan_id == plan.id, PlanIssue.period == period)
        .group_by(PlanIssue.outcome)
    ).all()
    counts = {str(outcome): int(total) for outcome, total in rows}
    expansion = expand(session, unit, plan)
    return {
        "period": period,
        "targets": len(expansion.assets),
        "issued": counts.get(IssueOutcome.ISSUED.value, 0),
        "skipped_pending": counts.get(IssueOutcome.PENDING_WORK.value, 0),
        "skipped_recent": counts.get(IssueOutcome.RECENTLY_ATTENDED.value, 0),
        "caveats": expansion.caveats,
        "note": expansion.note,
    }


def completion(session: Session, unit: BusinessUnit, plan: MaintenancePlan) -> dict[str, Any]:
    """How much of what the plan issued this period actually got done.

    The number the maintenance area is asked for — «¿cumplimos el plan?» — and it is not the same as
    the issue count: a plan that issued eleven orders nobody executed has 100 % issuance and 0 %
    compliance, and reporting only the first would be the more flattering of two honest numbers.
    """
    period = period_of(
        plan.cadence, plan.cadence_days, datetime.now(UTC).date(), anchor=plan.starts_on
    )
    order_ids = list(
        session.execute(
            select(PlanIssue.work_order_id).where(
                PlanIssue.plan_id == plan.id,
                PlanIssue.period == period,
                PlanIssue.work_order_id.is_not(None),
            )
        ).scalars()
    )
    if not order_ids:
        return {"period": period, "issued": 0, "submitted": 0}
    submitted = session.execute(
        select(func.count(func.distinct(FormResponse.work_order_id))).where(
            FormResponse.work_order_id.in_(order_ids),
            FormResponse.submitted_at.is_not(None),
        )
    ).scalar_one()
    return {"period": period, "issued": len(order_ids), "submitted": int(submitted)}
