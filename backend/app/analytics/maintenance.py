"""The maintenance board (RF-133): defects by feeder, recurrence by asset, open findings.

The three panels answer the three questions the maintenance area plans with: which feeder is
deteriorating, which asset keeps coming back, and what is still waiting. All three come from the
findings the crews record — the repeatable table of block B11 — which live inside a capture's JSONB
rather than in a table of their own.

That last fact shapes the module, and one decision follows from it that has to be stated rather
than assumed: **a finding has no state, so "open" is a definition and not a fact.** Here it means
*no later work order was closed on the same asset*. It is an approximation — a crew may close an
order on that asset for something else — and the payload says so in words, because a backlog number
whose definition nobody can see is one that gets argued about instead of worked.

The heat of a feeder is a share, not a colour: the platform holds no feeder geometry (that lives in
the GIS), so what it can honestly report is how the defects distribute across feeders and let the
screen draw the intensity. A map of points is possible later from the captures' own coordinates.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.responses.models import FormResponse
from app.workorders.models import WorkOrder, WorkOrderState

#: Answer keys read here. Canonical (ADR-004): no real GIS field name appears in this module.
KEY_FINDINGS = "findings"
KEY_DEFECTS = "defects"
KEY_ASSET = "asset_code"
KEY_DEFECT = "defect_code"
KEY_CRITICALITY = "criticality"
KEY_WANTS_ORDER = "generate_work_order"

#: Worst first, which is the order a planner reads in. Written out rather than sorted
#: alphabetically, because «alta» before «critica» would put the second-worst first.
CRITICALITY_ORDER = ("critica", "alta", "media", "baja")

#: States that mean a work order dealt with the asset. `aprobada` counts: the field work is done
#: and the office is finishing the paperwork; a finding is not open because a supervisor is away.
ATTENDED_STATES = (WorkOrderState.CLOSED_FIELD, WorkOrderState.APPROVED, WorkOrderState.CLOSED)

#: What "open" means here, in the words the payload carries. Written once so the definition the
#: screen shows and the one the code applies cannot drift.
OPEN_DEFINITION = (
    "abierto significa que no hay ninguna OT posterior cerrada sobre el mismo activo. Es una "
    "aproximación: la cuadrilla pudo cerrar una OT en ese activo por otra cosa. El activo sin "
    "código no se puede seguir, y esos hallazgos se cuentan aparte"
)


@dataclass(frozen=True)
class Finding:
    """One finding a crew recorded, with where and when."""

    work_order_id: uuid.UUID
    order_code: str | None
    asset_code: str | None
    defect_code: str
    criticality: str
    feeder_code: str | None
    recorded_at: datetime | None
    #: True when the crew asked for a work order to be generated from it.
    wants_order: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": str(self.work_order_id),
            "order_code": self.order_code,
            "asset_code": self.asset_code,
            "defect_code": self.defect_code,
            "criticality": self.criticality,
            "feeder_code": self.feeder_code,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "wants_order": self.wants_order,
        }


@dataclass(frozen=True)
class FeederHeat:
    feeder_code: str
    defects: int
    #: Share of the period's defects on this feeder. The "heat" the screen draws.
    share: float
    #: The defect that dominates it: what says whether the feeder needs pruning or hardware.
    top_defect: tuple[str, int] | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "feeder_code": self.feeder_code,
            "defects": self.defects,
            "share": self.share,
            "top_defect": (
                {"defect_code": self.top_defect[0], "times": self.top_defect[1]}
                if self.top_defect
                else None
            ),
        }


@dataclass(frozen=True)
class AssetRecurrence:
    asset_code: str
    findings: int
    #: The distinct defects seen on it. One defect three times is a repair that did not hold; three
    #: different defects is an asset at the end of its life, and the planner does different things.
    defects: dict[str, int]
    worst_criticality: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset_code": self.asset_code,
            "findings": self.findings,
            "defects": self.defects,
            "worst_criticality": self.worst_criticality,
        }


@dataclass
class MaintenanceBoard:
    since: datetime
    until: datetime
    defect_filter: str | None = None
    findings: int = 0
    by_feeder: list[FeederHeat] = field(default_factory=list)
    #: Findings whose capture recorded no feeder. They cannot be placed, and a heat map that
    #: silently dropped them would under-report every feeder.
    without_feeder: int = 0
    recurrence: list[AssetRecurrence] = field(default_factory=list)
    open_by_criticality: dict[str, int] = field(default_factory=dict)
    attended: int = 0
    #: Open findings with no asset code: they cannot be followed, and they are not «attended».
    untrackable: int = 0
    wants_order: int = 0
    by_defect: dict[str, int] = field(default_factory=dict)
    open_findings: list[Finding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "since": self.since.isoformat(),
            "until": self.until.isoformat(),
            "defect_filter": self.defect_filter,
            "findings": self.findings,
            "heat": {
                "by_feeder": [item.as_dict() for item in self.by_feeder],
                "without_feeder": self.without_feeder,
            },
            "recurrence": [item.as_dict() for item in self.recurrence],
            "backlog": {
                "open_by_criticality": self.open_by_criticality,
                "open": sum(self.open_by_criticality.values()),
                "attended": self.attended,
                "untrackable": self.untrackable,
                "wants_order": self.wants_order,
                "definition": OPEN_DEFINITION,
            },
            "by_defect": self.by_defect,
            "open_findings": [item.as_dict() for item in self.open_findings],
        }


def _captures(
    session: Session, unit_id: uuid.UUID, since: datetime, until: datetime
) -> list[tuple[WorkOrder, FormResponse]]:
    rows = session.execute(
        select(WorkOrder, FormResponse)
        .join(FormResponse, FormResponse.work_order_id == WorkOrder.id)
        .where(
            WorkOrder.business_unit_id == unit_id,
            FormResponse.submitted_at.is_not(None),
            FormResponse.submitted_at >= since,
            FormResponse.submitted_at <= until,
        )
        .order_by(FormResponse.submitted_at)
    )
    return [(order, response) for order, response in rows]


def _findings_of(order: WorkOrder, response: FormResponse) -> list[Finding]:
    """The findings of one capture, from the repeatable table and from the plain defect list.

    Both, because they are the same information in two places: B11 is the table a crew fills for a
    finding it wants followed up, and B05's `defects` is the list of what it saw on the asset it was
    working on. A board that read only the table would miss every defect noticed during a routine
    inspection, which is most of them.
    """
    answers = response.answers or {}
    found: list[Finding] = []

    rows = answers.get(KEY_FINDINGS)
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            defect = row.get(KEY_DEFECT)
            if not isinstance(defect, str) or not defect.strip():
                continue
            found.append(
                Finding(
                    work_order_id=order.id,
                    order_code=order.code,
                    asset_code=_text(row.get(KEY_ASSET)) or order.asset_code,
                    defect_code=defect.strip(),
                    criticality=_text(row.get(KEY_CRITICALITY)) or "media",
                    feeder_code=_text(answers.get("feeder_code")) or order.feeder_code,
                    recorded_at=response.submitted_at,
                    wants_order=bool(row.get(KEY_WANTS_ORDER)),
                )
            )

    plain = answers.get(KEY_DEFECTS)
    if isinstance(plain, list):
        for defect in plain:
            if not isinstance(defect, str) or not defect.strip():
                continue
            found.append(
                Finding(
                    work_order_id=order.id,
                    order_code=order.code,
                    asset_code=_text(answers.get("code")) or order.asset_code,
                    defect_code=defect.strip(),
                    # The plain list carries no criticality; the asset's general condition is the
                    # closest thing the capture says, and inventing «alta» would put work at the
                    # top of a planner's list that nobody asked to be there.
                    criticality=_criticality_from_condition(answers.get("general_condition")),
                    feeder_code=_text(answers.get("feeder_code")) or order.feeder_code,
                    recorded_at=response.submitted_at,
                    wants_order=False,
                )
            )
    return found


def _criticality_from_condition(condition: Any) -> str:
    """The asset's condition read as a criticality, for a defect recorded without one."""
    return {"critico": "critica", "malo": "alta", "regular": "media", "bueno": "baja"}.get(
        condition if isinstance(condition, str) else "", "media"
    )


