"""Dispatch endpoints: what the crews were sent and whether they have it (RF-104, RF-360).

The screen these serve is the one a dispatcher watches before the crews leave. It answers
one question the planning board cannot: assignment is an intention, delivery is a fact, and
the gap between them is work that will not get done today.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.dispatch import positions
from app.dispatch.service import device_readiness, dispatch_board
from app.infra.database import get_session
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.sync.models import Device
from app.sync.service import (
    CrossUnitError,
    assign_device_to_crew,
    build_offline_package,
    current_package,
)
from app.workorders.service import UnknownCrewError, get_crew_by_code

router = APIRouter(prefix="/api/v1/dispatch", tags=["dispatch"], dependencies=[Depends(unit_scope)])

SessionDep = Annotated[Session, Depends(get_session)]


def _unit(session: Session, code: str):  # type: ignore[no-untyped-def]
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/units/{unit_code}/board")
def board(
    session: SessionDep,
    unit_code: str,
    principal: Annotated[Any, Depends(unit_scope)] = None,
) -> list[dict[str, Any]]:
    """Per-crew dispatch state: assigned, delivered, stale, in progress, returned."""
    unit = _unit(session, unit_code)
    return [row.as_dict() for row in dispatch_board(session, unit, principal=principal)]


@router.get("/units/{unit_code}/devices")
def devices(session: SessionDep, unit_code: str) -> list[dict[str, Any]]:
    """Per-device readiness, with the reasons a phone should not leave yet."""
    unit = _unit(session, unit_code)
    return [row.as_dict() for row in device_readiness(session, unit)]


#: Quien despacha. Y solo quien despacha: saber dónde está cada compañero no es parte del trabajo de
#: campo, y un mapa de posiciones abierto a todo el personal es vigilancia entre pares con otro
#: nombre. El técnico reporta su posición y no lee la de nadie.
DISPATCHERS = (Role.SUPERVISOR, Role.PLANNER, Role.IT_ADMIN, Role.FUNCTIONAL_ADMIN)


@router.get(
    "/units/{unit_code}/crews.geojson",
    dependencies=[Depends(require_roles(*DISPATCHERS))],
    summary="La última posición de las cuadrillas, para el mapa de despacho (RF-020)",
)
def crew_positions(
    session: SessionDep,
    unit_code: str,
    zone: Annotated[str | None, Query()] = None,
    principal: Annotated[Any, Depends(require_roles(*DISPATCHERS))] = None,
) -> dict[str, Any]:
    """Las posiciones como GeoJSON, con su edad y con lo que no se puede afirmar de ellas.

    Cada punto lleva `minutes_old`, `stale` y `doubtful` porque una posición sin su edad miente: se
    captura cuando el teléfono sincroniza, así que es tan vieja como el último sync, y un punto de
    hace cuatro horas dibujado con la misma confianza que uno de hace uno manda una cuadrilla a la
    parroquia equivocada.
    """
    unit = _unit(session, unit_code)
    found = positions.crew_positions(session, unit, zone=zone, principal=principal)
    return {
        "type": "FeatureCollection",
        "features": [row.as_feature() for row in found],
        # Los umbrales, dichos por el servidor: si la web los repitiera, cambiarlos aquí dejaría a
        # la pantalla pintando «reciente» sobre lo que el servidor ya considera viejo.
        "stale_after_minutes": int(positions.STALE_AFTER.total_seconds() // 60),
        "doubtful_accuracy_m": positions.DOUBTFUL_ACCURACY_M,
    }


class DeviceCrewIn(BaseModel):
    """La cuadrilla a la que sirve un teléfono compartido; nula para soltarlo (RF-320)."""

    crew_code: str | None = Field(default=None, max_length=32)


@router.put(
    "/units/{unit_code}/devices/{device_key}/crew",
    summary="Declarar el teléfono compartido de una cuadrilla (RF-320)",
)
def set_device_crew(
    session: SessionDep,
    unit_code: str,
    device_key: str,
    payload: DeviceCrewIn,
    principal: Annotated[Any, Depends(require_roles(*DISPATCHERS))] = None,
) -> dict[str, Any]:
    """Desde aquí, una OT asignada solo a la cuadrilla llega a este teléfono en su próximo pull, y
    las que tenía de la cuadrilla anterior le llegan como retiradas.

    Lo fija la web y nunca el teléfono: un equipo que pudiera declarar su propia cuadrilla podría
    leer el trabajo de otra.
    """
    unit = _unit(session, unit_code)
    device = session.scalars(
        select(Device).where(Device.device_key == device_key, Device.business_unit_id == unit.id)
    ).first()
    if device is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "el dispositivo no está enrolado en esta unidad de negocio"
        )
    crew = None
    if payload.crew_code is not None:
        try:
            crew = get_crew_by_code(session, unit, payload.crew_code)
        except UnknownCrewError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        if not principal.may_see(zone=crew.zone, agency=crew.agency, contractor=crew.contractor):
            # Fuera del ámbito es «no existe» (RF-002), igual que en el resto de la plataforma.
            raise HTTPException(status.HTTP_404_NOT_FOUND, "la cuadrilla no existe")
        if not crew.active:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "la cuadrilla está desactivada; no recibe trabajo"
            )
    try:
        assign_device_to_crew(session, unit, device, crew, actor=principal.subject)
    except CrossUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    session.commit()
    return {
        "device_key": device.device_key,
        "crew_code": crew.code if crew is not None else None,
    }


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


@router.post(
    "/units/{unit_code}/packages",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.PLANNER, Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN))],
)
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
