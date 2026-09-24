"""Raising work-order proposals from findings, and deciding on them (RF-013, RF-114).

Generation reuses the finding reader of the maintenance board (RF-133) rather than parsing the
captures again: two readers of the same two form blocks would drift, and the one that drifted would
be the one that quietly stopped seeing a defect.

Three decisions shape this module:

* **One open proposal per asset and defect.** A crossarm inspected three times in a month is one
  piece of work, not three. The uniqueness is in the database (a partial index over the open state),
  because a check in this function is a check a second worker can race.
* **An asset with open work is not proposed again.** RF-014's «alerta si existe una OT abierta sobre
  el mismo activo» — here as a refusal rather than an alert, because a tray with a proposal for work
  already scheduled is a tray a supervisor learns to skim.
* **Nothing becomes a work order without a person.** `approve` is the only path from this table to
  `work_order`, it takes the decider from a token, and there is no scheduled job that calls it. The
  same rule the batch approval of RF-176 lives under.

The rejected reason is a catalogue code and not free text, because RF-114 says «el motivo de rechazo
se usa como señal negativa en el entrenamiento» and free text cannot be a label. Which *kind* of
signal each reason carries is an attribute of the catalogue: «no es un defecto» means the detection
was wrong, while «ya está resuelto» means it was right and the world moved on, and using the second
as a negative example would teach a model not to see a defect that was really there.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.maintenance import ATTENDED_STATES, Finding, _captures, _findings_of
from app.audit.models import ActorKind, EventKind
from app.audit.service import record
from app.catalogs import service as catalogs
from app.forms.catalog import definitions_for_asset_type
from app.org.models import BusinessUnit
from app.proposals.criticality import Criticality, compute, suggested_deadline_hours
from app.proposals.models import ProposalOrigin, ProposalState, WorkOrderProposal
from app.workorders.models import STORAGE_SRID, Priority, WorkOrder, WorkOrderSource
from app.workorders.service import create_work_order, pending_field_work
from app.zones.models import Zone

#: The catalogues this module reads. Named so a caller can see what has to be loaded for the
#: criticality to be anything but defaults.
DEFECT_CATALOG = "defect"
CONSEQUENCE_CATALOG = "consequence_by_asset"
PRIORITY_CATALOG = "priority"
REJECT_REASON_CATALOG = "proposal_reject_reason"

#: The work type a proposal carries. A correction: the form the crew will fill is chosen from the
#: asset type, and this is what the boards group by.
PROPOSED_WORK_TYPE = "correctivo"


class ProposalError(Exception):
    pass


class NotOpenError(ProposalError):
    """Raised when a decision is taken on a proposal that already has one."""


class UnknownReasonError(ProposalError):
    """Raised when a rejection names a reason the catalogue does not have."""


@dataclass
class GenerationReport:
    """What a generation pass did, and what it refused to do."""

    created: list[uuid.UUID] = field(default_factory=list)
    #: Findings skipped because the asset already has open work. Counted, not hidden: a tray that
    #: silently dropped them would look like a generator that missed them.
    skipped_open_order: list[str] = field(default_factory=list)
    #: Skipped because an open proposal for that asset and defect already exists.
    skipped_duplicate: list[str] = field(default_factory=list)
    #: Findings with no asset code: there is nothing to propose work on.
    skipped_no_asset: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "created": [str(item) for item in self.created],
            "skipped_open_order": self.skipped_open_order,
            "skipped_duplicate": self.skipped_duplicate,
            "skipped_no_asset": self.skipped_no_asset,
        }


def _attributes(session: Session, catalog: str, code: str | None) -> dict[str, Any] | None:
    """One catalogue entry's attributes, or None when the code is not there.

    None and `{}` are different answers and the criticality matrix treats them differently: an entry
    with no attributes declared nothing, an absent entry means the catalogue does not know the code
    at all, and only the second is worth telling a supervisor about.
    """
    if not code:
        return None
    try:
        resolved = catalogs.resolve(session, catalog)
    except catalogs.UnknownCatalogError:
        return None
    for entry in resolved.entries:
        if entry.code == code:
            return entry.attributes
    return None


def _exposed(session: Session, unit: BusinessUnit, zone_code: str | None) -> bool:
    """Whether the zone raises the consequence by one level (Annex C's exposure adjustment)."""
    if not zone_code:
        return False
    row = session.execute(
        select(Zone.exposure).where(
            Zone.business_unit_id == unit.id, Zone.code == zone_code, Zone.active.is_(True)
        )
    ).scalar_one_or_none()
    return bool(row)


def criticality_of(
    session: Session,
    unit: BusinessUnit,
    *,
    defect_code: str,
    asset_type_key: str | None,
    zone_code: str | None,
) -> Criticality:
    """The Annex C computation for one finding, over the catalogues as they are now."""
    return compute(
        defect_attributes=_attributes(session, DEFECT_CATALOG, defect_code),
        asset_attributes=_attributes(session, CONSEQUENCE_CATALOG, asset_type_key),
        defect_code=defect_code,
        asset_type_key=asset_type_key,
        exposed=_exposed(session, unit, zone_code),
    )


def _form_for(asset_type_key: str | None) -> str | None:
    """The form a corrective order on this asset type would use.

    Taken from the form catalogue's own `applies_to_asset_types` rather than from a table here: the
    forms are the data that says which asset they apply to (rule 3), and a second mapping would be a
    second thing to keep in step.
    """
    if not asset_type_key:
        return None
    definitions = definitions_for_asset_type(asset_type_key)
    return definitions[0].code if definitions else None


def _open_pairs(session: Session, unit: BusinessUnit) -> set[tuple[str, str]]:
    rows = session.execute(
        select(WorkOrderProposal.asset_code, WorkOrderProposal.defect_code).where(
            WorkOrderProposal.business_unit_id == unit.id,
            WorkOrderProposal.state == ProposalState.OPEN,
        )
    ).all()
    return {(asset, defect) for asset, defect in rows if asset}


def generate_from_findings(
    session: Session,
    unit: BusinessUnit,
    *,
    since: datetime,
    until: datetime,
    only_wanted: bool = True,
    actor: str = "sistema:propuestas",
) -> GenerationReport:
    """Raise proposals from the findings of a period.

    :param only_wanted: when True, only findings the crew flagged for follow-up become proposals.
        Default because the crew's flag is the cheapest and most reliable signal there is: a
        technician who ticked «generar OT» has decided this needs coming back for. Setting it False
        proposes from every finding, which is what a supervisor reviewing a backlog wants.
    """
    report = GenerationReport()

    findings: list[Finding] = []
    for order, response in _captures(session, unit.id, since, until):
        for finding in _findings_of(order, response):
            if only_wanted and not finding.wants_order:
                continue
            findings.append(finding)

    if not findings:
        return report

    assets = {item.asset_code for item in findings if item.asset_code}
    pending = pending_field_work(session, unit, assets)
    existing = _open_pairs(session, unit)
    seen: set[tuple[str, str]] = set()

    for finding in findings:
        if not finding.asset_code:
            report.skipped_no_asset += 1
            continue
        pair = (finding.asset_code, finding.defect_code)
        if pending.get(finding.asset_code, set()) - {finding.work_order_id}:
            report.skipped_open_order.append(finding.asset_code)
            continue
        if pair in existing or pair in seen:
            report.skipped_duplicate.append(f"{pair[0]}/{pair[1]}")
            continue
        seen.add(pair)
        proposal = _raise(session, unit, finding, actor=actor)
        report.created.append(proposal.id)

    return report


def _raise(
    session: Session, unit: BusinessUnit, finding: Finding, *, actor: str
) -> WorkOrderProposal:
    source = session.get(WorkOrder, finding.work_order_id)
    asset_type_key = source.asset_type_key if source else None
    zone_code = source.zone if source else None
    critical = criticality_of(
        session,
        unit,
        defect_code=finding.defect_code,
        asset_type_key=asset_type_key,
        zone_code=zone_code,
    )
    deadline = suggested_deadline_hours(_attributes(session, PRIORITY_CATALOG, critical.priority))

    label = _defect_label(session, finding.defect_code)
    justification = (
        f"{label} en {finding.asset_code}, registrado en la OT "
        f"{finding.order_code or 'sin código'}. {critical.explain()}."
    )

    proposal = WorkOrderProposal(
        business_unit_id=unit.id,
        source_work_order_id=finding.work_order_id,
        origin=ProposalOrigin.FIELD_FINDING,
        state=ProposalState.OPEN,
        asset_code=finding.asset_code,
        asset_type_key=asset_type_key,
        feeder_code=finding.feeder_code,
        zone=zone_code,
        defect_code=finding.defect_code,
        work_type=PROPOSED_WORK_TYPE,
        form_code=_form_for(asset_type_key),
        priority=critical.priority,
        criticality=critical.as_dict(),
        suggested_deadline_hours=deadline,
        justification=justification,
        findings=[finding.as_dict()],
    )
    if source is not None and source.location is not None:
        proposal.location = func.ST_SetSRID(
            func.ST_MakePoint(
                *_coordinates(session, source.id),
            ),
            STORAGE_SRID,
        )
    session.add(proposal)
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.CREATED,
        subject_type="work_order_proposal",
        subject_id=str(proposal.id),
        work_order_id=finding.work_order_id,
        asset_code=finding.asset_code,
        actor=actor,
        actor_kind=ActorKind.SYSTEM,
        payload={
            "defect_code": finding.defect_code,
            "priority": critical.priority,
            "score": critical.score,
            "estimated": critical.is_estimated,
        },
    )
    return proposal


