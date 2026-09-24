"""Requesting, granting and returning a consignación (RF-024).

The acceptance criterion is a refusal — «no se habilita el formulario F-TR-02 sin un N.º de
consignación» — and :func:`permit_blocker` is where it lives. It returns the sentence that explains
the refusal rather than a boolean, because a crew stopped by a rule they cannot read is a crew that
calls the office, and the office does not know either.

Three rules this module enforces and one it deliberately does not:

* **Two people.** Whoever requested a consignación cannot grant it. A descargo somebody granted to
  themselves is the failure the whole procedure exists to prevent, and the platform will not be the
  place that made it possible.
* **A number when granting.** The state alone is not the authority: the number is what the crew
  reads back over the radio and what an investigation asks for.
* **A window with both ends.** An open-ended consignación is not a window, and recording one exists
  precisely to be able to say whether the work happened inside it.
* **Not refused: working outside the window.** That is recorded, loudly, in the capture's own review
  and in the trail. Refusing the capture would lose the record of what actually happened — the one
  thing an investigation needs — so the platform refuses what must not happen and records what did.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import EventKind
from app.audit.service import record
from app.org.models import BusinessUnit
from app.outages.models import OutageRequest, OutageState
from app.workorders.models import WorkOrder

#: The form the consignación gates (SRS 4.3). Named here because the rule is about this form and
#: nothing else: the ATS has its own gate, and a routine inspection needs no descargo.
PERMIT_FORM = "F-TR-02"


class OutageError(Exception):
    pass


class NotDecidableError(OutageError):
    """Raised when a request already has a decision."""


class SelfApprovalError(OutageError):
    """Raised when the requester tries to grant their own consignación."""


@dataclass(frozen=True)
class WindowCheck:
    """Whether a moment falls inside the approved window, and what to say when it does not."""

    inside: bool
    #: In Spanish, for the review screen and the trail. None when inside.
    message: str | None = None
    minutes_early: int = 0
    minutes_late: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "inside": self.inside,
            "message": self.message,
            "minutes_early": self.minutes_early,
            "minutes_late": self.minutes_late,
        }


def request_outage(
    session: Session,
    unit: BusinessUnit,
    *,
    equipment: str,
    window_start: datetime,
    window_end: datetime,
    requested_by: str,
    feeder_code: str | None = None,
    substation_code: str | None = None,
    note: str | None = None,
) -> OutageRequest:
    """Ask the Centro de Control for a consignación."""
    if window_end <= window_start:
        raise OutageError(
            "la ventana termina antes de empezar: una consignación sin ventana no se puede "
            "comparar con nada, y compararla es para lo que se registra"
        )
    if not equipment.strip():
        raise OutageError("hay que decir qué equipo o tramo se consigna")
    request = OutageRequest(
        business_unit_id=unit.id,
        equipment=equipment.strip(),
        feeder_code=feeder_code,
        substation_code=substation_code,
        window_start=window_start,
        window_end=window_end,
        requested_by=requested_by,
        note=note,
        state=OutageState.REQUESTED,
    )
    session.add(request)
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.CREATED,
        subject_type="outage_request",
        subject_id=str(request.id),
        actor=requested_by,
        payload={
            "equipment": request.equipment,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        },
    )
    return request


def approve(
    session: Session,
    unit: BusinessUnit,
    request: OutageRequest,
    *,
    number: str,
    decided_by: str,
    note: str | None = None,
) -> OutageRequest:
    """Grant the consignación with the number the Centro de Control assigned."""
    _must_be_open(request)
    if not number.strip():
        raise OutageError(
            "una consignación aprobada sin número no habilita nada: el número es la autoridad, "
            "es lo que la cuadrilla repite por radio y lo que se pide después"
        )
    if decided_by == request.requested_by:
        raise SelfApprovalError(
            "quien solicitó la consignación no puede otorgarla: un descargo que alguien se dio a "
            "sí mismo es justamente lo que el procedimiento existe para evitar"
        )
    request.number = number.strip()
    request.state = OutageState.APPROVED
    request.decided_by = decided_by
    request.decided_at = datetime.now(UTC)
    if note:
        request.note = note
    session.flush()
    _decided(session, unit, request, actor=decided_by, payload={"number": request.number})
    return request


def reject(
    session: Session,
    unit: BusinessUnit,
    request: OutageRequest,
    *,
    decided_by: str,
    note: str,
) -> OutageRequest:
    """Refuse the consignación, with the reason.

    The reason is required: «no» without a reason sends the planner back to the Centro de Control to
    ask what it was, which is a phone call the platform can save.
    """
    _must_be_open(request)
    if not note.strip():
        raise OutageError("una consignación negada tiene que decir por qué")
    if decided_by == request.requested_by:
        raise SelfApprovalError("quien solicitó la consignación no puede decidirla")
    request.state = OutageState.REJECTED
    request.decided_by = decided_by
    request.decided_at = datetime.now(UTC)
    request.note = note.strip()
    session.flush()
    _decided(session, unit, request, actor=decided_by, payload={"note": request.note})
    return request


def hand_back(
    session: Session,
    unit: BusinessUnit,
    request: OutageRequest,
    *,
    returned_by: str,
    at: datetime | None = None,
) -> OutageRequest:
    """Record that the crew handed the consignación back and the equipment may be re-energised."""
    if request.state != OutageState.APPROVED:
        raise OutageError(
            f"la consignación está «{request.state}»: solo se devuelve una que esté aprobada"
        )
    request.state = OutageState.RETURNED
    request.returned_at = at or datetime.now(UTC)
    request.returned_by = returned_by
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.TRANSITION,
        subject_type="outage_request",
        subject_id=str(request.id),
        actor=returned_by,
        payload={"to": OutageState.RETURNED.value, "number": request.number},
    )
    return request


def expire_due(
    session: Session, unit: BusinessUnit, *, now: datetime | None = None
) -> list[OutageRequest]:
    """Mark as expired the granted consignaciones whose window has passed unreturned.

    «Vencida» and not «rechazada»: nobody refused it, the window simply went by. The distinction
    matters to whoever asks later why the work was not done.
    """
    moment = now or datetime.now(UTC)
    rows = list(
        session.execute(
            select(OutageRequest).where(
                OutageRequest.business_unit_id == unit.id,
                OutageRequest.state == OutageState.APPROVED,
                OutageRequest.window_end < moment,
            )
        ).scalars()
    )
    for request in rows:
        request.state = OutageState.EXPIRED
        record(
            session,
            unit.id,
            kind=EventKind.TRANSITION,
            subject_type="outage_request",
            subject_id=str(request.id),
            actor="sistema:consignaciones",
            payload={"to": OutageState.EXPIRED.value, "number": request.number},
        )
    session.flush()
    return rows


def link(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    request: OutageRequest,
    *,
    actor: str,
) -> WorkOrder:
    """Attach a work order to the consignación it will work under (RF-024)."""
    if order.business_unit_id != unit.id or request.business_unit_id != unit.id:
        raise OutageError("la OT y la consignación tienen que ser de la misma unidad de negocio")
    order.outage_request_id = request.id
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.FIELD_CHANGED,
        subject_type="orden_trabajo",
        subject_id=str(order.id),
        work_order_id=order.id,
        asset_code=order.asset_code,
        actor=actor,
        payload={
            "field": "outage_request_id",
            "to": str(request.id),
            "number": request.number,
        },
    )
    return order


def unlink(session: Session, unit: BusinessUnit, order: WorkOrder, *, actor: str) -> WorkOrder:
    if order.outage_request_id is None:
        raise OutageError("esa OT no está vinculada a ninguna consignación")
    previous = order.outage_request_id
    order.outage_request_id = None
    session.flush()
    record(
        session,
        unit.id,
        kind=EventKind.FIELD_CHANGED,
        subject_type="orden_trabajo",
        subject_id=str(order.id),
        work_order_id=order.id,
        actor=actor,
        payload={"field": "outage_request_id", "from": str(previous), "to": None},
    )
    return order


def outage_of(session: Session, order: WorkOrder) -> OutageRequest | None:
    if order.outage_request_id is None:
        return None
    return session.get(OutageRequest, order.outage_request_id)


def permit_blocker(session: Session, order: WorkOrder, form_code: str) -> str | None:
    """Why the permit form cannot be filled for this order, or None when it can (RF-024).

    The criterion in one function: «no se habilita el formulario F-TR-02 sin un N.º de
    consignación». A sentence and not a boolean, because a crew stopped by a rule they cannot read
    calls the office, and the office does not know either.
    """
    if form_code != PERMIT_FORM:
        return None
    request = outage_of(session, order)
    if request is None:
        return (
            f"el formulario {PERMIT_FORM} necesita una consignación: vincule la OT con la "
            "solicitud otorgada por el Centro de Control antes de llenar el permiso de trabajo"
        )
    if not request.number:
        return (
            f"la consignación está «{request.state}» y todavía no tiene número; el "
            f"{PERMIT_FORM} se habilita con el número que otorga el Centro de Control"
        )
    if request.state not in (OutageState.APPROVED, OutageState.RETURNED):
        return (
            f"la consignación {request.number} está «{request.state}»: el {PERMIT_FORM} se llena "
            "bajo una consignación otorgada"
        )
    return None


def window_check(request: OutageRequest, at: datetime) -> WindowCheck:
    """Whether `at` falls inside the approved window.

    Never a refusal, always a record. A crew working outside the window is working on a line that
    may be re-energised, and that is exactly what has to be **visible** afterwards — refusing the
    capture would lose the only record of what happened.
    """
    start, end = _aware(request.window_start), _aware(request.window_end)
    moment = _aware(at)
    if moment < start:
        minutes = int((start - moment).total_seconds() // 60)
        return WindowCheck(
            inside=False,
            minutes_early=minutes,
            message=(
                f"el trabajo se registró {minutes} minuto(s) antes de que empezara la ventana de "
                f"la consignación {request.number or 'sin número'} "
                f"({start.isoformat()} a {end.isoformat()})"
            ),
        )
    if moment > end:
        minutes = int((moment - end).total_seconds() // 60)
        return WindowCheck(
            inside=False,
            minutes_late=minutes,
            message=(
                f"el trabajo se registró {minutes} minuto(s) después de que terminara la ventana "
                f"de la consignación {request.number or 'sin número'} "
                f"({start.isoformat()} a {end.isoformat()})"
            ),
        )
    return WindowCheck(inside=True)


def requests_of(
    session: Session, unit: BusinessUnit, *, state: str | None = None
) -> list[OutageRequest]:
    query = select(OutageRequest).where(OutageRequest.business_unit_id == unit.id)
    if state:
        query = query.where(OutageRequest.state == state)
    return list(
        session.execute(query.order_by(OutageRequest.window_start, OutageRequest.id)).scalars()
    )


def orders_under(session: Session, request: OutageRequest) -> list[WorkOrder]:
    """The work orders working under this consignación.

    Several, by design: «consignación del alimentador sur, sábado de 06:00 a 12:00» covers every
    front under it, and one request per order would have the Centro de Control granting six
    descargos for one outage.
    """
    return list(
        session.execute(
            select(WorkOrder)
            .where(WorkOrder.outage_request_id == request.id)
            .order_by(WorkOrder.code.nulls_last(), WorkOrder.id)
        ).scalars()
    )


def as_dict(request: OutageRequest, *, orders: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(request.id),
        "number": request.number,
        "state": request.state,
        "equipment": request.equipment,
        "feeder_code": request.feeder_code,
        "substation_code": request.substation_code,
        "window_start": request.window_start.isoformat(),
        "window_end": request.window_end.isoformat(),
        "requested_by": request.requested_by,
        "decided_by": request.decided_by,
        "decided_at": request.decided_at.isoformat() if request.decided_at else None,
        "returned_at": request.returned_at.isoformat() if request.returned_at else None,
        "returned_by": request.returned_by,
        "note": request.note,
        "grants_permit": request.grants_permit,
    }
    if orders is not None:
        payload["orders"] = orders
    return payload


def _must_be_open(request: OutageRequest) -> None:
    if request.state != OutageState.REQUESTED:
        raise NotDecidableError(
            f"la consignación ya está «{request.state}»: una decisión no se toma dos veces"
        )


def _decided(
    session: Session,
    unit: BusinessUnit,
    request: OutageRequest,
    *,
    actor: str,
    payload: dict[str, Any],
) -> None:
    record(
        session,
        unit.id,
        kind=EventKind.DECIDED,
        subject_type="outage_request",
        subject_id=str(request.id),
        actor=actor,
        payload={"state": request.state, **payload},
    )


def _aware(moment: datetime) -> datetime:
    """A timezone-aware moment. PostgreSQL hands these back aware; a test may not."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def pending_for(session: Session, unit: BusinessUnit) -> dict[str, int]:
    """Counts for the screen: how many are waiting on the Centro de Control."""
    counts: dict[str, int] = {}
    for request in requests_of(session, unit):
        counts[request.state] = counts.get(request.state, 0) + 1
    return counts


def unused_ids(session: Session, unit: BusinessUnit) -> list[uuid.UUID]:
    """Granted consignaciones with no work order attached.

    A descargo nobody used is a line de-energised for nothing: customers without service and an
    index the unit reports. Surfaced rather than counted silently.
    """
    granted = requests_of(session, unit, state=OutageState.APPROVED.value)
    return [request.id for request in granted if not orders_under(session, request)]
