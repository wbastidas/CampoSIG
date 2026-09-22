"""The acta and its verification page (RF-115).

Two routes with opposite audiences, which is the whole design:

* **Issuing** is corporate and scoped to a business unit: a supervisor or inspector prints the
  acta of a work order in their own unit.
* **Verifying** is public, because the person scanning the QR is the customer whose light was
  repaired, and they have no corporate account. So it has to be open, and it has to disclose
  almost nothing: whether the platform issued that document, for which work-order code, when,
  and the hash of the file — enough to tell a genuine acta from a photocopied fiction, and
  nothing about the customer, the address or the answers.

A code the platform never issued gets "no consta". That sentence is the reason the QR is worth
printing.
"""

from __future__ import annotations

import html
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import PrincipalDep, require_roles, unit_scope
from app.auth.principal import Role
from app.infra.database import get_session
from app.org.models import BusinessUnit
from app.org.service import UnknownBusinessUnitError, get_business_unit_by_code
from app.reports.service import documents_for_order, find_by_code, issue_acta, order_label
from app.settings import get_settings
from app.workorders.models import WorkOrder

#: Corporate half: unit-scoped at the door, like every other reviewing route.
router = APIRouter(prefix="/api/v1/reports", tags=["reports"], dependencies=[Depends(unit_scope)])

#: Public half, and deliberately not under /api: it is a page a person opens, not an API a
#: client calls. Listed as an exception in the route-authentication guard, with its reason.
public_router = APIRouter(tags=["reports"])

SessionDep = Annotated[Session, Depends(get_session)]

#: Path the QR encodes, under the platform's public base URL.
VERIFY_PATH = "/verificar"


def _unit(session: Session, code: str) -> BusinessUnit:
    try:
        return get_business_unit_by_code(session, code)
    except UnknownBusinessUnitError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _order(session: Session, unit_id: uuid.UUID, order_id: uuid.UUID) -> WorkOrder:
    order = session.get(WorkOrder, order_id)
    if order is None or order.business_unit_id != unit_id:
        # 404 for another unit's work order rather than 403: probing ids should teach nothing
        # about what exists elsewhere (ADR-009).
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"la OT '{order_id}' no existe")
    return order


@router.post(
    "/units/{unit_code}/work-orders/{order_id}/acta",
    summary="Emitir el acta en PDF de una OT y registrarla para su verificación",
    dependencies=[Depends(require_roles(Role.SUPERVISOR, Role.INSPECTOR, Role.CREW_LEADER))],
)
def issue(
    unit_code: str,
    order_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> Response:
    """Render, register and return the PDF.

    Who issued it comes from the token, never from the request: a document whose author the
    caller could type is a document nobody signed (ADR-013).
    """
    unit = _unit(session, unit_code)
    order = _order(session, unit.id, order_id)
    settings = get_settings()

    record, pdf = issue_acta(
        session,
        unit,
        order,
        issued_by=principal.subject,
        verification_base_url=f"{settings.public_base_url.rstrip('/')}{VERIFY_PATH}",
        # No image loader yet: the evidence lives in object storage and the acta prints each
        # missing photograph with its hash rather than pretending it has it. Wiring the loader
        # is a change here, not in the document.
        image_loader=None,
    )
    session.commit()

    filename = f"acta-{order.code or order.id}-{record.verification_code}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # So a caller can check the hash without parsing the PDF.
            "X-SIGEC-Document-Hash": record.content_hash,
            "X-SIGEC-Verification-Code": record.verification_code,
        },
    )


