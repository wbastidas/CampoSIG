"""Reading, editing and delta-downloading the catalogues (RF-034).

The two questions this module answers are not the same question, and conflating them is how a mobile
sync ends up either heavy or wrong:

1. **«What can a technician choose right now?»** — the resolved, active values for one business
   unit: the national list with the unit's own additions folded in.
2. **«What changed since I last synced?»** — every row above a revision, **including the retired
   ones**. A delta that skipped tombstones would leave a phone offering a defect code the utility
   withdrew, forever, and nobody would notice because the value looks perfectly ordinary.

One decision worth naming: a unit's entry with the same code as a national one **overrides** it
rather than duplicating it. Two rows with one code in a picker is a bug a technician sees; and the
override is what lets a unit relabel «cruceta podrida» to its own wording without the matrix having
to agree.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalogs.models import Catalog, CatalogEntry, CatalogSource
from app.org.models import BusinessUnit

#: Catalogues whose values do not live here: they come from the unit's synced GIS metadata and
#: differ per unit (RF-304). Named so the guard test can tell a missing catalogue from one that is
#: somebody else's to serve.
GIS_BACKED = ("feeder", "substation", "station")


class CatalogError(Exception):
    pass


class UnknownCatalogError(CatalogError):
    pass


class NotEditableError(CatalogError):
    """Raised when somebody tries to hand-edit a catalogue an integration owns."""


@dataclass(frozen=True)
class ResolvedEntry:
    """One value as a picker shows it."""

    code: str
    label: str
    synonyms: list[str]
    parent_code: str | None
    attributes: dict[str, Any]
    #: True when this value came from the unit rather than from the national list.
    local: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "synonyms": self.synonyms,
            "parent_code": self.parent_code,
            "attributes": self.attributes,
            "local": self.local,
        }


@dataclass
class ResolvedCatalog:
    """A catalogue as one unit sees it."""

    code: str
    title: str
    source: str
    version: int
    note: str | None
    entries: list[ResolvedEntry] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.entries

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "source": self.source,
            "version": self.version,
            "note": self.note,
            "empty": self.is_empty,
            "entries": [item.as_dict() for item in self.entries],
        }


@dataclass
class Delta:
    """What a device has to apply, and the revision to ask from next time."""

    #: Rows above the requested revision, retired ones included.
    changes: list[dict[str, Any]] = field(default_factory=list)
    #: The highest revision in this batch, or the one asked for when there was nothing.
    revision: int = 0
    #: True when the batch was capped, so a device knows to ask again rather than believing it is
    #: up to date. A silent cap is how a phone ends up permanently missing the tail of a catalogue.
    more: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"changes": self.changes, "revision": self.revision, "more": self.more}


#: Cap on one delta response. Large enough that an ordinary sync is one call, small enough that the
#: first sync of a 1 500-parish catalogue does not arrive as a single payload.
MAX_DELTA = 1000


def get_catalog(session: Session, code: str) -> Catalog:
    row = session.execute(select(Catalog).where(Catalog.code == code)).scalar_one_or_none()
    if row is None:
        raise UnknownCatalogError(f"el catálogo «{code}» no existe")
    return row


def list_catalogs(session: Session) -> list[Catalog]:
    return list(session.execute(select(Catalog).order_by(Catalog.code)).scalars())


def resolve(session: Session, code: str, unit: BusinessUnit | None = None) -> ResolvedCatalog:
    """The active values a technician of this unit can choose from.

    A unit's entry overrides the national one of the same code. Order: the catalogue's own
    `sort_order`, then the label, so a picker reads the same way every time.
    """
    catalog = get_catalog(session, code)
    statement = select(CatalogEntry).where(
        CatalogEntry.catalog_code == code, CatalogEntry.active.is_(True)
    )
    if unit is None:
        statement = statement.where(CatalogEntry.business_unit_id.is_(None))
    else:
        statement = statement.where(
            (CatalogEntry.business_unit_id.is_(None)) | (CatalogEntry.business_unit_id == unit.id)
        )
    rows = list(session.execute(statement).scalars())

    def entry_of(row: CatalogEntry) -> ResolvedEntry:
        return ResolvedEntry(
            code=row.code,
            label=row.label,
            synonyms=list(row.synonyms or []),
            parent_code=row.parent_code,
            attributes=dict(row.attributes or {}),
            local=row.business_unit_id is not None,
        )

    # Two explicit passes rather than one that prefers `local` as it goes: the query's row order is
    # not specified, and a single pass that depended on it would be right by luck. This way the
    # override is a statement — the second pass wins — and a test can break it on purpose.
    merged: dict[str, ResolvedEntry] = {}
    order: dict[str, tuple[int, str]] = {}
    for row in rows:
        if row.business_unit_id is None:
            merged[row.code] = entry_of(row)
            order[row.code] = (row.sort_order, row.label)
    for row in rows:
        if row.business_unit_id is not None:
            merged[row.code] = entry_of(row)
            order[row.code] = (row.sort_order, row.label)

    entries = sorted(merged.values(), key=lambda item: order[item.code])
    return ResolvedCatalog(
        code=catalog.code,
        title=catalog.title,
        source=catalog.source,
        version=catalog.version,
        note=catalog.note,
        entries=entries,
    )


def versions(session: Session) -> dict[str, int]:
    """Catalogue code → version, for the offline package manifest.

    One number per catalogue, so a device compares twelve integers instead of scanning entries it
    already holds. The delta is what it asks for when one of them moved.
    """
    rows = session.execute(select(Catalog.code, Catalog.version)).all()
    return {str(code): int(version) for code, version in rows}


def delta(
    session: Session,
    *,
    since: int = 0,
    unit: BusinessUnit | None = None,
    codes: list[str] | None = None,
    limit: int = MAX_DELTA,
) -> Delta:
    """Everything a device has to apply, retired entries included.

    :param since: the revision the device holds. 0 means «I have nothing».
    :param unit: when given, the national rows plus that unit's. A device belongs to exactly one
        unit (ADR-009), so it never receives another unit's additions.
    :param codes: restrict to these catalogues. Used when only one of them moved.

    The tombstones are the point: an entry that stopped being active has to travel, or the phone
    keeps offering a code that no longer exists.
    """
    statement = select(CatalogEntry).where(CatalogEntry.revision > since)
    if unit is None:
        statement = statement.where(CatalogEntry.business_unit_id.is_(None))
    else:
        statement = statement.where(
            (CatalogEntry.business_unit_id.is_(None)) | (CatalogEntry.business_unit_id == unit.id)
        )
    if codes:
        statement = statement.where(CatalogEntry.catalog_code.in_(codes))
    rows = list(
        session.execute(statement.order_by(CatalogEntry.revision).limit(limit + 1)).scalars()
    )
    more = len(rows) > limit
    rows = rows[:limit]
    changes = [
        {
            "catalog": row.catalog_code,
            "code": row.code,
            "label": row.label,
            "synonyms": list(row.synonyms or []),
            "parent_code": row.parent_code,
            "attributes": dict(row.attributes or {}),
            "active": row.active,
            "local": row.business_unit_id is not None,
            "revision": row.revision,
        }
        for row in rows
    ]
    return Delta(
        changes=changes,
        revision=rows[-1].revision if rows else since,
        more=more,
    )


def _bump(session: Session, code: str) -> None:
    """Advance the catalogue's version, so a device knows this one moved."""
    catalog = get_catalog(session, code)
    catalog.version += 1
    session.flush()


