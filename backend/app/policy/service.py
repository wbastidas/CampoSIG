"""Resolving the capture policy, and saying where each value came from (RF-151).

The acceptance criterion is «cambiar la política se refleja en el móvil en el siguiente sync», and
what makes that checkable is not the write — it is that the resolved policy travels **inside the
offline package manifest**, whose content hash is what tells a device it is holding something stale.
Change a policy and the hash changes; the device downloads and obeys the new one. No separate
notification channel to keep in step.

Two things this module insists on:

* **Every effective value carries its origin.** «min_photos = 4» is not an answer an administrator
  can act on; «4, de la zona NORTE» is. Without it, somebody changes the unit's policy, sees no
  change on a phone in the north, and concludes the sync is broken.
* **The platform default is a value like any other, and it is named.** A field nobody has ever set
  still resolves, and the screen says «por omisión de la plataforma» rather than showing a number
  with no author.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import EventKind
from app.audit.service import record
from app.org.models import BusinessUnit
from app.policy.models import CapturePolicy

#: Where a value came from. Ordered most specific first, which is also resolution order.
SOURCE_ZONE = "zona"
SOURCE_UNIT = "unidad"
SOURCE_DEFAULT = "por omisión de la plataforma"

#: The fields a policy carries. Named once so the resolver, the API and the manifest cannot drift:
#: a field added to the model and forgotten in the manifest would be a policy the phone never sees.
FIELDS = (
    "store_audio",
    "require_audio_consent",
    "audio_retention_days",
    "min_photos",
    "photo_max_edge_px",
    "photo_quality",
    "evidence_retention_days",
    "upload_on_metered",
    "metered_upload_limit_mb",
    "downscale_on_metered",
)

#: What holds when nobody has decided. Chosen to be the conservative reading of each requirement
#: rather than the convenient one: audio is **not** kept (RF-058 makes keeping it the exception),
#: consent is asked, and nothing is uploaded over mobile data. A default that silently uploaded a
#: day of photographs over a technician's own data plan would be a default nobody chose.
DEFAULTS: dict[str, Any] = {
    "store_audio": False,
    "require_audio_consent": True,
    "audio_retention_days": 90,
    "min_photos": 1,
    "photo_max_edge_px": 1600,
    "photo_quality": 80,
    "evidence_retention_days": 1825,
    "upload_on_metered": False,
    "metered_upload_limit_mb": None,
    "downscale_on_metered": True,
}

#: Fields whose value must be a positive integer when set. A retention of zero days is not a policy,
#: it is a deletion rule, and it would arrive as a typo rather than as a decision.
POSITIVE_INTEGER_FIELDS = (
    "audio_retention_days",
    "photo_max_edge_px",
    "evidence_retention_days",
    "metered_upload_limit_mb",
)


class PolicyError(Exception):
    pass


@dataclass(frozen=True)
class EffectiveValue:
    """One resolved field: what it is and who decided it."""

    value: Any
    source: str

    def as_dict(self) -> dict[str, Any]:
        return {"value": self.value, "source": self.source}


@dataclass(frozen=True)
class EffectivePolicy:
    """The policy a device in this unit — and optionally this zone — must obey."""

    business_unit: str
    zone_code: str | None
    values: dict[str, EffectiveValue]

    def value(self, field: str) -> Any:
        return self.values[field].value

    def source(self, field: str) -> str:
        return self.values[field].source

    def as_dict(self) -> dict[str, Any]:
        """The shape the API returns and the screen reads."""
        return {
            "business_unit": self.business_unit,
            "zone_code": self.zone_code,
            "values": {name: item.as_dict() for name, item in self.values.items()},
        }

    def for_device(self) -> dict[str, Any]:
        """The flat shape the phone obeys: field → value, with no provenance.

        The origins are for the administrator's screen. A device that received them would be a
        device that could be made to branch on them, and the policy is meant to be obeyed, not
        interpreted.
        """
        return {name: item.value for name, item in self.values.items()}


def _row(
    session: Session, business_unit_id: uuid.UUID, zone_code: str | None
) -> CapturePolicy | None:
    statement = select(CapturePolicy).where(CapturePolicy.business_unit_id == business_unit_id)
    statement = statement.where(
        CapturePolicy.zone_code.is_(None)
        if zone_code is None
        else CapturePolicy.zone_code == zone_code
    )
    return session.execute(statement).scalar_one_or_none()


def resolve_field(
    session: Session, business_unit_id: uuid.UUID, field: str, zone_code: str | None = None
) -> EffectiveValue:
    """Resolve one field without loading the business unit.

    The enforcement points need exactly this: a capture arriving from a phone knows its unit's id
    and its work order's zone, and asking «may this audio be kept» must not cost a second query for
    a row it does not otherwise need.
    """
    if field not in FIELDS:
        raise PolicyError(f"«{field}» no es un campo de la política")
    for row, source in (
        (_row(session, business_unit_id, zone_code) if zone_code else None, SOURCE_ZONE),
        (_row(session, business_unit_id, None), SOURCE_UNIT),
    ):
        found = getattr(row, field, None) if row is not None else None
        if found is not None:
            return EffectiveValue(found, source)
    return EffectiveValue(DEFAULTS[field], SOURCE_DEFAULT)


def get_policy(
    session: Session, unit: BusinessUnit, zone_code: str | None = None
) -> CapturePolicy | None:
    """The row for exactly this scope, without inheritance. For the editing screen."""
    return _row(session, unit.id, zone_code)


def list_policies(session: Session, unit: BusinessUnit) -> list[CapturePolicy]:
    """The unit's row first, then its zones by code — which is the order they override in."""
    rows = list(
        session.execute(
            select(CapturePolicy).where(CapturePolicy.business_unit_id == unit.id)
        ).scalars()
    )
    return sorted(rows, key=lambda row: (row.zone_code is not None, row.zone_code or ""))


