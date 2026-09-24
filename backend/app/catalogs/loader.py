"""Loading the catalogue seeds (RF-034).

The seeds under `seeds/catalogs/` are the baseline. Three properties the loader keeps:

* **Idempotent.** Re-running updates labels and synonyms and never duplicates a code, because the
  normal way a correction reaches production is «edit the file, load it again».
* **It never retires what the file omits**, unless asked. An incomplete file must not be able to
  empty a catalogue in production — that failure is silent on the server and very loud in the field,
  where a picker suddenly has three values instead of twenty.
* **It validates before it writes.** A file with two entries sharing a code, or a catalogue with no
  code, is refused whole. Half a catalogue is worse than none: the missing half looks like a value
  somebody retired on purpose.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.catalogs import service as catalogs
from app.catalogs.models import Catalog, CatalogEntry, CatalogSource
from app.org.models import BusinessUnit

#: Who a seed load is attributed to when nobody says. Obviously a script rather than a person.
SEED_ACTOR = "carga.semilla"


def seeds_root() -> Path:
    return Path(__file__).resolve().parents[3] / "seeds" / "catalogs"


def load_files(root: Path | None = None) -> list[dict[str, Any]]:
    """Every catalogue document in the seed directory, in file order.

    Multiple documents per file are allowed — the three «why» catalogues share one file because they
    are one idea — so the loader reads streams rather than single documents.
    """
    base = root or seeds_root()
    documents: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.yaml")):
        for document in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if not document:
                continue
            document["_file"] = path.name
            documents.append(document)
    return documents


def validate(documents: list[dict[str, Any]]) -> list[str]:
    """Everything wrong with the seeds, in Spanish, before anything is written."""
    problems: list[str] = []
    seen: dict[str, str] = {}
    for document in documents:
        where = document.get("_file", "?")
        header = document.get("catalog")
        if not isinstance(header, dict) or not header.get("code"):
            problems.append(f"{where}: un documento no trae `catalog.code`")
            continue
        code = str(header["code"])
        if code in seen:
            problems.append(f"{where}: el catálogo «{code}» ya venía en {seen[code]}")
            continue
        seen[code] = where
        if not header.get("title"):
            problems.append(f"{where}: el catálogo «{code}» no trae título")
        source = str(header.get("source", CatalogSource.MANUAL))
        if source not in tuple(CatalogSource):
            problems.append(f"{where}: origen «{source}» desconocido en «{code}»")

        entries = document.get("entries") or []
        if not isinstance(entries, list):
            problems.append(f"{where}: `entries` de «{code}» no es una lista")
            continue
        codes: set[str] = set()
        for position, entry in enumerate(entries):
            if not isinstance(entry, dict) or not entry.get("code"):
                problems.append(f"{where}: la entrada {position} de «{code}» no trae código")
                continue
            entry_code = str(entry["code"])
            if entry_code in codes:
                problems.append(f"{where}: «{code}» repite el valor «{entry_code}»")
            codes.add(entry_code)
            if not entry.get("label"):
                problems.append(f"{where}: «{code}/{entry_code}» no trae etiqueta")
        if not entries and not header.get("note"):
            # An empty catalogue is legitimate — the political division is deliberately empty — but
            # it has to say why, or an operator meets an empty picker with no explanation.
            problems.append(f"{where}: «{code}» viene vacío y sin `note` que explique por qué")
    return problems


def apply_seeds(
    session: Session,
    documents: list[dict[str, Any]] | None = None,
    *,
    root: Path | None = None,
    actor: str = SEED_ACTOR,
    unit: BusinessUnit | None = None,
    retire_missing: bool = False,
) -> dict[str, int]:
    """Write the seeds. Returns catalogue code → how many entries were written.

    :param retire_missing: deactivate values the file no longer carries. Off by default and on
        purpose: an incomplete file must not be able to empty a catalogue in production.
    """
    docs = documents if documents is not None else load_files(root)
    problems = validate(docs)
    if problems:
        raise catalogs.CatalogError("; ".join(problems))

    written: dict[str, int] = {}
    for document in docs:
        header = document["catalog"]
        code = str(header["code"])
        existing = session.query(Catalog).filter(Catalog.code == code).one_or_none()
        if existing is None:
            existing = Catalog(code=code)
            session.add(existing)
        existing.title = str(header["title"])
        existing.source = str(header.get("source", CatalogSource.MANUAL))
        existing.note = header.get("note")
        session.flush()

        entries = document.get("entries") or []
        seen: set[str] = set()
        for position, entry in enumerate(entries):
            seen.add(str(entry["code"]))
            catalogs.upsert_entry(
                session,
                code,
                entry_code=str(entry["code"]),
                label=str(entry["label"]),
                unit=unit,
                synonyms=[str(item) for item in entry.get("synonyms") or []],
                parent_code=entry.get("parent_code"),
                attributes=entry.get("attributes") or {},
                sort_order=int(entry.get("sort_order", position)),
                actor=actor,
                # The seed is allowed to write an integration-owned catalogue: it is how the
                # catalogue comes into existence before the connector's first delivery.
                from_integration=True,
            )
        written[code] = len(entries)

        if retire_missing:
            for row_out in list(
                session.query(CatalogEntry).filter(
                    CatalogEntry.catalog_code == code,
                    CatalogEntry.business_unit_id.is_(None if unit is None else unit.id),
                    CatalogEntry.active.is_(True),
                )
            ):
                if row_out.code not in seen:
                    catalogs.retire_entry(session, code, row_out.code, unit=unit, actor=actor)
    return written


def missing_for_forms(session: Session, refs: set[str], profile_enums: set[str]) -> list[str]:
    """Catalogue references from `forms/` that nothing can serve.

    Three things can serve one: a catalogue here, the unit's synced GIS metadata, or the profile's
    asset-model enums. A reference none of them covers is a picker with no values, which is the
    failure this module was built to remove.
    """
    served = catalogs.known_codes(session) | set(catalogs.GIS_BACKED) | profile_enums
    return sorted(ref for ref in refs if ref not in served)
