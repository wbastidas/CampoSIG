"""Ingest metadata and batch results from the arcpy agent (RF-349, RF-353).

This is the backend's half of the contract in ADR-008. The agent runs on the ArcMap
machine under Python 2.7 and posts here; nothing in this module knows how arcpy works,
and nothing on the agent knows how the platform stores anything. That narrow seam is what
lets the GIS side be replaced — by feature services, or by whatever ArcGIS Pro requires
after the migration — without touching the rest of the platform.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.gis_gateway.models import AsBuiltBatch, MetadataSnapshot, ProposalResult
from app.model_profile.metadata import GisMetadata
from app.model_profile.profile import DataModelProfile, load_profile, validate_against_amd
from app.org.models import BusinessUnit

#: Contract versions this backend accepts from an agent. Rejecting an unknown version
#: beats silently mis-parsing a payload from a newer agent.
SUPPORTED_CONTRACT_VERSIONS = frozenset({1})


class ContractVersionError(Exception):
    """Raised when an agent speaks a contract version this backend does not support."""


class UnknownProfileError(Exception):
    """Raised when an agent reports metadata for a profile that is not configured."""


class CrossUnitError(Exception):
    """Raised when an operation would move data between business units."""


def ingest_metadata(
    session: Session,
    unit: BusinessUnit,
    metadata: GisMetadata,
    *,
    contract_version: int = 1,
    agent_version: str | None = None,
) -> MetadataSnapshot:
    """Store a business unit's metadata export and run the diagnostic (RF-302).

    Snapshots are keyed by **business unit**, not by profile: units normally share one
    profile because the schema is national, but each has its own domain contents — the
    feeder and substation codes of its own network. Keying by profile would let one unit's
    catalogues overwrite another's.

    Supersedes the unit's previous snapshot rather than deleting it: a form generated
    earlier must stay traceable to the metadata it came from.

    :raises ContractVersionError: if the agent's contract version is unsupported.
    :raises UnknownProfileError: if the unit's profile is not configured.
    :raises CrossUnitError: if the payload claims a profile other than the unit's.
    """
    if contract_version not in SUPPORTED_CONTRACT_VERSIONS:
        supported = ", ".join(str(v) for v in sorted(SUPPORTED_CONTRACT_VERSIONS))
        raise ContractVersionError(
            f"el agente habla la versión de contrato {contract_version}; "
            f"este backend soporta: {supported}"
        )

    # The unit's registration decides which profile applies — never the payload. An agent
    # that reports a different profile is misconfigured, and silently accepting it would
    # store one unit's catalogues under another unit's schema.
    if metadata.profile_id != unit.profile_id:
        raise CrossUnitError(
            f"el agente de la unidad '{unit.code}' reportó metadatos del perfil "
            f"'{metadata.profile_id}', pero la unidad usa '{unit.profile_id}'"
        )

    try:
        profile = load_profile(unit.profile_id)
    except FileNotFoundError as exc:
        raise UnknownProfileError(str(exc)) from exc

    # Diagnose against the canonical vocabulary at ingest time, so a gap is visible on
    # the admin screen instead of surfacing later as a broken form.
    problems = validate_against_amd(profile)
    problems.extend(_metadata_problems(metadata, profile))

    session.execute(
        update(MetadataSnapshot)
        .where(
            MetadataSnapshot.business_unit_id == unit.id,
            MetadataSnapshot.superseded_at.is_(None),
        )
        .values(superseded_at=datetime.now(UTC))
    )

    snapshot = MetadataSnapshot(
        business_unit_id=unit.id,
        profile_id=unit.profile_id,
        agent_version=agent_version,
        contract_version=contract_version,
        payload=metadata.model_dump(mode="json"),
        domain_count=len(metadata.domains),
        layer_count=len(metadata.layers),
        relationship_count=len(metadata.relationships),
        problems=problems,
        exported_at=_parse_timestamp(metadata.exported_at),
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def _metadata_problems(metadata: GisMetadata, profile: DataModelProfile) -> list[str]:
    """Gaps between what the profile expects and what the agent actually exported."""
    problems: list[str] = []
    exported_layers = {layer.name.upper() for layer in metadata.layers}

    for asset_key, binding in profile.bindings.items():
        if binding.layer.upper() not in exported_layers:
            problems.append(f"el perfil mapea '{asset_key}' a una capa que el agente no exportó")
            continue
        layer = metadata.layer(binding.layer)
        assert layer is not None  # guaranteed by the membership check above
        exported_fields = {field.name.upper() for field in layer.fields}
        for attribute_key, bound in binding.attributes.items():
            if bound.field.upper() not in exported_fields:
                problems.append(
                    f"'{asset_key}.{attribute_key}' apunta a un campo ausente de la capa exportada"
                )

    # A volatile domain that failed to export is worse than a missing stable one: the
    # form would fall back to a stale catalogue without anyone noticing (RF-304).
    for asset_key, binding in profile.bindings.items():
        for attribute_key, bound in binding.attributes.items():
            if (
                bound.volatile_by_business_unit
                and bound.domain
                and metadata.domain(bound.domain) is None
            ):
                problems.append(
                    f"el dominio volátil de '{asset_key}.{attribute_key}' no llegó en "
                    "esta sincronización; no usar catálogos en caché para ese campo"
                )
    return problems


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        # A malformed timestamp from the agent must not reject an otherwise good export.
        return None


def current_snapshot(session: Session, business_unit_id: uuid.UUID) -> MetadataSnapshot | None:
    """The snapshot form generation should use for a business unit."""
    return session.scalars(
        select(MetadataSnapshot).where(
            MetadataSnapshot.business_unit_id == business_unit_id,
            MetadataSnapshot.superseded_at.is_(None),
        )
    ).first()


def record_batch_results(
    session: Session,
    batch_id: uuid.UUID,
    outcomes: list[dict[str, Any]],
    *,
    business_unit_id: uuid.UUID | None = None,
) -> AsBuiltBatch:
    """Record what the agent reported for each proposal (RF-353).

    Idempotent by (batch, proposal): the agent is allowed to retry a batch, and a retry
    must update the outcome rather than accumulate duplicates.

    :param business_unit_id: when given, the batch must belong to this unit. Callers
        serving an agent always pass it, so one unit's agent cannot report on another
        unit's batch even if it learns the id.
    :raises CrossUnitError: if the batch belongs to a different business unit.
    """
    batch = session.get(AsBuiltBatch, batch_id)
    if batch is None:
        raise LookupError(f"lote '{batch_id}' no existe")
    if business_unit_id is not None and batch.business_unit_id != business_unit_id:
        # Deliberately the same message as a missing batch would produce upstream: an
        # agent probing for other units' batch ids learns nothing from the difference.
        raise CrossUnitError(f"lote '{batch_id}' no pertenece a esta unidad de negocio")

    existing = {result.proposal_id: result for result in batch.results}
    for outcome in outcomes:
        proposal_id = uuid.UUID(str(outcome["proposal_id"]))
        status = outcome["status"]
        message = outcome.get("message")
        if proposal_id in existing:
            existing[proposal_id].status = status
            existing[proposal_id].message = message
            existing[proposal_id].reported_at = datetime.now(UTC)
        else:
            session.add(
                ProposalResult(
                    batch_id=batch.id,
                    proposal_id=proposal_id,
                    status=status,
                    message=message,
                )
            )

    session.flush()
    session.refresh(batch)

    # A batch is complete once nothing is still pending. 'requires_arcfm' counts as
    # settled: the agent has said all it can, and the rest is the GIS team's call (D11).
    unresolved = [r for r in batch.results if r.status in {"pending", "dispatched"}]
    if not unresolved:
        batch.status = "completed"
        batch.completed_at = datetime.now(UTC)
    session.flush()
    return batch
