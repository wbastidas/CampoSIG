"""Nothing crosses between business units (ADR-009, RF-002).

The utility is one holding company with several business units, each with its own network,
its own geodatabase and its own arcpy agent. A single platform instance serves all of them,
so the isolation between them is not a nicety: field data landing in the wrong unit's
geodatabase would corrupt a network nobody was working on.

Every test here tries to make something cross, and asserts it cannot.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.gis_gateway.ingest import (
    CrossUnitError,
    current_snapshot,
    ingest_metadata,
    record_batch_results,
)
from app.gis_gateway.models import AsBuiltBatch
from app.org.models import AgentRegistration, BusinessUnit, Organization
from app.org.service import (
    AgentNotAuthorisedError,
    UnknownBusinessUnitError,
    active_units,
    context_for_unit,
    get_business_unit_by_code,
    metadata_for_unit,
    resolve_agent,
    resolver_for_unit,
)
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration


@pytest.fixture
def org(session: Session) -> Organization:
    organization = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(organization)
    session.flush()
    return organization


@pytest.fixture
def units(session: Session, org: Organization) -> dict[str, BusinessUnit]:
    """Two units sharing one profile — the realistic case, since the schema is national."""
    created = {}
    for code, name in (("GYE", "Unidad Guayaquil"), ("MAN", "Unidad Manabí")):
        unit = BusinessUnit(organization_id=org.id, code=code, name=name, profile_id="cnel-gye")
        session.add(unit)
        created[code] = unit
    session.flush()
    return created


@pytest.fixture
def agents(session: Session, units: dict[str, BusinessUnit]) -> dict[str, AgentRegistration]:
    created = {}
    for code, unit in units.items():
        agent = AgentRegistration(business_unit_id=unit.id, agent_key=f"arcmap-{code.lower()}-01")
        session.add(agent)
        created[code] = agent
    session.flush()
    return created


class TestUnitsShareAProfileButNotSnapshots:
    """The schema is national; the domain contents are not."""

    def test_both_units_resolve_the_same_schema(self, units: dict[str, BusinessUnit]):
        gye = resolver_for_unit(units["GYE"])
        man = resolver_for_unit(units["MAN"])
        assert gye.layer("support_structure") == man.layer("support_structure")

    def test_each_unit_has_its_own_snapshot(self, session: Session, units):
        ingest_metadata(session, units["GYE"], build_metadata("cnel-gye"))
        ingest_metadata(session, units["MAN"], build_metadata("cnel-gye"))
        gye_snapshot = current_snapshot(session, units["GYE"].id)
        man_snapshot = current_snapshot(session, units["MAN"].id)
        assert gye_snapshot is not None and man_snapshot is not None
        assert gye_snapshot.id != man_snapshot.id

    def test_one_units_sync_does_not_supersede_anothers(self, session: Session, units):
        """The bug this guards: keying snapshots by profile instead of by unit."""
        gye = ingest_metadata(session, units["GYE"], build_metadata("cnel-gye"))
        ingest_metadata(session, units["MAN"], build_metadata("cnel-gye"))
        session.refresh(gye)
        assert gye.is_current, "el sync de otra unidad no debe invalidar este snapshot"

    def test_a_unit_without_a_sync_sees_no_metadata(self, session: Session, units):
        ingest_metadata(session, units["GYE"], build_metadata("cnel-gye"))
        assert metadata_for_unit(session, units["MAN"]) is None

    def test_form_generation_context_is_per_unit(self, session: Session, units):
        ingest_metadata(session, units["GYE"], build_metadata("cnel-gye"))
        _, gye_metadata = context_for_unit(session, units["GYE"])
        _, man_metadata = context_for_unit(session, units["MAN"])
        assert gye_metadata is not None
        assert man_metadata is None, "generar formularios de MAN no debe usar datos de GYE"


class TestAgentCannotActOutsideItsUnit:
    def test_agent_resolves_to_its_own_unit(self, session: Session, units, agents):
        resolved = resolve_agent(session, agents["GYE"].agent_key)
        assert resolved.business_unit_id == units["GYE"].id

    def test_unknown_agent_key_is_refused(self, session: Session, units):
        with pytest.raises(AgentNotAuthorisedError):
            resolve_agent(session, "agente-inventado")

    def test_inactive_agent_is_refused(self, session: Session, agents):
        agents["GYE"].active = False
        session.flush()
        with pytest.raises(AgentNotAuthorisedError):
            resolve_agent(session, agents["GYE"].agent_key)

    def test_agent_of_an_inactive_unit_is_refused(self, session: Session, units, agents):
        """Deactivating a unit must stop its agent, not just hide it from listings."""
        units["GYE"].active = False
        session.flush()
        with pytest.raises(AgentNotAuthorisedError):
            resolve_agent(session, agents["GYE"].agent_key)

    def test_agent_cannot_report_on_another_units_batch(self, session: Session, units, agents):
        """The core routing guarantee, stated as a test."""
        batch = AsBuiltBatch(
            business_unit_id=units["MAN"].id,
            profile_id="cnel-gye",
            asset_type_key="support_structure",
            status="dispatched",
        )
        session.add(batch)
        session.flush()

        with pytest.raises(CrossUnitError):
            record_batch_results(
                session,
                batch.id,
                [{"proposal_id": str(uuid.uuid4()), "status": "applied"}],
                business_unit_id=units["GYE"].id,
            )

    def test_agent_can_report_on_its_own_batch(self, session: Session, units, agents):
        batch = AsBuiltBatch(
            business_unit_id=units["GYE"].id,
            profile_id="cnel-gye",
            asset_type_key="support_structure",
            status="dispatched",
        )
        session.add(batch)
        session.flush()
        updated = record_batch_results(
            session,
            batch.id,
            [{"proposal_id": str(uuid.uuid4()), "status": "applied"}],
            business_unit_id=units["GYE"].id,
        )
        assert updated.status == "completed"


class TestMetadataCannotClaimAnotherProfile:
    def test_mismatched_profile_in_payload_is_refused(self, session: Session, units):
        """The unit's registration decides the profile, never the payload."""
        metadata = build_metadata("alt-synthetic")
        with pytest.raises(CrossUnitError, match="perfil"):
            ingest_metadata(session, units["GYE"], metadata)

    def test_a_unit_on_a_different_profile_is_honoured(self, session: Session, org):
        """A unit genuinely on another schema works — that is what profiles are for."""
        unit = BusinessUnit(
            organization_id=org.id, code="ALT", name="Unidad piloto", profile_id="alt-synthetic"
        )
        session.add(unit)
        session.flush()
        snapshot = ingest_metadata(session, unit, build_metadata("alt-synthetic"))
        assert snapshot.profile_id == "alt-synthetic"
        assert snapshot.problems == []


class TestUnitLookup:
    def test_lookup_by_code(self, session: Session, units):
        assert get_business_unit_by_code(session, "GYE").id == units["GYE"].id

    def test_inactive_unit_is_not_found(self, session: Session, units):
        units["MAN"].active = False
        session.flush()
        with pytest.raises(UnknownBusinessUnitError):
            get_business_unit_by_code(session, "MAN")

    def test_active_units_are_listed_in_code_order(self, session: Session, units):
        codes = [u.code for u in active_units(session)]
        assert codes == ["GYE", "MAN"]

    def test_the_same_code_may_exist_under_a_different_organization(
        self, session: Session, org, units
    ):
        """Uniqueness is per organisation, so a merger does not collide."""
        other = Organization(code="OTRA", name="Otra distribuidora")
        session.add(other)
        session.flush()
        session.add(
            BusinessUnit(
                organization_id=other.id, code="GYE", name="Homónima", profile_id="cnel-gye"
            )
        )
        session.flush()  # must not raise
