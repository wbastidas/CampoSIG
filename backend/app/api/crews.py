"""Crew administration (RF-005, M01).

Read for planners, supervisors and dispatchers — they assign and dispatch against this roster
every day — and write for the functional administrator alone, the same split `zones.py` uses for
its own administrative records: a boundary or a crew roster is an administrative act, not a
planning convenience.

Create and edit share one endpoint (`PUT .../{code}`), as they do in `zones.py`: the form that
fills it in cannot tell which case it is in without asking the server first, and asking first just
to ask again is the request this collapses into one.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit.service import as_dict as audit_as_dict
from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.auth.scope import may_see_crew
from app.infra.database import get_session
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.workorders.service import (
    UnknownCrewError,
    as_crew_dict,
    crew_history,
    get_crew_by_code,
    list_crews,
    save_crew,
    set_crew_active,
)

router = APIRouter(prefix="/api/v1/crews", tags=["crews"], dependencies=[Depends(unit_scope)])

SessionDep = Annotated[Session, Depends(get_session)]

#: Who may look. The same audience that already reads the workload board and the dispatch map.
READERS = (Role.PLANNER, Role.SUPERVISOR, Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN)

#: Who may create, edit or deactivate a crew. One role, deliberately (see the module docstring).
EDITORS = (Role.FUNCTIONAL_ADMIN,)


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _crew(session: Session, unit: BusinessUnit, code: str, principal: Any) -> Any:
    """The crew by code, or 404 — also outside the principal's ámbito (RF-002)."""
    try:
        crew = get_crew_by_code(session, unit, code)
    except UnknownCrewError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    if not may_see_crew(principal, crew):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"la cuadrilla «{code}» no existe en esta unidad de negocio"
        )
    return crew


class CrewIn(BaseModel):
    """One crew's roster, as the administration screen edits it."""

    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    leader_name: str | None = Field(default=None, max_length=255)
    vehicle: str | None = Field(default=None, max_length=64)
    competencies: list[str] = Field(default_factory=list)
    members: list[str] = Field(default_factory=list)
    zone: str | None = Field(default=None, max_length=64)
    # No `created_by`/`updated_by`: the author is whoever the token says they are.


class ActiveIn(BaseModel):
    active: bool


@router.get("/units/{unit_code}", summary="Las cuadrillas de la unidad (RF-005)")
def index(
    unit_code: str,
    session: SessionDep,
    include_inactive: Annotated[bool, Query()] = False,
    principal: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> list[dict[str, Any]]:
    unit = _unit(session, unit_code)
    rows = list_crews(session, unit, include_inactive=include_inactive, principal=principal)
    return [as_crew_dict(crew) for crew in rows]


@router.put(
    "/units/{unit_code}/{code}",
    dependencies=[Depends(require_roles(*EDITORS))],
    summary="Crear o editar una cuadrilla (RF-005)",
)
def save(
    unit_code: str,
    code: str,
    payload: CrewIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*EDITORS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    if payload.code != code:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"el código de la ruta («{code}») y el del cuerpo («{payload.code}») no coinciden",
        )
    crew = save_crew(
        session,
        unit,
        code=code,
        name=payload.name,
        leader_name=payload.leader_name,
        vehicle=payload.vehicle,
        competencies=payload.competencies,
        members=payload.members,
        zone=payload.zone,
        actor=principal.subject,
    )
    session.commit()
    return as_crew_dict(crew)


@router.post(
    "/units/{unit_code}/{code}/active",
    dependencies=[Depends(require_roles(*EDITORS))],
    summary="Desactivar o reactivar una cuadrilla (RF-005)",
)
def set_active(
    unit_code: str,
    code: str,
    payload: ActiveIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*EDITORS))] = None,
) -> dict[str, Any]:
    """Deactivated, never deleted: a crew that carried a year of closed work orders is part of
    their history (the same reasoning the zone administration screen already relies on)."""
    unit = _unit(session, unit_code)
    crew = _crew(session, unit, code, principal)
    crew = set_crew_active(session, unit, crew, active=payload.active, actor=principal.subject)
    session.commit()
    return as_crew_dict(crew)


@router.get(
    "/units/{unit_code}/{code}/history",
    dependencies=[Depends(require_roles(*READERS))],
    summary="Historial de cambios de una cuadrilla (RF-005)",
)
def history(
    unit_code: str,
    code: str,
    session: SessionDep,
    principal: Annotated[Any, Depends(unit_scope)] = None,
) -> list[dict[str, Any]]:
    unit = _unit(session, unit_code)
    crew = _crew(session, unit, code, principal)
    return [audit_as_dict(event) for event in crew_history(session, unit, crew)]


__all__ = ["router"]
