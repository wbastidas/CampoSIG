"""Rutas sugeridas para un conjunto de OT (RF-025).

Una sugerencia, no una asignación ni un despacho: el planificador selecciona las OT en el mapa,
pide el orden y decide si lo sigue. Nada aquí escribe en ninguna OT.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.routing import service as routing

router = APIRouter(prefix="/api/v1/routing", tags=["routing"], dependencies=[Depends(unit_scope)])

SessionDep = Annotated[Session, Depends(get_session)]

#: Quien mueve gente en el mapa. Los mismos roles del despacho (RF-020): sugerir una ruta es parte
#: de decidir a quién mandar a dónde.
DISPATCHERS = (Role.SUPERVISOR, Role.PLANNER, Role.IT_ADMIN, Role.FUNCTIONAL_ADMIN)


def _unit(session: Session, code: str) -> Any:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


class RouteIn(BaseModel):
    """Qué ordenar y desde dónde, si hay un desde-dónde.

    Un punto de partida explícito y un dispositivo son excluyentes: pedir los dos sería ambiguo
    sobre cuál manda, y la API no adivina.
    """

    work_order_ids: list[uuid.UUID] = Field(min_length=2, max_length=routing.MAX_STOPS)
    start_latitude: float | None = Field(default=None, ge=-90, le=90)
    start_longitude: float | None = Field(default=None, ge=-180, le=180)
    #: Toma la última posición reportada por este dispositivo como punto de partida (RF-020).
    start_device_key: str | None = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def _one_start_at_most(self) -> RouteIn:
        explicit = self.start_latitude is not None or self.start_longitude is not None
        if explicit and (self.start_latitude is None or self.start_longitude is None):
            raise ValueError("la latitud y la longitud de inicio van juntas")
        if explicit and self.start_device_key is not None:
            raise ValueError("un punto de partida explícito y un dispositivo son excluyentes")
        return self


@router.post(
    "/units/{unit_code}/suggest",
    dependencies=[Depends(require_roles(*DISPATCHERS))],
    summary="Sugerir el orden de visita de un conjunto de OT (RF-025)",
)
def suggest(unit_code: str, payload: RouteIn, session: SessionDep) -> dict[str, Any]:
    unit = _unit(session, unit_code)
    start: tuple[float, float] | None = None
    if payload.start_latitude is not None and payload.start_longitude is not None:
        start = (payload.start_longitude, payload.start_latitude)
    elif payload.start_device_key is not None:
        try:
            start = routing.device_position(session, unit, payload.start_device_key)
        except routing.RoutingError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    try:
        suggestion = routing.suggest_route(session, unit, payload.work_order_ids, start=start)
    except routing.RoutingError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return suggestion.as_dict()
