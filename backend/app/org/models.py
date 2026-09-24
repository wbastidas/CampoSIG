"""Organisational hierarchy: headquarters and business units.

The utility is national: one holding company (the *matriz*) with several business units,
each operating its own distribution network and its own ArcSDE geodatabase.

The split that makes this tractable comes straight from the source material. The data
model is **national** — identical classes, fields and relationships in every business
unit — while three domains (`Codigo Alimentador`, `Numero Estacion`, `Subestacion`) hold
each unit's own physical network and therefore differ. So:

* a **data-model profile** describes the schema and is normally *shared* by every unit;
* a **metadata snapshot** carries the actual domain contents and is *per unit*;
* an **arcpy agent** talks to one unit's geodatabase and is *per unit*.

A field device belongs to exactly one business unit. That is what lets the platform route
what it captures to the right geodatabase without the device knowing any of this exists.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


class Organization(Base):
    """The holding company. One row in practice, but modelled explicitly.

    Having it as a row rather than a constant means reports, catalogues and regulatory
    parameters can hang off it, and a future merger does not become a migration.
    """

    __tablename__ = "organization"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="EC")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    business_units: Mapped[list[BusinessUnit]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class BusinessUnit(Base):
    """One business unit: its own network, its own geodatabase, its own agent.

    `profile_id` is usually the same across units, because the schema is national. What
    differs is the metadata snapshot, which is why snapshots are keyed by unit.
    """

    __tablename__ = "business_unit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    #: Which data-model profile this unit's geodatabase follows. Shared by default.
    profile_id: Mapped[str] = mapped_column(String(64), nullable=False)

    #: Spatial reference of this unit's geodatabase. Usually the same nationally, but a
    #: unit in another UTM zone is entirely possible, so it is not assumed.
    spatial_reference: Mapped[int] = mapped_column(nullable=False, default=32717)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    organization: Mapped[Organization] = relationship(back_populates="business_units")
    agents: Mapped[list[AgentRegistration]] = relationship(
        back_populates="business_unit", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_business_unit_code"),
        Index("ix_business_unit_active", "active"),
    )


class AgentRegistration(Base):
    """An arcpy agent authorised to act for one business unit (ADR-008).

    Registration is per unit and explicit. An agent can only ever see and report on
    batches for its own unit, which is how the platform keeps one unit's field data out
    of another unit's geodatabase — a routing rule and a security boundary at once.
    """

    __tablename__ = "agent_registration"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    #: Stable identifier the agent presents, e.g. the machine name.
    agent_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    business_unit: Mapped[BusinessUnit] = relationship(back_populates="agents")

    __table_args__ = (Index("ix_agent_registration_unit", "business_unit_id"),)