def _coordinates(session: Session, order_id: uuid.UUID) -> tuple[float, float]:
    row = session.execute(
        select(func.ST_X(WorkOrder.location), func.ST_Y(WorkOrder.location)).where(
            WorkOrder.id == order_id
        )
    ).first()
    if row is None or row[0] is None or row[1] is None:
        return (0.0, 0.0)
    return (float(row[0]), float(row[1]))


def _defect_label(session: Session, code: str) -> str:
    try:
        resolved = catalogs.resolve(session, DEFECT_CATALOG)
    except catalogs.UnknownCatalogError:
        return code
    for entry in resolved.entries:
        if entry.code == code:
            return entry.label
    return code


def tray(
    session: Session,
    unit: BusinessUnit,
    *,
    state: str = ProposalState.OPEN,
    limit: int = 200,
) -> list[WorkOrderProposal]:
    """The supervisor's tray: worst first, then oldest first.

    Worst first because the tray is worked from the top and a P1 that sat under twenty P4s is the
    failure this ordering exists to prevent. Oldest first within a priority so nothing starves.
    """
    rank = {
        Priority.CRITICAL.value: 0,
        Priority.HIGH.value: 1,
        Priority.MEDIUM.value: 2,
        Priority.LOW.value: 3,
    }
    rows = list(
        session.execute(
            select(WorkOrderProposal).where(
                WorkOrderProposal.business_unit_id == unit.id,
                WorkOrderProposal.state == state,
            )
        ).scalars()
    )
    rows.sort(key=lambda item: (rank.get(item.priority, 9), item.created_at))
    return rows[:limit]


