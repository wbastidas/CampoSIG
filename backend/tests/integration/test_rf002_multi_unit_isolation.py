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


class TestAsBuiltStagingDoesNotCrossUnits:
    """El hueco que esta clase cierra, escrito tal como era.

    `asbuilt_proposal` no tenía columna de unidad de negocio, y `create_batch` seleccionaba
    **toda** propuesta aprobada de un tipo de activo, sin importar de quién era, para meterla en
    el lote de la unidad que lo pidió. Es decir: los datos de campo de una unidad despachados al
    agente arcpy de otra, y escritos en una geodatabase donde nadie estaba trabajando. No es una
    fuga de lectura; es una escritura cruzada, que es peor y más difícil de deshacer.

    Se descubrió escribiendo la consulta de la bandeja GIS de la pantalla de revisión, no por un
    test — de ahí que ahora haya uno.
    """

    @pytest.fixture
    def approved_orders(self, session: Session, units: dict[str, BusinessUnit]):
        from app.workorders.models import WorkOrderState
        from app.workorders.service import create_work_order

        created = {}
        for code, unit in units.items():
            order = create_work_order(
                session,
                unit,
                work_type="inspeccion_preventiva",
                form_code="F-MT-01",
                asset_type_key="support_structure",
                longitude=-79.9,
                latitude=-2.17,
            )
            order.state = WorkOrderState.APPROVED
            created[code] = order
        session.flush()
        return created

    def _stage(self, session: Session, unit: BusinessUnit, order) -> uuid.UUID:
        from app.gis_gateway.asbuilt import build_proposal, stage_from_work_order

        proposal = build_proposal(
            resolver_for_unit(unit),
            asset_type_key="support_structure",
            action="update",
            attributes={"material": "concrete"},
            gis_global_id="{" + str(uuid.uuid4()).upper() + "}",
        )
        proposal["proposal_id"] = uuid.uuid4()
        staged = stage_from_work_order(session, unit, order, [proposal])
        return staged[0]

    def test_rf_002_a_batch_only_carries_its_own_units_proposals(
        self, session: Session, units, approved_orders
    ):
        from app.gis_gateway.asbuilt import create_batch
        from app.gis_gateway.staging_table import asbuilt_proposal

        mine = self._stage(session, units["GYE"], approved_orders["GYE"])
        theirs = self._stage(session, units["MAN"], approved_orders["MAN"])

        batch = create_batch(session, units["GYE"], asset_type_key="support_structure")
        assert batch is not None

        from sqlalchemy import select

        in_batch = {
            row[0]
            for row in session.execute(
                select(asbuilt_proposal.c.proposal_id).where(
                    asbuilt_proposal.c.batch_id == batch.id
                )
            ).all()
        }
        assert in_batch == {mine}
        assert theirs not in in_batch

    def test_rf_002_the_other_units_proposal_stays_available_for_its_own_batch(
        self, session: Session, units, approved_orders
    ):
        """Y no queda atrapada: sigue esperando el lote de su propia unidad."""
        from app.gis_gateway.asbuilt import create_batch

        self._stage(session, units["GYE"], approved_orders["GYE"])
        theirs = self._stage(session, units["MAN"], approved_orders["MAN"])

        create_batch(session, units["GYE"], asset_type_key="support_structure")
        their_batch = create_batch(session, units["MAN"], asset_type_key="support_structure")
        assert their_batch is not None

        from sqlalchemy import select

        from app.gis_gateway.staging_table import asbuilt_proposal

        assert (
            session.execute(
                select(asbuilt_proposal.c.batch_id).where(asbuilt_proposal.c.proposal_id == theirs)
            ).scalar()
            == their_batch.id
        )

    def test_rf_002_every_staged_proposal_carries_its_unit(
        self, session: Session, units, approved_orders
    ):
        from sqlalchemy import select

        from app.gis_gateway.staging_table import asbuilt_proposal

        self._stage(session, units["GYE"], approved_orders["GYE"])
        rows = session.execute(
            select(asbuilt_proposal.c.business_unit_id, asbuilt_proposal.c.work_order_ref)
        ).all()
        assert rows
        assert all(row[0] == units["GYE"].id for row in rows)

    def test_rf_002_a_unit_with_nothing_approved_gets_no_batch(
        self, session: Session, units, approved_orders
    ):
        """Aunque la unidad vecina tenga propuestas listas."""
        from app.gis_gateway.asbuilt import create_batch

        self._stage(session, units["MAN"], approved_orders["MAN"])
        assert create_batch(session, units["GYE"], asset_type_key="support_structure") is None
