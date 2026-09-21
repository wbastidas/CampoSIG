"""The server half of the sync contract (RF-004, RF-101, RF-102, RF-322, RF-360).

Mirrors what `android/core/sync` promises: replaying an operation is safe, and nothing crosses
between business units. Where the Kotlin tests assert the device's side of a rule, these assert
the server's — the two have to agree or the guarantee is fiction.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.org.models import BusinessUnit, Organization
from app.sync.models import DeviceStatus
from app.sync.service import (
    CrossUnitError,
    DeviceBlockedError,
    UnknownDeviceError,
    already_processed,
    block_device,
    build_offline_package,
    current_package,
    decode_cursor,
    encode_cursor,
    enrol_device,
    form_versions,
    pull_work_orders,
    push_operation,
    resolve_device,
    undelivered_for,
)
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order

pytestmark = pytest.mark.integration


@pytest.fixture
def units(session: Session) -> dict[str, BusinessUnit]:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created = {}
    for code, name in (("GYE", "Unidad Guayaquil"), ("MAN", "Unidad Manabí")):
        unit = BusinessUnit(organization_id=org.id, code=code, name=name, profile_id="cnel-gye")
        session.add(unit)
        created[code] = unit
    session.flush()
    return created


@pytest.fixture
def unit(units: dict[str, BusinessUnit]) -> BusinessUnit:
    return units["GYE"]


@pytest.fixture
def device(session: Session, unit: BusinessUnit):
    created, _ = enrol_device(
        session, unit, device_key="phone-001", user_sub="tecnico.a", model="Pixel 8a"
    )
    return created


def make_order(session: Session, unit: BusinessUnit, *, user_sub: str | None = "tecnico.a"):
    order = create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code="F-MT-01",
        longitude=-79.9,
        latitude=-2.17,
        planner_id="planner.a",
    )
    order.state = WorkOrderState.ASSIGNED
    order.assigned_user_sub = user_sub
    session.flush()
    return order


class TestRf004Enrolment:
    def test_device_is_enrolled_into_its_unit(self, session: Session, unit: BusinessUnit):
        created, was_new = enrol_device(session, unit, device_key="phone-xyz")
        assert was_new is True
        assert created.business_unit_id == unit.id
        assert created.status == DeviceStatus.ACTIVE

    def test_re_enrolment_updates_instead_of_duplicating(self, session: Session, unit):
        """The app re-registers on every upgrade and after a reinstall."""
        first, _ = enrol_device(session, unit, device_key="phone-xyz", app_version="1.0.0")
        second, was_new = enrol_device(session, unit, device_key="phone-xyz", app_version="1.1.0")
        assert was_new is False
        assert first.id == second.id
        assert second.app_version == "1.1.0"

    def test_unknown_device_is_refused(self, session: Session):
        with pytest.raises(UnknownDeviceError):
            resolve_device(session, "telefono-inventado")

    def test_active_device_resolves(self, session: Session, device):
        assert resolve_device(session, "phone-001").id == device.id


class TestRf004RemoteBlock:
    def test_a_blocked_device_cannot_sync(self, session: Session, device):
        block_device(session, device, reason="extravío reportado")
        with pytest.raises(DeviceBlockedError, match="extravío"):
            resolve_device(session, "phone-001")

    def test_the_block_is_auditable(self, session: Session, device):
        block_device(session, device, reason="robo")
        assert device.blocked_at is not None
        assert device.blocked_reason == "robo"

    def test_the_reason_reaches_the_error(self, session: Session, device):
        """An administrator must be able to tell a technician why their phone stopped."""
        block_device(session, device, reason="equipo reasignado a otra zona")
        with pytest.raises(DeviceBlockedError) as excinfo:
            resolve_device(session, "phone-001")
        assert "reasignado" in str(excinfo.value)


class TestRf102DeltaPull:
    def test_first_pull_returns_assigned_work(self, session: Session, unit, device):
        order = make_order(session, unit)
        orders, cursor = pull_work_orders(session, device)
        assert [o.id for o in orders] == [order.id]
        assert cursor is not None

    def test_second_pull_without_changes_returns_nothing(self, session: Session, unit, device):
        make_order(session, unit)
        _, cursor = pull_work_orders(session, device)
        orders, next_cursor = pull_work_orders(session, device, cursor=cursor)
        # RF-102: a second sync with no changes must transfer almost nothing.
        assert orders == []
        assert next_cursor is None

    def test_a_change_after_the_cursor_is_returned(self, session: Session, unit, device):
        make_order(session, unit)
        _, cursor = pull_work_orders(session, device)
        later = make_order(session, unit)
        orders, _ = pull_work_orders(session, device, cursor=cursor)
        assert [o.id for o in orders] == [later.id]

    def test_work_of_another_user_is_not_sent(self, session: Session, unit, device):
        make_order(session, unit, user_sub="tecnico.b")
        orders, _ = pull_work_orders(session, device)
        assert orders == []

    def test_work_of_another_unit_is_never_sent(self, session: Session, units, device):
        """The isolation guarantee, on the query every phone runs constantly."""
        make_order(session, units["MAN"])
        orders, _ = pull_work_orders(session, device)
        assert all(o.business_unit_id == units["GYE"].id for o in orders)

    def test_closed_work_is_not_pushed_back_to_the_phone(self, session: Session, unit, device):
        order = make_order(session, unit)
        order.state = WorkOrderState.CLOSED
        session.flush()
        orders, _ = pull_work_orders(session, device)
        assert orders == []

    def test_returned_work_comes_back_to_the_phone(self, session: Session, unit, device):
        # A supervisor returning work must put it back on the technician's list.
        order = make_order(session, unit)
        order.state = WorkOrderState.RETURNED
        session.flush()
        orders, _ = pull_work_orders(session, device)
        assert [o.id for o in orders] == [order.id]

    def test_limit_is_honoured_and_the_cursor_advances(self, session: Session, unit, device):
        for _ in range(5):
            make_order(session, unit)
        first, cursor = pull_work_orders(session, device, limit=2)
        assert len(first) == 2
        second, _ = pull_work_orders(session, device, cursor=cursor, limit=2)
        assert len(second) == 2
        assert {o.id for o in first} & {o.id for o in second} == set()


class TestCursorEncoding:
    def test_round_trip(self):
        when = datetime.now(UTC)
        ident = uuid.uuid4()
        decoded = decode_cursor(encode_cursor(when, ident))
        assert decoded is not None
        assert decoded[0] == when
        assert decoded[1] == ident

    def test_a_corrupt_cursor_starts_from_the_beginning(self):
        """A device with a corrupt cursor must be able to resync, not be locked out."""
        assert decode_cursor("esto-no-es-un-cursor") is None
        assert decode_cursor("") is None
        assert decode_cursor(None) is None

    def test_the_cursor_is_a_tuple_not_just_a_timestamp(self):
        """Several orders can share a timestamp; a timestamp-only cursor would skip them."""
        when = datetime.now(UTC)
        low, high = sorted([uuid.uuid4(), uuid.uuid4()])
        assert encode_cursor(when, low) != encode_cursor(when, high)


class TestRf101IdempotentPush:
    def test_an_operation_is_recorded(self, session: Session, unit, device):
        order = make_order(session, unit)
        entry, applied = push_operation(
            session, device, operation_id="op-1", kind="form_response", work_order_id=order.id
        )
        assert applied is True
        assert entry.accepted is True
        assert entry.work_order_id == order.id

    def test_replaying_returns_the_recorded_outcome_without_reapplying(
        self, session: Session, unit, device
    ):
        """The promise the mobile engine relies on: a lost reply costs a duplicate request,
        never duplicate data."""
        order = make_order(session, unit)
        first, applied_first = push_operation(
            session, device, operation_id="op-1", kind="form_response", work_order_id=order.id
        )
        second, applied_second = push_operation(
            session, device, operation_id="op-1", kind="form_response", work_order_id=order.id
        )
        assert applied_first is True
        assert applied_second is False, "un reenvío no debe volver a aplicarse"
        assert first.id == second.id

    def test_the_same_operation_id_from_another_device_is_independent(self, session: Session, unit):
        # Ids are generated per device, so two devices can legitimately pick the same string.
        one, _ = enrol_device(session, unit, device_key="phone-a", user_sub="tecnico.a")
        two, _ = enrol_device(session, unit, device_key="phone-b", user_sub="tecnico.b")
        _, applied_one = push_operation(session, one, operation_id="op-1", kind="transition")
        _, applied_two = push_operation(session, two, operation_id="op-1", kind="transition")
        assert applied_one is True
        assert applied_two is True

    def test_an_operation_for_a_missing_order_is_rejected_not_retried_forever(
        self, session: Session, device
    ):
        entry, applied = push_operation(
            session, device, operation_id="op-1", kind="form_response", work_order_id=uuid.uuid4()
        )
        assert applied is True
        assert entry.accepted is False
        # Recorded as a rejection so the device parks it, rather than raising and making the
        # device retry an operation that can never succeed.
        assert entry.rejection_reason is not None

    def test_an_operation_against_another_unit_is_refused(self, session: Session, units, device):
        foreign = make_order(session, units["MAN"])
        with pytest.raises(CrossUnitError):
            push_operation(
                session, device, operation_id="op-1", kind="form_response", work_order_id=foreign.id
            )

    def test_push_updates_the_last_sync_timestamp(self, session: Session, device):
        assert device.last_sync_at is None
        push_operation(session, device, operation_id="op-1", kind="transition")
        assert device.last_sync_at is not None

    def test_the_device_clock_is_kept_separately(self, session: Session, device):
        """Field devices work offline and their clocks drift, so both times are recorded."""
        device_time = datetime.now(UTC) - timedelta(hours=6)
        entry, _ = push_operation(
            session,
            device,
            operation_id="op-1",
            kind="transition",
            device_created_at=device_time,
        )
        assert entry.device_created_at == device_time
        assert entry.received_at != device_time

    def test_already_processed_finds_the_ledger_entry(self, session: Session, device):
        push_operation(session, device, operation_id="op-1", kind="transition")
        assert already_processed(session, device, "op-1") is not None
        assert already_processed(session, device, "op-2") is None


class TestRf322ReleaseGate:
    def test_nothing_delivered_means_the_device_still_owes_data(
        self, session: Session, unit, device
    ):
        order = make_order(session, unit)
        assert undelivered_for(session, device, order.id) is True

    def test_once_something_arrived_the_server_has_seen_it(self, session: Session, unit, device):
        order = make_order(session, unit)
        push_operation(
            session, device, operation_id="op-1", kind="form_response", work_order_id=order.id
        )
        assert undelivered_for(session, device, order.id) is False


class TestRf360OfflinePackage:
    def test_a_package_is_built_with_a_content_hash(self, session: Session, unit):
        package = build_offline_package(
            session, unit, zone="norte", tile_url="/tiles/norte.pmtiles", asset_count=1200
        )
        assert package.version == 1
        assert len(package.content_hash) == 64
        assert package.manifest["business_unit"] == unit.code

    def test_an_identical_rebuild_is_reused(self, session: Session, unit):
        """Two devices on the same zone must share one artifact, not re-download it."""
        first = build_offline_package(
            session, unit, zone="norte", tile_url="/tiles/norte.pmtiles", asset_count=1200
        )
        second = build_offline_package(
            session, unit, zone="norte", tile_url="/tiles/norte.pmtiles", asset_count=1200
        )
        assert first.id == second.id
        assert second.version == 1

    def test_a_changed_package_supersedes_the_previous_one(self, session: Session, unit):
        first = build_offline_package(
            session, unit, zone="norte", tile_url="/tiles/norte.pmtiles", asset_count=1200
        )
        second = build_offline_package(
            session, unit, zone="norte", tile_url="/tiles/norte.pmtiles", asset_count=1500
        )
        session.refresh(first)
        assert first.superseded_at is not None
        assert second.version == 2
        assert current_package(session, unit, "norte").id == second.id

    def test_zones_are_independent(self, session: Session, unit):
        build_offline_package(session, unit, zone="norte", tile_url="/t/n", asset_count=1)
        build_offline_package(session, unit, zone="sur", tile_url="/t/s", asset_count=1)
        assert current_package(session, unit, "norte") is not None
        assert current_package(session, unit, "sur") is not None

    def test_units_are_independent(self, session: Session, units):
        build_offline_package(session, units["GYE"], zone="norte", tile_url="/t/n", asset_count=1)
        assert current_package(session, units["MAN"], "norte") is None

    def test_the_manifest_lists_parts_for_resumable_transfer(self, session: Session, unit):
        """RF-104: parts are fetched independently so an interrupted transfer resumes."""
        package = build_offline_package(
            session, unit, zone="norte", tile_url="/tiles/norte.pmtiles", asset_count=10
        )
        names = {part["name"] for part in package.manifest["parts"]}
        assert {"tiles", "assets", "forms"} <= names

    def test_the_manifest_pins_the_form_versions(self, session: Session, unit):
        package = build_offline_package(session, unit, zone="norte", tile_url="/t", asset_count=1)
        forms = next(p for p in package.manifest["parts"] if p["name"] == "forms")
        assert forms["versions"] == form_versions()

    def test_the_manifest_carries_the_units_spatial_reference(self, session: Session, unit):
        # Units may sit in different UTM zones; the device must know which it received.
        package = build_offline_package(session, unit, zone="norte", tile_url="/t", asset_count=1)
        assert package.manifest["spatial_reference"] == unit.spatial_reference