def counts(session: Session, unit: BusinessUnit) -> dict[str, int]:
    rows = session.execute(
        select(WorkOrderProposal.state, func.count())
        .where(WorkOrderProposal.business_unit_id == unit.id)
        .group_by(WorkOrderProposal.state)
    ).all()
    return {str(state): int(total) for state, total in rows}


# --- decisions (RF-114) -------------------------------------------------------------------


def _decided(
    session: Session,
    unit: BusinessUnit,
    proposal: WorkOrderProposal,
    *,
    state: str,
    actor: str,
    payload: dict[str, Any],
) -> None:
    proposal.state = state
    proposal.decided_by = actor
    proposal.decided_at = datetime.now(UTC)
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.DECIDED,
        subject_type="work_order_proposal",
        subject_id=str(proposal.id),
        work_order_id=proposal.work_order_id or proposal.merged_into_id,
        asset_code=proposal.asset_code,
        actor=actor,
        payload={"state": state, **payload},
    )


def _must_be_open(proposal: WorkOrderProposal) -> None:
    if not proposal.is_open:
        raise NotOpenError(
            f"la propuesta ya está «{proposal.state}»: una decisión no se toma dos veces"
        )


def approve(
    session: Session,
    unit: BusinessUnit,
    proposal: WorkOrderProposal,
    *,
    actor: str,
    priority: str | None = None,
    note: str | None = None,
) -> WorkOrder:
    """Turn a proposal into a planned work order (RF-013).

    The only path from this table to `work_order`, and it takes the decider from a token. No
    scheduled job calls it: «requieren aprobación» is the requirement's own wording, and an
    automatic path would make the tray decoration.

    :param priority: the supervisor's own call. Annex C computed one and the supervisor may disagree
        — they know whether that MV segment is a trunk, which the platform does not — so the
        override is a parameter and what they chose is what the order carries.
    """
    _must_be_open(proposal)
    chosen = priority or proposal.priority
    order = create_work_order(
        session,
        unit,
        work_type=proposal.work_type,
        form_code=proposal.form_code or _fallback_form(),
        priority=chosen,
        source=WorkOrderSource.AI_FINDING,
        description=proposal.justification,
        asset_type_key=proposal.asset_type_key,
        asset_code=proposal.asset_code,
        feeder_code=proposal.feeder_code,
        zone=proposal.zone,
        sla_due_at=_deadline_from(proposal),
        planner_id=actor,
    )
    proposal.work_order_id = order.id
    _decided(
        session,
        unit,
        proposal,
        state=ProposalState.APPROVED,
        actor=actor,
        payload={
            "work_order_id": str(order.id),
            "priority": chosen,
            "priority_overridden": priority is not None
            and priority != proposal.criticality.get("priority"),
            "note": note,
        },
    )
    return order