def _text(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _last_attended(session: Session, unit_id: uuid.UUID, assets: set[str]) -> dict[str, datetime]:
    """When each asset was last worked on, from the audit trail.

    From the trail and **not** from `work_order.updated_at`, which was the first version and was
    wrong: that column moves on any edit to the row — a note, a reassignment — so reassigning an old
    order today would have closed a finding recorded yesterday. The trail records the moment the
    order *reached* a closing state, which is the thing this needs, and it cannot be rewritten
    (RF-160).

    Only orders whose asset is one of the findings' assets, and only their closing transitions: the
    query is bounded by the backlog it is answering about.
    """
    if not assets:
        return {}
    reached = AuditEvent.payload["to"].astext.label("reached")
    rows = session.execute(
        select(WorkOrder.asset_code, func.max(AuditEvent.occurred_at))
        .join(AuditEvent, AuditEvent.work_order_id == WorkOrder.id)
        .where(
            WorkOrder.business_unit_id == unit_id,
            WorkOrder.asset_code.in_(list(assets)),
            reached.in_([state.value for state in ATTENDED_STATES]),
        )
        .group_by(WorkOrder.asset_code)
    ).all()
    return {asset: when for asset, when in rows if asset is not None and when is not None}


def build(
    session: Session,
    unit_id: uuid.UUID,
    *,
    since: datetime,
    until: datetime,
    defect_code: str | None = None,
) -> MaintenanceBoard:
    """The whole board, over the findings of the period."""
    board = MaintenanceBoard(since=since, until=until, defect_filter=defect_code)

    findings: list[Finding] = []
    for order, response in _captures(session, unit_id, since, until):
        findings.extend(_findings_of(order, response))
    if defect_code is not None:
        findings = [item for item in findings if item.defect_code == defect_code]
    board.findings = len(findings)
    if not findings:
        return board

    per_feeder: dict[str, list[Finding]] = defaultdict(list)
    per_asset: dict[str, list[Finding]] = defaultdict(list)
    defects: Counter[str] = Counter()
    for item in findings:
        defects[item.defect_code] += 1
        if item.wants_order:
            board.wants_order += 1
        if item.feeder_code is None:
            board.without_feeder += 1
        else:
            per_feeder[item.feeder_code].append(item)
        if item.asset_code is not None:
            per_asset[item.asset_code].append(item)

    placed = sum(len(rows) for rows in per_feeder.values())
    board.by_feeder = sorted(
        (
            FeederHeat(
                feeder_code=feeder,
                defects=len(rows),
                share=len(rows) / placed if placed else 0.0,
                top_defect=Counter(row.defect_code for row in rows).most_common(1)[0],
            )
            for feeder, rows in per_feeder.items()
        ),
        key=lambda item: (-item.defects, item.feeder_code),
    )

    board.recurrence = sorted(
        (
            AssetRecurrence(
                asset_code=asset,
                findings=len(rows),
                defects=dict(Counter(row.defect_code for row in rows).most_common()),
                worst_criticality=_worst(row.criticality for row in rows),
            )
            for asset, rows in per_asset.items()
            if len(rows) > 1
        ),
        key=lambda item: (
            -item.findings,
            CRITICALITY_ORDER.index(item.worst_criticality)
            if item.worst_criticality in CRITICALITY_ORDER
            else len(CRITICALITY_ORDER),
            item.asset_code,
        ),
    )

    board.by_defect = dict(defects.most_common())
    _fill_backlog(session, unit_id, board, findings)
    return board


def _worst(values: Any) -> str:
    """The worst criticality of a set, by the requirement's own order."""
    seen = {value for value in values if value in CRITICALITY_ORDER}
    for level in CRITICALITY_ORDER:
        if level in seen:
            return level
    return "media"


def _fill_backlog(
    session: Session, unit_id: uuid.UUID, board: MaintenanceBoard, findings: list[Finding]
) -> None:
    """Which findings are still waiting, by the definition the payload carries."""
    assets = {item.asset_code for item in findings if item.asset_code}
    attended_since = _last_attended(session, unit_id, assets)

    open_counts: Counter[str] = Counter()
    for item in findings:
        if item.asset_code is None:
            # Nothing to follow it by. Counted apart rather than called open or attended: both would
            # be a claim the data does not support.
            board.untrackable += 1
            continue
        attended = attended_since.get(item.asset_code)
        if attended is not None and item.recorded_at is not None and attended > item.recorded_at:
            board.attended += 1
            continue
        open_counts[item.criticality] += 1
        board.open_findings.append(item)

    board.open_by_criticality = {
        level: open_counts[level] for level in CRITICALITY_ORDER if open_counts[level]
    }
    board.open_findings.sort(
        key=lambda item: (
            CRITICALITY_ORDER.index(item.criticality)
            if item.criticality in CRITICALITY_ORDER
            else len(CRITICALITY_ORDER),
            item.recorded_at or datetime.min,
        )
    )
