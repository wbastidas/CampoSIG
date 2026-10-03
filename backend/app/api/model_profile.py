"""The profile importer's endpoints: `/admin/model-profile` behind the web (RF-301, RF-302).

What acceptance of I2 asks for, in HTTP terms: starting from the metadata export of another
business unit, a functional administrator produces a working profile and generates the
forms **without writing code or recompiling**.

Every route is scoped to a business unit and restricted to the functional or IT
administrator. A data-model profile decides where field data lands, so it is not something a
planner or a supervisor should be able to change — and `unit_scope_query` at the router door
means a route added later cannot forget either check.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import PrincipalDep, require_roles, unit_scope_query
from app.auth.principal import Role
from app.gis_gateway.ingest import current_snapshot
from app.infra.database import get_session
from app.model_profile.drafts import (
    DraftError,
    history,
    open_draft,
    publish_draft,
    published_draft,
    save_decisions,
    start_draft,
)
from app.model_profile.matching import (
    AssetProposal,
    DocumentError,
    ProfileDecisions,
    ProfileProposal,
    propose_asset_against,
    propose_profile,
    render_profile_yaml,
)
from app.model_profile.metadata import GisMetadata
from app.model_profile.models import ProfileDraft
from app.model_profile.profile import ProfileHeader
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code

router = APIRouter(
    prefix="/api/v1/model-profile",
    tags=["model-profile"],
    dependencies=[Depends(unit_scope_query)],
)

SessionDep = Annotated[Session, Depends(get_session)]

#: Who may touch a profile. Narrow on purpose: this is the mapping that decides which
#: feature class a crew's work is written to.
AdminDep = Annotated[Any, Depends(require_roles(Role.FUNCTIONAL_ADMIN, Role.IT_ADMIN))]


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _metadata(session: Session, unit: BusinessUnit) -> tuple[GisMetadata, uuid.UUID]:
    snapshot = current_snapshot(session, unit.id)
    if snapshot is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"la unidad '{unit.code}' no tiene metadatos sincronizados; su agente arcpy "
            "todavía no ha corrido, y sin metadatos no hay nada que mapear",
        )
    return GisMetadata.model_validate(snapshot.payload), snapshot.id


# --- request / response models ------------------------------------------------------
class DraftOut(BaseModel):
    draft_id: uuid.UUID
    business_unit_code: str
    profile_id: str
    version: int
    status: str
    ready: bool
    problems: list[str]
    decisions: dict[str, Any]
    document: dict[str, Any] | None
    created_by: str
    updated_by: str | None
    published_by: str | None
    updated_at: str | None
    published_at: str | None

    @classmethod
    def of(cls, draft: ProfileDraft, unit_code: str) -> DraftOut:
        return cls(
            draft_id=draft.id,
            business_unit_code=unit_code,
            profile_id=draft.profile_id,
            version=draft.version,
            status=draft.status,
            ready=draft.ready,
            problems=list(draft.problems),
            decisions=dict(draft.decisions),
            document=dict(draft.document) if draft.document else None,
            created_by=draft.created_by,
            updated_by=draft.updated_by,
            published_by=draft.published_by,
            updated_at=draft.updated_at.isoformat() if draft.updated_at else None,
            published_at=draft.published_at.isoformat() if draft.published_at else None,
        )


class ProposalOut(BaseModel):
    """The proposal, plus what the administrator still has to decide."""

    profile_id: str
    proposal: ProfileProposal
    gaps: list[str]
    layer_names: list[str] = Field(
        description="Toda clase del snapshot, para elegir a mano cuando la propuesta falla"
    )


class StartDraftIn(BaseModel):
    """Only the header travels: the decisions come from the proposal, and the identity
    from the token (ADR-013)."""

    profile_id: str
    label: str | None = None
    arcgis_version: str | None = None
    geometric_network: str | None = None
    feature_dataset: str | None = None


class SaveDecisionsIn(BaseModel):
    decisions: ProfileDecisions


class HistoryEntry(BaseModel):
    draft_id: uuid.UUID
    version: int
    status: str
    problems: list[str]
    created_by: str
    published_by: str | None
    published_at: str | None


# --- routes -------------------------------------------------------------------------
@router.get(
    "/proposal",
    response_model=ProposalOut,
    summary="Proponer bindings desde los metadatos vigentes, con la evidencia de cada uno",
)
def get_proposal(
    session: SessionDep, business_unit: str, principal: AdminDep = None
) -> ProposalOut:
    """Assisted matching over the current snapshot. Proposes; never binds."""
    unit = _unit(session, business_unit)
    metadata, _ = _metadata(session, unit)
    proposal = propose_profile(metadata)
    return ProposalOut(
        profile_id=unit.profile_id,
        proposal=proposal,
        gaps=proposal.gaps,
        layer_names=sorted(layer.name for layer in metadata.layers),
    )


@router.get(
    "/proposal/{asset_type_key}",
    response_model=AssetProposal,
    summary="Reevaluar un tipo de activo contra una clase elegida a mano",
)
def get_asset_proposal(
    asset_type_key: str,
    layer: str,
    session: SessionDep,
    business_unit: str,
    principal: AdminDep = None,
) -> AssetProposal:
    """Re-score one asset type when the administrator rejects the leading candidate."""
    unit = _unit(session, business_unit)
    metadata, _ = _metadata(session, unit)
    try:
        return propose_asset_against(metadata, asset_type_key, layer)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except DocumentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post(
    "/drafts",
    response_model=DraftOut,
    status_code=status.HTTP_201_CREATED,
    summary="Abrir un borrador de perfil, prellenado con lo que la evidencia resuelve",
)
def create_draft(
    payload: StartDraftIn,
    session: SessionDep,
    business_unit: str,
    principal: PrincipalDep,
    _admin: AdminDep = None,
) -> DraftOut:
    unit = _unit(session, business_unit)
    metadata, snapshot_id = _metadata(session, unit)
    header = ProfileHeader(
        id=payload.profile_id,
        label=payload.label,
        # The agent is the only provider there is (ADR-008); it is not a choice a screen
        # should offer, so it is not in the request body.
        provider="arcpy-agent",
        arcgis_version=payload.arcgis_version,
        spatial_reference=unit.spatial_reference,
        geometric_network=payload.geometric_network,
        feature_dataset=payload.feature_dataset,
    )
    try:
        draft = start_draft(
            session,
            unit_id=unit.id,
            profile_id=payload.profile_id,
            header=header,
            metadata=metadata,
            snapshot_id=snapshot_id,
            created_by=principal.subject,
        )
    except DraftError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    session.commit()
    return DraftOut.of(draft, unit.code)


@router.get(
    "/drafts/current",
    response_model=DraftOut,
    summary="El borrador abierto de un perfil en esta unidad",
)
def get_current_draft(
    session: SessionDep, business_unit: str, profile_id: str, principal: AdminDep = None
) -> DraftOut:
    unit = _unit(session, business_unit)
    draft = open_draft(session, unit.id, profile_id)
    if draft is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"no hay borrador abierto del perfil '{profile_id}' en la unidad '{unit.code}'",
        )
    return DraftOut.of(draft, unit.code)


@router.put(
    "/drafts/{draft_id}",
    response_model=DraftOut,
    summary="Guardar decisiones y recalcular lo que falta",
)
def put_decisions(
    draft_id: uuid.UUID,
    payload: SaveDecisionsIn,
    session: SessionDep,
    business_unit: str,
    principal: PrincipalDep,
    _admin: AdminDep = None,
) -> DraftOut:
    unit = _unit(session, business_unit)
    draft = _draft_of_unit(session, draft_id, unit)
    metadata, _ = _metadata(session, unit)
    try:
        save_decisions(session, draft, metadata, payload.decisions, updated_by=principal.subject)
    except DraftError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    session.commit()
    return DraftOut.of(draft, unit.code)


@router.post(
    "/drafts/{draft_id}/publish",
    response_model=DraftOut,
    summary="Publicar el perfil: la unidad lo adopta y la versión anterior queda superada",
)
def post_publish(
    draft_id: uuid.UUID,
    session: SessionDep,
    business_unit: str,
    principal: PrincipalDep,
    _admin: AdminDep = None,
) -> DraftOut:
    unit = _unit(session, business_unit)
    draft = _draft_of_unit(session, draft_id, unit)
    try:
        publish_draft(session, draft, published_by=principal.subject)
    except DraftError as exc:
        # 422 rather than 409: the request is well formed and the state is right; what is
        # wrong is the content, and the message lists exactly what.
        session.commit()  # keep the re-validated `problems`, which is what the screen shows
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return DraftOut.of(draft, unit.code)


@router.get(
    "/drafts/{draft_id}/yaml",
    response_class=Response,
    summary="El perfil como el YAML que se versiona en profiles/",
)
def get_yaml(
    draft_id: uuid.UUID, session: SessionDep, business_unit: str, principal: AdminDep = None
) -> Response:
    """Export for review and commit.

    A published profile works from the database, and is still exported here: a schema
    mapping that only ever existed in a production database is one nobody can diff when the
    data turns out wrong.
    """
    unit = _unit(session, business_unit)
    draft = _draft_of_unit(session, draft_id, unit)
    if draft.document is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "el borrador todavía no arma un perfil; faltan decisiones",
        )
    return Response(
        content=render_profile_yaml(draft.document),
        media_type="application/yaml",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{draft.profile_id}-v{draft.version}.yaml"'
            )
        },
    )


@router.get(
    "/history",
    response_model=list[HistoryEntry],
    summary="Versiones del perfil en esta unidad, de la más reciente a la más antigua",
)
def get_history(
    session: SessionDep, business_unit: str, profile_id: str, principal: AdminDep = None
) -> list[HistoryEntry]:
    unit = _unit(session, business_unit)
    return [
        HistoryEntry(
            draft_id=draft.id,
            version=draft.version,
            status=draft.status,
            problems=list(draft.problems),
            created_by=draft.created_by,
            published_by=draft.published_by,
            published_at=draft.published_at.isoformat() if draft.published_at else None,
        )
        for draft in history(session, unit.id, profile_id)
    ]


@router.get(
    "/published",
    response_model=DraftOut,
    summary="El perfil que la unidad tiene adoptado",
)
def get_published(
    session: SessionDep, business_unit: str, profile_id: str, principal: AdminDep = None
) -> DraftOut:
    unit = _unit(session, business_unit)
    draft = published_draft(session, unit.id, profile_id)
    if draft is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"la unidad '{unit.code}' no ha publicado el perfil '{profile_id}'; "
            "sigue funcionando con el archivo de profiles/",
        )
    return DraftOut.of(draft, unit.code)


def _draft_of_unit(session: Session, draft_id: uuid.UUID, unit: BusinessUnit) -> ProfileDraft:
    """Fetch a draft that belongs to this unit.

    404 for another unit's draft rather than 403: an administrator probing ids should not
    learn that one exists somewhere else (ADR-009).
    """
    draft = session.get(ProfileDraft, draft_id)
    if draft is None or draft.business_unit_id != unit.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"el borrador '{draft_id}' no existe")
    return draft
