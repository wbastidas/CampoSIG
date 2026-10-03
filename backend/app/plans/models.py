"""Preventive maintenance plans (RF-012).

«Crear OT desde planes de mantenimiento preventivo (por activo, frecuencia, ruta o alimentador)»,
and the acceptance is a count: «un plan mensual genera N OT en la fecha programada».

A count is the whole difficulty. A plan that generates one order too many sends a crew to a pole
that is fine; one that generates one too few leaves an inspection undone and the area only finds out
at the audit. So the design is built around **being able to say, afterwards, exactly what a plan
issued and what it refused to issue**, and around making a second run of the same period impossible
rather than merely unlikely:

* Every issued order is recorded in `plan_issue` with the **period** it belongs to, and the
  uniqueness of (plan, asset, period) is a database index. A check in Python is a check a second
  worker — or a planner pressing the button while the nightly job runs — can race.
* The period is a *label*, not a timestamp: `2026-09` for a monthly plan, `2026-T3` for a quarterly
  one. Two runs on the 3rd and the 27th of September belong to the same period and the second issues
  nothing. A `generated_at > cadence` comparison would have made the second run legal.
* `plan_issue` also holds the refusals, with their reason, because a plan that issued 4 of 11 orders
  and said nothing about the other 7 is a plan nobody can trust with the 4.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


class Cadence(StrEnum):
    """How often a plan comes round.

    Calendar names rather than a number of days, because the areas plan in months: «la inspección
    trimestral» is a quarter of the calendar and not 90 days from whenever the last run happened.
    `CUSTOM_DAYS` exists for the plans that really are «cada 45 días», with `cadence_days`.
    """

    MONTHLY = "mensual"
    QUARTERLY = "trimestral"
    SEMIANNUAL = "semestral"
    ANNUAL = "anual"
    CUSTOM_DAYS = "dias"


class PlanScope(StrEnum):
    """Where a plan's assets come from.

    `ASSETS` is the exact one: a list the area typed or imported, and a route is that list in visit
    order. The other two are **expansions over what the platform has seen in the field**, because
    the asset inventory lives in the GIS and not here (ADR-006): what this platform knows about a
    feeder is the assets its own crews have already worked on. That is an approximation, it is
    declared as one in every generation report, and it stops being one when the scheduled
    down-replication of RF-340 lands.
    """

    ASSETS = "activos"
    FEEDER = "alimentador"
    ZONE = "zona"


class IssueOutcome(StrEnum):
    """What a plan did about one asset in one period."""

    ISSUED = "emitida"
    #: There is already work pending in the field on that asset.
    PENDING_WORK = "trabajo_pendiente"
    #: The asset was attended recently enough that the plan's own guard skipped it.
    RECENTLY_ATTENDED = "atendida_hace_poco"


class MaintenancePlan(Base):
    """One preventive plan: what work, on which assets, how often."""

    __tablename__ = "maintenance_plan"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    #: The work the plan issues. The form is validated against the catalogue when the plan is saved,
    #: not when it fires: a plan pointing at a form that does not exist must fail in front of the
    #: person who wrote it, not at five in the morning in a worker's log.
    work_type: Mapped[str] = mapped_column(String(32), nullable=False)
    form_code: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    asset_type_key: Mapped[str | None] = mapped_column(String(64))

    cadence: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Only for `dias`. Null for the calendar cadences, which take their period from the calendar.
    cadence_days: Mapped[int | None] = mapped_column(Integer)
    #: The day of the month a calendar plan fires. Capped at 28 by the service: «el 31 de cada mes»
    #: does not exist in February, and a plan that silently skipped February would report an annual
    #: count that is wrong by one.
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    #: The feeder or zone code for the expanded scopes. Null for `activos`.
    scope_value: Mapped[str | None] = mapped_column(String(64))

    #: Do not issue for an asset attended within this many days. Null means no guard — which is a
    #: real choice for a plan whose whole point is a fixed calendar (a regulatory inspection).
    skip_if_attended_within_days: Mapped[int | None] = mapped_column(Integer)

    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    #: Null means open-ended.
    ends_on: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_by: Mapped[str | None] = mapped_column(String(255))
    updated_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("business_unit_id", "code", name="uq_maintenance_plan_code"),
        Index("ix_maintenance_plan_active", "business_unit_id", "active"),
    )


class PlanTarget(Base):
    """One asset a plan covers, in visit order.

    A separate table rather than a JSONB array because a route is worked one asset at a time and the
    order is data the area maintains: «primero el alimentador sur, de la subestación hacia afuera».
    """

    __tablename__ = "plan_target"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_plan.id", ondelete="CASCADE"), nullable=False
    )
    asset_code: Mapped[str] = mapped_column(String(128), nullable=False)
    asset_type_key: Mapped[str | None] = mapped_column(String(64))
    feeder_code: Mapped[str | None] = mapped_column(String(32))
    zone: Mapped[str | None] = mapped_column(String(64))
    #: The visit order. A plan whose targets are a route is this list sorted by it.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("plan_id", "asset_code", name="uq_plan_target_asset"),
        Index("ix_plan_target_order", "plan_id", "sort_order"),
    )


class PlanIssue(Base):
    """What a plan did about one asset in one period: issued an order, or refused and why.

    The refusals are rows and not log lines. A plan that issued 4 of 11 orders is either working
    correctly (7 assets already have crews on the way) or badly (a guard nobody meant to set), and
    the only way to tell is a record per asset with the reason.
    """

    __tablename__ = "plan_issue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_plan.id", ondelete="CASCADE"), nullable=False
    )
    #: The period label: `2026-09`, `2026-T3`, `2026-S2`, `2026`, or the scheduled date for a plan
    #: measured in days. A label and not a timestamp, so two runs inside one period are one period.
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Null for a plan that issues one order for the whole scope rather than one per asset.
    asset_code: Mapped[str | None] = mapped_column(String(128))
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    #: In Spanish, for the person reading the plan's history. Null when the order was issued.
    reason: Mapped[str | None] = mapped_column(Text)
    work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="SET NULL")
    )
    #: What the expansion could not know, when the scope was a feeder or a zone. Carried per issue
    #: rather than per plan because it is the sentence the planner needs next to the count.
    caveats: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        #: One row per plan, asset and period. Two partial indexes because PostgreSQL treats NULLs
        #: as distinct, so a single index over a nullable `asset_code` would let a scope-level plan
        #: issue the same period twice — which is the exact failure this table exists to prevent.
        Index(
            "uq_plan_issue_asset_period",
            "plan_id",
            "asset_code",
            "period",
            unique=True,
            postgresql_where="asset_code IS NOT NULL",
        ),
        Index(
            "uq_plan_issue_scope_period",
            "plan_id",
            "period",
            unique=True,
            postgresql_where="asset_code IS NULL",
        ),
        Index("ix_plan_issue_history", "plan_id", "period"),
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "asset_code": self.asset_code,
            "outcome": self.outcome,
            "reason": self.reason,
            "work_order_id": str(self.work_order_id) if self.work_order_id else None,
            "caveats": self.caveats,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
        }
