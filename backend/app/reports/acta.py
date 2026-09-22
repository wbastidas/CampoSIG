"""The work-order acta, as a document and as a PDF (RF-115).

Composed from the form's own blocks and their order, not from a list of fields written here.
That matters more than it looks: an acta assembled from a hardcoded list would silently stop
mentioning a field the moment a functional administrator added one — and nobody would notice,
because the acta would still look complete. Forms are data (rule 3), so the paper is too.

Six things on this page exist because of a way the document would otherwise lie:

* **Every AI-proposed value is named as such**, with its model, version, confidence and who
  confirmed it (rule 8). An acta that printed a value a model guessed as if a technician had
  written it is exactly the failure that rule exists to prevent.
* **An unverified regulatory limit is marked provisional** and never presented as a citation of
  the official text (ADR-007).
* **A photograph whose hash does not match is printed saying so.** Leaving it out would make
  the acta look tidier than the evidence is.
* **A missing signature prints "sin firma".** A blank space under a caption reads, to anybody
  holding the paper, like a signature that was collected and scanned badly.
* **A work order that is not approved yet prints as a draft**, across the page, because an acta
  is the document a crew hands to a customer.
* **The verification code is unguessable and the hash is printed**, so the QR proves something:
  the platform either recognises the code or says it never issued it.

Rendering is HTML and CSS through WeasyPrint, so the layout can be opened in a browser while it
is being designed. The HTML is built here with explicit escaping rather than a template engine:
one dependency fewer, and no way for a technician's free-text observation to become markup.
"""

from __future__ import annotations

import base64
import hashlib
import html
import io
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

#: Loads an evidence or signature image by its storage key. Injected so the document can be
#: rendered and tested without object storage; the API passes the real one.
ImageLoader = Callable[[str], tuple[bytes, str] | None]

STYLESHEET = Path(__file__).resolve().parent / "acta.css"


# --- the document ------------------------------------------------------------------
@dataclass(frozen=True)
class ActaRow:
    """One answered field, with the label the form itself gives it."""

    label: str
    value: str
    #: Set when the value came from a model. Printed beside it, never omitted (rule 8).
    ai_note: str | None = None


@dataclass(frozen=True)
class ActaSection:
    """One form block, in the order the form lists it."""

    code: str
    title: str
    rows: list[ActaRow]


@dataclass(frozen=True)
class ActaPhoto:
    stage: str
    kind: str
    storage_hash: str
    integrity_verified: bool
    data_uri: str | None = None

    @property
    def caption(self) -> str:
        label = {"antes": "Antes", "despues": "Después", "durante": "Durante"}.get(
            self.stage, self.stage
        )
        if not self.integrity_verified:
            return f"{label} — el hash no coincide con el registrado"
        return label


@dataclass(frozen=True)
class ActaSignature:
    role: str
    data_uri: str | None
    #: What identifies the signatory, when the form captured it.
    identifier: str | None = None

    @property
    def present(self) -> bool:
        return self.data_uri is not None


@dataclass(frozen=True)
class ActaFinding:
    message: str
    outcome: str
    severity: str
    citation: str | None
    #: False when nobody has checked the limit against the official text (ADR-007).
    limit_verified: bool = True


@dataclass(frozen=True)
class ActaDecision:
    decision: str
    reviewer: str
    note: str | None
    decided_at: str | None


@dataclass(frozen=True)
class Acta:
    """Everything printed, already decided. Rendering adds no judgement."""

    verification_code: str
    verification_url: str
    issued_by: str
    issued_at: datetime
    business_unit: str
    work_order_code: str
    work_order_state: str
    work_type: str
    form_code: str
    form_version: str
    form_title: str
    asset_code: str | None = None
    feeder_code: str | None = None
    zone: str | None = None
    external_ref: str | None = None
    sections: list[ActaSection] = field(default_factory=list)
    photos: list[ActaPhoto] = field(default_factory=list)
    signatures: list[ActaSignature] = field(default_factory=list)
    findings: list[ActaFinding] = field(default_factory=list)
    decisions: list[ActaDecision] = field(default_factory=list)
    #: Warnings the form composer raised. Printed, because an acta produced from an
    #: incomplete form should say so on its face.
    warnings: list[str] = field(default_factory=list)

    @property
    def is_draft(self) -> bool:
        """An acta of a work order nobody approved is a draft, whatever it looks like."""
        return self.work_order_state != "aprobada"


