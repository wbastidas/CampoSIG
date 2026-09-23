"""Administrable catalogues (RF-034).

The forms already reference them. `forms/blocks/b11-hallazgos.yaml` says
``x-catalog-ref: defect`` and `b06-actividades.yaml` says ``x-catalog-ref: activity``, and **nothing
served either list**: a phone rendering those blocks had a code field and no values to choose from.
The reference existed, the catalogue did not.

Three kinds of catalogue meet here, and the platform only owns one of them:

* **GIS-derived** (`feeder`, `substation`): they come from the unit's synced metadata and differ per
  unit (RF-304). Not stored here.
* **Profile enums** (`voltage_level`, `technology.lamp`): canonical vocabulary from the asset model
  descriptor. Not stored here either.
* **Operational catalogues** (`defect`, `activity`, `delay_reason`…): the utility's own lists, which
  a functional administrator maintains. These are what this module holds.

Two design points:

* **A monotonic `revision` per entry, assigned by a trigger.** That is what makes the delta
  download of RF-034 possible: a device asks for everything above the revision it holds. A timestamp
  could not do it — `now()` is the transaction clock, so a batch of entries edited together would
  share one value and a device could not tell where it left off. (The same lesson as the regulatory
  revision log and the published-form history; by now it is a rule.)

  The trigger, rather than the service assigning it: an entry written by the ERP integration must
  get a revision too, and a rule that lives in one function is a rule the next writer forgets. It
  fires on INSERT **and** UPDATE, because an edited label has to reach the device as surely as a new
  value does.
* **Deleting is deactivating.** A removed entry must still travel to the device, as a tombstone,
  or a phone keeps offering a defect code the utility retired two years ago. `active = false` is
  the tombstone, and it carries a revision like any other change.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    DDL,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base

#: The sequence the trigger draws revisions from. Declared here so the metadata creates it for the
#: tests, which build the schema from the ORM rather than from Alembic.
REVISION_SEQUENCE = Sequence("catalog_entry_revision_seq")


class CatalogSource(StrEnum):
    """Who owns the values. Shown on the admin screen so nobody edits what they do not own."""

    #: A functional administrator types them.
    MANUAL = "manual"
    #: An integration writes them — materials come from the ERP (RF-034, RF-121).
    INTEGRATION = "integracion"


class Catalog(Base):
    """One catalogue, identified by the same code the forms reference."""

    __tablename__ = "catalog"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    #: Exactly the string in `x-catalog-ref`. A mismatch is the whole failure mode this module
    #: exists to remove, and a test walks `forms/` to prove there is none.
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default=CatalogSource.MANUAL)

    #: Why this catalogue is empty, when it is. Loaded from the seed so an operator sees «falta la
    #: división política oficial del INEC» instead of an empty picker with no explanation.
    note: Mapped[str | None] = mapped_column(Text)

    #: Bumped on every change to any of its entries, so a device can compare one number per
    #: catalogue instead of scanning entries it already has.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CatalogEntry(Base):
    """One value of a catalogue, national or added by one business unit."""

    __tablename__ = "catalog_entry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    #: The order the device downloads by. Assigned by a trigger on insert and on update, never a
    #: timestamp and never the service (see the module docstring).
    revision: Mapped[int] = mapped_column(
        BigInteger,
        REVISION_SEQUENCE,
        server_default=REVISION_SEQUENCE.next_value(),
        nullable=False,
        unique=True,
    )

    catalog_code: Mapped[str] = mapped_column(
        String(64), ForeignKey("catalog.code", ondelete="CASCADE"), nullable=False
    )

    #: Null for a national value; set for one a unit added or overrode. Same two-level shape as the
    #: capture policy (RF-151), and for the same reason: most lists are national and a few are not.
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE")
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    #: What a technician might say instead of the label. Feeds the ASR lexicon (RF-147, ADR-011),
    #: which is why it is data and not a table in the voice module.
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(String(64)), nullable=False, default=list)

    #: For hierarchical catalogues: a canton's province, a parish's canton.
    parent_code: Mapped[str | None] = mapped_column(String(64))

    #: Anything the value carries beyond its label — a defect's default criticality, a unit's
    #: symbol. JSONB because it differs per catalogue and the form that reads it knows its shape.
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    #: False is the tombstone. A retired value still travels to the device, or a phone keeps
    #: offering a code the utility withdrew.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    updated_by: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "catalog_code", "business_unit_id", "code", name="uq_catalog_entry_identity"
        ),
        #: The constraint above does not cover the national rows: PostgreSQL treats nulls as
        #: distinct, so two `defect/cruceta_podrida` with no unit would both be accepted and the
        #: resolution would return whichever the scan found.
        Index(
            "uq_catalog_entry_national",
            "catalog_code",
            "code",
            unique=True,
            postgresql_where="business_unit_id IS NULL",
        ),
        Index("ix_catalog_entry_delta", "revision"),
        Index("ix_catalog_entry_catalog", "catalog_code", "business_unit_id"),
    )


#: The trigger that keeps `revision` monotonic. On the table rather than in the service because an
#: entry written by the ERP integration needs a revision too, and a rule that lives in one function
#: is a rule the next writer forgets. Attached after create so the schema the tests build from the
#: ORM behaves like the migrated one.
REVISION_TRIGGER = DDL(  # type: ignore[no-untyped-call]
    """
CREATE OR REPLACE FUNCTION catalog_entry_stamp_revision() RETURNS trigger AS $$
BEGIN
    NEW.revision := nextval('catalog_entry_revision_seq');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER catalog_entry_revision
    BEFORE INSERT OR UPDATE ON catalog_entry
    FOR EACH ROW EXECUTE FUNCTION catalog_entry_stamp_revision();
"""
)

event.listen(
    CatalogEntry.__table__, "after_create", REVISION_TRIGGER.execute_if(dialect="postgresql")
)
