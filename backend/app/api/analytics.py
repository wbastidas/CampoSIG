"""The AI dashboard endpoint (RF-134, RF-111a).

One call, five panels plus the supervisor-agent agreement. Assembled server-side for the same
reason the review detail is: a screen that makes six calls is a screen where one failure silently
removes a panel, and a metric that vanishes is worse than one that reads badly — nobody notices the
absence.

Restricted to the ML analyst and the supervisor, as RF-134 says. Not because the numbers are
secret: an acceptance rate per technician in the wrong hands stops being a training signal and
becomes a performance file, and the roles are where that line gets drawn.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.analytics import ai_dashboard
from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.review import blind

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["analytics"],
    dependencies=[Depends(unit_scope), Depends(require_roles(Role.ML_ANALYST, Role.SUPERVISOR))],
)

SessionDep = Annotated[Session, Depends(get_session)]


@router.get(
    "/units/{unit_code}/ai-dashboard",
    summary="Tablero de IA: aceptación por campo, correcciones por clase, error de palabras, "
    "adopción de la voz y versiones en la flota",
)
def ai(
    unit_code: str,
    session: SessionDep,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    """RF-134, with the kappa of RF-111a beside it.

    The period is optional and open on both sides. Dated by submission rather than by capture, so a
    week's numbers cover the work the crews did that week and not whenever their phones found
    signal.
    """
    try:
        unit = get_business_unit_by_code(session, unit_code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    if since is not None and until is not None and since > until:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "el inicio del periodo es posterior a su fin",
        )

    body = ai_dashboard.build(session, unit.id, since=since, until=until).as_dict()
    # RF-111a's acceptance criterion is literal: «el tablero RF-134 muestra el kappa
    # supervisor-agente calculado sobre la muestra ciega». Here it is, in the dashboard, computed
    # over the blind sample and nothing else.
    body["agreement"] = blind.agreement(session, unit.id).as_dict()
    return body
