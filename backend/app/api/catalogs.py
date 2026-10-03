"""Catalogue endpoints (RF-034, M04).

Three audiences, and they ask different questions:

* **A device** asks for the delta: everything above the revision it holds, retired values included.
* **A screen** asks for the resolved list: the active values this unit can choose from.
* **An administrator** writes. Only the ones the platform owns: a catalogue the ERP maintains
  refuses a hand edit, because a value typed over one the connector will overwrite tonight
  disappears without explanation.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal, require_roles, unit_scope
from app.auth.principal import Role
from app.catalogs import service as catalogs
from app.catalogs.service import MAX_DELTA
from app.infra.database import get_session
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code

# El segmento literal `catalog/` antes del código no es decoración: sin él,
# `/units/GYE/delta` casa con `/units/{unit_code}/{catalog_code}` y el delta del dispositivo
# resuelve al catálogo inexistente «delta». Lo encontró un test, y la forma de que no vuelva a
# pasar no es ordenar las rutas —deja la ambigüedad latente para un catálogo que se llame así—
# sino que ningún código de catálogo pueda ocupar la posición de un verbo.
router = APIRouter(
    prefix="/api/v1/catalogs", tags=["catalogs"], dependencies=[Depends(current_principal)]
)

SessionDep = Annotated[Session, Depends(get_session)]

EDITORS = (Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN)


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


class EntryIn(BaseModel):
    """One value. No author: it is the token's subject."""

    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    synonyms: list[str] = Field(default_factory=list, max_length=50)
    parent_code: str | None = Field(default=None, max_length=64)
    attributes: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    active: bool = True


@router.get("/", summary="Los catálogos que la plataforma sirve, con sus versiones (RF-034)")
def index(session: SessionDep) -> dict[str, Any]:
    """One number per catalogue, which is what a device compares before asking for a delta."""
    counts = catalogs.entry_counts(session)
    rows = []
    for catalog in catalogs.list_catalogs(session):
        live, gone = counts.get(catalog.code, (0, 0))
        rows.append(
            {
                "code": catalog.code,
                "title": catalog.title,
                "source": catalog.source,
                "version": catalog.version,
                "note": catalog.note,
                "active_entries": live,
                "retired_entries": gone,
                #: An empty catalogue is legitimate and has to explain itself: the political
                #: division is deliberately empty until the official list is loaded.
                "empty": live == 0,
            }
        )
    return {"catalogs": rows, "gis_backed": list(catalogs.GIS_BACKED)}


@router.get(
    "/units/{unit_code}/catalog/{catalog_code}",
    dependencies=[Depends(unit_scope)],
    summary="Los valores que puede elegir un técnico de esta unidad (RF-034)",
)
def resolved(session: SessionDep, unit_code: str, catalog_code: str) -> dict[str, Any]:
    """The national list with this unit's own additions folded in; a local code overrides."""
    unit = _unit(session, unit_code)
    try:
        return catalogs.resolve(session, catalog_code, unit).as_dict()
    except catalogs.UnknownCatalogError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get(
    "/units/{unit_code}/delta",
    dependencies=[Depends(unit_scope)],
    summary="Lo que cambió desde una revisión, lápidas incluidas (RF-034)",
)
def delta(
    session: SessionDep,
    unit_code: str,
    since: Annotated[int, Query(ge=0)] = 0,
    codes: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_DELTA)] = MAX_DELTA,
) -> dict[str, Any]:
    """The retired values travel too: a delta that skipped them would leave a phone offering a code
    the utility withdrew, and nobody would notice because the value looks ordinary."""
    unit = _unit(session, unit_code)
    return catalogs.delta(session, since=since, unit=unit, codes=codes, limit=limit).as_dict()


@router.put(
    "/catalog/{catalog_code}/entries/{entry_code}",
    dependencies=[Depends(require_roles(*EDITORS))],
    summary="Crear o corregir un valor nacional (RF-034)",
)
def upsert_national(
    session: SessionDep,
    catalog_code: str,
    entry_code: str,
    payload: EntryIn,
    principal: Annotated[Any, Depends(current_principal)] = None,
) -> dict[str, Any]:
    if payload.code != entry_code:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"el código de la ruta («{entry_code}») y el del cuerpo («{payload.code}») difieren",
        )
    try:
        row = catalogs.upsert_entry(
            session,
            catalog_code,
            entry_code=entry_code,
            label=payload.label,
            synonyms=payload.synonyms,
            parent_code=payload.parent_code,
            attributes=payload.attributes,
            sort_order=payload.sort_order,
            active=payload.active,
            actor=principal.subject,
        )
    except catalogs.NotEditableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except catalogs.UnknownCatalogError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    session.commit()
    return {"catalog": catalog_code, "code": row.code, "revision": row.revision}


@router.put(
    "/units/{unit_code}/catalog/{catalog_code}/entries/{entry_code}",
    dependencies=[Depends(unit_scope), Depends(require_roles(*EDITORS))],
    summary="Crear o corregir un valor propio de una unidad (RF-034)",
)
def upsert_local(
    session: SessionDep,
    unit_code: str,
    catalog_code: str,
    entry_code: str,
    payload: EntryIn,
    principal: Annotated[Any, Depends(current_principal)] = None,
) -> dict[str, Any]:
    """A unit's value with a national one's code overrides it rather than duplicating it."""
    unit = _unit(session, unit_code)
    try:
        row = catalogs.upsert_entry(
            session,
            catalog_code,
            entry_code=entry_code,
            label=payload.label,
            unit=unit,
            synonyms=payload.synonyms,
            parent_code=payload.parent_code,
            attributes=payload.attributes,
            sort_order=payload.sort_order,
            active=payload.active,
            actor=principal.subject,
        )
    except catalogs.NotEditableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except catalogs.UnknownCatalogError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    session.commit()
    return {"catalog": catalog_code, "code": row.code, "revision": row.revision}


@router.delete(
    "/catalog/{catalog_code}/entries/{entry_code}",
    dependencies=[Depends(require_roles(*EDITORS))],
    summary="Retirar un valor nacional (RF-034)",
)
def retire_national(
    session: SessionDep,
    catalog_code: str,
    entry_code: str,
    principal: Annotated[Any, Depends(current_principal)] = None,
) -> dict[str, Any]:
    """Deactivates; there is no delete. The tombstone has to reach the device."""
    try:
        row = catalogs.retire_entry(session, catalog_code, entry_code, actor=principal.subject)
    except catalogs.UnknownCatalogError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    session.commit()
    return {"catalog": catalog_code, "code": row.code, "active": row.active}