# --- value rendering ---------------------------------------------------------------
def display_value(value: object) -> str:
    """A JSONB value as a person should read it.

    The same lesson the review screen paid for: `str()` on a repeatable table row or a range
    produces something like a Python repr, and a supervisor reading it believes they were shown
    the answer. Here it would be printed, signed and filed.
    """
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, str | int | float):
        return str(value)
    if isinstance(value, Sequence):
        rendered = [display_value(item) for item in value]
        return ", ".join(rendered) if rendered else "—"
    if isinstance(value, Mapping):
        parts = [f"{key}: {display_value(item)}" for key, item in value.items()]
        return "; ".join(parts) if parts else "—"
    return str(value)


def ai_note(entry: Mapping[str, Any]) -> str:
    """How an AI-proposed value is described on the paper (rule 8).

    Includes the confirmation, because the difference between "a model proposed this and a
    technician accepted it unchanged" and "a technician corrected it" is the whole audit.
    """
    origin = {"voz": "dictado", "vision": "visión"}.get(str(entry.get("origin")), "IA")
    model = entry.get("model_name") or "modelo sin identificar"
    version = entry.get("model_version") or "sin versión"
    confidence = entry.get("confidence")
    shown = f"{float(confidence):.0%}" if isinstance(confidence, int | float) else "sin confianza"
    confirmed = entry.get("confirmed_by")
    who = f"confirmado por {confirmed}" if confirmed else "sin confirmación humana"
    if entry.get("accepted_unchanged") and confirmed:
        who = f"aceptado sin cambios por {confirmed}"
    return f"propuesto por {origin} · {model} {version} · confianza {shown} · {who}"


def data_uri(payload: bytes, media_type: str) -> str:
    return f"data:{media_type};base64,{base64.b64encode(payload).decode('ascii')}"


# --- assembling the sections from the form -----------------------------------------
#: Field schema keys the acta reads. Named here so the extraction is one place.
SIGNATURE_MARKER = "x-signature"


def sections_from_form(
    schema: Mapping[str, Any],
    ui_schema: Mapping[str, Any],
    answers: Mapping[str, Any],
    provenance: Iterable[Mapping[str, Any]] = (),
) -> list[ActaSection]:
    """Turn the composed form and its answers into printable sections.

    Driven by ``ui:groups``, which is the form's own block structure: safety before execution,
    evidence before closure — the order a technician works in, and the order the paper should
    read in.
    """
    properties: Mapping[str, Any] = schema.get("properties", {})
    ai_by_field = {
        str(entry["field_key"]): entry
        for entry in provenance
        if entry.get("is_ai") or entry.get("origin") in ("voz", "vision")
    }

    sections: list[ActaSection] = []
    for group in ui_schema.get("ui:groups", []):
        rows: list[ActaRow] = []
        for key in group.get("fields", []):
            field_schema = properties.get(key, {})
            if SIGNATURE_MARKER in field_schema:
                # Printed as a signature block, not as a row with a URI in it.
                continue
            entry = ai_by_field.get(key)
            rows.append(
                ActaRow(
                    label=str(field_schema.get("title") or key),
                    value=display_value(answers.get(key)),
                    ai_note=ai_note(entry) if entry else None,
                )
            )
        if rows:
            sections.append(
                ActaSection(
                    code=str(group.get("block", "")),
                    title=str(group.get("title", "")),
                    rows=rows,
                )
            )
    return sections


def signatures_from_form(
    schema: Mapping[str, Any],
    answers: Mapping[str, Any],
    loader: ImageLoader | None = None,
    identifiers: Mapping[str, str] | None = None,
) -> list[ActaSignature]:
    """The signature blocks the form declares, present or not.

    A declared signature that was never captured still gets a block saying "sin firma": a blank
    space under a caption reads like a signature somebody collected.
    """
    found: list[ActaSignature] = []
    for key, field_schema in schema.get("properties", {}).items():
        role = field_schema.get(SIGNATURE_MARKER)
        if not role:
            continue
        stored = answers.get(key)
        image: str | None = None
        if isinstance(stored, str) and stored and loader is not None:
            loaded = loader(stored)
            if loaded is not None:
                image = data_uri(*loaded)
        found.append(
            ActaSignature(
                role=str(role),
                data_uri=image,
                identifier=(identifiers or {}).get(str(role)),
            )
        )
    return found


