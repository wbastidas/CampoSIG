"""Work orders, crews and assignment (SRS 3.3, M02, M03; RF-310..RF-324).

Scoped by business unit throughout (ADR-009). Every query in this module's service layer
takes a unit, and the isolation tests try to make data cross between units.

**Geometry is stored in EPSG:4326**, not in each unit's projected reference. Three reasons:
the phone's GPS produces WGS84, MapLibre consumes WGS84, and units may sit in different UTM
zones — a single column cannot hold mixed SRIDs usefully. Projection to the unit's own
reference happens at the GIS boundary, in the arcpy agent, where it belongs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base

#: Canonical storage reference for everything the platform holds. See module docstring.
STORAGE_SRID = 4326


class WorkOrderState(StrEnum):
    """States of SRS 3.3. Transitions are validated by the service layer."""

    DRAFT = "borrador"
    PLANNED = "planificada"
    ASSIGNED = "asignada"
    DOWNLOADED = "descargada"
    EN_ROUTE = "en_camino"
    ON_SITE = "en_sitio"
    IN_EXECUTION = "en_ejecucion"
    SUSPENDED = "suspendida"
    CLOSED_FIELD = "cerrada_campo"
    SYNCED = "sincronizada"
    IN_REVIEW = "en_revision"
    RETURNED = "devuelta"
    APPROVED = "aprobada"
    CLOSED = "cerrada"
    CANCELLED = "anulada"


class WorkOrderSource(StrEnum):
    """Where the work came from (addendum 4.1)."""

    MANUAL = "manual"
    #: The corporate work-order platform owns the number (RF-120, satellite mode).
    EXTERNAL_SYSTEM = "sistema_ot"
    #: A GIS quality review to verify in the field (RF-351).
    GIS_REVIEW = "revision_sig"
    #: Raised from a field finding or a vision detection (RF-013).
    AI_FINDING = "hallazgo_ia"
    PREVENTIVE_PLAN = "plan_preventivo"
    CALL_CENTER = "call_center"


class Priority(StrEnum):
    LOW = "baja"
    MEDIUM = "media"
    HIGH = "alta"
    CRITICAL = "critica"


class Crew(Base):
    """A crew: its members, its leader, its competencies and its zone (RF-005)."""

    __tablename__ = "crew"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    leader_name: Mapped[str | None] = mapped_column(String(255))
    vehicle: Mapped[str | None] = mapped_column(String(64))
    #: MV, LV, live-line work, APG, height — drives dispatch suggestions.
    competencies: Mapped[list[str]] = mapped_column(ARRAY(String(32)), nullable=False, default=list)
    zone: Mapped[str | None] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("business_unit_id", "code", name="uq_crew_code"),
        Index("ix_crew_unit_active", "business_unit_id", "active"),
    )


class WorkOrder(Base):
    """One unit of field work."""

    __tablename__ = "work_order"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )

    #: Sequential per unit and year (RF-010). Null while the external system owns the number.
    code: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(24), nullable=False, default=WorkOrderSource.MANUAL)
    #: Idempotency key for imports: the same external order never creates two rows (RF-011).
    external_ref: Mapped[str | None] = mapped_column(String(64))

    #: Work type, which decides the form the phone shows (SRS 4.8).
    work_type: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Form code and the version pinned when assigned: a work order executes with the
    #: version current at assignment time, not whatever is current at closing (SRS 4.1.6).
    form_code: Mapped[str] = mapped_column(String(16), nullable=False)
    form_version: Mapped[str | None] = mapped_column(String(16))

    state: Mapped[str] = mapped_column(String(24), nullable=False, default=WorkOrderState.DRAFT)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default=Priority.MEDIUM)
    description: Mapped[str | None] = mapped_column(Text)

    asset_type_key: Mapped[str | None] = mapped_column(String(64))
    asset_code: Mapped[str | None] = mapped_column(String(128))
    #: Point location in EPSG:4326 — what the planner's map draws and selects against.
    location: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=STORAGE_SRID, spatial_index=False)
    )
    feeder_code: Mapped[str | None] = mapped_column(String(32))
    zone: Mapped[str | None] = mapped_column(String(64))

    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: Owning planner, so several planners never silently take over each other's work
    #: (RF-312).
    planner_id: Mapped[str | None] = mapped_column(String(255))
    assigned_crew_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crew.id", ondelete="SET NULL")
    )
    assigned_user_sub: Mapped[str | None] = mapped_column(String(255))

    #: Optimistic lock: two planners editing the same order do not overwrite each other
    #: (RF-311). Incremented by the service on every administrative change.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    crew: Mapped[Crew | None] = relationship()
    custody: Mapped[list[DeviceCustody]] = relationship(
        back_populates="work_order", cascade="all, delete-orphan", order_by="DeviceCustody.since"
    )

    __table_args__ = (
        # Idempotent import: the same external reference cannot enter a unit twice.
        UniqueConstraint("business_unit_id", "external_ref", name="uq_work_order_external_ref"),
        UniqueConstraint("business_unit_id", "code", name="uq_work_order_code"),
        # The planner's board: this unit's orders in this state.
        Index("ix_work_order_unit_state", "business_unit_id", "state"),
        Index("ix_work_order_unit_crew", "business_unit_id", "assigned_crew_id"),
        Index("ix_work_order_sla", "sla_due_at"),
        # GiST index for the map's bbox and polygon selection, which is the hot query of
        # the graphical assignment screen.
        Index("ix_work_order_location", "location", postgresql_using="gist"),
    )

    @property
    def is_assignable(self) -> bool:
        return self.state in {WorkOrderState.PLANNED, WorkOrderState.ASSIGNED}


class DeviceCustody(Base):
    """Who held a work order, on which device, since when and why (RF-324).

    Append-only. Reassignment closes the open row and opens a new one, so the full chain of
    custody survives — which is what makes a dispute about who had what answerable.
    """

    __tablename__ = "device_custody"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[str | None] = mapped_column(String(128))
    user_sub: Mapped[str | None] = mapped_column(String(255))
    crew_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crew.id", ondelete="SET NULL")
    )
    since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    #: Null while this is the current holder.
    until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String(500))
    #: True when the previous holder still had unsynced captured data (RF-322).
    # text("false"), not func.false(): the latter renders as the invalid SQL `false()`.
    # Only a real database catches this — offline SQL rendering and mypy both accept it.
    had_unsynced_data: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    granted_by: Mapped[str | None] = mapped_column(String(255))
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    work_order: Mapped[WorkOrder] = relationship(back_populates="custody")

    __table_args__ = (
        Index("ix_device_custody_order", "work_order_id"),
        # Finding the current holder is the query reassignment always runs.
        Index(
            "ix_device_custody_current",
            "work_order_id",
            postgresql_where="until IS NULL",
        ),
    )
