"""Published form versions (RF-032).

The acceptance criterion is one sentence — «publicar la v2 no altera las OT asignadas con la v1» —
and the platform did not meet it. Forms live as files under `forms/` and the catalogue keyed them by
code alone, so editing `F-AP-01.yaml` changed what *every* order composed with, including the ones a
technician was already carrying. A field renamed on Tuesday would have made Monday's answers fail
validation against a form nobody in the field had ever seen.

So publication is what freezes a version:

* The files are the **draft**. Editing one changes nothing for anybody until it is published.
* Publishing snapshots the definition **and the blocks it uses** into the database under
  ``(code, version)``. Freezing only the definition would leave the shape at the mercy of a block
  edit, which is the same bug one level down.
* An order composes against **its own** version. An obsoleted version still composes, because the
  orders that carry it still exist; obsoleting only stops new orders from being created with it.

And one distinction that is deliberate rather than an omission: **the form's shape is frozen; the
unit's catalogue values are not.** A published F-AP-01 still offers the feeder codes that exist
today, because an order executed today has to name a feeder that exists today (RF-304's volatile
domains). Freezing those would hand a technician a list of substations from last year.

Nothing here writes to `forms/`. The files are generated from the data-model profile (rule 3) and
this module only reads them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.forms.catalog import CatalogError, FormBlock, FormDefinition, get_definition, load_blocks
from app.forms.models import PublishedForm


class FormState(StrEnum):
    """The lifecycle RF-032 names. «Borrador» is the file on disk, so it is not stored here."""

    PUBLISHED = "publicado"
    #: No new order may use it. Existing orders still compose against it.
    OBSOLETE = "obsoleto"


class FormNotPublishedError(Exception):
    """Raised when a version is asked for and nobody published it."""


class AlreadyPublishedError(Exception):
    """Raised when a version already exists. Republishing the same number silently would make
    «v1.0.0» mean two different shapes, which is worse than refusing."""


@dataclass(frozen=True)
class FrozenCatalogue:
    """A published version's shape: the definition and the blocks it referenced.

    Used in place of the files when composing an order's form, so the shape is the one that was
    published and not the one on disk today.
    """

    code: str
    version: str
    definition: FormDefinition
    blocks: dict[str, FormBlock]
    published_at: datetime
    published_by: str | None
    state: str

    @property
    def is_obsolete(self) -> bool:
        return self.state == FormState.OBSOLETE


def _snapshot_hash(definition: dict[str, Any], blocks: dict[str, Any]) -> str:
    """A content hash over the frozen shape.

    Lets a publisher see that two versions differ only in the number, and lets a test assert that
    publishing did not quietly pick up a different file.
    """
    payload = json.dumps(
        {"definition": definition, "blocks": blocks}, sort_keys=True, ensure_ascii=False
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def publish(session: Session, code: str, *, actor: str, note: str | None = None) -> PublishedForm:
    """Freeze the current file's shape as the published version of ``code``.

    :raises CatalogError: when the form or one of its blocks does not exist on disk. Publishing a
        form with a missing block would publish a shape that cannot be composed, and the error
        belongs at publication time rather than on a phone.
    :raises AlreadyPublishedError: when that version number already exists.
    """
    definition = get_definition(code)
    library = load_blocks()
    missing = [item for item in definition.form.blocks if item not in library]
    if missing:
        raise CatalogError(
            f"no se puede publicar {code}: falta(n) el/los bloque(s) {', '.join(missing)}"
        )
    version = definition.version

    existing = session.execute(
        select(PublishedForm).where(PublishedForm.code == code, PublishedForm.version == version)
    ).scalar_one_or_none()
    if existing is not None:
        raise AlreadyPublishedError(
            f"{code} v{version} ya está publicado; suba la versión en el archivo antes de publicar"
        )

    frozen_blocks = {item: library[item].model_dump(mode="json") for item in definition.form.blocks}
    frozen_definition = definition.model_dump(mode="json")

    # The previous published version becomes obsolete: two published versions of one form would
    # leave «which one does a new order get» to whichever row the query saw first.
    for row in session.execute(
        select(PublishedForm).where(
            PublishedForm.code == code, PublishedForm.state == FormState.PUBLISHED
        )
    ).scalars():
        row.state = FormState.OBSOLETE
        row.obsoleted_at = datetime.now(UTC)

    published = PublishedForm(
        code=code,
        version=version,
        state=FormState.PUBLISHED,
        definition=frozen_definition,
        blocks=frozen_blocks,
        content_hash=_snapshot_hash(frozen_definition, frozen_blocks),
        published_by=actor,
        note=note,
    )
    session.add(published)
    session.flush()
    return published


def obsolete(session: Session, code: str, version: str, *, actor: str) -> PublishedForm:
    """Stop new orders from using a version, without touching the ones that already do."""
    row = _row(session, code, version)
    if row.state != FormState.OBSOLETE:
        row.state = FormState.OBSOLETE
        row.obsoleted_at = datetime.now(UTC)
        row.obsoleted_by = actor
        session.flush()
    return row


def _row(session: Session, code: str, version: str) -> PublishedForm:
    row = session.execute(
        select(PublishedForm).where(PublishedForm.code == code, PublishedForm.version == version)
    ).scalar_one_or_none()
    if row is None:
        raise FormNotPublishedError(f"{code} v{version} no está publicado")
    return row


def _as_frozen(row: PublishedForm) -> FrozenCatalogue:
    return FrozenCatalogue(
        code=row.code,
        version=row.version,
        definition=FormDefinition.model_validate(row.definition),
        blocks={
            name: FormBlock.model_validate(value) for name, value in (row.blocks or {}).items()
        },
        published_at=row.published_at,
        published_by=row.published_by,
        state=row.state,
    )


def frozen(session: Session, code: str, version: str) -> FrozenCatalogue:
    """The published shape of one version, whatever its state.

    Obsolete versions answer too: the orders that carry them still have to compose.
    """
    return _as_frozen(_row(session, code, version))


def current(session: Session, code: str) -> FrozenCatalogue | None:
    """The version a new order should get, or None when nothing is published for this code."""
    row = session.execute(
        select(PublishedForm).where(
            PublishedForm.code == code, PublishedForm.state == FormState.PUBLISHED
        )
    ).scalar_one_or_none()
    return _as_frozen(row) if row is not None else None


def current_version(session: Session, code: str) -> str | None:
    found = current(session, code)
    return found.version if found is not None else None


def history(session: Session, code: str) -> list[PublishedForm]:
    """Every published version of a code, newest first."""
    return list(
        session.execute(
            select(PublishedForm)
            .where(PublishedForm.code == code)
            .order_by(PublishedForm.sequence.desc())
        ).scalars()
    )


def published_versions(session: Session) -> dict[str, str]:
    """Code → the version in force, for the offline package manifest and the catalogue screen."""
    rows = session.execute(
        select(PublishedForm.code, PublishedForm.version).where(
            PublishedForm.state == FormState.PUBLISHED
        )
    ).all()
    return {str(code): str(version) for code, version in rows}


def as_dict(row: PublishedForm) -> dict[str, Any]:
    return {
        "code": row.code,
        "version": row.version,
        "state": row.state,
        "content_hash": row.content_hash,
        "published_by": row.published_by,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "obsoleted_at": row.obsoleted_at.isoformat() if row.obsoleted_at else None,
        "obsoleted_by": row.obsoleted_by,
        "note": row.note,
        #: The block codes the version froze, so a reader can see what a form was made of without
        #: downloading the whole snapshot.
        "blocks": sorted(row.blocks or {}),
    }


def resolve_for_order(
    session: Session, code: str, version: str | None
) -> tuple[FrozenCatalogue | None, str | None]:
    """The shape an order composes with, and a caveat when it is not a frozen one.

    Three cases, and the difference matters:

    1. The order names a version and it is published → that frozen shape. What RF-032 asks for.
    2. The order names a version nobody published → the files, with a caveat. This is the state of
       a platform that has not published yet, and pretending otherwise would refuse to compose a
       form a technician needs today.
    3. The order names no version → the files, with a caveat.

    The caveat is returned rather than logged because it belongs on the screen: a reviewer looking
    at answers should know whether the form they are reading is the one the technician filled in.
    """
    if version:
        try:
            return frozen(session, code, version), None
        except FormNotPublishedError:
            return None, (
                f"la OT declara {code} v{version} y esa versión no está publicada: se compone "
                "contra el archivo actual, que puede haber cambiado"
            )
    return None, f"la OT no declara versión de {code}: se compone contra el archivo actual"
