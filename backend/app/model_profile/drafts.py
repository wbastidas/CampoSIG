"""Versioned profile drafts: what an administrator is deciding, and what they decided.

The importer's persistence half (RF-301). A draft is where assisted matching meets a
person: the proposal arrives with evidence, the person accepts, overrides or leaves gaps,
and the draft holds that state between sessions — because mapping six asset types against
a schema of two hundred classes is not one sitting.

Three properties this module exists to guarantee:

* **A published profile is immutable.** Publishing supersedes the previous version rather
  than editing it, for the same reason a regulatory parameter closes its period instead of
  being overwritten: a form generated in March has to stay explainable in September, and
  it can only be explained by the profile that generated it.
* **An incomplete profile cannot be published.** `validate_against_amd` is the gate, and it
  is checked at publication, not only while editing. A draft that was complete an hour ago
  can stop being complete when a newer snapshot drops a class.
* **One open draft per unit and profile.** Two administrators editing the same profile in
  parallel, each unaware, is how half of one person's decisions disappear. The database
  refuses it rather than the screen hoping.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.model_profile.matching import (
    ProfileDecisions,
    build_profile_document,
    default_decisions,
    propose_profile,
    validate_document,
)
from app.model_profile.metadata import GisMetadata
from app.model_profile.models import (
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    STATUS_SUPERSEDED,
    ProfileDraft,
)
from app.model_profile.profile import DataModelProfile, ProfileHeader


class DraftError(Exception):
    """Raised when an operation does not apply to the draft in its current state."""


def _next_version(session: Session, unit_id: uuid.UUID, profile_id: str) -> int:
    highest = session.scalar(
        select(func.max(ProfileDraft.version)).where(
            ProfileDraft.business_unit_id == unit_id, ProfileDraft.profile_id == profile_id
        )
    )
    return (highest or 0) + 1


def open_draft(session: Session, unit_id: uuid.UUID, profile_id: str) -> ProfileDraft | None:
    return session.scalars(
        select(ProfileDraft).where(
            ProfileDraft.business_unit_id == unit_id,
            ProfileDraft.profile_id == profile_id,
            ProfileDraft.status == STATUS_DRAFT,
        )
    ).first()


def published_draft(session: Session, unit_id: uuid.UUID, profile_id: str) -> ProfileDraft | None:
    return session.scalars(
        select(ProfileDraft).where(
            ProfileDraft.business_unit_id == unit_id,
            ProfileDraft.profile_id == profile_id,
            ProfileDraft.status == STATUS_PUBLISHED,
        )
    ).first()


def published_profile(
    session: Session, unit_id: uuid.UUID, profile_id: str
) -> DataModelProfile | None:
    """The profile a unit has adopted, or None while it still runs on the file."""
    record = published_draft(session, unit_id, profile_id)
    if record is None or record.document is None:
        return None
    return DataModelProfile.model_validate(record.document)


def start_draft(
    session: Session,
    *,
    unit_id: uuid.UUID,
    profile_id: str,
    header: ProfileHeader,
    metadata: GisMetadata,
    snapshot_id: uuid.UUID | None,
    created_by: str,
) -> ProfileDraft:
    """Open a draft pre-filled with what the evidence settles (RF-301).

    Starting from the previous published version rather than from the proposal when one
    exists: an administrator who re-imports after a metadata sync is correcting a profile,
    not writing one, and losing their earlier overrides would make re-importing something
    people avoid.
    """
    existing = open_draft(session, unit_id, profile_id)
    if existing is not None:
        raise DraftError(
            f"ya hay un borrador abierto del perfil '{profile_id}' en esta unidad "
            f"(versión {existing.version}); ciérrelo o publíquelo antes de abrir otro"
        )

    proposal = propose_profile(metadata)
    decisions = default_decisions(proposal, header)

    previous = published_draft(session, unit_id, profile_id)
    if previous is not None and previous.decisions:
        decisions = _carry_over(ProfileDecisions.model_validate(previous.decisions), decisions)

    draft = ProfileDraft(
        business_unit_id=unit_id,
        profile_id=profile_id,
        version=_next_version(session, unit_id, profile_id),
        status=STATUS_DRAFT,
        snapshot_id=snapshot_id,
        created_by=created_by,
    )
    session.add(draft)
    _apply(draft, metadata, decisions, updated_by=created_by)
    return draft


def _carry_over(previous: ProfileDecisions, proposed: ProfileDecisions) -> ProfileDecisions:
    """Keep the earlier decisions, and add whatever the new proposal settles on top.

    A decision a person took beats a proposal a machine made, every time — including when
    the machine now scores something else higher. The new snapshot's contribution is the
    asset types and attributes nobody had decided yet.
    """
    merged = ProfileDecisions(header=proposed.header, assets=dict(previous.assets))
    for key, proposal in proposed.assets.items():
        kept = merged.assets.get(key)
        if kept is None:
            merged.assets[key] = proposal
            continue
        for attribute_key, field in proposal.attributes.items():
            kept.attributes.setdefault(attribute_key, field)
    return merged


def _apply(
    draft: ProfileDraft, metadata: GisMetadata, decisions: ProfileDecisions, *, updated_by: str
) -> ProfileDraft:
    """Store decisions and recompute the document and its problems in one step.

    One step on purpose: a draft whose `problems` came from an earlier set of decisions is
    a draft that says "ready" about something else.
    """
    draft.decisions = decisions.model_dump(mode="json", by_alias=True)
    try:
        document = build_profile_document(metadata, decisions)
    except Exception as exc:  # DocumentError, and anything the snapshot made impossible
        draft.document = None
        draft.problems = [str(exc)]
    else:
        draft.document = document
        draft.problems = validate_document(document)
    draft.updated_by = updated_by
    draft.updated_at = datetime.now(UTC)
    return draft


def save_decisions(
    session: Session,
    draft: ProfileDraft,
    metadata: GisMetadata,
    decisions: ProfileDecisions,
    *,
    updated_by: str,
) -> ProfileDraft:
    if draft.status != STATUS_DRAFT:
        raise DraftError(
            f"la versión {draft.version} del perfil '{draft.profile_id}' ya está "
            f"{draft.status}; abra un borrador nuevo para cambiarla"
        )
    return _apply(draft, metadata, decisions, updated_by=updated_by)


def publish_draft(session: Session, draft: ProfileDraft, *, published_by: str) -> ProfileDraft:
    """Adopt a draft as the unit's profile, superseding the previous version.

    Re-validated here rather than trusting `problems`: those were computed when the
    decisions were saved, and a metadata sync since then may have removed a class the
    profile names.
    """
    if draft.status != STATUS_DRAFT:
        raise DraftError(f"esta versión ya está {draft.status}")
    if draft.document is None:
        raise DraftError("el borrador todavía no arma un perfil; faltan decisiones")

    problems = validate_document(draft.document)
    draft.problems = problems
    if problems:
        raise DraftError(
            "el perfil no está completo y no se puede publicar: " + "; ".join(problems)
        )

    previous = published_draft(session, draft.business_unit_id, draft.profile_id)
    if previous is not None:
        previous.status = STATUS_SUPERSEDED
    # Flushed before the new row claims the partial unique index the old one held.
    session.flush()

    draft.status = STATUS_PUBLISHED
    draft.published_by = published_by
    draft.published_at = datetime.now(UTC)
    return draft


def history(session: Session, unit_id: uuid.UUID, profile_id: str) -> list[ProfileDraft]:
    return list(
        session.scalars(
            select(ProfileDraft)
            .where(
                ProfileDraft.business_unit_id == unit_id,
                ProfileDraft.profile_id == profile_id,
            )
            .order_by(ProfileDraft.version.desc())
        )
    )
