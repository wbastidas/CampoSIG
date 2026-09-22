"""Who is calling (RF-001, RF-002).

Until this module existed, every identity in the platform was **self-asserted**: the reviewer's
username arrived in the body of the request that recorded their approval, and the person who
confirmed an AI value was whoever the caller said it was. That makes the entire audit trail
fiction — a supervisor's approval is only worth the claim that it was the supervisor.

A :class:`Principal` is built from a verified token and nothing else. The request body can no
longer name a person, which is the point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Role(StrEnum):
    """Realm roles, mirroring ``infra/keycloak/sigec-realm.json``.

    Named here so the code asks for a role rather than a string literal, and so a role that
    the realm does not define fails at import rather than at three in the morning.
    """

    TECHNICIAN = "tecnico"
    CREW_LEADER = "jefe_cuadrilla"
    INSPECTOR = "inspector"
    SUPERVISOR = "supervisor"
    PLANNER = "planificador"
    GIS_EDITOR = "editor_gis"
    ML_ANALYST = "analista_ml"
    FUNCTIONAL_ADMIN = "admin_funcional"
    IT_ADMIN = "admin_ti"
    AUDITOR = "auditor"
    #: The arcpy agent's service account (ADR-008).
    GIS_AGENT = "agente_gis"


@dataclass(frozen=True)
class Principal:
    """An authenticated caller."""

    #: The token's subject. This is what gets written to `reviewer_sub`, `confirmed_by` and
    #: every other identity column — never anything the caller typed.
    subject: str
    username: str | None = None
    display_name: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    #: Business-unit codes this person may act in, from the token. Empty means "every unit",
    #: which only the corporate administrators get.
    business_units: frozenset[str] = field(default_factory=frozenset)
    #: The token's `jti`, so one request can be tied to one token in an audit.
    token_id: str | None = None

    def has(self, *roles: Role | str) -> bool:
        return any(str(role) in self.roles for role in roles)

    @property
    def is_corporate(self) -> bool:
        """Whether this person acts across every business unit.

        Two ways in, and both are explicit: a corporate role, or a token with no unit claim at
        all. The second is deliberate for administrators, whose accounts are not tied to one
        unit — and it is exactly why `may_act_in` is a method and not an `in` check scattered
        through the endpoints.
        """
        return (
            self.has(Role.IT_ADMIN, Role.FUNCTIONAL_ADMIN, Role.AUDITOR) or not self.business_units
        )

    def may_act_in(self, unit_code: str) -> bool:
        """Whether this person may act in a business unit (ADR-009)."""
        return self.is_corporate or unit_code.upper() in {u.upper() for u in self.business_units}

    def describe(self) -> str:
        """For a log line or an error message. Never the raw token."""
        return f"{self.username or self.subject} [{', '.join(sorted(self.roles)) or 'sin roles'}]"
