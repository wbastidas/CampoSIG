"""Consignaciones (RF-024).

Quien planifica solicita; el Centro de Control otorga o niega. Son dos roles distintos y dos
endpoints distintos a propósito: un descargo que alguien se dio a sí mismo es justamente lo que el
procedimiento existe para evitar, y el servicio lo rechaza además por autor.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.outages import service as outages
from app.outages.models import OutageRequest, OutageState
from app.workorders.models import WorkOrder

router = APIRouter(prefix="/api/v1/outages", tags=["outages"], dependencies=[Depends(unit_scope)])

SessionDep = Annotated[Session, Depends(get_session)]

#: Quien solicita. Planificación, y la administración funcional para poder cargar lo ya acordado.
REQUESTERS = (Role.PLANNER, Role.FUNCTIONAL_ADMIN)

#: Quien otorga. El Centro de Control es operación: el supervisor de operación y la administración
#: de TI para los casos de soporte. No el planificador, que es quien pide.
GRANTERS = (Role.SUPERVISOR, Role.IT_ADMIN)

READERS = (*REQUESTERS, *GRANTERS, Role.AUDITOR, Role.TECHNICIAN)


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _request(session: Session, unit: BusinessUnit, request_id: uuid.UUID) -> OutageRequest:
    row = session.get(OutageRequest, request_id)
    if row is None or row.business_unit_id != unit.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "la consignación no existe en esta unidad de negocio"
        )
    return row


class RequestIn(BaseModel):
    """A consignación as the planner asks for it.

    No `requested_by`: the requester is the token's subject. It has to be, because the service
    refuses an approval by the same person — and a requester the caller could type would make that
    refusal decorative.
    """

    equipment: str = Field(min_length=1, max_length=255)
    window_start: datetime
    window_end: datetime
    feeder_code: str | None = None
    substation_code: str | None = None
    note: str | None = Field(default=None, max_length=2000)


class ApproveIn(BaseModel):
    number: str = Field(min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=2000)


class RejectIn(BaseModel):
    """The reason is required: «no» without one sends the planner to the phone."""

    note: str = Field(min_length=1, max_length=2000)


class LinkIn(BaseModel):
    work_order_id: uuid.UUID


@router.get("/units/{unit_code}", summary="Las consignaciones de la unidad (RF-024)")
def index(
    unit_code: str,
    session: SessionDep,
    state: Annotated[OutageState | None, Query()] = None,
    _: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    rows = outages.requests_of(session, unit, state=state.value if state else None)
    unused = set(outages.unused_ids(session, unit))
    return {
        "counts": outages.pending_for(session, unit),
        "requests": [
            {
                **outages.as_dict(row, orders=len(outages.orders_under(session, row))),
                # Una consignación otorgada sin ninguna OT es una línea desenergizada para nada:
                # clientes sin servicio y un índice que la unidad reporta. Se muestra, no se cuenta
                # en silencio.
                "unused": row.id in unused,
            }
            for row in rows
        ],
    }


@router.get("/units/{unit_code}/{request_id}", summary="Una consignación con sus OT")
def detail(
    unit_code: str,
    request_id: uuid.UUID,
    session: SessionDep,
    _: Annotated[Any, Depends(require_roles(*READERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    row = _request(session, unit, request_id)
    orders = outages.orders_under(session, row)
    return {
        **outages.as_dict(row, orders=len(orders)),
        "work_orders": [
            {
                "work_order_id": str(order.id),
                "code": order.code,
                "work_type": order.work_type,
                "state": order.state,
                "form_code": order.form_code,
            }
            for order in orders
        ],
    }


@router.post(
    "/units/{unit_code}",
    dependencies=[Depends(require_roles(*REQUESTERS))],
    summary="Solicitar una consignación al Centro de Control (RF-024)",
)
def create(
    unit_code: str,
    payload: RequestIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*REQUESTERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    try:
        row = outages.request_outage(
            session,
            unit,
            equipment=payload.equipment,
            window_start=payload.window_start,
            window_end=payload.window_end,
            requested_by=principal.subject,
            feeder_code=payload.feeder_code,
            substation_code=payload.substation_code,
            note=payload.note,
        )
    except outages.OutageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return outages.as_dict(row)


@router.post(
    "/units/{unit_code}/{request_id}/approve",
    dependencies=[Depends(require_roles(*GRANTERS))],
    summary="Otorgar la consignación con su número (RF-024)",
)
def approve(
    unit_code: str,
    request_id: uuid.UUID,
    payload: ApproveIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*GRANTERS))] = None,
) -> dict[str, Any]:
    """El número es la autoridad: lo que la cuadrilla repite por radio y lo que se pide después."""
    unit = _unit(session, unit_code)
    row = _request(session, unit, request_id)
    try:
        outages.approve(
            session,
            unit,
            row,
            number=payload.number,
            decided_by=principal.subject,
            note=payload.note,
        )
    except outages.SelfApprovalError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except outages.NotDecidableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except outages.OutageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return outages.as_dict(row)


@router.post(
    "/units/{unit_code}/{request_id}/reject",
    dependencies=[Depends(require_roles(*GRANTERS))],
    summary="Negar la consignación, con el motivo (RF-024)",
)
def reject(
    unit_code: str,
    request_id: uuid.UUID,
    payload: RejectIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*GRANTERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    row = _request(session, unit, request_id)
    try:
        outages.reject(session, unit, row, decided_by=principal.subject, note=payload.note)
    except outages.SelfApprovalError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except outages.NotDecidableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except outages.OutageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return outages.as_dict(row)


@router.post(
    "/units/{unit_code}/{request_id}/return",
    dependencies=[Depends(require_roles(*GRANTERS, Role.CREW_LEADER))],
    summary="Devolver la consignación al Centro de Control (RF-024)",
)
def hand_back(
    unit_code: str,
    request_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*GRANTERS, Role.CREW_LEADER))] = None,
) -> dict[str, Any]:
    """La devuelve quien la recibió: el jefe de cuadrilla, o el Centro de Control por él."""
    unit = _unit(session, unit_code)
    row = _request(session, unit, request_id)
    try:
        outages.hand_back(session, unit, row, returned_by=principal.subject)
    except outages.OutageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return outages.as_dict(row)


@router.post(
    "/units/{unit_code}/{request_id}/work-orders",
    dependencies=[Depends(require_roles(*REQUESTERS, *GRANTERS))],
    summary="Vincular una OT a la consignación bajo la que trabajará (RF-024)",
)
def link_order(
    unit_code: str,
    request_id: uuid.UUID,
    payload: LinkIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*REQUESTERS, *GRANTERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    row = _request(session, unit, request_id)
    order = session.get(WorkOrder, payload.work_order_id)
    if order is None or order.business_unit_id != unit.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "la OT no existe en esta unidad de negocio")
    try:
        outages.link(session, unit, order, row, actor=principal.subject)
    except outages.OutageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return {"work_order_id": str(order.id), "number": row.number, "state": row.state}


@router.delete(
    "/units/{unit_code}/work-orders/{work_order_id}",
    dependencies=[Depends(require_roles(*REQUESTERS, *GRANTERS))],
    summary="Desvincular una OT de su consignación (RF-024)",
)
def unlink_order(
    unit_code: str,
    work_order_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*REQUESTERS, *GRANTERS))] = None,
) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    order = session.get(WorkOrder, work_order_id)
    if order is None or order.business_unit_id != unit.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "la OT no existe en esta unidad de negocio")
    try:
        outages.unlink(session, unit, order, actor=principal.subject)
    except outages.OutageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return {"work_order_id": str(order.id), "outage_request_id": None}
