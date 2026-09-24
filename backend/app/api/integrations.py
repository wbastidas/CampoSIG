"""The integrations screen's endpoints (RF-125).

What a person needs in order to fix an integration: which connector is unhappy, what exactly
failed, and a button that retries it. The retry is a real endpoint and not a hint, because a
ledger you can read but not act on just tells you about the problem twice a day.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.integrations import erp_adapter
from app.integrations.erp_models import StockLocationKind
from app.integrations.models import Connector, EventStatus, IntegrationEvent
from app.integrations.service import abandon, connector_health, ledger, retry_now
from app.integrations.transport import HttpTransport, TransportError
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.settings import get_settings

router = APIRouter(
    prefix="/api/v1/integrations", tags=["integrations"], dependencies=[Depends(unit_scope)]
)

SessionDep = Annotated[Session, Depends(get_session)]


def _unit(session: Session, code: str):  # type: ignore[no-untyped-def]
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _event(session: Session, unit_id: uuid.UUID, event_id: uuid.UUID) -> IntegrationEvent:
    event = session.get(IntegrationEvent, event_id)
    if event is None or event.business_unit_id != unit_id:
        # Same answer for "not yours" as for "does not exist" (ADR-009).
        raise HTTPException(status.HTTP_404_NOT_FOUND, "el evento de integración no existe")
    return event


def _as_dict(event: IntegrationEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "connector": event.connector,
        "direction": event.direction,
        "kind": event.kind,
        "status": event.status,
        "idempotency_key": event.idempotency_key,
        "external_ref": event.external_ref,
        "work_order_id": str(event.work_order_id) if event.work_order_id else None,
        "attempts": event.attempts,
        "last_error": event.last_error,
        "next_attempt_at": event.next_attempt_at.isoformat() if event.next_attempt_at else None,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "delivered_at": event.delivered_at.isoformat() if event.delivered_at else None,
        "needs_attention": event.needs_attention,
        "payload": event.payload,
        "response": event.response,
    }


@router.get("/units/{unit_code}/connectors")
def connectors(session: SessionDep, unit_code: str) -> list[dict[str, Any]]:
    """Per-connector state. `waiting_for_a_person` is the number that matters."""
    return connector_health(session, _unit(session, unit_code))


@router.get("/units/{unit_code}/events")
def events(
    session: SessionDep,
    unit_code: str,
    connector: Annotated[Connector | None, Query()] = None,
    event_status: Annotated[EventStatus | None, Query(alias="status")] = None,
    work_order_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[dict[str, Any]]:
    """The consultable log of every exchange, newest first."""
    unit = _unit(session, unit_code)
    rows = ledger(
        session,
        unit,
        connector=connector,
        status=event_status,
        order_id=work_order_id,
        limit=limit,
    )
    return [_as_dict(row) for row in rows]


@router.post("/units/{unit_code}/events/{event_id}/retry")
def retry(
    session: SessionDep,
    unit_code: str,
    event_id: uuid.UUID,
    principal: Annotated[Any, Depends(require_roles(Role.IT_ADMIN, Role.FUNCTIONAL_ADMIN))] = None,
) -> dict[str, Any]:
    """Put a failed exchange back in the queue (RF-125)."""
    unit = _unit(session, unit_code)
    event = retry_now(session, _event(session, unit.id, event_id), by=principal.subject)
    session.commit()
    return _as_dict(event)


class AbandonIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


@router.post("/units/{unit_code}/events/{event_id}/abandon")
def abandon_event(
    session: SessionDep,
    unit_code: str,
    event_id: uuid.UUID,
    payload: AbandonIn,
    principal: Annotated[Any, Depends(require_roles(Role.IT_ADMIN, Role.FUNCTIONAL_ADMIN))] = None,
) -> dict[str, Any]:
    """Give up on an exchange, on the record and with a reason."""
    unit = _unit(session, unit_code)
    event = abandon(
        session,
        _event(session, unit.id, event_id),
        reason=payload.reason,
        by=principal.subject,
    )
    session.commit()
    return _as_dict(event)


#: Who may pull from the ERP by hand. The same roles that run any other import: it is an
#: administrative act, and a supervisor pressing it would be pulling somebody else's inventory.
IMPORTERS = (Role.IT_ADMIN, Role.FUNCTIONAL_ADMIN)


@router.get("/units/{unit_code}/stock", summary="Existencias por bodega o vehículo (RF-122)")
def stock(
    session: SessionDep,
    unit_code: str,
    location_kind: Annotated[StockLocationKind | None, Query()] = None,
    location_code: Annotated[str | None, Query()] = None,
    material_code: Annotated[str | None, Query()] = None,
    _: Annotated[Any, Depends(require_roles(*IMPORTERS, Role.PLANNER, Role.SUPERVISOR))] = None,
) -> dict[str, Any]:
    """Lo que el ERP dijo la última vez, con la hora en que lo dijo.

    `as_of` viaja en cada línea a propósito: una existencia de un lote nocturno tiene horas, y un
    número presentado como actual es como una cuadrilla maneja hasta una bodega por algo que ya no
    está.
    """
    unit = _unit(session, unit_code)
    rows = erp_adapter.stock_of(
        session,
        unit,
        location_kind=location_kind.value if location_kind else None,
        location_code=location_code,
        material_code=material_code,
    )
    return {
        "lines": [
            {
                "material_code": row.material_code,
                "location_kind": row.location_kind,
                "location_code": row.location_code,
                "location_name": row.location_name,
                "quantity": float(row.quantity),
                "unit": row.unit,
                "as_of": row.as_of.isoformat(),
            }
            for row in rows
        ],
        # Los códigos con existencia que el catálogo no conoce. No es un error —los dos lotes
        # llegan por separado— pero es la señal de que se están desviando.
        "unknown_in_catalogue": erp_adapter.unknown_codes(session, unit),
    }


@router.post(
    "/units/{unit_code}/erp/import-materials",
    dependencies=[Depends(require_roles(*IMPORTERS))],
    summary="Traer el catálogo de materiales del ERP (RF-122)",
)
def import_materials(session: SessionDep, unit_code: str) -> dict[str, Any]:
    """El ERP es el dueño de estos valores: la plataforma los escribe solo como el ERP."""
    unit = _unit(session, unit_code)
    base_url = get_settings().erp_url
    if not base_url:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "el conector del ERP no está configurado; sin su URL no hay de dónde traer nada",
        )
    try:
        report = erp_adapter.import_materials(session, unit, HttpTransport(), base_url=base_url)
    except TransportError as exc:
        # 502 y no 500: el fallo es del sistema del otro lado, y la diferencia importa para quien
        # tiene que decidir a quién llamar.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    session.commit()
    return report


@router.post(
    "/units/{unit_code}/erp/import-stock",
    dependencies=[Depends(require_roles(*IMPORTERS))],
    summary="Traer las existencias del ERP (RF-122)",
)
def import_stock(session: SessionDep, unit_code: str) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    base_url = get_settings().erp_url
    if not base_url:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "el conector del ERP no está configurado; sin su URL no hay de dónde traer nada",
        )
    try:
        report = erp_adapter.import_stock(session, unit, HttpTransport(), base_url=base_url)
    except TransportError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    session.commit()
    return report
