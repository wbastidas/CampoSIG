"""Issuing and verifying the acta (RF-115).

Issuance is a transaction: the register row is written, the PDF is rendered from that row's own
code and timestamp, and the hash of the bytes goes back onto the row. That order matters — the
document has to carry the code that identifies it, so the code cannot be derived from the
document.

Reprinting issues a **new** document. It would be tempting to hand back the same one, but the
work order may have been corrected in between, and two people would then hold two different
papers claiming the same identity. A register that cannot tell them apart is worse than none.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.org.models import BusinessUnit
from app.reports.acta import (
    Acta,
    ActaDecision,
    ActaFinding,
    ActaPhoto,
    ImageLoader,
    data_uri,
    render_pdf,
    sections_from_form,
    signatures_from_form,
)
from app.reports.models import KIND_ACTA, IssuedDocument
from app.responses.models import Evidence, FormResponse, ValueOrigin
from app.responses.service import compose_for
from app.review.service import compliance_findings, decision_history
from app.workorders.models import WorkOrder

#: Length of the code the QR carries, in random bytes before encoding. 12 bytes is 16
#: URL-safe characters: unguessable, and short enough to read aloud over a radio when the
#: camera will not focus.
CODE_BYTES = 12


def _new_code() -> str:
    return secrets.token_urlsafe(CODE_BYTES)


def order_label(order: WorkOrder) -> str:
    """What identifies a work order on paper and on the verification page.

    One function because the two must never disagree. Most work orders here have no
    human-readable code — `create_work_order` does not assign one, only the imported ones carry
    an external number — so the identifier is usually the id. When the acta printed the id and
    the page printed a dash, verification failed to match on exactly the work orders that are
    the majority.
    """
    return order.code or str(order.id)


def _photos(evidence: list[Evidence], loader: ImageLoader | None) -> list[ActaPhoto]:
    """Photographs, in the order before → during → after, whatever order they were stored in."""
    stage_order = {"antes": 0, "durante": 1, "despues": 2}
    ordered = sorted(evidence, key=lambda item: (stage_order.get(item.stage, 9), item.storage_key))
    photos: list[ActaPhoto] = []
    for item in ordered:
        loaded = loader(item.storage_key) if loader else None
        photos.append(
            ActaPhoto(
                stage=item.stage,
                kind=item.kind,
                storage_hash=item.content_hash,
                integrity_verified=item.integrity_verified,
                data_uri=None if loaded is None else data_uri(*loaded),
            )
        )
    return photos


def build_acta(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    verification_code: str,
    issued_by: str,
    issued_at: datetime,
    verification_base_url: str,
    image_loader: ImageLoader | None = None,
) -> Acta:
    """Assemble the document from stored data only.

    Nothing is computed for the paper that is not already the platform's answer: the compliance
    findings come from the same deterministic rules the approval gate used, and the AI
    provenance from the same rows the supervisor audited. An acta that recomputed anything could
    disagree with the decision it documents.
    """
    response = session.scalars(
        select(FormResponse).where(FormResponse.work_order_id == order.id)
    ).first()
    form = compose_for(session, unit, order)
    answers: Mapping[str, object] = response.answers if response else {}

    provenance = [
        {
            "field_key": entry.field_key,
            "origin": entry.origin,
            "confidence": entry.confidence,
            "model_name": entry.model_name,
            "model_version": entry.model_version,
            "accepted_unchanged": entry.accepted_unchanged,
            "confirmed_by": entry.confirmed_by,
            "is_ai": entry.origin in (ValueOrigin.VOICE, ValueOrigin.VISION),
        }
        for entry in (response.provenance if response else [])
    ]

    findings = [
        ActaFinding(
            message=finding.message,
            outcome=finding.outcome.value,
            severity=finding.severity.value,
            citation=" ".join(part for part in (finding.norm_ref, finding.article_ref) if part)
            or None,
            limit_verified=finding.limit_verified,
        )
        for finding in compliance_findings(session, order, response)
    ]

    decisions = [
        ActaDecision(
            decision=row.decision,
            reviewer=row.reviewer_sub,
            note=row.note,
            decided_at=row.decided_at.isoformat(timespec="minutes") if row.decided_at else None,
        )
        for row in decision_history(session, order)
    ]

    identifiers = {"cliente": str(answers.get("customer_id") or "") or None}
    return Acta(
        verification_code=verification_code,
        verification_url=f"{verification_base_url.rstrip('/')}/{verification_code}",
        issued_by=issued_by,
        issued_at=issued_at,
        business_unit=unit.code,
        work_order_code=order_label(order),
        work_order_state=str(order.state),
        work_type=str(order.work_type),
        form_code=form.code,
        form_version=form.version,
        form_title=form.definition.form.title,
        asset_code=order.asset_code,
        feeder_code=order.feeder_code,
        zone=order.zone,
        external_ref=order.external_ref,
        sections=sections_from_form(form.schema, form.ui_schema, answers, provenance),
        photos=_photos(list(response.evidence) if response else [], image_loader),
        signatures=signatures_from_form(
            form.schema,
            answers,
            image_loader,
            {key: value for key, value in identifiers.items() if value},
        ),
        findings=findings,
        decisions=decisions,
        warnings=list(form.warnings),
    )


def issue_acta(
    session: Session,
    unit: BusinessUnit,
    order: WorkOrder,
    *,
    issued_by: str,
    verification_base_url: str,
    image_loader: ImageLoader | None = None,
) -> tuple[IssuedDocument, bytes]:
    """Render the acta and register it, so its QR can be verified later."""
    response = session.scalars(
        select(FormResponse).where(FormResponse.work_order_id == order.id)
    ).first()
    issued_at = datetime.now(UTC)
    record = IssuedDocument(
        business_unit_id=order.business_unit_id,
        work_order_id=order.id,
        response_id=response.id if response else None,
        kind=KIND_ACTA,
        verification_code=_new_code(),
        content_hash="",
        byte_size=0,
        state_at_issue=str(order.state),
        issued_by=issued_by,
        issued_at=issued_at,
    )

    acta = build_acta(
        session,
        unit,
        order,
        verification_code=record.verification_code,
        issued_by=issued_by,
        issued_at=issued_at,
        verification_base_url=verification_base_url,
        image_loader=image_loader,
    )
    record.form_code = acta.form_code
    record.form_version = acta.form_version

    pdf, digest = render_pdf(acta)
    record.content_hash = digest
    record.byte_size = len(pdf)
    session.add(record)
    session.flush()
    return record, pdf


def find_by_code(session: Session, code: str) -> IssuedDocument | None:
    """The document a QR points at, or None.

    None is the answer that makes the QR mean something: a code the platform never issued is a
    document the platform never produced, and saying so is the entire point of verifying.
    """
    return session.scalars(
        select(IssuedDocument).where(IssuedDocument.verification_code == code)
    ).first()


def documents_for_order(
    session: Session, unit_id: uuid.UUID, order_id: uuid.UUID
) -> list[IssuedDocument]:
    return list(
        session.scalars(
            select(IssuedDocument)
            .where(
                IssuedDocument.business_unit_id == unit_id,
                IssuedDocument.work_order_id == order_id,
            )
            .order_by(IssuedDocument.issued_at.desc())
        )
    )