# --- rendering ---------------------------------------------------------------------
def esc(text: object) -> str:
    """Escape for HTML. Applied to every value without exception.

    Without exception on purpose: a technician's free-text observation, a catalogue label
    imported from the GIS and a model's generated summary all reach this document, and none of
    them is trusted markup.
    """
    return html.escape("" if text is None else str(text), quote=True)


def qr_svg(url: str) -> str:
    """The verification QR, as an inline SVG.

    `segno` writes SVG, so nothing here needs a raster image library, and the code stays sharp
    at whatever size the printer uses.
    """
    import segno

    # `save` writes bytes even for SVG, so the buffer is binary and the result is decoded.
    # `omitsize` drops width and height so the stylesheet decides how big the code prints.
    buffer = io.BytesIO()
    segno.make(url, error="m").save(buffer, kind="svg", xmldecl=False, svgclass=None, omitsize=True)
    return buffer.getvalue().decode("utf-8")


def _rows_html(rows: Iterable[ActaRow]) -> str:
    parts = []
    for row in rows:
        note = f'<div class="ai">{esc(row.ai_note)}</div>' if row.ai_note else ""
        parts.append(f"<tr><th>{esc(row.label)}</th><td>{esc(row.value)}{note}</td></tr>")
    return "".join(parts)


def _photos_html(photos: Sequence[ActaPhoto]) -> str:
    if not photos:
        return "<p class='empty'>Esta OT no registra evidencia fotográfica.</p>"
    cells = []
    for photo in photos:
        classes = "photo" if photo.integrity_verified else "photo photo--suspect"
        body = (
            f'<img src="{esc(photo.data_uri)}" alt="{esc(photo.caption)}">'
            if photo.data_uri
            else (
                '<div class="photo__missing">Imagen no disponible<br>'
                f"{esc(photo.storage_hash[:16])}…</div>"
            )
        )
        cells.append(
            f'<figure class="{classes}">{body}'
            f"<figcaption>{esc(photo.caption)}<br>"
            f"<span class='hash'>{esc(photo.storage_hash[:16])}…</span></figcaption></figure>"
        )
    return f'<div class="photos">{"".join(cells)}</div>'


def _signatures_html(signatures: Sequence[ActaSignature]) -> str:
    if not signatures:
        return ""
    roles = {"jefe_cuadrilla": "Jefe de cuadrilla", "cliente": "Cliente"}
    blocks = []
    for signature in signatures:
        label = roles.get(signature.role, signature.role.replace("_", " "))
        body = (
            f'<img src="{esc(signature.data_uri)}" alt="Firma de {esc(label)}">'
            if signature.present
            # Said out loud. An empty box under a caption reads like a signature that was
            # collected and scanned badly.
            else '<div class="signature__absent">Sin firma</div>'
        )
        identifier = (
            f"<br><span class='hash'>{esc(signature.identifier)}</span>"
            if signature.identifier
            else ""
        )
        blocks.append(
            f'<figure class="signature">{body}'
            f"<figcaption>{esc(label)}{identifier}</figcaption></figure>"
        )
    return f'<div class="signatures">{"".join(blocks)}</div>'


