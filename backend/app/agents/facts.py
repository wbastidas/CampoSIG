"""What the pre-review nodes read (RF-171, RF-174).

A plain dataclass rather than a session, on purpose and for two reasons. The nodes stay pure, so
every rule below is testable without a database. And rule 14 — agents read through tools and write
only their report — holds structurally: a node that never receives a session cannot write one.

The cross-order half exists because that is where the value is. Reused evidence inside one work
order is already caught on the review screen; the same photograph appearing in a *different* work
order, or the same GPS reading closing two orders on opposite sides of a parish, is a pattern
nothing looks at today, and it is the one an anomaly agent is for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class PhotoFact:
    evidence_id: str
    stage: str
    content_hash: str
    integrity_verified: bool


@dataclass(frozen=True)
class AiValueFact:
    """An AI-proposed value and what a person did with it."""

    field_key: str
    origin: str
    confidence: float | None
    model_name: str | None
    model_version: str | None
    accepted_unchanged: bool
    confirmed_by: str | None
    transcript: str | None = None


@dataclass(frozen=True)
class RegulatoryFact:
    """A finding the deterministic compliance rules already produced (ADR-007).

    Carried rather than recomputed: the report must agree with the approval gate, and a node that
    evaluated the rules again could disagree with the decision it documents.
    """

    rule: str
    outcome: str
    severity: str
    message: str
    norm_ref: str | None
    article_ref: str | None
    limit_verified: bool


@dataclass(frozen=True)
class OtherOrderFact:
    """The little another work order contributes to a cross-order pattern."""

    work_order_id: str
    code: str | None
    photo_hashes: frozenset[str] = frozenset()
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class PreReviewFacts:
    """Everything the deterministic nodes get. All optional: a capture may be sparse."""

    work_order_id: str
    work_order_code: str | None = None
    asset_code: str | None = None
    #: Where the asset is, from the work order.
    asset_latitude: float | None = None
    asset_longitude: float | None = None
    answers: dict[str, Any] = field(default_factory=dict)
    photos: list[PhotoFact] = field(default_factory=list)
    ai_values: list[AiValueFact] = field(default_factory=list)
    regulatory: list[RegulatoryFact] = field(default_factory=list)
    other_orders: list[OtherOrderFact] = field(default_factory=list)
    #: When the capture reached the server, for "closed too fast" style checks.
    submitted_at: datetime | None = None

    def answer(self, key: str) -> Any:
        return self.answers.get(key)

    def time(self, key: str) -> datetime | None:
        """A time answer, parsed. Unparseable is None — a bad string is the form's problem.

        Not an error: the schema already rejects a malformed date-time on submission, so anything
        odd reaching here is old data, and old data should not stop a report being produced.
        """
        raw = self.answers.get(key)
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    @property
    def capture_latitude(self) -> float | None:
        return _coordinate(self.answers.get("gps"), "latitude")

    @property
    def capture_longitude(self) -> float | None:
        return _coordinate(self.answers.get("gps"), "longitude")

    @property
    def photo_hashes(self) -> list[str]:
        return [photo.content_hash for photo in self.photos]


def _coordinate(gps: Any, key: str) -> float | None:
    if not isinstance(gps, dict):
        return None
    value = gps.get(key)
    return float(value) if isinstance(value, int | float) else None
