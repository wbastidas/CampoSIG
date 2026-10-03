"""Traceability queries over the audit trail (RF-161).

Read-only, and that is the point rather than an omission: RF-160's acceptance criterion is that no
endpoint edits or deletes the trail, so this router has GETs and nothing else. A structural test
walks the module's syntax tree and fails if a POST, PUT, PATCH or DELETE ever appears here.

For the auditor, and for IT administration because somebody has to be able to answer «did this
platform lose an event» during an incident. Not for the supervisor: a trail is not a management
report, and the four questions it answers — by work order, by asset, by person, by device — are the
questions of an investigation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code

router = APIRouter(
    prefix="/api/v1/audit",
    tags=["audit"],
    dependencies=[
        Depends(unit_scope),
        Depends(require_roles(Role.AUDITOR, Role.IT_ADMIN)),
    ],
)

SessionDep = Annotated[Session, Depends(get_session)]


def _unit_id(session: Session, code: str) -> uuid.UUID:
    try:
        return get_business_unit_by_code(session, code).id
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get(
    "/units/{unit_code}/trail",
    summary="Trazabilidad por OT, activo, usuario o dispositivo (RF-161)",
)
def trail(
    unit_code: str,
    session: SessionDep,
    work_order_id: Annotated[uuid.UUID | None, Query()] = None,
    asset_code: Annotated[str | None, Query()] = None,
    actor: Annotated[str | None, Query()] = None,
    device_key: Annotated[str | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """The four questions of RF-161, oldest event first.

    Oldest first because the answer to all four is a story, and a story read backwards is a
    different story. Every filter is optional and they compose: «what did this person do to this
    work order» is one call.
    """
    unit_id = _unit_id(session, unit_code)
    events = audit.trail(
        session,
        unit_id,
        work_order_id=work_order_id,
        asset_code=asset_code,
        actor=actor,
        device_key=device_key,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    return {
        "total": audit.count(session, unit_id),
        "events": [audit.as_dict(event) for event in events],
    }


@router.get(
    "/units/{unit_code}/verify",
    summary="Verificar la cadena de hashes de la bitácora (RF-160)",
)
def verify(unit_code: str, session: SessionDep) -> dict[str, Any]:
    """Walk the whole chain and say whether it holds, and where it breaks if it does not.

    Deliberately a plain answer and not a 500 when the chain is broken: a broken chain is a finding
    the auditor has to read and report, not a server error that a monitoring dashboard swallows.
    """
    return audit.verify(session, _unit_id(session, unit_code)).as_dict()
