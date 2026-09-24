"""Integration tests for the agent gateway (RF-349, RF-353).

Need a real PostgreSQL: the models use JSONB and UUID columns. They skip when none is
reachable and run in CI, which provisions PostGIS.

Isolation between business units is covered separately, in
test_rf002_multi_unit_isolation.py; here the focus is one unit's happy path and failures.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.gis_gateway.ingest import (
    ContractVersionError,
    CrossUnitError,
    current_snapshot,
    ingest_metadata,
    record_batch_results,
)
from app.gis_gateway.models import AsBuiltBatch
from app.org.models import BusinessUnit, Organization
from app.org.service import context_for_unit
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration


@pytest.fixture
def unit(session: Session) -> BusinessUnit:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created = BusinessUnit(
        organization_id=org.id, code="GYE", name="Unidad Guayaquil", profile_id="cnel-gye"
    )
    session.add(created)
    session.flush()
    return created


class TestMetadataIngest:
    def test_snapshot_is_stored_with_counts(self, session: Session, unit: BusinessUnit):
        metadata = build_metadata("cnel-gye")
        snapshot = ingest_metadata(session, unit, metadata, agent_version="0.1.0")
        assert snapshot.business_unit_id == unit.id
        assert snapshot.profile_id == "cnel-gye"
        assert snapshot.layer_count == len(metadata.layers)
        assert snapshot.domain_count == len(metadata.domains)
        assert snapshot.agent_version == "0.1.0"
        assert snapshot.is_current

    def test_clean_metadata_records_no_problems(self, session: Session, unit: BusinessUnit):
        snapshot = ingest_metadata(session, unit, build_metadata("cnel-gye"))
        assert snapshot.problems == []

    def test_second_snapshot_supersedes_the_first(self, session: Session, unit: BusinessUnit):
        first = ingest_metadata(session, unit, build_metadata("cnel-gye"))
        second = ingest_metadata(session, unit, build_metadata("cnel-gye"))
        session.refresh(first)
        # Superseded, not deleted: a form generated earlier stays traceable to its source.
        assert first.superseded_at is not None
        assert second.is_current
        current = current_snapshot(session, unit.id)
        assert current is not None
        assert current.id == second.id

    def test_unsupported_contract_version_is_rejected(self, session: Session, unit: BusinessUnit):
        with pytest.raises(ContractVersionError, match="versión de contrato"):
            ingest_metadata(session, unit, build_metadata("cnel-gye"), contract_version=99)

    def test_payload_from_another_profile_is_rejected(self, session: Session, unit: BusinessUnit):
        with pytest.raises(CrossUnitError):
            ingest_metadata(session, unit, build_metadata("alt-synthetic"))

    def test_problems_are_persisted_for_the_admin_screen(
        self, session: Session, unit: BusinessUnit
    ):
        metadata = build_metadata("cnel-gye")
        metadata.layers.clear()
        snapshot = ingest_metadata(session, unit, metadata)
        assert snapshot.problems, "un export sin capas debe dejar constancia del problema"


class TestContextForUnit:
    def test_returns_none_before_any_sync(self, session: Session, unit: BusinessUnit):
        resolver, metadata = context_for_unit(session, unit)
        assert resolver.profile.id == "cnel-gye"
        assert metadata is None

    def test_round_trips_through_jsonb(self, session: Session, unit: BusinessUnit):
        """The payload must survive storage: forms are generated from what comes back."""
        original = build_metadata("cnel-gye")
        ingest_metadata(session, unit, original)
        _, restored = context_for_unit(session, unit)
        assert restored is not None
        assert {layer.name for layer in restored.layers} == {
            layer.name for layer in original.layers
        }
        assert len(restored.domains) == len(original.domains)

    def test_volatile_flag_survives_storage(self, session: Session, unit: BusinessUnit):
        ingest_metadata(session, unit, build_metadata("cnel-gye"))
        _, restored = context_for_unit(session, unit)
        assert restored is not None
        assert restored.volatile_domains, "el indicador de dominio volátil debe persistir"


class TestRf353BatchResults:
    @pytest.fixture
    def batch(self, session: Session, unit: BusinessUnit) -> AsBuiltBatch:
        created = AsBuiltBatch(
            business_unit_id=unit.id,
            profile_id="cnel-gye",
            asset_type_key="support_structure",
            status="dispatched",
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
        updated = record_batch_results(
            session, batch.id, [{"proposal_id": str(uuid.uuid4()), "status": "applied"}]
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
