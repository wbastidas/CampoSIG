"""Form publication (RF-032, M04).

Publishing is the act that freezes a shape, so it is functional administration and not a planning
convenience: after it, every new work order carries that version for the rest of its life.

Reading is wider — a supervisor looking at a returned order needs to know which version it was
filled in with, and a planner needs to see what a phone will download.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import current_principal, require_roles
from app.auth.principal import Role
from app.forms import registry
from app.forms.catalog import CatalogError, load_definitions
from app.infra.database import get_session

# Los formularios son nacionales, como el modelo de datos del que se generan (ADR-009), así que aquí
# no hay ámbito por unidad — pero sí hace falta estar autenticado.
router = APIRouter(
    prefix="/api/v1/forms", tags=["forms"], dependencies=[Depends(current_principal)]
)

SessionDep = Annotated[Session, Depends(get_session)]

EDITORS = (Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN)


class PublishIn(BaseModel):
    """Why this version is being published. No author: it is the token's subject."""

    note: str | None = Field(default=None, max_length=2000)


@router.get("/catalogue", summary="Qué hay en el archivo y qué está publicado (RF-032)")
def catalogue(session: SessionDep) -> dict[str, Any]:
    """The two states side by side.

    A code whose file version differs from the published one has an unpublished draft, and that is
    the one thing this screen exists to make visible: a form edited weeks ago that nobody published
    is a form nobody in the field has ever seen.
    """
    published = registry.published_versions(session)
    rows = []
    for code, definition in sorted(load_definitions().items()):
        in_force = published.get(code)
        rows.append(
            {
                "code": code,
                "title": definition.form.title,
                "area": definition.form.area.value,
                "file_version": definition.version,
                "published_version": in_force,
                "has_unpublished_draft": in_force is not None and in_force != definition.version,
                "never_published": in_force is None,
            }
        )
    return {"forms": rows}


@router.get("/{code}/versions", summary="Historia de versiones publicadas de un formulario")
def versions(session: SessionDep, code: str) -> list[dict[str, Any]]:
    return [registry.as_dict(row) for row in registry.history(session, code)]


@router.post(
    "/{code}/publish",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*EDITORS))],
    summary="Publicar la versión del archivo y congelar su forma (RF-032)",
)
def publish(
    session: SessionDep,
    code: str,
    payload: PublishIn,
    principal: Annotated[Any, Depends(current_principal)] = None,
) -> dict[str, Any]:
    """After this, a new order carries this version for the rest of its life."""
    try:
        row = registry.publish(session, code, actor=principal.subject, note=payload.note)
    except CatalogError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except registry.AlreadyPublishedError as exc:
        # 409, not 422: the request is well formed and the conflict is with what already exists.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    session.commit()
    return registry.as_dict(row)


@router.post(
    "/{code}/versions/{version}/obsolete",
    dependencies=[Depends(require_roles(*EDITORS))],
    summary="Retirar una versión para que no la use ninguna OT nueva (RF-032)",
)
def obsolete(
    session: SessionDep,
    code: str,
    version: str,
    principal: Annotated[Any, Depends(current_principal)] = None,
) -> dict[str, Any]:
    """The orders already carrying it still compose against it: they exist and must be closed."""
    try:
        row = registry.obsolete(session, code, version, actor=principal.subject)
    except registry.FormNotPublishedError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    session.commit()
    return registry.as_dict(row)
