"""Capture policy per area (RF-151).

The requirement lists five things an area decides for itself: audio, minimum photographs, quality,
sending over the network, and retention. Three design points:

* **Every column is nullable, and a null means «no opinion».** A zone that differs from its unit
  only in refusing uploads over mobile data should say that and nothing else. Whole-row overrides
  would force it to restate the other nine values, and the day the unit changes one of them the
  zone would silently keep the old figure — which is the failure this shape makes impossible.

* **Two levels, unit and zone.** The unit is the area (ADR-009); the zone is the exception inside
  it, because network coverage and retention pressure are not uniform across a service area. More
  levels were considered and left out: a chain nobody can recite is a chain nobody can debug.

* **What is a policy and what is a regulatory limit are different things.** A retention period is
  an operational decision an area takes; a maximum restoration time is a figure a regulator
  published. The second lives in ``regulatory_parameter`` with its period of force and its
  citation (ADR-007) and never here. If a norm ever *caps* a retention period, that cap belongs
  there too and a deterministic rule refuses a policy above it — the policy row must not become
  the place a legal limit is quietly stored.
"""

from __future__ import annotations

import uuid
from datetime import datetime

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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


class CapturePolicy(Base):
    """One row of policy, for a business unit or for one of its zones.

    The unit's row has ``zone_code`` null. A zone's row overrides, field by field, the values its
    unit sets; anything it leaves null it inherits.
    """

    __tablename__ = "capture_policy"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )

    #: Null for the unit's own policy. Otherwise the zone this row refines. Deliberately the zone
    #: *code* and not a foreign key to `zone`: a unit may set a policy for a zone whose polygon
    #: nobody has drawn yet, and the code is the identity either way (RF-152).
    zone_code: Mapped[str | None] = mapped_column(String(64))

    # --- Audio (RF-055..RF-058) ---
    #: Whether the original recording is kept after the transcript. RF-058 names this parameter and
    #: makes it per area, because keeping a customer's voice is a decision with consequences.
    store_audio: Mapped[bool | None] = mapped_column(Boolean)
    #: Whether the technician must confirm consent before recording (RF-058, LOPDP).
    require_audio_consent: Mapped[bool | None] = mapped_column(Boolean)
    audio_retention_days: Mapped[int | None] = mapped_column(Integer)

    # --- Photographs (RF-070..RF-077) ---
    #: A floor, not the requirement: a form may ask for more, never for fewer.
    min_photos: Mapped[int | None] = mapped_column(Integer)
    photo_max_edge_px: Mapped[int | None] = mapped_column(Integer)
    photo_quality: Mapped[int | None] = mapped_column(Integer)
    evidence_retention_days: Mapped[int | None] = mapped_column(Integer)

    # --- Network (RF-100..RF-104) ---
    #: Whether evidence may be uploaded over mobile data at all. False means «wait for Wi-Fi»,
    #: which in a unit paying per megabyte is the difference between a pilot and an invoice.
    upload_on_metered: Mapped[bool | None] = mapped_column(Boolean)
    #: A cap in megabytes per device per day when uploading over mobile data is allowed.
    metered_upload_limit_mb: Mapped[int | None] = mapped_column(Integer)
    #: Whether photographs are uploaded at full resolution or downscaled first when off Wi-Fi.
    downscale_on_metered: Mapped[bool | None] = mapped_column(Boolean)

    #: Why this row exists, for whoever reads it in a year.
    note: Mapped[str | None] = mapped_column(Text)

    updated_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        #: One row per scope. The unit's row is the one with a null zone, and PostgreSQL treats
        #: nulls as distinct in a unique index — so the uniqueness of the unit row is enforced by
        #: the partial index below rather than by this constraint.
        UniqueConstraint("business_unit_id", "zone_code", name="uq_capture_policy_scope"),
        Index(
            "uq_capture_policy_unit_row",
            "business_unit_id",
            unique=True,
            postgresql_where="zone_code IS NULL",
        ),
    )