@router.get(
    "/units/{unit_code}/work-orders/{order_id}/documents",
    summary="Actas emitidas de una OT, de la más reciente a la más antigua",
)
def issued(unit_code: str, order_id: uuid.UUID, session: SessionDep) -> list[dict[str, Any]]:
    """The trail of reprints. Two papers in the world are two rows here."""
    unit = _unit(session, unit_code)
    order = _order(session, unit.id, order_id)
    return [
        {
            "document_id": str(record.id),
            "kind": record.kind,
            "verification_code": record.verification_code,
            "content_hash": record.content_hash,
            "byte_size": record.byte_size,
            "state_at_issue": record.state_at_issue,
            "form_code": record.form_code,
            "form_version": record.form_version,
            "issued_by": record.issued_by,
            "issued_at": record.issued_at.isoformat(),
        }
        for record in documents_for_order(session, unit.id, order.id)
    ]


# --- the public page ---------------------------------------------------------------
def _page(title: str, body: str, *, found: bool) -> Response:
    """A self-contained page, in Ecuadorian Spanish, readable on a phone.

    Self-contained because whoever scans this is standing in the street on a bad connection,
    and a verification page that needs three more requests is one that fails when it matters.
    """
    status_code = status.HTTP_200_OK if found else status.HTTP_404_NOT_FOUND
    return Response(
        status_code=status_code,
        media_type="text/html; charset=utf-8",
        content=f"""<!DOCTYPE html>
<html lang="es-EC"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
 body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1.5rem;
         color: #1c1917; background: #fff; }}
 main {{ max-width: 34rem; margin: 0 auto; }}
 h1 {{ font-size: 1.3rem; }}
 dl {{ display: grid; grid-template-columns: auto 1fr; gap: .3rem 1rem; }}
 dt {{ color: #57534e; }}
 code {{ word-break: break-all; font-size: .85rem; }}
 .no {{ border: 2px solid #7f1d1d; background: #fef2f2; color: #7f1d1d;
        padding: .75rem; border-radius: 4px; }}
</style></head>
<body><main><h1>{html.escape(title)}</h1>{body}</main></body></html>""",
    )


@public_router.get(
    f"{VERIFY_PATH}/{{code}}",
    summary="Verificar un acta emitida por la plataforma (página pública)",
    response_class=Response,
)
def verify(code: str, session: SessionDep) -> Response:
    """Confirm the platform issued this document, or say it did not.

    Everything shown comes from the register, never from the URL. Echoing the code back as if it
    were a finding is what a verification page must not do — the paper already has the code, and
    repeating it proves nothing.
    """
    record = find_by_code(session, code)
    if record is None:
        return _page(
            "Este documento no consta",
            "<p class='no'>La plataforma no emitió ningún acta con este código de "
            "verificación.</p>"
            "<p>Si le entregaron un documento con este código, no proviene de esta "
            "plataforma o fue alterado. Repórtelo a la distribuidora.</p>",
            found=False,
        )

    unit = session.get(BusinessUnit, record.business_unit_id)
    order = session.get(WorkOrder, record.work_order_id)
    draft = (
        "<p class='no'>Este acta se imprimió cuando la orden de trabajo todavía no estaba "
        "aprobada, así que es un borrador.</p>"
        if record.state_at_issue != "aprobada"
        else ""
    )
    rows = [
        # The same label the paper prints, from the same function: a page that showed a dash
        # where the acta shows an id would fail to verify the work orders that have no
        # human-readable code, which here is most of them.
        ("Orden de trabajo", order_label(order) if order else "—"),
        ("Unidad de negocio", (unit.name if unit else "—")),
        ("Estado al emitirse", record.state_at_issue),
        ("Formulario", f"{record.form_code or '—'} v{record.form_version or '—'}"),
        ("Emitida", record.issued_at.isoformat(timespec="minutes")),
        ("Tamaño", f"{record.byte_size} bytes"),
    ]
    detail = "".join(
        f"<dt>{html.escape(label)}</dt><dd>{html.escape(str(value))}</dd>" for label, value in rows
    )
    return _page(
        "Acta verificada",
        f"{draft}<dl>{detail}</dl>"
        "<p>Huella del archivo (SHA-256). Compárela con la del PDF que tiene:</p>"
        f"<p><code>{html.escape(record.content_hash)}</code></p>",
        found=True,
    )