def merge(
    session: Session,
    unit: BusinessUnit,
    proposal: WorkOrderProposal,
    *,
    into: WorkOrder,
    actor: str,
    note: str | None = None,
) -> WorkOrderProposal:
    """Attach the proposal's findings to a work order that already exists (RF-114).

    The action a supervisor needs when the tray proposes what somebody already scheduled by hand.
    The findings travel into the order's description rather than being lost: a merged proposal that
    left no trace on the order would make the crew arrive without knowing why.
    """
    _must_be_open(proposal)
    if into.business_unit_id != unit.id:
        raise ProposalError("la OT de destino no es de esta unidad de negocio")
    if into.state in [state.value for state in ATTENDED_STATES]:
        raise ProposalError(
            f"la OT de destino está «{into.state}»: fusionar en trabajo ya cerrado no lo hace "
            "volver al campo"
        )
    proposal.merged_into_id = into.id
    tail = f"\n\nFusionado de una propuesta: {proposal.justification}"
    into.description = f"{into.description or ''}{tail}".strip()
    _decided(
        session,
        unit,
        proposal,
        state=ProposalState.MERGED,
        actor=actor,
        payload={"merged_into_id": str(into.id), "note": note},
    )
    return proposal


def reject(
    session: Session,
    unit: BusinessUnit,
    proposal: WorkOrderProposal,
    *,
    reason_code: str,
    actor: str,
    note: str | None = None,
) -> WorkOrderProposal:
    """Refuse a proposal with a catalogued reason (RF-114).

    The reason must be in the catalogue, and the refusal names the ones that are: «el motivo de
    rechazo se usa como señal negativa en el entrenamiento», and a code nobody declared is a label
    nobody can train on. Free text rides along in `note` for the human reader; it is not the label.
    """
    _must_be_open(proposal)
    reasons = {entry.code: entry for entry in reject_reasons(session)}
    if reason_code not in reasons:
        available = ", ".join(sorted(reasons)) or "ninguno cargado"
        raise UnknownReasonError(
            f"«{reason_code}» no está en el catálogo de motivos de rechazo; "
            f"disponibles: {available}"
        )
    proposal.reject_reason_code = reason_code
    proposal.reject_note = note
    _decided(
        session,
        unit,
        proposal,
        state=ProposalState.REJECTED,
        actor=actor,
        payload={
            "reason_code": reason_code,
            # The kind of training signal this reason carries, resolved now rather than looked up
            # later: the catalogue moves, and what the label meant on the day of the decision is
            # what a dataset has to be built from.
            "signal": reasons[reason_code].attributes.get("signal"),
            "note": note,
        },
    )
    return proposal


def reject_reasons(session: Session) -> list[catalogs.ResolvedEntry]:
    """The catalogued reasons a rejection may name, or nothing when the catalogue is not loaded.

    Public because the tray shows them: a screen that offered a free-text box would produce labels
    nobody can train on, and one that hard-coded the list would drift from the catalogue.
    """
    try:
        return catalogs.resolve(session, REJECT_REASON_CATALOG).entries
    except catalogs.UnknownCatalogError:
        return []


def _fallback_form() -> str:
    """The form an approved proposal uses when the asset type maps to none.

    F-MT-01 because a corrective visit to an asset nobody mapped is still an inspection with a
    finding, and refusing to create the order would leave the supervisor with a proposal they
    approved and no work.
    """
    return "F-MT-01"


def _deadline_from(proposal: WorkOrderProposal) -> datetime | None:
    hours = proposal.suggested_deadline_hours
    if hours is None:
        return None
    return datetime.now(UTC) + timedelta(hours=hours)


def training_signals(session: Session, unit: BusinessUnit) -> dict[str, int]:
    """Rejection reasons counted by the signal they carry (RF-114).

    What a dataset builder asks for, and the reason the signal is an attribute of the catalogue: a
    “false positive” and a “already fixed” both mean «rejected» to the tray and opposite things to a
    training set.
    """
    rows = session.execute(
        select(WorkOrderProposal.reject_reason_code, func.count())
        .where(
            WorkOrderProposal.business_unit_id == unit.id,
            WorkOrderProposal.state == ProposalState.REJECTED,
            WorkOrderProposal.reject_reason_code.is_not(None),
        )
        .group_by(WorkOrderProposal.reject_reason_code)
    ).all()
    signals: dict[str, int] = {}
    by_code = {entry.code: entry for entry in reject_reasons(session)}
    for code, total in rows:
        entry = by_code.get(str(code))
        signal = str((entry.attributes.get("signal") if entry else None) or "sin_clasificar")
        signals[signal] = signals.get(signal, 0) + int(total)
    return signals
