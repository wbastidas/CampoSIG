"""Applying what a device pushed (RF-101, RF-103, RF-105).

The ledger of :func:`app.sync.service.push_operation` answers «did this operation arrive before?».
This module answers «and what did it do?» — it dispatches an operation to the service that owns the
change, so the phone's outbox has one endpoint and the platform keeps one implementation of each
rule.

Three decisions shape it:

* **A device may only drive the states of the field.** The phone can say «en camino», «en sitio»,
  «suspendida» or «cerrada en campo»; it cannot say «aprobada», «cerrada» or «anulada». Those are
  decisions of the office, taken by a person who answers for them, and a transition table alone
  would happily accept them from a phone — it describes what is reachable, not who may ask.
* **A rejection is recorded, not raised.** A form that fails validation, a transition that does not
  exist, an evidence without its response: the device has to **park** that operation and show it to
  a human, so it is written into the ledger and answered with a reason. An exception would make the
  outbox retry it until the end of time.
* **The answers come before their evidence.** Evidence hangs off a response, so an evidence pushed
  first is rejected with that sentence rather than silently dropped — the order is part of the
  contract the outbox has to respect.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.org.models import BusinessUnit
from app.responses.models import EvidenceStage, FormResponse
from app.responses.service import (
    AnswerValidationError,
    AudioNotAllowedError,
    NotEditableError,
    OutagePermitError,
    register_evidence,
    save_answers,
)
from app.sync.models import Device
from app.workorders.models import WorkOrder, WorkOrderState
from app.workorders.service import (
    InvalidTransitionError,
    ReasonRequiredError,
    transition,
)

#: The operation kinds a device may push. Anything else is parked with a reason: a phone that
#: invented a kind is a phone running a version the server does not know, and guessing what it
#: meant is how captured work gets silently dropped.
KIND_TRANSITION = "transition"
KIND_FORM_RESPONSE = "form_response"
KIND_EVIDENCE = "evidence"

APPLICABLE_KINDS = (KIND_TRANSITION, KIND_FORM_RESPONSE, KIND_EVIDENCE)

#: States a device may ask for. The field ones, and nothing else: `aprobada`, `cerrada` and
#: `anulada` are decisions of the office and `en_revision` is the reviewer's queue.
DEVICE_TRANSITIONS = frozenset(
    {
        WorkOrderState.DOWNLOADED,
        WorkOrderState.EN_ROUTE,
        WorkOrderState.ON_SITE,
        WorkOrderState.IN_EXECUTION,
        WorkOrderState.SUSPENDED,
        WorkOrderState.CLOSED_FIELD,
        WorkOrderState.SYNCED,
    }
)


class OperationRejectedError(Exception):
    """The operation cannot be applied and the device must park it.

    Carries the sentence a technician reads, because «rechazada» on its own sends them to the
    office to ask what happened.
    """


def apply_operation(
    session: Session,
    unit: BusinessUnit,
    device: Device,
    *,
    kind: str,
    order: WorkOrder | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Apply one pushed operation, returning what to record in the ledger.

    :raises OperationRejectedError: for anything the device must park and show to a person.
    """
    if kind not in APPLICABLE_KINDS:
        raise OperationRejectedError(
            f"la plataforma no conoce operaciones de tipo «{kind}»; admitidos: "
            f"{', '.join(APPLICABLE_KINDS)}"
        )
    if order is None:
        raise OperationRejectedError(f"una operación «{kind}» necesita la OT a la que pertenece")

    if kind == KIND_TRANSITION:
        return _apply_transition(session, device, order, payload)
    if kind == KIND_FORM_RESPONSE:
        return _apply_form_response(session, unit, device, order, payload)
    return _apply_evidence(session, order, payload)


def _apply_transition(
    session: Session, device: Device, order: WorkOrder, payload: dict[str, Any]
) -> dict[str, Any]:
    target = str(payload.get("target") or "").strip()
    if not target:
        raise OperationRejectedError("la operación no dice a qué estado pasar")
    if target not in DEVICE_TRANSITIONS:
        raise OperationRejectedError(
            f"un dispositivo no puede llevar una OT a «{target}»: es una decisión de la oficina"
        )
    reason = payload.get("reason")
    previous = order.state
    try:
        transition(
            session,
            order,
            target,
            reason=str(reason) if reason else None,
            actor=device.user_sub or device.device_key,
        )
    except (InvalidTransitionError, ReasonRequiredError) as exc:
        raise OperationRejectedError(str(exc)) from exc
    return {"from": previous, "to": order.state}


def _apply_form_response(
    session: Session,
    unit: BusinessUnit,
    device: Device,
    order: WorkOrder,
    payload: dict[str, Any],
) -> dict[str, Any]:
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        raise OperationRejectedError("la operación no trae las respuestas del formulario")
    try:
        response = save_answers(
            session,
            unit,
            order,
            answers=answers,
            device_key=device.device_key,
            captured_by=device.user_sub,
            captured_at=_time(payload.get("captured_at")),
            submit=bool(payload.get("submit")),
        )
    except (AnswerValidationError, NotEditableError, OutagePermitError) as exc:
        raise OperationRejectedError(str(exc)) from exc
    return {
        "response_id": str(response.id),
        "form_code": response.form_code,
        "form_version": response.form_version,
        "state": response.state,
        "fields": len(answers),
    }


def _apply_evidence(session: Session, order: WorkOrder, payload: dict[str, Any]) -> dict[str, Any]:
    response = session.scalars(
        select(FormResponse).where(
            FormResponse.work_order_id == order.id,
            FormResponse.form_code == order.form_code,
        )
    ).first()
    if response is None:
        # The order matters and is part of the contract: evidence hangs off a response.
        raise OperationRejectedError(
            "hay que enviar la respuesta del formulario antes que sus evidencias"
        )
    storage_key = str(payload.get("storage_key") or "").strip()
    content_hash = str(payload.get("content_hash") or "").strip()
    kind = str(payload.get("kind") or "").strip()
    if not (storage_key and content_hash and kind):
        raise OperationRejectedError(
            "una evidencia necesita su tipo, su clave de almacenamiento y su hash"
        )
    try:
        evidence = register_evidence(
            session,
            response,
            kind=kind,
            storage_key=storage_key,
            content_hash=content_hash,
            stage=str(payload.get("stage") or EvidenceStage.NOT_APPLICABLE),
            size_bytes=int(payload.get("size_bytes") or 0),
            mime_type=payload.get("mime_type"),
            latitude=_number(payload.get("latitude")),
            longitude=_number(payload.get("longitude")),
            gps_accuracy_m=_number(payload.get("gps_accuracy_m")),
            captured_at=_time(payload.get("captured_at")),
            framing=payload.get("framing"),
        )
    except AudioNotAllowedError as exc:
        # The area's policy says this audio is not kept (RF-151). A rejection and not an error:
        # the phone has to stop offering to send it, and the technician has to know why.
        raise OperationRejectedError(str(exc)) from exc
    return {
        "evidence_id": str(evidence.id),
        "kind": evidence.kind,
        "stage": evidence.stage,
        "content_hash": evidence.content_hash,
    }


def order_of(session: Session, work_order_id: uuid.UUID | None) -> WorkOrder | None:
    return session.get(WorkOrder, work_order_id) if work_order_id else None


def _time(value: Any) -> datetime | None:
    """A device clock, parsed leniently: a bad timestamp is not worth losing the capture over."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