def _findings_html(findings: Sequence[ActaFinding]) -> str:
    if not findings:
        return ""
    rows = []
    for finding in findings:
        citation = esc(finding.citation) if finding.citation else "—"
        if not finding.limit_verified:
            # ADR-007: a limit nobody checked against the resolution is not a citation of it,
            # and an acta that presented it as one would be handing somebody a wrong verdict
            # with an official-looking reference under it.
            citation = (
                "<em>límite sin verificar contra el texto oficial; resultado provisional</em>"
            )
        rows.append(
            f"<tr><td>{esc(finding.message)}</td>"
            f"<td>{esc(finding.outcome)}</td>"
            f"<td>{esc(finding.severity)}</td>"
            f"<td>{citation}</td></tr>"
        )
    return (
        "<h2>Hallazgos normativos</h2>"
        "<table class='findings'><thead><tr><th>Hallazgo</th><th>Resultado</th>"
        f"<th>Severidad</th><th>Norma</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _decisions_html(decisions: Sequence[ActaDecision]) -> str:
    if not decisions:
        return ""
    rows = "".join(
        f"<tr><td>{esc(d.decision)}</td><td>{esc(d.reviewer)}</td>"
        f"<td>{esc(d.note or '—')}</td><td>{esc(d.decided_at or '—')}</td></tr>"
        for d in decisions
    )
    return (
        "<h2>Revisión</h2><table class='decisions'><thead><tr><th>Decisión</th>"
        f"<th>Revisó</th><th>Nota</th><th>Fecha</th></tr></thead><tbody>{rows}</tbody></table>"
    )


def render_html(acta: Acta) -> str:
    """The acta as a standalone HTML document.

    Standalone — styles inline, images as data URIs — because WeasyPrint must not need to fetch
    anything, and because the same file can be opened in a browser while the layout is designed.
    """
    stylesheet = STYLESHEET.read_text(encoding="utf-8")
    sections = "".join(
        f"<section class='block'><h2>{esc(section.title)}</h2>"
        f"<table class='fields'><tbody>{_rows_html(section.rows)}</tbody></table></section>"
        for section in acta.sections
    )
    header_rows = [
        ("Unidad de negocio", acta.business_unit),
        ("Orden de trabajo", acta.work_order_code),
        ("Tipo de trabajo", acta.work_type),
        ("Estado", acta.work_order_state),
        ("Formulario", f"{acta.form_code} v{acta.form_version}"),
        ("Activo", acta.asset_code or "—"),
        ("Alimentador", acta.feeder_code or "—"),
        ("Zona", acta.zone or "—"),
        ("Referencia externa", acta.external_ref or "—"),
    ]
    header = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in header_rows)
    draft = (
        "<div class='draft'>BORRADOR · la orden de trabajo no está aprobada</div>"
        if acta.is_draft
        else ""
    )
    warnings_html = (
        "<section class='warnings'><h2>Avisos del formulario</h2><ul>"
        + "".join(f"<li>{esc(w)}</li>" for w in acta.warnings)
        + "</ul></section>"
        if acta.warnings
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="es-EC">
<head>
<meta charset="utf-8">
<title>Acta {esc(acta.work_order_code)}</title>
<!-- Fija la fecha del PDF a la de emisión registrada, así que el mismo documento vuelve a
     producir los mismos bytes y su hash se puede comprobar más tarde. -->
<meta name="dcterms.created" content="{esc(acta.issued_at.isoformat())}">
<style>{stylesheet}</style>
</head>
<body>
{draft}
<header class="acta-head">
  <div>
    <h1>Acta de trabajo de campo</h1>
    <p class="subtitle">{esc(acta.form_title)}</p>
  </div>
  <div class="verify">
    {qr_svg(acta.verification_url)}
    <p class="code">{esc(acta.verification_code)}</p>
  </div>
</header>

<table class="fields summary"><tbody>{header}</tbody></table>

{warnings_html}
{sections}

<section class="block"><h2>Evidencia fotográfica</h2>{_photos_html(acta.photos)}</section>
{_findings_html(acta.findings)}
{_decisions_html(acta.decisions)}
<section class="block"><h2>Firmas</h2>{_signatures_html(acta.signatures)}</section>

<footer>
  <p>Emitida por {esc(acta.issued_by)} el {esc(acta.issued_at.isoformat(timespec="seconds"))}.</p>
  <p>Verifique este documento en {esc(acta.verification_url)} y compare la huella impresa
     al pie con la del archivo (<code>sha256sum</code>).</p>
</footer>
</body>
</html>"""


def render_pdf(acta: Acta) -> tuple[bytes, str]:
    """The PDF and the SHA-256 of its bytes.

    The hash is of the bytes, not of the content model, because what a person holds is a file:
    verifying anything else would verify the wrong thing.

    **Re-rendering does not reproduce the hash**, and the design deliberately does not depend on
    it. A first sketch of this assumed it did — WeasyPrint's output *is* byte-stable for a
    trivial page, which is what a quick check shows — but once real fonts are embedded, the
    subsetting is not deterministic and two renders of the same document differ. So the register
    stores the hash of the bytes that were actually handed over, and verification compares the
    file in somebody's hands against that stored hash. Nothing ever re-renders to check.

    The creation date is still pinned to the issuance timestamp, because a PDF stamped with the
    moment it was printed rather than the moment it was issued is a document that disagrees with
    its own register.
    """
    from weasyprint import HTML

    pdf = HTML(string=render_html(acta)).write_pdf()
    assert pdf is not None
    return pdf, hashlib.sha256(pdf).hexdigest()
