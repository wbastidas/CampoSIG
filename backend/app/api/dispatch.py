"""Dispatch endpoints: what the crews were sent and whether they have it (RF-104, RF-360).

The screen these serve is the one a dispatcher watches before the crews leave. It answers
one question the planning board cannot: assignment is an intention, delivery is a fact, and
the gap between them is work that will not get done today.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dispatch.service import device_readiness, dispatch_board
from app.infra.database import get_session
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.sync.service import build_offline_package, current_package

router = APIRouter(prefix="/api/v1/dispatch", tags=["dispatch"])

SessionDep = Annotated[Session, Depends(get_session)]


def _unit(session: Session, code: str):  # type: ignore[no-untyped-def]
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/units/{unit_code}/board")
def board(session: SessionDep, unit_code: str) -> list[dict[str, Any]]:
    """Per-crew dispatch state: assigned, delivered, stale, in progress, returned."""
    unit = _unit(session, unit_code)
    return [row.as_dict() for row in dispatch_board(session, unit)]


@router.get("/units/{unit_code}/devices")
def devices(session: SessionDep, unit_code: str) -> list[dict[str, Any]]:
    """Per-device readiness, with the reasons a phone should not leave yet."""
    unit = _unit(session, unit_code)
    return [row.as_dict() for row in device_readiness(session, unit)]


class PublishPackageIn(BaseModel):
    """Publish a zone's offline package (RF-360).

    The tile URL is supplied rather than generated because the tiles are built outside the
    API, by `tools/tiles/build_pmtiles.sh`, and uploaded to object storage. The API's job is
    to publish the manifest that tells devices what to fetch.
    """

    zone: str = Field(min_length=1, max_length=64)
    tile_url: str = Field(min_length=1, max_length=1000)
    asset_count: int = Field(ge=0)
    model_package_version: str | None = None


@router.post("/units/{unit_code}/packages", status_code=status.HTTP_201_CREATED)
def publish_package(
    session: SessionDep, unit_code: str, payload: PublishPackageIn
) -> dict[str, Any]:
    """Publish a new offline package for a zone, or return the current one unchanged."""
    unit = _unit(session, unit_code)
    package = build_offline_package(
        session,
        unit,
        zone=payload.zone,
        tile_url=payload.tile_url,
        asset_count=payload.asset_count,
        model_package_version=payload.model_package_version,
    )
    session.commit()
    return {
        "zone": package.zone,
        "version": package.version,
        "content_hash": package.content_hash,
        "built_at": package.built_at.isoformat(),
        "manifest": package.manifest,
    }


@router.get("/units/{unit_code}/packages/{zone}")
def package(session: SessionDep, unit_code: str, zone: str) -> dict[str, Any]:
    """The package a device in this zone should be holding."""
    unit = _unit(session, unit_code)
    found = current_package(session, unit, zone)
    if found is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"la zona '{zone}' no tiene un paquete publicado"
        )
    return {
        "zone": found.zone,
        "version": found.version,
        "content_hash": found.content_hash,
        "built_at": found.built_at.isoformat(),
        "manifest": found.manifest,
    }
