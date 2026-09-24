"""Capture policy administration (RF-151, M15).

The device does not call this: it receives the resolved policy inside its offline package, whose
content hash makes a change arrive through the ordinary sync. So these endpoints are for the two
people who need them — the administrator who sets a policy, and the planner or supervisor who needs
to see what a crew's phone is actually obeying before asking why it did something.

The effective view is the important one. A list of rows does not answer «what will the phone in
NORTE do»; the resolution does, and it names the origin of every value so that changing the unit's
policy and seeing no change in the north is explainable instead of mysterious.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.policy import service as policy

router = APIRouter(prefix="/api/v1/policies", tags=["policies"], dependencies=[Depends(unit_scope)])

SessionDep = Annotated[Session, Depends(get_session)]

READERS = (Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN, Role.SUPERVISOR, Role.PLANNER)
EDITORS = (Role.FUNCTIONAL_ADMIN,)


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


class PolicyIn(BaseModel):
    """A partial policy.

    Every field is optional and `None` is a value, not an omission: sending `null` clears a field so
    the scope goes back to inheriting. `model_fields_set` is what tells the two apart, which is why
    this is not a dict of defaults — a screen that posted every field on every save would turn «I
    did not touch this» into «set this to null».
    """

    store_audio: bool | None = None
    require_audio_consent: bool | None = None
    audio_retention_days: int | None = None
    min_photos: int | None = None
    photo_max_edge_px: int | None = None
    photo_quality: int | None = None
    evidence_retention_days: int | None = None
    upload_on_metered: bool | None = None
    metered_upload_limit_mb: int | None = None
    downscale_on_metered: bool | None = None
    note: str | None = Field(default=None, max_length=2000)

    def changes(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.model_fields_set}


def _as_dict(row: Any) -> dict[str, Any]:
    return {
        "zone_code": row.zone_code,
        "values": {field: getattr(row, field) for field in policy.FIELDS},
        "note": row.note,
        "updated_by": row.updated_by,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/units/{unit_code}", summary="Las filas de política de la unidad y sus zonas (RF-151)")
def list_policies(
    unit_code: str,
    session: SessionDep,
    _: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    return {
        "fields": list(policy.FIELDS),
        "defaults": policy.DEFAULTS,
        "rows": [_as_dict(row) for row in policy.list_policies(session, unit)],
    }


@router.get(
    "/units/{unit_code}/effective",
    summary="Qué política obedece un teléfono, con el origen de cada valor (RF-151)",
)
def effective(
    unit_code: str,
    session: SessionDep,
    zone: Annotated[str | None, Query(max_length=64)] = None,
    _: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> dict[str, Any]:
    """The origin of each value travels too: without it, a unit-level change that a zone overrides
    looks like a broken sync."""
    unit = _unit(session, unit_code)
    return policy.effective(session, unit, zone).as_dict()


@router.put("/units/{unit_code}", summary="Fijar la política de la unidad (RF-151)")
def set_unit_policy(
    unit_code: str,
    payload: PolicyIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*EDITORS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    try:
        row = policy.set_policy(session, unit, changes=payload.changes(), actor=principal.subject)
    except policy.PolicyError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return _as_dict(row)


@router.put(
    "/units/{unit_code}/zones/{zone_code}", summary="Fijar la política de una zona (RF-151)"
)
def set_zone_policy(
    unit_code: str,
    zone_code: str,
    payload: PolicyIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*EDITORS))] = None,
) -> dict[str, Any]:
    """A zone states only what it differs in; everything else it inherits from its unit."""
    unit = _unit(session, unit_code)
    try:
        row = policy.set_policy(
            session,
            unit,
            zone_code=zone_code,
            changes=payload.changes(),
            actor=principal.subject,
        )
    except policy.PolicyError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return _as_dict(row)


@router.delete(
    "/units/{unit_code}/zones/{zone_code}",
    summary="Quitar la política de una zona para que vuelva a heredar (RF-151)",
)
def clear_zone_policy(
    unit_code: str,
    zone_code: str,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*EDITORS))] = None,
) -> dict[str, Any]:
    """Only a zone's row. Removing the unit's would move ten values to the platform defaults at
    once, which is a decision to take field by field and in the open."""
    unit = _unit(session, unit_code)
    removed = policy.clear_policy(session, unit, zone_code=zone_code, actor=principal.subject)
    if not removed:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"la zona «{zone_code}» no tiene política propia"
        )
    session.commit()
    return {"zone_code": zone_code, "removed": True}
