"""Stock the ERP owns, as the platform sees it (RF-122).

A **snapshot**, not a ledger. The ERP is the system of record for inventory; what this table holds
is «lo que el ERP dijo la última vez», so a planner can tell whether the crossarm is in the
warehouse before sending a crew, and a crew can see what their own vehicle carries.

Two decisions follow from it being a snapshot:

* **It is replaced per location, never merged.** A warehouse that sends five lines today and four
  tomorrow has four: merging would leave a phantom row for the material that ran out, and a phantom
  row is worse than no row because somebody plans against it.
* **It carries `as_of` and the platform shows it.** Stock from a nightly batch is hours old, and a
  number presented as current when it is twelve hours old is how a crew drives to a warehouse for
  something that is gone.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


class StockLocationKind(StrEnum):
    """«Existencias por bodega o vehículo» (RF-122), which are not interchangeable.

    A warehouse is where work is planned from; a vehicle is what a crew already has with them, and
    it is the one that decides whether today's job can be done at all.
    """

    WAREHOUSE = "bodega"
    VEHICLE = "vehiculo"


class MaterialStock(Base):
    """How much of one material one location holds, as of one moment."""

    __tablename__ = "material_stock"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )

    #: The code as the ERP knows it. Not a foreign key to `catalog_entry`: the stock batch and the
    #: catalogue batch arrive separately and either may be first, and a constraint between them
    #: would reject good data for arriving in the wrong order. What it does instead is report the
    #: codes it holds that the catalogue does not know, so somebody can see the two drifting.
    material_code: Mapped[str] = mapped_column(String(64), nullable=False)
    location_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    location_code: Mapped[str] = mapped_column(String(64), nullable=False)
    location_name: Mapped[str | None] = mapped_column(String(255))

    #: Numeric and not float: a count of crossarms and a length of cable are both quantities, and
    #: binary floating point turns 0.1 metres into an argument.
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(16))

    #: When the ERP says this was true. Shown next to the number, always.
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "business_unit_id",
            "location_kind",
            "location_code",
            "material_code",
            name="uq_material_stock_line",
        ),
        Index("ix_material_stock_location", "business_unit_id", "location_kind", "location_code"),
        Index("ix_material_stock_material", "business_unit_id", "material_code"),
    )
