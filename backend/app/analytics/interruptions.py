"""The interruption base, exportable for FMIK and TTIK (RF-132).

What this module does **not** do is the point of it: it does not compute FMIK or TTIK. Those two
indices divide by the unit's installed kVA, which lives in the corporate systems and not here, and a
platform that published an index against a denominator it had guessed would be publishing a number
the utility then has to defend before the regulator. So the export carries the base and the two
numerators — the kVA affected and the kVA-hours — and says what is missing.

Two other rules shape it:

**The threshold is not here.** Whether an interruption counts towards the indices is decided by the
deterministic rule over `regulatory_parameter` (ADR-007), the same one the review screen shows. This
module asks it and carries the answer with its citation; it never compares a duration to a number of
its own.

**The format is a file.** «Formato configurable» in the requirement means the column set, their
headers, their order and the separator live in `seeds/export-formats/`, because the regulation
renames and reorders them every few years and that should be a file to add rather than code to
change.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.regulatory import rules as compliance
from app.responses.models import FormResponse
from app.review.service import compliance_findings
from app.workorders.models import WorkOrder

#: Where the layouts live. Data, not code.
FORMATS_DIR = Path(__file__).resolve().parents[3] / "seeds" / "export-formats"

#: The form that registers an interruption (SRS 4.4).
INTERRUPTION_FORM = "F-OP-03"

#: The rule that classifies an interruption as computable or not.
COMPUTABLE_RULE = "interrupcion_no_computable"

#: Answer keys read here. Canonical (ADR-004).
KEY_STARTED = "started_at_interruption"
KEY_RESTORED = "restored_at_interruption"
KEY_SECONDS = "interruption_seconds"
KEY_KVA = "kva_affected"
KEY_PARTIALS = "partial_restorations"


class UnknownFormatError(Exception):
    """Raised when a caller asks for a layout that is not on disk."""


@dataclass(frozen=True)
class Column:
    header: str
    source: str
    #: How the value is written: text, number, datetime or boolean.
    as_: str = "text"


@dataclass(frozen=True)
class ExportFormat:
    code: str
    title: str
    norm_ref: str | None
    delimiter: str
    decimal: str
    byte_order_mark: bool
    columns: tuple[Column, ...]


def available_formats() -> list[str]:
    """The codes a caller may ask for.

    The declared code and not the file name: what the API lists has to be what the API accepts, and
    a listing of file stems would hand the screen a value the endpoint then rejects.
    """
    if not FORMATS_DIR.is_dir():
        return []
    codes: list[str] = []
    for path in sorted(FORMATS_DIR.glob("*.yaml")):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        codes.append(str((loaded.get("format") or {}).get("code") or path.stem))
    return sorted(codes)


def load_format(code: str) -> ExportFormat:
    """One layout, by file name or by the code it declares.

    :raises UnknownFormatError: when no file matches. Named rather than falling back to a default:
        an export that silently used another layout would produce a file the regulator rejects for
        reasons nobody can trace.
    """
    for path in sorted(FORMATS_DIR.glob("*.yaml")):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        declared = loaded.get("format", {})
        if code not in (path.stem, declared.get("code")):
            continue
        return ExportFormat(
            code=str(declared.get("code") or path.stem),
            title=str(declared.get("title") or path.stem),
            norm_ref=declared.get("norm_ref"),
            delimiter=str(declared.get("delimiter") or ";"),
            decimal=str(declared.get("decimal") or ","),
            byte_order_mark=bool(declared.get("byte_order_mark", True)),
            columns=tuple(
                Column(
                    header=str(entry["header"]),
                    source=str(entry["source"]),
                    as_=str(entry.get("as") or "text"),
                )
                for entry in loaded.get("columns") or []
            ),
        )
    raise UnknownFormatError(
        f"no existe el formato de exportación '{code}'; disponibles: "
        f"{', '.join(available_formats()) or 'ninguno'}"
    )


@dataclass
class Interruption:
    """One registered interruption, with what the rule said about it."""

    work_order_id: uuid.UUID
    order_code: str | None
    answers: dict[str, Any]
    #: None when the rule could not classify it: no duration, or no threshold loaded.
    computable: bool | None = None
    threshold_seconds: float | None = None
    threshold_verified: bool = False
    threshold_norm: str | None = None

    @property
    def seconds(self) -> float | None:
        value = self.answers.get(KEY_SECONDS)
        return float(value) if isinstance(value, int | float) else None

    @property
    def duration_hours(self) -> float | None:
        seconds = self.seconds
        return seconds / 3600 if seconds is not None else None

    @property
    def kva(self) -> float | None:
        value = self.answers.get(KEY_KVA)
        return float(value) if isinstance(value, int | float) else None

    @property
    def kva_hours(self) -> float | None:
        """The TTIK numerator's contribution: kVA out of service times hours out of service."""
        kva = self.kva
        hours = self.duration_hours
        return kva * hours if kva is not None and hours is not None else None

    @property
    def partial_restorations(self) -> int:
        value = self.answers.get(KEY_PARTIALS)
        return len(value) if isinstance(value, list) else 0

    def computed(self, name: str) -> Any:
        return {
            "duration_hours": self.duration_hours,
            "kva_hours": self.kva_hours,
            "partial_restorations": self.partial_restorations,
            "computable": self.computable,
            "threshold_seconds": self.threshold_seconds,
            "threshold_verified": self.threshold_verified,
            "threshold_norm": self.threshold_norm,
        }.get(name)


