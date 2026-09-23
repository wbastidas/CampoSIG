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

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.analytics import ai_dashboard, apg, interruptions, operations
from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.review import blind

# `unit_scope` at the door for every board here (ADR-009). The roles differ per board, so each one
# declares its own: the AI dashboard is the ML analyst's and the supervisor's, and the operational
# board is the supervisor's and the planner's.
router = APIRouter(
    prefix="/api/v1/analytics", tags=["analytics"], dependencies=[Depends(unit_scope)]
)

SessionDep = Annotated[Session, Depends(get_session)]


def _unit(session: Session, code: str):  # type: ignore[no-untyped-def]
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _period_or_422(since: datetime | None, until: datetime | None) -> None:
    """A backwards period is refused rather than answered with an empty board.

    An empty board reads as «no hubo trabajo», which is the opposite of «preguntaste mal».
    """
    if since is not None and until is not None and since > until:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "el inicio del periodo es posterior a su fin",
        )


@router.get(
    "/units/{unit_code}/ai-dashboard",
    dependencies=[Depends(require_roles(Role.ML_ANALYST, Role.SUPERVISOR))],
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
    unit = _unit(session, unit_code)
    _period_or_422(since, until)

    body = ai_dashboard.build(session, unit.id, since=since, until=until).as_dict()
    # RF-111a's acceptance criterion is literal: «el tablero RF-134 muestra el kappa
    # supervisor-agente calculado sobre la muestra ciega». Here it is, in the dashboard, computed
    # over the blind sample and nothing else.
    body["agreement"] = blind.agreement(session, unit.id).as_dict()
    return body


@router.get(
    "/units/{unit_code}/operations",
    summary="Tablero operativo: OT por estado, SLA, productividad por cuadrilla y tiempos",
    dependencies=[Depends(require_roles(Role.SUPERVISOR, Role.PLANNER))],
)
def operational(
    unit_code: str,
    session: SessionDep,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    """RF-130, computed live on every call.

    Live and not cached: the acceptance criterion is that the data is no more than five minutes
    old, and the way to guarantee that is for the screen to ask again every five minutes. A cache
    would add an invalidation bug in exchange for a query a supervisor makes twelve times an hour.
    `computed_at` travels so the screen can say how fresh the number on it is.
    """
    unit = _unit(session, unit_code)
    _period_or_422(since, until)
    return operations.build(session, unit.id, since=since, until=until).as_dict()


#: How far back the APG board looks when nobody says. A month: the regulator reports monthly, and a
#: shorter window over a small operation has too few attentions to report a percentage at all.
APG_DEFAULT_DAYS = 30


def _apg_period(since: datetime | None, until: datetime | None) -> tuple[datetime, datetime]:
    _period_or_422(since, until)
    end = until or datetime.now(UTC)
    return since or (end - timedelta(days=APG_DEFAULT_DAYS)), end


@router.get(
    "/units/{unit_code}/apg",
    summary="Tablero de alumbrado público: reposición contra el plazo regulatorio, fallas y flota",
    dependencies=[Depends(require_roles(Role.SUPERVISOR, Role.PLANNER))],
)
def apg_board(
    unit_code: str,
    session: SessionDep,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    """RF-131. The deadline comes from `regulatory_parameter`, never from this code (ADR-007).

    Which means the board asks the same rule the approval gate asks, and re-running it over a March
    period reproduces March's deadline: the parameter carries its own period of force.
    """
    unit = _unit(session, unit_code)
    start, end = _apg_period(since, until)
    return apg.build(session, unit.id, since=start, until=end).as_dict()


@router.get(
    "/units/{unit_code}/apg.csv",
    summary="Incumplimientos de plazo de APG, exportables a Excel o CSV (RF-131)",
    dependencies=[Depends(require_roles(Role.SUPERVISOR, Role.PLANNER))],
    response_class=PlainTextResponse,
)
def apg_csv(
    unit_code: str,
    session: SessionDep,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
) -> PlainTextResponse:
    """The breach list as a file the area can open and work on.

    Text and not a spreadsheet library: a CSV with semicolons, comma decimals and a byte-order mark
    opens correctly in the Excel this area actually has, and it costs no dependency. `charset=utf-8`
    with the mark, because the one without it turns «Tecnología» into mojibake on a Windows default.
    """
    unit = _unit(session, unit_code)
    start, end = _apg_period(since, until)
    board = apg.build(session, unit.id, since=start, until=end)
    stamp = board.computed_at.strftime("%Y%m%d")
    return PlainTextResponse(
        apg.as_csv(board),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="apg-incumplimientos-{stamp}.csv"',
        },
    )


@router.get(
    "/units/{unit_code}/interruptions",
    summary="Base de interrupciones para el cálculo de FMIK y TTIK (RF-132)",
    dependencies=[Depends(require_roles(Role.SUPERVISOR, Role.PLANNER))],
)
def interruption_base(
    unit_code: str,
    session: SessionDep,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    """The base and the two numerators — never the indices themselves.

    FMIK and TTIK divide by the unit's installed kVA, which lives in the corporate systems and not
    here. Publishing an index against a denominator this platform had guessed would be publishing a
    number the utility then has to defend before the regulator.
    """
    unit = _unit(session, unit_code)
    start, end = _apg_period(since, until)
    return interruptions.collect(session, unit.id, since=start, until=end).as_dict()


@router.get(
    "/units/{unit_code}/interruptions.csv",
    summary="Exportar la base de interrupciones en un formato configurable (RF-132)",
    dependencies=[Depends(require_roles(Role.SUPERVISOR, Role.PLANNER))],
    response_class=PlainTextResponse,
)
def interruption_export(
    unit_code: str,
    session: SessionDep,
    layout: Annotated[str, Query(alias="format")] = "arcernnr-002-20",
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
) -> PlainTextResponse:
    """The export, in the layout the caller names.

    An unknown layout is a 404 and never a silent fallback to the default: an export that quietly
    used another format would produce a file the regulator rejects for reasons nobody can trace.
    """
    unit = _unit(session, unit_code)
    start, end = _apg_period(since, until)
    try:
        chosen = interruptions.load_format(layout)
    except interruptions.UnknownFormatError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    base = interruptions.collect(session, unit.id, since=start, until=end)
    stamp = end.strftime("%Y%m%d")
    return PlainTextResponse(
        interruptions.render(base, chosen),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="interrupciones-{chosen.code}-{stamp}.csv"'
            )
        },
    )
