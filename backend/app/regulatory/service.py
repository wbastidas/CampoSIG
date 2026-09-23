"""Reading and versioning regulatory parameters (SRS 1.4, ADR-007).

The one query every rule runs is "what was the limit for this code on this date", and it has
to be answerable for a date in the past: a supervisor's approval from March must stay
explicable against March's limit, not against today's.

So :func:`set_parameter` never overwrites. A new resolution closes the previous row on the
day before the new one starts, and :func:`value_in_force` picks the row that covers the date
it is asked about. Overlaps are refused rather than resolved by picking one, because two
limits in force on the same day means somebody imported a resolution wrong and guessing
would bury that.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.regulatory.models import RegulatoryParameter, RegulatoryRevision, RevisionAction

#: Who a change is attributed to when nothing said. Used by the seed loader run from a console,
#: where there is no token; never by an HTTP request, which always has a subject.
SYSTEM_ACTOR = "carga.semilla"

#: The fields whose change is worth recording. Deliberately not `id`, `created_at` or the
#: verification timestamp: the first two never move and the third travels with `verified_by`.
TRACKED_FIELDS = (
    "value",
    "unit",
    "description",
    "norm_ref",
    "article_ref",
    "source_url",
    "effective_from",
    "effective_to",
    "verified_by",
    "strict",
)


def _plain(value: Any) -> Any:
    """A field as JSON can hold it, so a revision row stays readable years later."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _snapshot(row: RegulatoryParameter) -> dict[str, Any]:
    """The row as a revision records it.

    The value is unwrapped: it is stored as ``{"v": 24}`` so JSONB querying is uniform, and a
    revision that showed a person «de {"v": 24} a {"v": 30}» would be making them read the storage
    shape to find the figure.
    """
    snapshot = {field: _plain(getattr(row, field)) for field in TRACKED_FIELDS}
    snapshot["value"] = _unwrap(row.value)
    return snapshot


