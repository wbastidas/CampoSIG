"""Planner endpoints: the map, the board and assignment (RF-310..RF-324).

Assignment is graphical: the planner sees work on a map, lassos a selection and assigns it
to a crew. So the read endpoint speaks GeoJSON, which MapLibre consumes directly, and the
assign endpoint takes a list of ids because a lasso is inherently plural.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope_query
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.workorders.models import Crew, WorkOrder, WorkOrderState
from app.workorders.service import (
    ConcurrentEditError,
    CrossUnitError,
    NotAssignableError,
    assign,
    assign_many,
    crew_workload,
    custody_history,
    in_bounding_box,
)

# El ámbito se comprueba en la puerta del router (ADR-009). `/states` no lleva unidad y por eso
# se declara aparte, más abajo: es un catálogo de constantes, no datos de nadie.
router = APIRouter(
    prefix="/api/v1/planning", tags=["planning"], dependencies=[Depends(unit_scope_query)]
)

SessionDep = Annotated[Session, Depends(get_session)]

#: Cap on a single map query. A planner zoomed out to the whole country must not pull every
#: work order ever created into the browser.
MAX_MAP_FEATURES = 2000


def _unit(session: Session, code: str):  # type: ignore[no-untyped-def]
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


class BoundingBox(BaseModel):
    """A map viewport in WGS84 degrees, as MapLibre reports it."""

    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)


class AssignSelectionIn(BaseModel):
    """Assign a map selection to one crew."""

    work_order_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    crew_id: uuid.UUID
    reason: str | None = None


class AssignFailure(BaseModel):
    work_order_id: uuid.UUID
    message: str


class AssignSelectionOut(BaseModel):
    assigned: list[uuid.UUID]
    #: Partial success is normal: one refused pin must not lose the planner the others.
    failures: list[AssignFailure]


class AssignOneIn(BaseModel):
    crew_id: uuid.UUID
    device_id: str | None = None
    user_sub: str | None = None
    reason: str | None = None
    #: The version the planner was looking at. Sent so two planners never silently
    #: overwrite each other (RF-311).
    expected_version: int | None = None


class CustodyEntry(BaseModel):
    device_id: str | None
    user_sub: str | None
    since: str
    until: str | None
    reason: str | None
    had_unsynced_data: bool
    granted_by: str | None


@router.get(
    "/work-orders.geojson",
    summary="OT dentro del viewport, como GeoJSON para el mapa",
)
def work_orders_geojson(
    session: SessionDep,
    business_unit: str,
    west: float,
    south: float,
    east: float,
    north: float,
    unassigned_only: bool = False,
    states: Annotated[list[str] | None, Query()] = None,
    limit: int = MAX_MAP_FEATURES,
) -> dict[str, Any]:
    """A FeatureCollection MapLibre can render without transformation.

    GeoJSON rather than a bespoke shape so the map layer needs no adapter, and so the same
    response can drive clustering, styling and hit-testing straight from the library.
    """
    unit = _unit(session, business_unit)
    bounds = BoundingBox(west=west, south=south, east=east, north=north)
    orders = in_bounding_box(
        session,
        unit,
        west=bounds.west,
        south=bounds.south,
        east=bounds.east,
        north=bounds.north,
        states=states,
        unassigned_only=unassigned_only,
        limit=min(limit, MAX_MAP_FEATURES),
    )

    # Read coordinates back as lon/lat. Done in one query rather than per feature, because
    # a hundred round trips would make the map feel broken.
    from geoalchemy2.functions import ST_X, ST_Y

    coordinates = {
        row[0]: (row[1], row[2])
        for row in session.execute(
            select(WorkOrder.id, ST_X(WorkOrder.location), ST_Y(WorkOrder.location)).where(
                WorkOrder.id.in_([o.id for o in orders])
            )
        ).all()
    }

    features = []
    for order in orders:
        lon_lat = coordinates.get(order.id)
        if lon_lat is None or lon_lat[0] is None:
            continue
        features.append(
            {
                "type": "Feature",
                "id": str(order.id),
                "geometry": {"type": "Point", "coordinates": [lon_lat[0], lon_lat[1]]},
                "properties": {
                    "code": order.code or order.external_ref,
                    "work_type": order.work_type,
                    "form_code": order.form_code,
                    "state": order.state,
                    "priority": order.priority,
                    "assigned": order.assigned_crew_id is not None,
                    "crew_id": str(order.assigned_crew_id) if order.assigned_crew_id else None,
                    "asset_code": order.asset_code,
                    "feeder_code": order.feeder_code,
                    "sla_due_at": order.sla_due_at.isoformat() if order.sla_due_at else None,
                    "version": order.version,
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        # Told plainly so the UI can warn instead of silently showing a partial map.
        "truncated": len(orders) >= min(limit, MAX_MAP_FEATURES),
    }


@router.get("/crews", summary="Cuadrillas de la unidad con su carga abierta")
def crews_with_workload(session: SessionDep, business_unit: str) -> list[dict[str, Any]]:
    """The shared board several planners work against (RF-313)."""
    return crew_workload(session, _unit(session, business_unit))


@router.post(
    "/assign-selection",
    dependencies=[Depends(require_roles(Role.PLANNER, Role.SUPERVISOR))],
    response_model=AssignSelectionOut,
    summary="Asignar una selección del mapa a una cuadrilla",
)
def assign_selection(
    payload: AssignSelectionIn, session: SessionDep, business_unit: str
) -> AssignSelectionOut:
    unit = _unit(session, business_unit)
    crew = session.get(Crew, payload.crew_id)
    if crew is None or crew.business_unit_id != unit.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "la cuadrilla no existe en esta unidad de negocio"
        )
    try:
        assigned, failures = assign_many(
            session, unit, payload.work_order_ids, crew=crew, reason=payload.reason
        )
    except CrossUnitError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    session.commit()
    return AssignSelectionOut(
        assigned=[order.id for order in assigned],
        failures=[AssignFailure(work_order_id=oid, message=msg) for oid, msg in failures],
    )


@router.post(
    "/work-orders/{work_order_id}/assign",
    summary="Asignar o reasignar una OT",
    dependencies=[Depends(require_roles(Role.PLANNER, Role.SUPERVISOR))],
)
def assign_one(
    work_order_id: uuid.UUID, payload: AssignOneIn, session: SessionDep, business_unit: str
) -> dict[str, Any]:
    unit = _unit(session, business_unit)
    order = session.get(WorkOrder, work_order_id)
    if order is None or order.business_unit_id != unit.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "la OT no existe en esta unidad")
    crew = session.get(Crew, payload.crew_id)
    if crew is None or crew.business_unit_id != unit.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "la cuadrilla no existe en esta unidad de negocio"
        )
    try:
        assign(
            session,
            order,
            crew=crew,
            user_sub=payload.user_sub,
            device_id=payload.device_id,
            expected_version=payload.expected_version,
            reason=payload.reason,
        )
    except ConcurrentEditError as exc:
        # 409 so the UI can offer "reload and retry" rather than a generic failure.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except (NotAssignableError, CrossUnitError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    session.commit()
    return {"work_order_id": str(order.id), "state": order.state, "version": order.version}


@router.get(
    "/work-orders/{work_order_id}/custody",
    response_model=list[CustodyEntry],
    summary="Historial de custodia de una OT",
)
def get_custody(
    work_order_id: uuid.UUID, session: SessionDep, business_unit: str
) -> list[CustodyEntry]:
    """RF-324: who held it, on which device, since when and why."""
    unit = _unit(session, business_unit)
    order = session.get(WorkOrder, work_order_id)
    if order is None or order.business_unit_id != unit.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "la OT no existe en esta unidad")
    return [
        CustodyEntry(
            device_id=entry.device_id,
            user_sub=entry.user_sub,
            since=entry.since.isoformat(),
            until=entry.until.isoformat() if entry.until else None,
            reason=entry.reason,
            had_unsynced_data=entry.had_unsynced_data,
            granted_by=entry.granted_by,
        )
        for entry in custody_history(session, order)
    ]


@router.get("/states", summary="Estados de OT disponibles para filtrar el mapa")
def list_states() -> list[str]:
    return [state.value for state in WorkOrderState]
