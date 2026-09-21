"""Resolve the data-model context of a business unit (multi-tenant).

Everything that used to read a single ``SIGEC_PROFILE`` setting now asks here instead, with
a business unit in hand. That setting survives only as the default for single-unit
development.

The invariant this module exists to protect: **nothing crosses between business units.**
A resolver, a metadata snapshot, a batch and an agent all belong to exactly one unit, and
asking for one unit's context can never hand back another's.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model_profile.metadata import GisMetadata
from app.model_profile.profile import load_profile
from app.model_profile.resolver import ModelResolver
from app.org.models import AgentRegistration, BusinessUnit


class UnknownBusinessUnitError(Exception):
    """Raised when a business unit code or id does not exist, or is inactive."""


class AgentNotAuthorisedError(Exception):
    """Raised when an agent key is unknown, inactive, or acting outside its unit."""


def get_business_unit(session: Session, unit_id: uuid.UUID) -> BusinessUnit:
    unit = session.get(BusinessUnit, unit_id)
    if unit is None or not unit.active:
        raise UnknownBusinessUnitError(f"unidad de negocio '{unit_id}' no existe o está inactiva")
    return unit


def get_business_unit_by_code(session: Session, code: str) -> BusinessUnit:
    unit = session.scalars(
        select(BusinessUnit).where(BusinessUnit.code == code, BusinessUnit.active.is_(True))
    ).first()
    if unit is None:
        raise UnknownBusinessUnitError(f"unidad de negocio '{code}' no existe o está inactiva")
    return unit


def resolve_agent(session: Session, agent_key: str) -> AgentRegistration:
    """Authorise an agent and return its registration.

    The agent's business unit comes from this registration, never from the payload it
    posts. An agent cannot claim to be acting for a different unit, because it is never
    asked.
    """
    agent = session.scalars(
        select(AgentRegistration).where(AgentRegistration.agent_key == agent_key)
    ).first()
    if agent is None or not agent.active:
        raise AgentNotAuthorisedError(f"el agente '{agent_key}' no está registrado o está inactivo")
    if not agent.business_unit.active:
        raise AgentNotAuthorisedError(
            f"la unidad de negocio del agente '{agent_key}' está inactiva"
        )
    return agent


def resolver_for_unit(unit: BusinessUnit) -> ModelResolver:
    """The model resolver for a unit, built from the profile the unit declares.

    Several units normally share one profile: the schema is national. What differs between
    them is the metadata snapshot, which is why snapshots are keyed by unit and resolvers
    are not cached across them.
    """
    return ModelResolver(load_profile(unit.profile_id))


def metadata_for_unit(session: Session, unit: BusinessUnit) -> GisMetadata | None:
    """The current metadata snapshot for a unit, or None before its first agent run."""
    # Imported here to keep the org layer from depending on the gateway at module level.
    from app.gis_gateway.ingest import current_snapshot

    snapshot = current_snapshot(session, unit.id)
    return GisMetadata.model_validate(snapshot.payload) if snapshot else None


def context_for_unit(
    session: Session, unit: BusinessUnit
) -> tuple[ModelResolver, GisMetadata | None]:
    """Everything the form generator needs for one business unit."""
    return resolver_for_unit(unit), metadata_for_unit(session, unit)


def active_units(session: Session) -> list[BusinessUnit]:
    return list(
        session.scalars(
            select(BusinessUnit).where(BusinessUnit.active.is_(True)).order_by(BusinessUnit.code)
        )
    )
