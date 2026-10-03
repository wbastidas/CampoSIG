"""Preventive maintenance plans (RF-012).

Writing a plan is planning, so it belongs to the planner and to functional administration. Firing
one by hand is the same act the nightly job performs, so it takes the same roles — and it is a POST,
never a side effect of reading the screen: a GET that issued work orders would issue them again
every time somebody refreshed.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.plans import service as plans
from app.plans.models import Cadence, MaintenancePlan, PlanScope
from app.workorders.models import Priority

router = APIRouter(prefix="/api/v1/plans", tags=["plans"], dependencies=[Depends(unit_scope)])

SessionDep = Annotated[Session, Depends(get_session)]

#: Who writes and fires plans. The supervisor reads: they are the one asked why a crew was sent.
WRITERS = (Role.PLANNER, Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN)
READERS = (*WRITERS, Role.SUPERVISOR, Role.AUDITOR)


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _plan(session: Session, unit: BusinessUnit, code: str) -> MaintenancePlan:
    try:
        return plans.get_plan(session, unit, code)
    except plans.UnknownPlanError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _as_dict(plan: MaintenancePlan) -> dict[str, Any]:
    return {
        "code": plan.code,
        "name": plan.name,
        "description": plan.description,
        "work_type": plan.work_type,
        "form_code": plan.form_code,
        "priority": plan.priority,
        "asset_type_key": plan.asset_type_key,
        "cadence": plan.cadence,
        "cadence_days": plan.cadence_days,
        "day_of_month": plan.day_of_month,
        "scope": plan.scope,
        "scope_value": plan.scope_value,
        "skip_if_attended_within_days": plan.skip_if_attended_within_days,
        "starts_on": plan.starts_on.isoformat(),
        "ends_on": plan.ends_on.isoformat() if plan.ends_on else None,
        "active": plan.active,
        "created_by": plan.created_by,
        "updated_by": plan.updated_by,
    }


class TargetIn(BaseModel):
    asset_code: str = Field(min_length=1, max_length=128)
    asset_type_key: str | None = None
    feeder_code: str | None = None
    zone: str | None = None
    #: The visit order. A route is this list sorted by it.
    sort_order: int = 0


class PlanIn(BaseModel):
    """A plan as the screen sends it.

    No author: the author is the token's subject. A plan whose author the caller could type is a
    plan nobody signed, and somebody has to answer for why a crew was sent to that pole.
    """

    name: str = Field(min_length=1, max_length=255)
    work_type: str = Field(min_length=1, max_length=32)
    form_code: str = Field(min_length=1, max_length=16)
    cadence: Cadence
    scope: PlanScope
    priority: Priority = Priority.MEDIUM
    description: str | None = Field(default=None, max_length=4000)
    asset_type_key: str | None = None
    cadence_days: int | None = None
    day_of_month: int = 1
    scope_value: str | None = None
    skip_if_attended_within_days: int | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    active: bool = True
    targets: list[TargetIn] | None = None


class RunIn(BaseModel):
    """The date to fire for.

    Explicit so an area can catch up a period the worker missed, and so a test can be about a
    calendar rather than about today.
    """

    on: date | None = None


@router.get("/units/{unit_code}", summary="Los planes preventivos de la unidad (RF-012)")
def index(
    unit_code: str,
    session: SessionDep,
    _: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    rows = plans.plans_of(session, unit)
    return {
        "plans": [
            {
                **_as_dict(plan),
                "targets": len(plans.targets_of(session, plan)),
                "coverage": plans.coverage(session, unit, plan),
                "completion": plans.completion(session, unit, plan),
            }
            for plan in rows
        ]
    }


@router.get("/units/{unit_code}/plan/{code}", summary="Un plan con su alcance y su historial")
def detail(
    unit_code: str,
    code: str,
    session: SessionDep,
    _: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    plan = _plan(session, unit, code)
    expansion = plans.expand(session, unit, plan)
    return {
        **_as_dict(plan),
        "coverage": plans.coverage(session, unit, plan),
        "completion": plans.completion(session, unit, plan),
        "targets": [
            {
                "asset_code": row.asset_code,
                "asset_type_key": row.asset_type_key,
                "feeder_code": row.feeder_code,
                "zone": row.zone,
                "sort_order": row.sort_order,
            }
            for row in plans.targets_of(session, plan)
        ],
        "expanded": [
            {"asset_code": item[0], "asset_type_key": item[1], "feeder_code": item[2]}
            for item in expansion.assets
        ],
        "caveats": expansion.caveats,
        "note": expansion.note,
        "history": [issue.as_dict() for issue in plans.history(session, plan)],
    }


@router.put(
    "/units/{unit_code}/plan/{code}",
    dependencies=[Depends(require_roles(*WRITERS))],
    summary="Crear o reemplazar un plan (RF-012)",
)
def save(
    unit_code: str,
    code: str,
    payload: PlanIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*WRITERS))] = None,
) -> dict[str, Any]:
    """Todo se valida aquí y no al disparar: un plan lo escribe una persona que está presente."""
    unit = _unit(session, unit_code)
    try:
        plan = plans.save_plan(
            session,
            unit,
            code=code,
            name=payload.name,
            work_type=payload.work_type,
            form_code=payload.form_code,
            cadence=payload.cadence.value,
            scope=payload.scope.value,
            actor=principal.subject,
            priority=payload.priority.value,
            asset_type_key=payload.asset_type_key,
            cadence_days=payload.cadence_days,
            day_of_month=payload.day_of_month,
            scope_value=payload.scope_value,
            skip_if_attended_within_days=payload.skip_if_attended_within_days,
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            description=payload.description,
            targets=[target.model_dump() for target in payload.targets]
            if payload.targets is not None
            else None,
            active=payload.active,
        )
    except plans.PlanError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return _as_dict(plan)


@router.post(
    "/units/{unit_code}/plan/{code}/run",
    dependencies=[Depends(require_roles(*WRITERS))],
    summary="Disparar el plan para un periodo (RF-012)",
)
def run(
    unit_code: str,
    code: str,
    payload: RunIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*WRITERS))] = None,
) -> dict[str, Any]:
    """Idempotente por periodo: volver a dispararlo informa lo ya emitido y no crea nada."""
    unit = _unit(session, unit_code)
    plan = _plan(session, unit, code)
    result = plans.run_plan(
        session, unit, plan, on=payload.on or date.today(), actor=principal.subject
    )
    session.commit()
    return result.as_dict()


@router.post(
    "/units/{unit_code}/run-due",
    dependencies=[Depends(require_roles(*WRITERS))],
    summary="Disparar todos los planes vencidos de la unidad (RF-012)",
)
def run_due(
    unit_code: str,
    payload: RunIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*WRITERS))] = None,
) -> dict[str, Any]:
    """Lo mismo que hace el job nocturno. Los planes que no vencían hoy vuelven contados."""
    unit = _unit(session, unit_code)
    report = plans.run_due(session, unit, on=payload.on, actor=principal.subject)
    session.commit()
    return report.as_dict()