def effective(
    session: Session, unit: BusinessUnit, zone_code: str | None = None
) -> EffectivePolicy:
    """Resolve the policy for a scope, field by field, most specific non-null wins.

    Built out of :func:`resolve_field` rather than walking the rows again: precedence stated twice
    is precedence that will eventually disagree with itself, and the half that disagrees would be
    the half a phone obeys.
    """
    values = {field: resolve_field(session, unit.id, field, zone_code) for field in FIELDS}
    return EffectivePolicy(business_unit=unit.code, zone_code=zone_code, values=values)


def _validate(changes: dict[str, Any]) -> None:
    unknown = sorted(set(changes) - set(FIELDS) - {"note"})
    if unknown:
        raise PolicyError(f"campos que no son de la política: {', '.join(unknown)}")
    for field in POSITIVE_INTEGER_FIELDS:
        given = changes.get(field)
        if given is not None and (not isinstance(given, int) or given <= 0):
            raise PolicyError(f"«{field}» debe ser un entero positivo; llegó {given!r}")
    quality = changes.get("photo_quality")
    if quality is not None and (not isinstance(quality, int) or not 1 <= quality <= 100):
        raise PolicyError(f"«photo_quality» va de 1 a 100; llegó {quality!r}")
    photos = changes.get("min_photos")
    if photos is not None and (not isinstance(photos, int) or photos < 0):
        raise PolicyError(f"«min_photos» no puede ser negativo; llegó {photos!r}")


def set_policy(
    session: Session,
    unit: BusinessUnit,
    *,
    zone_code: str | None = None,
    changes: dict[str, Any],
    actor: str,
) -> CapturePolicy:
    """Create or update the row for a scope, recording who changed what.

    A key present with ``None`` clears that field — which is how a zone stops having an opinion and
    goes back to inheriting. A key that is absent is left alone. The difference matters: a screen
    that sent every field on every save would turn «I did not touch this» into «set this to null».
    """
    _validate(changes)
    row = _row(session, unit.id, zone_code)
    created = row is None
    if row is None:
        row = CapturePolicy(business_unit_id=unit.id, zone_code=zone_code)
        session.add(row)
    before = {field: getattr(row, field) for field in FIELDS} if not created else {}
    for field, value in changes.items():
        setattr(row, field, value)
    row.updated_by = actor
    session.flush()

    changed = {
        field: {"from": before.get(field), "to": getattr(row, field)}
        for field in FIELDS
        if field in changes and (created or before.get(field) != getattr(row, field))
    }
    record(
        session,
        unit.id,
        kind=EventKind.CREATED if created else EventKind.FIELD_CHANGED,
        subject_type="capture_policy",
        subject_id=str(row.id),
        actor=actor,
        payload={"zone_code": zone_code, "changed": changed},
        reason=changes.get("note"),
    )
    return row


def clear_policy(session: Session, unit: BusinessUnit, *, zone_code: str, actor: str) -> bool:
    """Remove a zone's whole row, so it inherits everything again.

    Only a zone's. The unit's row is not removable here: deleting it would move ten values to the
    platform defaults at once, which is a decision that should be made field by field and visibly.
    """
    row = _row(session, unit.id, zone_code)
    if row is None:
        return False
    policy_id = str(row.id)
    session.delete(row)
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.FIELD_CHANGED,
        subject_type="capture_policy",
        subject_id=policy_id,
        actor=actor,
        payload={"zone_code": zone_code, "removed": True},
        reason="la zona vuelve a heredar la política de su unidad",
    )
    return True


def policy_for_package(session: Session, unit: BusinessUnit, zone_code: str) -> dict[str, Any]:
    """What goes into the offline package manifest (RF-151's acceptance criterion).

    Flat, with no provenance: see :meth:`EffectivePolicy.for_device`. Because it sits inside the
    manifest, changing a policy changes the manifest's content hash, and the device's ordinary
    staleness check is what makes the new policy arrive. Nothing else has to be notified.
    """
    return effective(session, unit, zone_code).for_device()


def unit_ids_with_policy(session: Session) -> list[uuid.UUID]:
    """Units that have set any policy at all. For the administrator's overview."""
    rows = session.execute(select(CapturePolicy.business_unit_id).distinct()).all()
    return [row[0] for row in rows]
