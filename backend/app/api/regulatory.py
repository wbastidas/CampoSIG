"""Regulatory parameter endpoints (SRS 1.4, ADR-007).

An administration surface, not a business one: what limits are loaded, since when, from which
norm, and — the field that matters most — which of them nobody has verified against the
official text yet. That list is what a deployment checklist has to be empty of.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal, require_roles
from app.auth.principal import Role
from app.infra.database import get_session
from app.regulatory.loader import unverified_codes
from app.regulatory.rules import REQUIRED_PARAMETER_CODES
from app.regulatory.service import (
    OverlappingPeriodError,
    UnknownParameterError,
    UnverifiedParameterError,
    history,
    known_codes,
    parameter_in_force,
    revisions,
    set_parameter,
    verify_parameter,
)

# Los parámetros regulatorios son nacionales, no de una unidad de negocio, así que aquí no hay
# ámbito por unidad — pero sí hace falta estar autenticado, y escribir un límite es un acto de
# administración funcional: quien lo carga afirma haber leído el texto oficial.
router = APIRouter(
    prefix="/api/v1/regulatory", tags=["regulatory"], dependencies=[Depends(current_principal)]
)

SessionDep = Annotated[Session, Depends(get_session)]


def _as_dict(row: Any) -> dict[str, Any]:
    return {
        "code": row.code,
        "value": row.value,
        "unit": row.unit,
        "description": row.description,
        "norm_ref": row.norm_ref,
        "article_ref": row.article_ref,
        "source_url": row.source_url,
        "effective_from": row.effective_from.isoformat(),
        "effective_to": row.effective_to.isoformat() if row.effective_to else None,
        "verified": row.is_verified,
        "verified_by": row.verified_by,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
        "strict": row.strict,
        # RF-150's «usuario que modificó». Kept apart from `verified_by`: loading a figure and
        # certifying it against the official text are different claims.
        "created_by": row.created_by,
        "updated_by": row.updated_by,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/parameters")
def list_parameters(session: SessionDep) -> dict[str, Any]:
    """What is loaded, what the rules need, and what nobody has verified."""
    loaded = known_codes(session)
    missing = [
        code
        for code in REQUIRED_PARAMETER_CODES
        if not any(existing == code or existing.startswith(f"{code}.") for existing in loaded)
    ]
    return {
        "loaded": loaded,
        "required_by_rules": list(REQUIRED_PARAMETER_CODES),
        # A rule with no parameter reports that it cannot judge; it never passes silently.
        # Surfacing the gap here is how it gets closed before the pilot.
        "missing": missing,
        "unverified": unverified_codes(session),
    }


@router.get("/parameters/{code}")
def parameter_history(session: SessionDep, code: str) -> list[dict[str, Any]]:
    """Every period recorded for a code — what makes an old approval explicable."""
    rows = history(session, code)
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no hay parámetros con el código '{code}'")
    return [_as_dict(row) for row in rows]


@router.get("/parameters/{code}/in-force")
def parameter_on_date(
    session: SessionDep,
    code: str,
    on: Annotated[date | None, Query()] = None,
) -> dict[str, Any]:
    """The value that governed a code on a date."""
    try:
        return _as_dict(parameter_in_force(session, code, on=on))
    except UnknownParameterError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except UnverifiedParameterError as exc:
        # 409, not 404: the value exists and is deliberately not usable yet.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


class ParameterIn(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    value: Any
    norm_ref: str = Field(min_length=1, max_length=255)
    effective_from: date
    unit: str | None = None
    description: str | None = None
    article_ref: str | None = None
    source_url: str | None = None
    effective_to: date | None = None
    strict: bool = False
    #: Why this row was written or corrected, for whoever reads the revision in a year.
    note: str | None = Field(default=None, max_length=2000)
    # No `verified_by`: a verification the caller could type is a verification nobody made. It is
    # its own endpoint below, and the person who read the official text is whoever the token says
    # they are. The seed loader still passes a name because it runs at a console with no token —
    # and it only certifies the entries the file itself marks verified.


@router.post(
    "/parameters",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN))],
)
def upsert_parameter(
    session: SessionDep,
    payload: ParameterIn,
    principal: Annotated[Any, Depends(current_principal)] = None,
) -> dict[str, Any]:
    """Record a regulatory value, closing the previous period rather than replacing it."""
    try:
        row = set_parameter(
            session,
            code=payload.code,
            value=payload.value,
            norm_ref=payload.norm_ref,
            effective_from=payload.effective_from,
            unit=payload.unit,
            description=payload.description,
            article_ref=payload.article_ref,
            source_url=payload.source_url,
            effective_to=payload.effective_to,
            strict=payload.strict,
            actor=principal.subject,
            note=payload.note,
        )
    except OverlappingPeriodError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    session.commit()
    return _as_dict(row)


@router.get(
    "/parameters/{code}/revisions", summary="Quién modificó qué, y desde qué valor (RF-150)"
)
def parameter_revisions(session: SessionDep, code: str) -> list[dict[str, Any]]:
    """The history of the *edits*, next to the history of the values the periods already hold.

    Oldest first: the answer is a story, and a story read backwards is a different story.
    """
    return [
        {
            "at": row.at.isoformat(),
            "action": row.action,
            "actor": row.actor,
            "changed": row.changed,
            "note": row.note,
        }
        for row in revisions(session, code)
    ]


class VerifyIn(BaseModel):
    """Which period is being certified. No `verified_by`: that is the token's subject."""

    effective_from: date
    note: str | None = Field(default=None, max_length=2000)


@router.post(
    "/parameters/{code}/verify",
    dependencies=[Depends(require_roles(Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN))],
    summary="Declarar que se leyó el texto oficial y el valor coincide (ADR-007)",
)
def verify(
    session: SessionDep,
    code: str,
    payload: VerifyIn,
    principal: Annotated[Any, Depends(current_principal)] = None,
) -> dict[str, Any]:
    """Its own endpoint, not a field on the write: loading a figure and certifying it are two acts,
    and folding them together is how a bulk import marks seven values verified for one flag."""
    try:
        row = verify_parameter(
            session,
            code,
            effective_from=payload.effective_from,
            actor=principal.subject,
            note=payload.note,
        )
    except UnknownParameterError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    session.commit()
    return _as_dict(row)
