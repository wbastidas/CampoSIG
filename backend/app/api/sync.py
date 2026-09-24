"""El contrato de sincronización del móvil (RF-004, RF-101 a RF-106).

Esto es lo único que el teléfono conoce de la plataforma: enrolarse, pedir lo que cambió y
entregar lo que capturó. **No conoce ArcGIS** (ADR-003) ni sabe a qué geodatabase acaba lo que
envía (ADR-009).

Tres reglas de este borde:

* **El dispositivo es del técnico que lo lleva.** La clave del dispositivo no basta: si el
  dispositivo está enrolado a nombre de alguien, el llamante tiene que ser ese alguien. Una clave de
  dispositivo es un dato que se puede copiar; el token, no.
* **Entregar es idempotente y el reenvío devuelve el resultado guardado**, que es lo que deja a la
  bandeja de salida reintentar sin miedo sobre un enlace que se cae a la mitad (RF-105).
* **Lo que no se puede aplicar se rechaza con su motivo y se registra**, nunca con un error de
  servidor: el teléfono tiene que *aparcar* esa operación y mostrársela a una persona. Un 500 haría
  que la reintentara para siempre.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.functions import ST_X, ST_Y
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Principal, Role
from app.catalogs.service import versions as catalog_versions
from app.infra.database import get_session
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.outages.models import OutageRequest
from app.sync import service as sync
from app.sync.models import Device
from app.sync.operations import OperationRejectedError, apply_operation, order_of
from app.workorders.models import WorkOrder

router = APIRouter(prefix="/api/v1/sync", tags=["sync"], dependencies=[Depends(unit_scope)])

SessionDep = Annotated[Session, Depends(get_session)]

#: Quien lleva un teléfono al campo. El administrador de TI entra para soporte: es quien recibe la
#: llamada de «se me bloqueó el equipo» y tiene que poder reproducirla.
FIELD_ROLES = (Role.TECHNICIAN, Role.CREW_LEADER, Role.INSPECTOR)
DEVICE_ROLES = (*FIELD_ROLES, Role.IT_ADMIN)

#: Cuántas OT lleva un `pull`. Un tope, porque el primer sync de un teléfono nuevo con toda una zona
#: asignada sería una respuesta que no termina de bajar en una parroquia rural.
MAX_PULL = 200


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _device(session: Session, unit: BusinessUnit, principal: Principal, device_key: str) -> Device:
    """The device this call is about, confirmed to be this unit's and this person's.

    :raises HTTPException: 404 unknown, 403 blocked (with the wipe instruction) or another
        person's.
    """
    try:
        device = sync.resolve_device(session, device_key)
    except sync.UnknownDeviceError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except sync.DeviceBlockedError as exc:
        # 403 with the instruction, not a bare refusal: a blocked phone has to destroy its local
        # database, and it only learns that here (RF-004).
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            {"detail": str(exc), "wipe": True},
        ) from exc
    if device.business_unit_id != unit.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "el dispositivo no está enrolado en esta unidad de negocio"
        )
    if (
        device.user_sub
        and device.user_sub != principal.subject
        and not principal.has(Role.IT_ADMIN.value)
    ):
        # A device key travels in a QR code and can be copied; the token cannot. Without this, one
        # technician's key would pull another's work.
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "este dispositivo está enrolado a nombre de otra persona"
        )
    return device


class EnrolIn(BaseModel):
    """Lo que el teléfono dice de sí mismo al enrolarse.

    Sin `user_sub`: el titular sale del token. Un dispositivo cuyo titular pudiera escribir el
    llamante haría decorativa la comprobación de arriba.
    """

    device_key: str = Field(min_length=8, max_length=128)
    model: str | None = Field(default=None, max_length=128)
    android_version: str | None = Field(default=None, max_length=32)
    app_version: str | None = Field(default=None, max_length=32)
    model_package_version: str | None = Field(default=None, max_length=32)


class OperationIn(BaseModel):
    """Una operación de la bandeja de salida del teléfono."""

    operation_id: str = Field(min_length=1, max_length=64)
    kind: str = Field(min_length=1, max_length=32)
    work_order_id: uuid.UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    #: El reloj del teléfono, que se guarda aparte del del servidor: trabajan offline y derivan.
    device_created_at: datetime | None = None


class PushIn(BaseModel):
    device_key: str = Field(min_length=8, max_length=128)
    operations: list[OperationIn] = Field(min_length=1, max_length=200)


@router.post(
    "/units/{unit_code}/devices",
    dependencies=[Depends(require_roles(*DEVICE_ROLES))],
    summary="Enrolar el dispositivo, o actualizar lo que se sabe de él (RF-004)",
)
def enrol(
    unit_code: str,
    payload: EnrolIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*DEVICE_ROLES))] = None,
) -> dict[str, Any]:
    """Idempotente: la app se reenrola en cada actualización y tras una reinstalación."""
    unit = _unit(session, unit_code)
    existing = session.scalars(
        select(Device).where(Device.device_key == payload.device_key)
    ).first()
    if existing is not None and existing.business_unit_id != unit.id:
        # Reenrolar en otra unidad movería el trabajo capturado de geodatabase (ADR-009). Se niega
        # y se dice: el dispositivo se da de baja y se enrola de nuevo, con un acta.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "el dispositivo ya está enrolado en otra unidad de negocio",
        )
    device, created = sync.enrol_device(
        session,
        unit,
        device_key=payload.device_key,
        user_sub=principal.subject,
        model=payload.model,
        android_version=payload.android_version,
        app_version=payload.app_version,
    )
    if payload.model_package_version:
        device.model_package_version = payload.model_package_version
    session.commit()
    return {
        "device_id": str(device.id),
        "device_key": device.device_key,
        "business_unit": unit.code,
        "user_sub": device.user_sub,
        "status": device.status,
        "created": created,
        "enrolled_at": device.enrolled_at.isoformat(),
    }


@router.get(
    "/units/{unit_code}/pull",
    dependencies=[Depends(require_roles(*DEVICE_ROLES))],
    summary="Lo que cambió para este dispositivo desde el cursor (RF-102)",
)
def pull(
    unit_code: str,
    session: SessionDep,
    device_key: Annotated[str, Query(min_length=8, max_length=128)],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PULL)] = MAX_PULL,
    principal: Annotated[Any, Depends(require_roles(*DEVICE_ROLES))] = None,
) -> dict[str, Any]:
    """Delta por cursor, no por «desde esta fecha»: el reloj del teléfono no manda."""
    unit = _unit(session, unit_code)
    device = _device(session, unit, principal, device_key)
    orders, next_cursor = sync.pull_work_orders(session, device, cursor=cursor, limit=limit)
    session.commit()
    return {
        "server_time": datetime.now(UTC).isoformat(),
        "work_orders": _for_device(session, orders),
        # Nulo cuando no cambió nada: el teléfono conserva el cursor que ya tenía.
        "next_cursor": next_cursor,
        "form_versions": sync.form_versions(session),
        "catalog_versions": catalog_versions(session),
    }


@router.post(
    "/units/{unit_code}/push",
    dependencies=[Depends(require_roles(*FIELD_ROLES))],
    summary="Entregar lo capturado, idempotentemente (RF-101, RF-105)",
)
def push(
    unit_code: str,
    payload: PushIn,
    session: SessionDep,
    principal: Annotated[Any, Depends(require_roles(*FIELD_ROLES))] = None,
) -> dict[str, Any]:
    """Cada operación con su resultado, y un reenvío devuelve el resultado guardado."""
    unit = _unit(session, unit_code)
    device = _device(session, unit, principal, payload.device_key)

    # El lote se revisa entero **antes** de aplicar nada: un dispositivo que manda trabajo de otra
    # unidad de negocio es una anomalía, no un dato malo, y se niega completo (ADR-009). Revisarlo
    # operación por operación dejaría aplicada la mitad del lote antes de encontrar la que cruza.
    _refuse_foreign_work(session, device, payload)

    results: list[dict[str, Any]] = []
    for operation in payload.operations:
        entry, applied = sync.push_operation(
            session,
            device,
            operation_id=operation.operation_id,
            kind=operation.kind,
            work_order_id=operation.work_order_id,
            payload=operation.payload,
            device_created_at=operation.device_created_at,
        )

        if not applied:
            results.append(_outcome(entry, replay=True))
            continue
        if not entry.accepted:
            # La bitácora ya lo rechazó: la OT no existe en el servidor.
            results.append(_outcome(entry, replay=False))
            continue

        try:
            entry.result = apply_operation(
                session,
                unit,
                device,
                kind=operation.kind,
                order=order_of(session, operation.work_order_id),
                payload=operation.payload,
            )
        except OperationRejectedError as exc:
            entry.accepted = False
            entry.rejection_reason = str(exc)[:500]
            entry.result = {"rejected": True}
        session.flush()
        results.append(_outcome(entry, replay=False))

    session.commit()
    return {
        "device_key": device.device_key,
        "accepted": sum(1 for item in results if item["accepted"]),
        "rejected": sum(1 for item in results if not item["accepted"]),
        "operations": results,
    }


@router.post(
    "/units/{unit_code}/wipe-acknowledged",
    dependencies=[Depends(require_roles(*DEVICE_ROLES))],
    summary="El dispositivo confirma que destruyó su base local (RF-004)",
)
def acknowledge_wipe(
    unit_code: str,
    session: SessionDep,
    device_key: Annotated[str, Query(min_length=8, max_length=128)],
    _: Annotated[Any, Depends(require_roles(*DEVICE_ROLES))] = None,
) -> dict[str, Any]:
    """Se acepta de un dispositivo **bloqueado**: es el único que tiene algo que confirmar.

    Sin esto, quien bloqueó un teléfono perdido no tiene forma de saber si el borrado ocurrió, y esa
    es justamente la pregunta que hay que contestar después de una pérdida.
    """
    unit = _unit(session, unit_code)
    device = session.scalars(select(Device).where(Device.device_key == device_key)).first()
    if device is None or device.business_unit_id != unit.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "el dispositivo no está enrolado en esta unidad de negocio"
        )
    if device.wipe_acknowledged_at is None:
        device.wipe_acknowledged_at = datetime.now(UTC)
    session.commit()
    return {
        "device_key": device.device_key,
        "status": device.status,
        "wipe_acknowledged_at": device.wipe_acknowledged_at.isoformat(),
    }


def _refuse_foreign_work(session: Session, device: Device, payload: PushIn) -> None:
    """Refuse the whole batch if any operation names another unit's work order (ADR-009).

    Up front and not inside the loop, for two reasons: half a batch applied before the offending
    operation is found would be a partial delivery nobody asked for, and the device needs one clear
    answer — «este lote no», not «tres sí y una no».
    """
    ids = {operation.work_order_id for operation in payload.operations if operation.work_order_id}
    if not ids:
        return
    foreign = session.execute(
        select(WorkOrder.id).where(
            WorkOrder.id.in_(ids), WorkOrder.business_unit_id != device.business_unit_id
        )
    ).first()
    if foreign is not None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "una operación no puede afectar trabajo de otra unidad de negocio",
        )


def _outcome(entry: Any, *, replay: bool) -> dict[str, Any]:
    return {
        "operation_id": entry.operation_id,
        "kind": entry.kind,
        "accepted": entry.accepted,
        # `replay` es lo que le dice a la bandeja de salida «ya estaba, bórralo» sin volver a
        # aplicar nada: sin este campo, el teléfono no distingue un éxito nuevo de uno repetido.
        "replay": replay,
        "rejection_reason": entry.rejection_reason,
        "result": entry.result,
        "received_at": entry.received_at.isoformat() if entry.received_at else None,
    }


def _for_device(session: Session, orders: list[WorkOrder]) -> list[dict[str, Any]]:
    """Las OT como las necesita el teléfono, con su ubicación y su consignación.

    La consignación viaja **dentro** de la OT: el permiso de trabajo F-TR-02 exige el número y el
    teléfono lo llena en una subestación sin cobertura (RF-024). Un número que hubiera que consultar
    al servidor sería un permiso que no se puede llenar donde se llena.
    """
    if not orders:
        return []
    coordinates = {
        row[0]: (row[1], row[2])
        for row in session.execute(
            select(WorkOrder.id, ST_X(WorkOrder.location), ST_Y(WorkOrder.location)).where(
                WorkOrder.id.in_([order.id for order in orders])
            )
        ).all()
    }
    outage_ids = {order.outage_request_id for order in orders if order.outage_request_id}
    outages: dict[uuid.UUID, OutageRequest] = {}
    if outage_ids:
        outages = {
            row.id: row
            for row in session.scalars(
                select(OutageRequest).where(OutageRequest.id.in_(outage_ids))
            )
        }

    payload: list[dict[str, Any]] = []
    for order in orders:
        lon_lat = coordinates.get(order.id) or (None, None)
        outage = outages.get(order.outage_request_id) if order.outage_request_id else None
        payload.append(
            {
                "work_order_id": str(order.id),
                "code": order.code or order.external_ref,
                "work_type": order.work_type,
                "form_code": order.form_code,
                # La versión con la que se ejecuta, congelada al asignar (RF-032): el teléfono
                # llena esa y no la que esté vigente al cerrar.
                "form_version": order.form_version,
                "state": order.state,
                "priority": order.priority,
                "description": order.description,
                "asset_type_key": order.asset_type_key,
                "asset_code": order.asset_code,
                "longitude": lon_lat[0],
                "latitude": lon_lat[1],
                "feeder_code": order.feeder_code,
                "zone": order.zone,
                "sla_due_at": order.sla_due_at.isoformat() if order.sla_due_at else None,
                #: La obra de la que este frente es parte (RF-015), para que el teléfono agrupe.
                "parent_id": str(order.parent_id) if order.parent_id else None,
                "version": order.version,
                "updated_at": order.updated_at.isoformat(),
                "outage": (
                    {
                        "number": outage.number,
                        "equipment": outage.equipment,
                        "window_start": outage.window_start.isoformat(),
                        "window_end": outage.window_end.isoformat(),
                        # Lo que decide si el F-TR-02 se habilita, resuelto en el servidor: el
                        # teléfono no reimplementa la regla, la obedece.
                        "grants_permit": outage.grants_permit,
                    }
                    if outage is not None
                    else None
                ),
            }
        )
    return payload
