"""Build compliance facts out of a capture (ADR-007).

The bridge between a form response and the rules. It is deliberately dumb: it reads the
answers by their **canonical** keys, converts what it finds, and leaves absent things absent.
No inference, no filling in from context — a rule that receives a guessed fact produces a
compliance verdict about something nobody measured.

The keys it reads are the ones the form blocks declare, and the form blocks declare which
regulatory parameter each one is judged against. That annotation is checked in the tests, so
an orphan field or an orphan rule shows up as a failure instead of as silence.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.regulatory.rules import Facts
from app.workorders.models import WorkOrder

#: Canonical answer keys the rules consume. One place, so adding a rule shows what it needs.
KEY_CLAIM_AT = "claim_at"
KEY_RESTORED_AT = "restored_at"
KEY_INTERRUPTION_SECONDS = "interruption_seconds"
KEY_EARTH_RESISTANCE = "earth_resistance_ohm"
KEY_GROUNDING_CONTEXT = "grounding_context"


def facts_from(
    order: WorkOrder,
    answers: dict[str, Any] | None,
    *,
    evaluated_on: date | None = None,
) -> Facts:
    """Facts for the rules, read from the work order and the submitted answers.

    :param evaluated_on: the date the limits are read as of. Defaults to the order's own
        capture date rather than today, so re-running the rules on a March order gives
        March's answer — which is the whole reason the parameters are versioned.
    """
    data = answers or {}
    reported = _datetime(data.get(KEY_CLAIM_AT))
    restored = _datetime(data.get(KEY_RESTORED_AT))

    # The date the compliance is judged as of, in decreasing order of what it should be:
    # when the work was restored, when the claim came in, when the order was created.
    reference = (
        evaluated_on
        or (restored.date() if restored else None)
        or (reported.date() if reported else None)
        or (order.created_at.date() if order.created_at else None)
        or datetime.now(UTC).date()
    )

    return Facts(
        reported_at=reported,
        restored_at=restored,
        zone_class=_zone_class(order),
        interruption_seconds=_number(data.get(KEY_INTERRUPTION_SECONDS)),
        earth_resistance_ohm=_number(data.get(KEY_EARTH_RESISTANCE)),
        grounding_context=_text(data.get(KEY_GROUNDING_CONTEXT)),
        evaluated_on=reference,
    )


def _zone_class(order: WorkOrder) -> str | None:
    """The key the restoration deadline may be tabulated by.

    The regulator distinguishes urban from rural service. The platform does not invent that
    classification: it uses the zone the planner assigned, lowercased for lookup, and when
    the order has no zone the rule falls back to the unkeyed limit.
    """
    if not order.zone:
        return None
    return order.zone.strip().lower().replace(" ", "_")


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        # A malformed timestamp is a missing fact, not a zero. Guessing a date here would
        # produce a restoration time measured from nowhere.
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _text(value: Any) -> str | None:
    return value.strip().lower() if isinstance(value, str) and value.strip() else None
