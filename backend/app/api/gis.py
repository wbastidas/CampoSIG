"""Endpoints the arcpy agent and the admin screens use (RF-302, RF-349, RF-353).

The agent's half of ADR-008. Routes are deliberately few and explicit: this is a contract
between two processes on different Python versions, so surprises here are expensive.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.forms.generator import FormGenerator
from app.gis_gateway.ingest import (
    ContractVersionError,
    CrossUnitError,
    UnknownProfileError,
    current_snapshot,
    ingest_metadata,
    record_batch_results,
)
from app.infra.database import get_session
from app.model_profile.metadata import GisMetadata
from app.org.models import AgentRegistration, BusinessUnit
from app.org.service import (
    AgentNotAuthorisedError,
    UnknownBusinessUnitError,
    context_for_unit,
    get_business_unit_by_code,
    resolve_agent,
)

router = APIRouter(prefix="/api/v1/gis", tags=["gis"])

SessionDep = Annotated[Session, Depends(get_session)]

#: Header the agent presents to identify itself. Its business unit comes from the
#: registration behind this key, never from the request body — an agent is never asked
#: which unit it serves, so it cannot claim a different one (ADR-009).
AGENT_KEY_HEADER = "X-SIGEC-Agent-Key"


def authorised_agent(
    session: SessionDep,
    agent_key: Annotated[str, Header(alias=AGENT_KEY_HEADER)],
) -> AgentRegistration:
    """Resolve and authorise the calling agent."""
    try:
        agent = resolve_agent(session, agent_key)
    except AgentNotAuthorisedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    agent.last_seen_at = datetime.now(UTC)
    return agent


AgentDep = Annotated[AgentRegistration, Depends(authorised_agent)]


def _unit_by_code(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


# --- request / response models -----------------------------------------------------
class MetadataUpload(BaseModel):
    """What the agent posts after running ListDomains and Describe."""

    contract_version: int = 1
    agent_version: str | None = None
    metadata: GisMetadata


class MetadataAccepted(BaseModel):
    snapshot_id: uuid.UUID
    business_unit_code: str
    profile_id: str
    domain_count: int
    layer_count: int
    relationship_count: int
    #: Gaps a functional administrator must look at. Empty means the profile is complete.
    problems: list[str]


class SnapshotSummary(BaseModel):
    snapshot_id: uuid.UUID
    business_unit_code: str
    profile_id: str
    agent_version: str | None
    domain_count: int
    layer_count: int
    relationship_count: int
    problems: list[str]
    received_at: str


class ProposalOutcomeIn(BaseModel):
    proposal_id: uuid.UUID
    status: str = Field(pattern="^(applied|rejected|error|requires_arcfm)$")
    message: str | None = None


class BatchResultsIn(BaseModel):
    outcomes: list[ProposalOutcomeIn]


class BatchStatusOut(BaseModel):
    batch_id: uuid.UUID
    status: str
    reported: int
    applied: int
    requires_arcfm: int
    failed: int


class GeneratedFormOut(BaseModel):
    asset_type: str
    schema_: dict[str, Any] = Field(alias="schema")
    ui_schema: dict[str, Any]
    warnings: list[str]

    model_config = {"populate_by_name": True}


# --- routes ------------------------------------------------------------------------
@router.post(
    "/metadata",
    response_model=MetadataAccepted,
    status_code=status.HTTP_201_CREATED,
    summary="Recibir metadatos exportados por el agente arcpy",
)
def upload_metadata(
    payload: MetadataUpload, session: SessionDep, agent: AgentDep
) -> MetadataAccepted:
    """Ingest a metadata export for the calling agent's own business unit."""
    unit = agent.business_unit
    try:
        snapshot = ingest_metadata(
            session,
            unit,
            payload.metadata,
            contract_version=payload.contract_version,
            agent_version=payload.agent_version,
        )
    except ContractVersionError as exc:
        # 409 rather than 400: the payload may be perfectly valid for a newer backend.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except CrossUnitError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except UnknownProfileError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    session.commit()
    return MetadataAccepted(
        snapshot_id=snapshot.id,
        business_unit_code=unit.code,
        profile_id=snapshot.profile_id,
        domain_count=snapshot.domain_count,
        layer_count=snapshot.layer_count,
        relationship_count=snapshot.relationship_count,
        problems=snapshot.problems,
    )


@router.get(
    "/metadata/current",
    response_model=SnapshotSummary,
    summary="Resumen de los metadatos vigentes de un perfil",
)
def get_current_metadata(session: SessionDep, business_unit: str) -> SnapshotSummary:
    unit = _unit_by_code(session, business_unit)
    snapshot = current_snapshot(session, unit.id)
    if snapshot is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"no hay metadatos sincronizados para la unidad '{unit.code}'; "
            "su agente arcpy todavía no ha corrido",
        )
    return SnapshotSummary(
        snapshot_id=snapshot.id,
        business_unit_code=unit.code,
        profile_id=snapshot.profile_id,
        agent_version=snapshot.agent_version,
        domain_count=snapshot.domain_count,
        layer_count=snapshot.layer_count,
        relationship_count=snapshot.relationship_count,
        problems=snapshot.problems,
        received_at=snapshot.received_at.isoformat(),
    )


@router.post(
    "/batches/{batch_id}/results",
    response_model=BatchStatusOut,
    summary="Registrar el resultado por propuesta de un lote aplicado",
)
def report_batch_results(
    batch_id: uuid.UUID, payload: BatchResultsIn, session: SessionDep, agent: AgentDep
) -> BatchStatusOut:
    """Record outcomes. The batch must belong to the calling agent's own unit."""
    try:
        batch = record_batch_results(
            session,
            batch_id,
            [o.model_dump(mode="json") for o in payload.outcomes],
            business_unit_id=agent.business_unit_id,
        )
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except CrossUnitError as exc:
        # 404, not 403: an agent probing for other units' batch ids learns nothing.
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    session.commit()
    statuses = [r.status for r in batch.results]
    return BatchStatusOut(
        batch_id=batch.id,
        status=batch.status,
        reported=len(statuses),
        applied=statuses.count("applied"),
        requires_arcfm=statuses.count("requires_arcfm"),
        failed=statuses.count("error") + statuses.count("rejected"),
    )


@router.get(
    "/forms/{asset_type_key}/proposal",
    response_model=GeneratedFormOut,
    summary="Generar una propuesta de formulario desde los metadatos vigentes",
)
def generate_form_proposal(
    asset_type_key: str, session: SessionDep, business_unit: str
) -> GeneratedFormOut:
    """Generate a form proposal. Never publishes — a human approves first (SRS 0.5)."""
    unit = _unit_by_code(session, business_unit)
    resolver, metadata = context_for_unit(session, unit)
    if metadata is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"no hay metadatos sincronizados para la unidad '{unit.code}'; ejecute su "
            "agente arcpy antes de generar formularios",
        )
    try:
        form = FormGenerator(resolver, metadata).generate(asset_type_key)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    return GeneratedFormOut(
        asset_type=form.asset_type_key,
        schema=form.schema,
        ui_schema=form.ui_schema,
        warnings=form.warnings,
    )
