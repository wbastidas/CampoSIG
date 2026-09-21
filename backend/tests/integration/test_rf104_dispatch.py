"""Dispatch: assignment is an intention, delivery is a fact (RF-104, RF-324, RF-360).

Before this existed the platform could say who a work order was assigned to and not whether
the phone had it. These tests are about that difference, and about the two ways a crew leaves
with the wrong thing: never having received the order, and holding a copy the planner has
since changed.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from app.dispatch.models import WorkOrderDelivery
from app.dispatch.service import device_readiness, dispatch_board, record_delivery
from app.org.models import BusinessUnit, Organization
from app.sync.models import DeviceStatus
from app.sync.service import (
    block_device,
    build_offline_package,
    enrol_device,
    pull_work_orders,
    push_operation,
)
from app.workorders.models import Crew, WorkOrderState
from app.workorders.service import assign, create_work_order

pytestmark = pytest.mark.integration


def make_unit(session: Session, code: str) -> BusinessUnit:
    org = session.query(Organization).filter_by(code="MATRIZ").first()
    if org is None:
        org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
        session.add(org)
        session.flush()
    unit = BusinessUnit(
        organization_id=org.id, code=code, name=f"Unidad {code}", profile_id="cnel-gye"
    )
    session.add(unit)
    session.flush()
    return unit


@pytest.fixture
def unit(session: Session) -> BusinessUnit:
    return make_unit(session, "GYE")


@pytest.fixture
def crew(session: Session, unit: BusinessUnit) -> Crew:
    created = Crew(
        business_unit_id=unit.id, code="C-01", name="Cuadrilla 1", zone="Durán", active=True
    )
    session.add(created)
    session.flush()
    return created


@pytest.fixture
def device(session: Session, unit: BusinessUnit):
    created, _ = enrol_device(
        session, unit, device_key="dev-001", user_sub="tecnico.1", app_version="1.0.0"
    )
    return created


def make_order(session: Session, unit: BusinessUnit, crew: Crew, zone: str = "Durán"):
    order = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        asset_type_key="support_structure",
        longitude=-79.9,
        latitude=-2.17,
        zone=zone,
        planner_id="planner.a",
    )
    assign(session, order, crew=crew, user_sub="tecnico.1", granted_by="planner.a")
    return order


class TestDeliveryIsRecordedWhereItHappens:
    def test_rf_104_assigned_work_is_not_delivered_work(self, session, unit, crew, device) -> None:
        """The number that ruins a morning: assigned, never on the phone."""
        make_order(session, unit, crew)
        row = dispatch_board(session, unit)[0]
        assert row.assigned == 1
        assert row.delivered == 0
        assert row.undelivered == 1

    def test_rf_104_pulling_records_the_hand_over(self, session, unit, crew, device) -> None:
        make_order(session, unit, crew)
        orders, _ = pull_work_orders(session, device)
        assert len(orders) == 1

        row = dispatch_board(session, unit)[0]
        assert row.delivered == 1
        assert row.undelivered == 0
        assert row.devices == ["dev-001"]

    def test_rf_104_re_pulling_does_not_duplicate_the_record(
        self, session, unit, crew, device
    ) -> None:
        """A phone that re-downloads is a real failure; a duplicated row would hide it."""
        make_order(session, unit, crew)
        pull_work_orders(session, device)
        pull_work_orders(session, device)  # no cursor: the same page again

        rows = session.query(WorkOrderDelivery).all()
        assert len(rows) == 1
        assert rows[0].delivery_count == 2

    def test_rf_104_recording_nothing_is_not_an_error(self, session, unit, device) -> None:
        assert record_delivery(session, device, []) == []


class TestTheCrewHoldsAnOldCopy:
    def test_rf_311_an_order_edited_after_delivery_is_flagged_stale(
        self, session, unit, crew, device
    ) -> None:
        """The crew is working from an old copy and nothing on the phone can tell them."""
        order = make_order(session, unit, crew)
        pull_work_orders(session, device)
        assert dispatch_board(session, unit)[0].stale_on_device == 0

        order.version += 1
        order.description = "el planificador cambió el alcance"
        session.flush()

        row = dispatch_board(session, unit)[0]
        assert row.delivered == 1
        assert row.stale_on_device == 1

    def test_rf_311_syncing_again_clears_the_staleness(self, session, unit, crew, device) -> None:
        order = make_order(session, unit, crew)
        pull_work_orders(session, device)
        order.version += 1
        session.flush()

        pull_work_orders(session, device)
        assert dispatch_board(session, unit)[0].stale_on_device == 0


class TestTheBoardCounts:
    def test_rf_104_work_in_progress_is_counted_separately(
        self, session, unit, crew, device
    ) -> None:
        order = make_order(session, unit, crew)
        pull_work_orders(session, device)
        order.state = WorkOrderState.IN_EXECUTION
        session.flush()

        row = dispatch_board(session, unit)[0]
        assert row.in_progress == 1
        assert row.assigned == 1

    def test_rf_104_returned_work_leaves_the_assigned_count(
        self, session, unit, crew, device
    ) -> None:
        order = make_order(session, unit, crew)
        order.state = WorkOrderState.SYNCED
        session.flush()

        row = dispatch_board(session, unit)[0]
        assert row.returned == 1
        assert row.assigned == 0

    def test_rf_002_one_unit_never_sees_another_unit_board(self, session, unit, crew) -> None:
        other = make_unit(session, "MAN")
        other_crew = Crew(
            business_unit_id=other.id, code="C-99", name="Cuadrilla ajena", active=True
        )
        session.add(other_crew)
        session.flush()
        make_order(session, other, other_crew)

        codes = {row.code for row in dispatch_board(session, unit)}
        assert codes == {"C-01"}
        assert dispatch_board(session, unit)[0].assigned == 0


class TestDeviceReadiness:
    def test_rf_104_a_device_that_never_synced_is_not_ready(self, session, unit, device) -> None:
        row = device_readiness(session, unit)[0]
        assert row.last_sync_at is None
        assert any("nunca ha sincronizado" in reason for reason in row.blockers)

    def test_rf_104_stale_orders_block_departure(self, session, unit, crew, device) -> None:
        order = make_order(session, unit, crew)
        pull_work_orders(session, device)
        device.last_sync_at = order.updated_at
        order.version += 1
        session.flush()

        row = device_readiness(session, unit)[0]
        assert row.held_orders == 1
        assert row.stale_orders == 1
        assert any("cambios posteriores" in reason for reason in row.blockers)

    def test_rf_360_a_package_published_after_the_last_sync_blocks_departure(
        self, session, unit, crew, device
    ) -> None:
        """A phone that never came back for the new zone package does not have it."""
        make_order(session, unit, crew, zone="Durán")
        pull_work_orders(session, device)
        package = build_offline_package(
            session, unit, zone="Durán", tile_url="s3://tiles/duran.pmtiles", asset_count=1200
        )
        session.flush()
        session.refresh(package)
        # Set the sync time relative to the package rather than to the wall clock:
        # PostgreSQL's now() is the *transaction* time, so a package built in the same
        # transaction as the sync carries a timestamp earlier than Python's datetime.now().
        # In production the two are different transactions; in a test they are not.
        device.last_sync_at = package.built_at - timedelta(minutes=5)
        session.flush()

        row = device_readiness(session, unit)[0]
        assert row.package_zone == "Durán"
        assert row.package_version == package.version
        assert row.package_current is False
        assert any("paquete offline" in reason for reason in row.blockers)

    def test_rf_004_a_blocked_device_says_so(self, session, unit, device) -> None:
        block_device(session, device, reason="extravío reportado")
        row = device_readiness(session, unit)[0]
        assert row.status == DeviceStatus.BLOCKED
        assert any("estado" in reason for reason in row.blockers)

    def test_rf_101_a_rejected_upload_is_captured_work_that_is_not_in_the_system(
        self, session, unit, crew, device
    ) -> None:
        make_order(session, unit, crew)
        # A rejection the server itself produces: the operation names a work order that no
        # longer exists, which is what a device holding stale ids sends after a purge.
        entry, applied = push_operation(
            session,
            device,
            operation_id="op-1",
            kind="respuesta",
            work_order_id=uuid.uuid4(),
            payload={},
        )
        assert applied and entry.accepted is False
        row = device_readiness(session, unit)[0]
        assert row.pending_uploads == 1
        assert any("por subir" in reason for reason in row.blockers)

    def test_rf_002_device_readiness_is_scoped_to_the_unit(self, session, unit, device) -> None:
        other = make_unit(session, "MAN")
        enrol_device(session, other, device_key="dev-999", user_sub="tecnico.9")
        keys = {row.device_key for row in device_readiness(session, unit)}
        assert keys == {"dev-001"}