@dataclass
class Base:
    """The interruption base of a period, with the numerators and what is missing."""

    since: datetime
    until: datetime
    rows: list[Interruption] = field(default_factory=list)
    #: Interruptions the rule could not classify. Counted, never assumed computable: assuming would
    #: inflate the indices, and assuming the opposite would hide interruptions that happened.
    unclassified: int = 0

    @property
    def computable(self) -> list[Interruption]:
        return [row for row in self.rows if row.computable is True]

    @property
    def kva_affected(self) -> float:
        """FMIK's numerator: the kVA out of service, summed over computable interruptions."""
        return sum(row.kva or 0.0 for row in self.computable)

    @property
    def kva_hours(self) -> float:
        """TTIK's numerator: kVA-hours out of service over computable interruptions."""
        return sum(row.kva_hours or 0.0 for row in self.computable)

    @property
    def missing_kva(self) -> int:
        """Computable interruptions with no kVA recorded. Each one makes both numerators too low."""
        return sum(1 for row in self.computable if row.kva is None)

    def as_dict(self) -> dict[str, Any]:
        return {
            "since": self.since.isoformat(),
            "until": self.until.isoformat(),
            "interruptions": len(self.rows),
            "computable": len(self.computable),
            "not_computable": sum(1 for row in self.rows if row.computable is False),
            "unclassified": self.unclassified,
            "numerators": {
                "kva_affected": self.kva_affected,
                "kva_hours": self.kva_hours,
                "missing_kva": self.missing_kva,
                # Said in the payload, because a number labelled FMIK that is not FMIK is the one
                # thing this module must never produce.
                "note": (
                    "numeradores de FMIK y TTIK. La plataforma no calcula los índices: el "
                    "denominador es el kVA instalado de la unidad, que vive en los sistemas "
                    "corporativos y no aquí, y publicar un índice contra un denominador supuesto "
                    "sería publicar un número que después hay que defender ante el regulador"
                ),
            },
            "formats": available_formats(),
        }


def collect(session: Session, unit_id: uuid.UUID, *, since: datetime, until: datetime) -> Base:
    """The period's interruptions, classified by the rule in force."""
    base = Base(since=since, until=until)
    rows = session.execute(
        select(WorkOrder, FormResponse)
        .join(FormResponse, FormResponse.work_order_id == WorkOrder.id)
        .where(
            WorkOrder.business_unit_id == unit_id,
            FormResponse.form_code == INTERRUPTION_FORM,
            FormResponse.submitted_at.is_not(None),
            FormResponse.submitted_at >= since,
            FormResponse.submitted_at <= until,
        )
        .order_by(FormResponse.submitted_at)
    )
    for order, response in rows:
        entry = Interruption(
            work_order_id=order.id,
            order_code=order.code,
            answers=dict(response.answers or {}),
        )
        finding = next(
            (
                item
                for item in compliance_findings(session, order, response)
                if item.rule == COMPUTABLE_RULE
            ),
            None,
        )
        if finding is not None and finding.outcome is compliance.Outcome.COMPLIES:
            # The rule's message carries the verdict; the flag is derived from the same comparison
            # so the export and the review screen cannot disagree.
            entry.threshold_seconds = (
                float(finding.limit) if isinstance(finding.limit, int | float) else None
            )
            entry.threshold_verified = finding.limit_verified
            entry.threshold_norm = finding.norm_ref
            seconds = entry.seconds
            entry.computable = (
                seconds >= entry.threshold_seconds
                if seconds is not None and entry.threshold_seconds is not None
                else None
            )
        if entry.computable is None:
            base.unclassified += 1
        base.rows.append(entry)
    return base


# --- writing the file --------------------------------------------------------------------


def render(base: Base, layout: ExportFormat) -> str:
    """The base as text, in the layout's own format."""
    lines = [layout.delimiter.join(column.header for column in layout.columns)]
    for row in base.rows:
        lines.append(
            layout.delimiter.join(
                _write(_value_of(row, column.source), column.as_, layout)
                for column in layout.columns
            )
        )
    body = "\r\n".join(lines) + "\r\n"
    return ("﻿" + body) if layout.byte_order_mark else body


def _value_of(row: Interruption, source: str) -> Any:
    if source.startswith("computed."):
        return row.computed(source.removeprefix("computed."))
    if source == "order.code":
        return row.order_code or str(row.work_order_id)
    if source.startswith("order."):
        return None
    return row.answers.get(source)


def _write(value: Any, kind: str, layout: ExportFormat) -> str:
    if value is None:
        return ""
    if kind == "boolean":
        return "sí" if value else "no"
    if kind == "number":
        if not isinstance(value, int | float):
            return ""
        return f"{float(value):.2f}".replace(".", layout.decimal)
    if kind == "datetime":
        text = str(value)
        # ISO with the T replaced: what a spreadsheet parses as a date-time in a Spanish locale.
        return text.replace("T", " ")[:19]
    text = str(value)
    # The delimiter is taken out rather than quoted: a quoting bug that shifts every column of one
    # row is harder to notice than a value missing a semicolon.
    return text.replace(layout.delimiter, ",").replace("\r", " ").replace("\n", " ").strip()