def upsert_entry(
    session: Session,
    code: str,
    *,
    entry_code: str,
    label: str,
    unit: BusinessUnit | None = None,
    synonyms: list[str] | None = None,
    parent_code: str | None = None,
    attributes: dict[str, Any] | None = None,
    sort_order: int = 0,
    active: bool = True,
    actor: str,
    from_integration: bool = False,
) -> CatalogEntry:
    """Create or update one value.

    :param from_integration: True for the ERP connector. A catalogue the integration owns refuses a
        hand edit, because a value typed over one the ERP will overwrite tonight is a value that
        disappears without explanation.
    """
    catalog = get_catalog(session, code)
    if catalog.source == CatalogSource.INTEGRATION and not from_integration:
        raise NotEditableError(
            f"el catálogo «{code}» lo mantiene una integración; editarlo a mano no sirve porque el "
            "siguiente envío lo sobreescribe"
        )

    statement = select(CatalogEntry).where(
        CatalogEntry.catalog_code == code, CatalogEntry.code == entry_code
    )
    statement = statement.where(
        CatalogEntry.business_unit_id.is_(None)
        if unit is None
        else CatalogEntry.business_unit_id == unit.id
    )
    row = session.execute(statement).scalar_one_or_none()
    if row is None:
        row = CatalogEntry(
            catalog_code=code,
            business_unit_id=unit.id if unit else None,
            code=entry_code,
        )
        session.add(row)
    row.label = label
    row.synonyms = list(synonyms or [])
    row.parent_code = parent_code
    row.attributes = dict(attributes or {})
    row.sort_order = sort_order
    row.active = active
    row.updated_by = actor
    session.flush()
    _bump(session, code)
    return row


def retire_entry(
    session: Session,
    code: str,
    entry_code: str,
    *,
    unit: BusinessUnit | None = None,
    actor: str,
) -> CatalogEntry:
    """Deactivate a value. There is no delete: the tombstone has to reach the device."""
    statement = select(CatalogEntry).where(
        CatalogEntry.catalog_code == code, CatalogEntry.code == entry_code
    )
    statement = statement.where(
        CatalogEntry.business_unit_id.is_(None)
        if unit is None
        else CatalogEntry.business_unit_id == unit.id
    )
    row = session.execute(statement).scalar_one_or_none()
    if row is None:
        raise UnknownCatalogError(f"el catálogo «{code}» no tiene el valor «{entry_code}»")
    if row.active:
        row.active = False
        row.updated_by = actor
        session.flush()
        _bump(session, code)
    return row


def entry_counts(session: Session) -> dict[str, tuple[int, int]]:
    """Catalogue code → (active, retired). What the admin screen shows at a glance."""
    rows = session.execute(
        select(
            CatalogEntry.catalog_code,
            func.count().filter(CatalogEntry.active.is_(True)),
            func.count().filter(CatalogEntry.active.is_(False)),
        ).group_by(CatalogEntry.catalog_code)
    ).all()
    return {str(code): (int(live), int(gone)) for code, live, gone in rows}


def known_codes(session: Session) -> set[str]:
    """Every catalogue code the platform serves. Used by the guard over `forms/`."""
    return {row.code for row in list_catalogs(session)}


def unit_of(session: Session, business_unit_id: uuid.UUID | None) -> BusinessUnit | None:
    if business_unit_id is None:
        return None
    return session.get(BusinessUnit, business_unit_id)
