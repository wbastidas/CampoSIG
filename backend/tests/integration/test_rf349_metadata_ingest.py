"""Integration tests for the agent gateway (RF-349, RF-353).

Need a real PostgreSQL: the models use JSONB and UUID columns. They skip when none is
reachable and run in CI, which provisions PostGIS.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.gis_gateway.ingest import (
    ContractVersionError,
    UnknownProfileError,
    current_snapshot,
    ingest_metadata,
    record_batch_results,
    resolver_and_metadata,
)
from app.gis_gateway.models import AsBuiltBatch
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration


class TestMetadataIngest:
    def test_snapshot_is_stored_with_counts(self, session: Session):
        metadata = build_metadata("cnel-gye")
        snapshot = ingest_metadata(session, metadata, agent_version="0.1.0")
        assert snapshot.profile_id == "cnel-gye"
        assert snapshot.layer_count == len(metadata.layers)
        assert snapshot.domain_count == len(metadata.domains)
        assert snapshot.agent_version == "0.1.0"
        assert snapshot.is_current

    def test_clean_metadata_records_no_problems(self, session: Session):
        snapshot = ingest_metadata(session, build_metadata("cnel-gye"))
        assert snapshot.problems == []

    def test_second_snapshot_supersedes_the_first(self, session: Session):
        first = ingest_metadata(session, build_metadata("cnel-gye"))
        second = ingest_metadata(session, build_metadata("cnel-gye"))
        session.refresh(first)
        # Superseded, not deleted: a form generated earlier stays traceable to its source.
        assert first.superseded_at is not None
        assert second.is_current
        assert current_snapshot(session, "cnel-gye").id == second.id

    def test_profiles_are_superseded_independently(self, session: Session):
        cnel = ingest_metadata(session, build_metadata("cnel-gye"))
        ingest_metadata(session, build_metadata("alt-synthetic"))
        session.refresh(cnel)
        assert cnel.is_current, "otro perfil no debe invalidar este snapshot"

    def test_unsupported_contract_version_is_rejected(self, session: Session):
        with pytest.raises(ContractVersionError, match="versión de contrato"):
            ingest_metadata(session, build_metadata("cnel-gye"), contract_version=99)

    def test_unknown_profile_is_rejected(self, session: Session):
        metadata = build_metadata("cnel-gye")
        metadata.profile_id = "perfil-que-no-existe"
        with pytest.raises(UnknownProfileError):
            ingest_metadata(session, metadata)

    def test_problems_are_persisted_for_the_admin_screen(self, session: Session):
        metadata = build_metadata("cnel-gye")
        metadata.layers.clear()
        snapshot = ingest_metadata(session, metadata)
        assert snapshot.problems, "un export sin capas debe dejar constancia del problema"


class TestResolverAndMetadata:
    def test_returns_none_before_any_sync(self, session: Session):
        resolver, metadata = resolver_and_metadata(session, "cnel-gye")
        assert resolver.profile.id == "cnel-gye"
        assert metadata is None

    def test_round_trips_through_jsonb(self, session: Session):
        """The payload must survive storage: forms are generated from what comes back."""
        original = build_metadata("cnel-gye")
        ingest_metadata(session, original)
        _, restored = resolver_and_metadata(session, "cnel-gye")
        assert restored is not None
        assert {layer.name for layer in restored.layers} == {
            layer.name for layer in original.layers
        }
        assert len(restored.domains) == len(original.domains)

    def test_volatile_flag_survives_storage(self, session: Session):
        ingest_metadata(session, build_metadata("cnel-gye"))
        _, restored = resolver_and_metadata(session, "cnel-gye")
        assert restored is not None
        assert restored.volatile_domains, "el indicador de dominio volátil debe persistir"


class TestRf353BatchResults:
    @pytest.fixture
    def batch(self, session: Session) -> AsBuiltBatch:
        created = AsBuiltBatch(
            profile_id="cnel-gye", asset_type_key="support_structure", status="dispatched"
        )
        session.add(created)
        session.flush()
        return created

    def test_outcomes_are_recorded(self, session: Session, batch: AsBuiltBatch):
        outcomes = [
            {"proposal_id": str(uuid.uuid4()), "status": "applied"},
            {"proposal_id": str(uuid.uuid4()), "status": "requires_arcfm", "message": "AU"},
        ]
        updated = record_batch_results(session, batch.id, outcomes)
        assert len(updated.results) == 2
        assert {r.status for r in updated.results} == {"applied", "requires_arcfm"}

    def test_batch_completes_when_nothing_is_pending(self, session: Session, batch: AsBuiltBatch):
        proposal = str(uuid.uuid4())
        updated = record_batch_results(
            session, batch.id, [{"proposal_id": proposal, "status": "applied"}]
        )
        assert updated.status == "completed"
        assert updated.completed_at is not None

    def test_requires_arcfm_counts_as_settled(self, session: Session, batch: AsBuiltBatch):
        """The agent has said all it can; the rest is the GIS team's call (D11)."""
        updated = record_batch_results(
            session, batch.id, [{"proposal_id": str(uuid.uuid4()), "status": "requires_arcfm"}]
        )
        assert updated.status == "completed"

    def test_retry_updates_instead_of_duplicating(self, session: Session, batch: AsBuiltBatch):
        """The agent is explicitly allowed to retry a batch (RF-353 idempotency)."""
        proposal = str(uuid.uuid4())
        record_batch_results(session, batch.id, [{"proposal_id": proposal, "status": "error"}])
        updated = record_batch_results(
            session, batch.id, [{"proposal_id": proposal, "status": "applied"}]
        )
        assert len(updated.results) == 1
        assert updated.results[0].status == "applied"

    def test_unknown_batch_is_reported(self, session: Session):
        with pytest.raises(LookupError, match="no existe"):
            record_batch_results(
                session, uuid.uuid4(), [{"proposal_id": str(uuid.uuid4()), "status": "applied"}]
            )