def _diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Only what moved. A revision listing ten unchanged fields hides the one that changed."""
    return {
        field: {"from": before.get(field), "to": after.get(field)}
        for field in TRACKED_FIELDS
        if before.get(field) != after.get(field)
    }


def _revise(
    session: Session,
    row: RegulatoryParameter,
    *,
    action: str,
    actor: str,
    changed: dict[str, Any],
    note: str | None,
) -> RegulatoryRevision:
    """Append one revision. The only function that writes to the revision log."""
    revision = RegulatoryRevision(
        parameter_id=row.id,
        code=row.code,
        action=action,
        actor=actor,
        changed=changed,
        note=note,
    )
    session.add(revision)
    session.flush()
    return revision


def revisions(session: Session, code: str) -> list[RegulatoryRevision]:
    """Every edit to a code, oldest first — because the answer is a story."""
    return list(
        session.scalars(
            select(RegulatoryRevision)
            .where(RegulatoryRevision.code == code)
            .order_by(RegulatoryRevision.sequence)
        )
    )


def verify_parameter(
    session: Session,
    code: str,
    *,
    effective_from: date,
    actor: str,
    note: str | None = None,
) -> RegulatoryParameter:
    """Record that a person read the official text and this value matches it (ADR-007).

    Separate from :func:`set_parameter` on purpose. Loading a figure and certifying it are two
    different acts, and folding them together is how a bulk import ends up marking seven values
    verified because one flag was set.

    :raises UnknownParameterError: when there is no period of that code starting on that date.
    """
    row = session.scalars(
        select(RegulatoryParameter).where(
            RegulatoryParameter.code == code,
            RegulatoryParameter.effective_from == effective_from,
        )
    ).first()
    if row is None:
        raise UnknownParameterError(
            f"el parámetro '{code}' no tiene un período que empiece el {effective_from}"
        )
    before = _snapshot(row)
    row.verified_by = actor
    row.verified_at = datetime.now(UTC)
    row.updated_by = actor
    session.flush()
    _revise(
        session,
        row,
        action=RevisionAction.VERIFIED,
        actor=actor,
        changed=_diff(before, _snapshot(row)),
        note=note,
    )
    return row


class UnknownParameterError(Exception):
    """Raised when no parameter with that code was in force on that date."""


class OverlappingPeriodError(Exception):
    """Raised when a new period would overlap an existing one for the same code."""


class UnverifiedParameterError(Exception):
    """Raised when a strict parameter has not been verified against the official text."""


def set_parameter(
    session: Session,
    *,
    code: str,
    value: Any,
    norm_ref: str,
    effective_from: date,
    unit: str | None = None,
    description: str | None = None,
    article_ref: str | None = None,
    source_url: str | None = None,
    effective_to: date | None = None,
    verified_by: str | None = None,
    strict: bool = False,
    actor: str = SYSTEM_ACTOR,
    note: str | None = None,
) -> RegulatoryParameter:
    """Record a regulatory value, closing the previous one instead of replacing it.

    Re-importing the same code and start date updates that row — a resolution can be
    corrected — but a *different* start date opens a new period and closes the open one.

    :raises OverlappingPeriodError: if the new period would overlap an existing closed one.
    """
    existing_periods = list(
        session.scalars(
            select(RegulatoryParameter)
            .where(RegulatoryParameter.code == code)
            .order_by(RegulatoryParameter.effective_from)
        )
    )

    same_start = next(
        (row for row in existing_periods if row.effective_from == effective_from), None
    )
    if same_start is not None:
        before = _snapshot(same_start)
        same_start.value = _wrap(value)
        same_start.unit = unit
        same_start.description = description
        same_start.norm_ref = norm_ref
        same_start.article_ref = article_ref
        same_start.source_url = source_url
        same_start.effective_to = effective_to
        same_start.strict = strict
        same_start.updated_by = actor
        if verified_by:
            same_start.verified_by = verified_by
            same_start.verified_at = datetime.now(UTC)
        session.flush()
        _revise(
            session,
            same_start,
            action=RevisionAction.CORRECTED,
            actor=actor,
            changed=_diff(before, _snapshot(same_start)),
            note=note,
        )
        return same_start

    for row in existing_periods:
        if row.effective_to is not None and row.effective_to >= effective_from:
            raise OverlappingPeriodError(
                f"el parámetro '{code}' ya tiene un período que cubre {effective_from} "
                f"({row.effective_from} a {row.effective_to}); revisar la importación"
            )
        if row.effective_to is None:
            if row.effective_from >= effective_from:
                raise OverlappingPeriodError(
                    f"el parámetro '{code}' tiene un período abierto que empieza en "
                    f"{row.effective_from}, posterior o igual a {effective_from}"
                )
            # The open period ends the day before the new one starts.
            row.effective_to = effective_from - timedelta(days=1)
            row.updated_by = actor
            session.flush()
            _revise(
                session,
                row,
                action=RevisionAction.CLOSED,
                actor=actor,
                changed={"effective_to": {"from": None, "to": row.effective_to.isoformat()}},
                note=f"cerrado porque se abre el período que empieza el {effective_from}",
            )

    created = RegulatoryParameter(
        code=code,
        value=_wrap(value),
        unit=unit,
        description=description,
        norm_ref=norm_ref,
        article_ref=article_ref,
        source_url=source_url,
        effective_from=effective_from,
        effective_to=effective_to,
        verified_by=verified_by,
        verified_at=datetime.now(UTC) if verified_by else None,
        strict=strict,
        created_by=actor,
        updated_by=actor,
    )
    session.add(created)
    session.flush()
    _revise(session, created, action=RevisionAction.CREATED, actor=actor, changed={}, note=note)
    return created


def parameter_in_force(
    session: Session, code: str, *, on: date | None = None
) -> RegulatoryParameter:
    """The parameter row that governs ``code`` on a date.

    :raises UnknownParameterError: when nothing covers that date. Deliberately an error and
        not a default: a rule with no limit must not silently pass everything.
    """
    moment = on or date.today()
    rows = list(
        session.scalars(select(RegulatoryParameter).where(RegulatoryParameter.code == code))
    )
    covering = [row for row in rows if row.in_force_on(moment)]
    if not covering:
        known = ", ".join(sorted({row.code for row in rows})) or "ninguno"
        raise UnknownParameterError(
            f"no hay un valor de '{code}' vigente el {moment}; períodos registrados: {known}"
        )
    if len(covering) > 1:
        raise OverlappingPeriodError(
            f"'{code}' tiene {len(covering)} valores vigentes el {moment}; "
            "hay una importación mal cerrada"
        )
    row = covering[0]
    if row.strict and not row.is_verified:
        raise UnverifiedParameterError(
            f"'{code}' es un límite de consecuencia legal y no está verificado contra el "
            f"texto de la norma ({row.norm_ref}); no se evalúa hasta que alguien lo verifique"
        )
    return row


def value_in_force(session: Session, code: str, *, on: date | None = None) -> Any:
    """Just the value, unwrapped. For rules that do not need the citation."""
    return _unwrap(parameter_in_force(session, code, on=on).value)


def history(session: Session, code: str) -> list[RegulatoryParameter]:
    """Every period recorded for a code, oldest first. What makes an old decision explicable."""
    return list(
        session.scalars(
            select(RegulatoryParameter)
            .where(RegulatoryParameter.code == code)
            .order_by(RegulatoryParameter.effective_from)
        )
    )


def known_codes(session: Session) -> list[str]:
    return sorted({row.code for row in session.scalars(select(RegulatoryParameter))})


def _wrap(value: Any) -> dict[str, Any]:
    """Store every value as an object, so JSONB querying is uniform.

    A bare scalar in JSONB is legal and awkward: every query has to know whether the column
    holds a number or an object. One shape costs nothing and removes that question.
    """
    if isinstance(value, dict):
        return value
    return {"v": value}


def _unwrap(stored: dict[str, Any]) -> Any:
    if set(stored) == {"v"}:
        return stored["v"]
    return stored
