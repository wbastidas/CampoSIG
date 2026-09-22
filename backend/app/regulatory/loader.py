"""Load regulatory parameters from a seed file (SRS 1.4, ADR-007).

The loader is where "the value is not verified" stops being a comment and becomes behaviour.
A seed entry carries ``verified: false`` until somebody has opened the official text, and the
loader refuses to mark anything verified on its own: verification is an act by a person, and
``--verified-by`` is that person putting their name on it.

Importing twice is safe. An entry with the same code and start date updates that row; a new
start date opens a new period and closes the previous one, so the history that makes an old
approval explicable survives every import.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.regulatory.models import RegulatoryParameter
from app.regulatory.service import set_parameter


class SeedError(Exception):
    """Raised when a seed file cannot be trusted enough to load."""


def default_seed_path() -> Path:
    return Path(__file__).resolve().parents[3] / "seeds" / "regulatory-ec.yaml"


def load_seed(path: str | Path | None = None) -> dict[str, Any]:
    location = Path(path) if path else default_seed_path()
    data = yaml.safe_load(location.read_text(encoding="utf-8"))
    problems = validate_seed(data)
    if problems:
        raise SeedError("; ".join(problems))
    return dict(data)


def validate_seed(data: Any) -> list[str]:
    """Everything wrong with a seed file, in readable Spanish."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["el archivo de parámetros no es un mapa"]
    entries = data.get("parameters")
    if not isinstance(entries, list) or not entries:
        return ["el archivo no declara 'parameters'"]

    seen: set[tuple[str, Any]] = set()
    for index, entry in enumerate(entries):
        where = f"parámetro #{index + 1}"
        if not isinstance(entry, dict):
            problems.append(f"{where}: no es un mapa")
            continue
        code = entry.get("code")
        if not code:
            problems.append(f"{where}: sin 'code'")
            continue
        where = f"'{code}'"
        if "value" not in entry:
            problems.append(f"{where}: sin 'value'")
        if not entry.get("norm_ref"):
            # A limit with no norm behind it cannot be cited, and an observation that cannot
            # cite its source is an opinion (SRS 10.4).
            problems.append(f"{where}: sin 'norm_ref'; un límite sin norma no se puede citar")
        effective_from = entry.get("effective_from")
        if not isinstance(effective_from, date):
            problems.append(f"{where}: 'effective_from' ausente o no es una fecha")
        key = (str(code), effective_from)
        if key in seen:
            problems.append(f"{where}: repetido con la misma fecha de vigencia")
        seen.add(key)
    return problems


def apply_seed(
    session: Session,
    data: dict[str, Any] | None = None,
    *,
    path: str | Path | None = None,
    verified_by: str | None = None,
    only_verified: bool = False,
) -> list[RegulatoryParameter]:
    """Write a seed file's parameters into the database.

    :param verified_by: the person who confirmed these values against the official text. Only
        entries the file itself marks ``verified: true`` are recorded as verified, even when
        this is given — otherwise one careless flag would certify seven numbers nobody read.
    :param only_verified: skip unverified entries entirely. What a production install uses.
    """
    seed = data if data is not None else load_seed(path)
    written: list[RegulatoryParameter] = []

    for entry in seed["parameters"]:
        file_verified = bool(entry.get("verified"))
        if only_verified and not file_verified:
            continue
        written.append(
            set_parameter(
                session,
                code=str(entry["code"]),
                value=entry["value"],
                unit=entry.get("unit"),
                description=entry.get("description"),
                norm_ref=str(entry["norm_ref"]),
                article_ref=entry.get("article_ref"),
                source_url=entry.get("source_url"),
                effective_from=entry["effective_from"],
                effective_to=entry.get("effective_to"),
                # The file decides whether a value counts as verified; the caller only
                # supplies who did it.
                verified_by=verified_by if file_verified else None,
                strict=bool(entry.get("strict")),
            )
        )
    return written


def unverified_codes(session: Session) -> list[str]:
    """Codes in force whose value nobody has checked against the official text.

    What the admin screen shows, and what a deployment checklist has to be empty of.
    """
    from sqlalchemy import select

    rows = session.scalars(
        select(RegulatoryParameter).where(RegulatoryParameter.effective_to.is_(None))
    )
    return sorted(row.code for row in rows if not row.is_verified)
