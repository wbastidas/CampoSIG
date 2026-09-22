"""From an approved work order to a batch the arcpy agent can apply (RF-342 to RF-344).

This closes the loop the platform exists to close: a technician records that a pole was
replaced, a supervisor approves it, and the change reaches the corporate geodatabase.

Two constraints shape everything here, both established in ADR-001 and ADR-008:

* the platform **never writes connectivity fields** — the trace maintains those;
* the agent **writes only the fields the profile maps**, which are by construction the fields
  the field process produces (decision D11).

So a proposal carries canonical attribute keys, and the agent resolves them to real field
names at the last moment, on the machine that actually talks to the geodatabase.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Table, select
from sqlalchemy.orm import Session

from app.gis_gateway.models import AsBuiltBatch
from app.gis_gateway.staging_table import asbuilt_proposal
from app.model_profile.resolver import NEVER_WRITE_FIELDS, ModelResolver
from app.org.models import BusinessUnit
from app.org.service import resolver_for_unit
from app.workorders.models import WorkOrder, WorkOrderState


class ProposalRejectedError(Exception):
    """Raised when a proposal would break one of the write invariants."""


#: Actions a field proposal may request.
VALID_ACTIONS = frozenset({"create", "update", "retire"})


def build_proposal(
    resolver: ModelResolver,
    *,
    asset_type_key: str,
    action: str,
    attributes: dict[str, Any],
    gis_global_id: str | None = None,
) -> dict[str, Any]:
    """Validate and normalise one as-built proposal.

    Checked here, before anything is stored, so an invalid proposal never reaches the machine
    with write access to the geodatabase.

    :raises ProposalRejectedError: on an unknown action, an unmapped attribute, a connectivity
        field, or an update with no element to update.
    """
    if action not in VALID_ACTIONS:
        raise ProposalRejectedError(
            f"acción '{action}' no válida; permitidas: {', '.join(sorted(VALID_ACTIONS))}"
        )
    if action in ("update", "retire") and not gis_global_id:
        raise ProposalRejectedError(f"una acción '{action}' necesita el identificador del elemento")

    mapped = resolver.fields(asset_type_key)
    unknown = sorted(set(attributes) - set(mapped))
    if unknown:
        # The profile defines the write scope (D11). A key it does not map is not part of the
        # field process, and the agent has no business writing it.
        raise ProposalRejectedError(
            f"atributos fuera del alcance del perfil para '{asset_type_key}': {', '.join(unknown)}"
        )

    # Belt and braces. The canonical vocabulary contains no connectivity field, so this can
    # only trigger if a profile is misconfigured — which is exactly when it matters.
    offending = sorted(
        key
        for key, field in mapped.items()
        if key in attributes and field.upper() in NEVER_WRITE_FIELDS
    )
    if offending:
        raise ProposalRejectedError(
            f"la plataforma nunca escribe campos de conectividad: {', '.join(offending)}"
        )

    return {
        "asset_type_key": asset_type_key,
        "action": action,
        "gis_global_id": gis_global_id,
        "attributes": attributes,
    }


def stage_from_work_order(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    proposals: list[dict[str, Any]],
) -> list[uuid.UUID]:
    """Materialise approved as-built proposals into staging (RF-342).

    Only from an approved work order: staging is the antechamber to the corporate geodatabase,
    and field data reaches it after a human said so, never before.

    :returns: the ids of the staged proposals.
    :raises ProposalRejectedError: if the work order is not approved, or a proposal is invalid.
    """
    if order.state != WorkOrderState.APPROVED:
        raise ProposalRejectedError(
            f"solo se materializan propuestas de una OT aprobada; esta está en '{order.state}'"
        )

    resolver = resolver_for_unit(unit)
    staged: list[uuid.UUID] = []

    for raw in proposals:
        validated = build_proposal(
            resolver,
            asset_type_key=raw["asset_type_key"],
            action=raw["action"],
            attributes=raw.get("attributes", {}),
            gis_global_id=raw.get("gis_global_id"),
        )
        proposal_id = uuid.UUID(str(raw["proposal_id"]))

        # Idempotent by the device-generated id: re-approving or replaying must not duplicate
        # a pole in the geodatabase, which is not a mistake anyone wants to unpick.
        existing = session.execute(
            select(1)
            .select_from(_proposal_table())
            .where(
                _proposal_table().c.proposal_id == proposal_id,
                _proposal_table().c.business_unit_id == unit.id,
            )
        ).first()
        if existing is not None:
            staged.append(proposal_id)
            continue

        session.execute(
            _proposal_table()
            .insert()
            .values(
                proposal_id=proposal_id,
                business_unit_id=unit.id,
                asset_type_key=validated["asset_type_key"],
                action=validated["action"],
                gis_global_id=validated["gis_global_id"],
                work_order_ref=str(order.id),
                attributes=validated["attributes"],
                geometry=raw.get("geometry"),
                status="approved",
                requires_arcfm=bool(raw.get("requires_arcfm", False)),
            )
        )
        staged.append(proposal_id)

    session.flush()
    return staged


def _proposal_table() -> Table:
    """The staging table. See ``staging_table`` for why it is Core and not a mapped class."""
    return asbuilt_proposal


def create_batch(
    session: Session,
    unit: BusinessUnit,
    *,
    asset_type_key: str,
    zone: str | None = None,
    limit: int = 200,
) -> AsBuiltBatch | None:
    """Group approved proposals into a batch for the agent (RF-343).

    Grouped by asset type because the agent applies one target feature class at a time:
    staging class, append, rebuild connectivity (ADR-008).

    :returns: the batch, or None when there is nothing approved to send.
    """
    table = _proposal_table()
    pending = session.execute(
        select(table.c.proposal_id)
        .where(
            # La unidad primero: un lote lleva propuestas de esta unidad y de ninguna otra.
            # Sin este filtro, el agente de una unidad recibiría propuestas de la vecina y
            # las escribiría en la geodatabase equivocada (ADR-009).
            table.c.business_unit_id == unit.id,
            table.c.status == "approved",
            table.c.asset_type_key == asset_type_key,
            table.c.batch_id.is_(None),
        )
        .limit(limit)
    ).all()
    if not pending:
        return None

    batch = AsBuiltBatch(
        business_unit_id=unit.id,
        profile_id=unit.profile_id,
        asset_type_key=asset_type_key,
        zone=zone,
        status="ready",
    )
    session.add(batch)
    session.flush()

    session.execute(
        table.update()
        .where(table.c.proposal_id.in_([row[0] for row in pending]))
        .values(batch_id=batch.id, status="dispatched")
    )
    batch.dispatched_at = datetime.now(UTC)
    session.flush()
    return batch


def batch_payload(session: Session, unit: BusinessUnit, batch: AsBuiltBatch) -> dict[str, Any]:
    """What the agent receives: canonical proposals plus the mapping it needs (RF-344).

    The real field names travel with the batch rather than being looked up by the agent, so
    the agent stays a thin executor and the profile remains the single place that knows how
    canonical keys map to a geodatabase.
    """
    resolver = resolver_for_unit(unit)
    table = _proposal_table()
    rows = session.execute(
        select(
            table.c.proposal_id,
            table.c.action,
            table.c.gis_global_id,
            table.c.attributes,
            table.c.geometry,
            table.c.requires_arcfm,
        ).where(table.c.batch_id == batch.id)
    ).all()

    field_map = resolver.fields(batch.asset_type_key)
    return {
        "batch_id": str(batch.id),
        "business_unit": unit.code,
        "profile_id": unit.profile_id,
        "asset_type": batch.asset_type_key,
        "target_layer": resolver.layer(batch.asset_type_key),
        "participates_in_geometric_network": resolver.participates_in_geometric_network(
            batch.asset_type_key
        ),
        "write_path": resolver.write_path(batch.asset_type_key).value,
        # Only the fields the profile maps travel; nothing else can reach the geodatabase.
        "field_map": field_map,
        "spatial_reference": unit.spatial_reference,
        "proposals": [
            {
                "proposal_id": str(row.proposal_id),
                "action": row.action,
                "gis_global_id": row.gis_global_id,
                "attributes": row.attributes,
                "geometry": row.geometry,
                "requires_arcfm": row.requires_arcfm,
            }
            for row in rows
        ],
    }


def apply_results(session: Session, batch: AsBuiltBatch, outcomes: list[dict[str, Any]]) -> None:
    """Record per-proposal outcomes onto the staging rows, so the trail is complete."""
    table = _proposal_table()
    for outcome in outcomes:
        session.execute(
            table.update()
            .where(table.c.proposal_id == uuid.UUID(str(outcome["proposal_id"])))
            .values(
                status=_status_for(outcome["status"]),
                apply_result=outcome,
            )
        )
    session.flush()


def _status_for(agent_status: str) -> str:
    """Map the agent's vocabulary onto the staging table's."""
    return {
        "applied": "applied",
        "rejected": "rejected",
        "error": "error",
        # The agent said all it can; the rest is the GIS team's call (D11). It stays
        # dispatched rather than becoming an error, because nothing failed.
        "requires_arcfm": "dispatched",
    }.get(agent_status, "error")
