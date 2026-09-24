"""Assignment, reassignment and graphical selection (RF-310..RF-324).

Need PostGIS: the map queries are spatial. They skip without a database and run in CI.

The two properties under test are the ones that hurt if they break: work must not cross
business units, and a reassignment must not cost a technician the work they already did.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.org.models import BusinessUnit, Organization
from app.workorders.models import Crew, Priority, WorkOrder, WorkOrderSource, WorkOrderState
from app.workorders.service import (
    ConcurrentEditError,
    CrossUnitError,
    InvalidTransitionError,
    NotAssignableError,
    ReasonRequiredError,
    assign,
    assign_many,
    assignable_in_box,
    create_work_order,
    crew_workload,
    current_custody,
    custody_history,
    import_external,
    in_bounding_box,
    mark_pending_handover,
    transition,
)

pytestmark = pytest.mark.integration

# Guayaquil, roughly — the pilot area.
GYE_LON, GYE_LAT = -79.90, -2.17


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
def crews(session: Session, units: dict[str, BusinessUnit]) -> dict[str, Crew]:
    created = {}
    for unit_code, crew_code in (("GYE", "C-01"), ("GYE", "C-02"), ("MAN", "M-01")):
        crew = Crew(
            business_unit_id=units[unit_code].id,
            code=crew_code,
            name=f"Cuadrilla {crew_code}",
            competencies=["MT", "BT"],
        )
        session.add(crew)
        created[crew_code] = crew
    session.flush()
    return created


def make_order(
    session: Session,
    unit: BusinessUnit,
    *,
    lon: float = GYE_LON,
    lat: float = GYE_LAT,
    form_code: str = "F-MT-01",
    planner_id: str = "planner.a",
    **kwargs,
) -> WorkOrder:
    return create_work_order(
        session,
        unit,
        work_type="inspeccion_preventiva",
        form_code=form_code,
        longitude=lon,
        latitude=lat,
        planner_id=planner_id,
        **kwargs,
    )


class TestCreationAndImport:
    def test_order_is_created_planned_when_a_planner_owns_it(
        self, session: Session, unit: BusinessUnit
    ):
        order = make_order(session, unit)
        assert order.state == WorkOrderState.PLANNED
        assert order.business_unit_id == unit.id

    def test_unknown_form_code_is_refused_at_creation(self, session: Session, unit: BusinessUnit):
        """A work order pointing at a missing form would only fail later, on a phone."""
        from app.forms.catalog import CatalogError

        with pytest.raises(CatalogError):
            make_order(session, unit, form_code="F-XX-99")

    def test_import_is_idempotent(self, session: Session, unit: BusinessUnit):
        """The external system owns the number and may resend it (RF-011)."""
        first, created_first = import_external(
            session,
            unit,
            external_ref="OT-2026-000101",
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
        )
        second, created_second = import_external(
            session,
            unit,
            external_ref="OT-2026-000101",
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
        )
        assert created_first is True
        assert created_second is False
        assert first.id == second.id

    def test_the_same_reference_may_exist_in_another_unit(self, session: Session, units):
        """Two units can legitimately receive orders numbered alike by different systems."""
        for code in ("GYE", "MAN"):
            _, created = import_external(
                session,
                units[code],
                external_ref="OT-2026-000101",
                work_type="inspeccion_preventiva",
                form_code="F-MT-01",
            )
            assert created is True

    def test_source_defaults_to_external_on_import(self, session: Session, unit: BusinessUnit):
        order, _ = import_external(
            session,
            unit,
            external_ref="OT-1",
            work_type="inspeccion_preventiva",
            form_code="F-MT-01",
        )
        assert order.source == WorkOrderSource.EXTERNAL_SYSTEM


class TestStateMachine:
    def test_valid_transition_is_applied(self, session: Session, unit: BusinessUnit):
        order = make_order(session, unit)
        transition(session, order, WorkOrderState.ASSIGNED)
        assert order.state == WorkOrderState.ASSIGNED

    def test_invalid_transition_lists_what_is_allowed(self, session: Session, unit: BusinessUnit):
        order = make_order(session, unit)
        with pytest.raises(InvalidTransitionError, match="permitidos"):
            transition(session, order, WorkOrderState.CLOSED)

    @pytest.mark.parametrize(
        ("start", "target"),
        [
            (WorkOrderState.IN_EXECUTION, WorkOrderState.SUSPENDED),
            (WorkOrderState.IN_REVIEW, WorkOrderState.RETURNED),
            (WorkOrderState.PLANNED, WorkOrderState.CANCELLED),
        ],
    )
    def test_transitions_that_need_a_reason_refuse_without_one(
        self, session: Session, unit: BusinessUnit, start: str, target: str
    ):
        order = make_order(session, unit)
        order.state = start
        session.flush()
        with pytest.raises(ReasonRequiredError):
            transition(session, order, target)
        transition(session, order, target, reason="motivo registrado")
        assert order.state == target

    def test_a_closed_order_is_terminal(self, session: Session, unit: BusinessUnit):
        order = make_order(session, unit)
        order.state = WorkOrderState.CLOSED
        session.flush()
        with pytest.raises(InvalidTransitionError):
            transition(session, order, WorkOrderState.IN_EXECUTION)


class TestAssignment:
    def test_assignment_records_custody(self, session: Session, unit, crews):
        order = make_order(session, unit)
        assign(session, order, crew=crews["C-01"], device_id="dev-1", granted_by="planner.a")
        held = current_custody(session, order)
        assert held is not None
        assert held.device_id == "dev-1"
        assert held.until is None

    def test_form_version_is_pinned_at_assignment(self, session: Session, unit, crews):
        """An order executes with the version current when assigned (SRS 4.1.6)."""
        order = make_order(session, unit)
        assert order.form_version is None
        assign(session, order, crew=crews["C-01"])
        assert order.form_version is not None

    def test_reassignment_closes_the_previous_custody(self, session: Session, unit, crews):
        order = make_order(session, unit)
        assign(session, order, crew=crews["C-01"], device_id="dev-1")
        assign(session, order, crew=crews["C-02"], device_id="dev-2", reason="cambio de zona")

        history = custody_history(session, order)
        assert len(history) == 2
        assert history[0].until is not None, "la custodia anterior debe quedar cerrada"
        assert history[0].reason == "cambio de zona"
        assert history[1].until is None
        assert history[1].device_id == "dev-2"

    def test_full_chain_of_custody_survives(self, session: Session, unit, crews):
        """RF-324: who held it, on which device, since when and why."""
        order = make_order(session, unit)
        for device in ("dev-1", "dev-2", "dev-3"):
            assign(session, order, crew=crews["C-01"], device_id=device, reason=f"a {device}")
        history = custody_history(session, order)
        assert [h.device_id for h in history] == ["dev-1", "dev-2", "dev-3"]
        assert sum(1 for h in history if h.until is None) == 1

    def test_crew_of_another_unit_is_refused(self, session: Session, unit, crews):
        """The routing guarantee, at the assignment boundary."""
        order = make_order(session, unit)
        with pytest.raises(CrossUnitError):
            assign(session, order, crew=crews["M-01"])

    def test_an_order_in_execution_cannot_be_assigned(self, session: Session, unit, crews):
        order = make_order(session, unit)
        order.state = WorkOrderState.IN_EXECUTION
        session.flush()
        with pytest.raises(NotAssignableError):
            assign(session, order, crew=crews["C-01"])


class TestRf311ConcurrentPlanners:
    """Two planners must never silently overwrite each other."""

    def test_stale_version_is_refused(self, session: Session, unit, crews):
        order = make_order(session, unit)
        seen_by_planner_b = order.version
        # Planner A assigns first, bumping the version.
        assign(session, order, crew=crews["C-01"])
        with pytest.raises(ConcurrentEditError, match="recargue"):
            assign(session, order, crew=crews["C-02"], expected_version=seen_by_planner_b)

    def test_current_version_is_accepted(self, session: Session, unit, crews):
        order = make_order(session, unit)
        assign(session, order, crew=crews["C-01"], expected_version=order.version)
        assert order.assigned_crew_id == crews["C-01"].id

    def test_version_increments_on_every_change(self, session: Session, unit, crews):
        order = make_order(session, unit)
        start = order.version
        assign(session, order, crew=crews["C-01"])
        assign(session, order, crew=crews["C-02"])
        assert order.version == start + 2


class TestRf322ReassignmentPreservesCapturedWork:
    """A technician can have an order taken away; their captured work must survive."""

    def test_unsynced_data_is_flagged_on_the_closed_custody(self, session: Session, unit, crews):
        order = make_order(session, unit)
        assign(session, order, crew=crews["C-01"], device_id="dev-1")
        mark_pending_handover(session, order, device_id="dev-1")
        assign(session, order, crew=crews["C-02"], device_id="dev-2", reason="reasignada")

        history = custody_history(session, order)
        first = next(h for h in history if h.device_id == "dev-1")
        assert first.had_unsynced_data is True, (
            "la plataforma debe saber que el dispositivo origen tenía datos sin subir"
        )

    def test_the_record_survives_the_reassignment(self, session: Session, unit, crews):
        order = make_order(session, unit)
        assign(session, order, crew=crews["C-01"], device_id="dev-1")
        mark_pending_handover(session, order, device_id="dev-1")
        assign(session, order, crew=crews["C-02"], device_id="dev-2")
        # Nothing is deleted: the chain is append-only.
        assert len(custody_history(session, order)) == 2

    def test_marking_an_unknown_device_is_harmless(self, session: Session, unit, crews):
        order = make_order(session, unit)
        assign(session, order, crew=crews["C-01"], device_id="dev-1")
        assert mark_pending_handover(session, order, device_id="dev-desconocido") is None


class TestGraphicalSelection:
    """The map is the planner's primary tool, so its queries get their own tests."""

    @pytest.fixture
    def scattered(self, session: Session, unit: BusinessUnit) -> dict[str, WorkOrder]:
        inside = make_order(session, unit, lon=GYE_LON, lat=GYE_LAT)
        # Quito, comfortably outside a Guayaquil viewport.
        outside = make_order(session, unit, lon=-78.47, lat=-0.18)
        nowhere = create_work_order(
            session, unit, work_type="bitacora", form_code="F-IC-03", planner_id="planner.a"
        )
        return {"inside": inside, "outside": outside, "nowhere": nowhere}

    def test_bbox_returns_only_what_is_inside(self, session: Session, unit, scattered):
        found = in_bounding_box(session, unit, west=-80.1, south=-2.4, east=-79.7, north=-1.9)
        ids = {o.id for o in found}
        assert scattered["inside"].id in ids
        assert scattered["outside"].id not in ids

    def test_orders_without_a_location_are_excluded(self, session: Session, unit, scattered):
        found = in_bounding_box(session, unit, west=-81.5, south=-5.5, east=-75.0, north=2.0)
        assert scattered["nowhere"].id not in {o.id for o in found}

    def test_bbox_never_returns_another_units_work(self, session: Session, units, scattered):
        """The isolation guarantee, on the query the map runs constantly."""
        make_order(session, units["MAN"], lon=GYE_LON, lat=GYE_LAT)
        found = in_bounding_box(
            session, units["GYE"], west=-80.1, south=-2.4, east=-79.7, north=-1.9
        )
        assert all(o.business_unit_id == units["GYE"].id for o in found)

    def test_unassigned_filter(self, session: Session, unit, crews, scattered):
        assign(session, scattered["inside"], crew=crews["C-01"])
        found = in_bounding_box(
            session,
            unit,
            west=-80.1,
            south=-2.4,
            east=-79.7,
            north=-1.9,
            unassigned_only=True,
        )
        assert scattered["inside"].id not in {o.id for o in found}

    def test_limit_is_honoured(self, session: Session, unit: BusinessUnit):
        for _ in range(5):
            make_order(session, unit)
        found = in_bounding_box(
            session, unit, west=-80.1, south=-2.4, east=-79.7, north=-1.9, limit=3
        )
        assert len(found) == 3

    def test_assignable_in_box_excludes_work_in_progress(self, session: Session, unit, scattered):
        scattered["inside"].state = WorkOrderState.IN_EXECUTION
        session.flush()
        found = assignable_in_box(session, unit, west=-80.1, south=-2.4, east=-79.7, north=-1.9)
        assert scattered["inside"].id not in {o.id for o in found}


class TestLassoAssignment:
    """Assigning a map selection to one crew, in one gesture."""

    def test_a_selection_is_assigned_together(self, session: Session, unit, crews):
        orders = [make_order(session, unit) for _ in range(3)]
        assigned, failures = assign_many(session, unit, [o.id for o in orders], crew=crews["C-01"])
        assert len(assigned) == 3
        assert failures == []

    def test_one_bad_order_does_not_lose_the_rest(self, session: Session, unit, crews):
        """Partial success by design: nineteen good pins must not fail for one bad one."""
        good = [make_order(session, unit) for _ in range(2)]
        blocked = make_order(session, unit)
        blocked.state = WorkOrderState.IN_EXECUTION
        session.flush()

        assigned, failures = assign_many(
            session, unit, [o.id for o in [*good, blocked]], crew=crews["C-01"]
        )
        assert len(assigned) == 2
        assert [order_id for order_id, _ in failures] == [blocked.id]
        assert "no se puede asignar" in failures[0][1]

    def test_an_order_from_another_unit_is_reported_not_assigned(
        self, session: Session, units, crews
    ):
        foreign = make_order(session, units["MAN"])
        assigned, failures = assign_many(session, units["GYE"], [foreign.id], crew=crews["C-01"])
        assert assigned == []
        assert failures[0][0] == foreign.id

    def test_a_crew_from_another_unit_is_refused_outright(self, session: Session, units, crews):
        order = make_order(session, units["GYE"])
        with pytest.raises(CrossUnitError):
            assign_many(session, units["GYE"], [order.id], crew=crews["M-01"])

    def test_unknown_ids_are_reported(self, session: Session, unit, crews):
        missing = uuid.uuid4()
        assigned, failures = assign_many(session, unit, [missing], crew=crews["C-01"])
        assert assigned == []
        assert failures[0][0] == missing


class TestRf313SharedWorkload:
    def test_workload_counts_open_work_per_crew(self, session: Session, unit, crews):
        for _ in range(2):
            order = make_order(session, unit)
            assign(session, order, crew=crews["C-01"])
        board = {row["code"]: row["open_work_orders"] for row in crew_workload(session, unit)}
        assert board["C-01"] == 2
        assert board["C-02"] == 0

    def test_closed_work_is_not_counted_as_load(self, session: Session, unit, crews):
        order = make_order(session, unit)
        assign(session, order, crew=crews["C-01"])
        order.state = WorkOrderState.CLOSED
        session.flush()
        board = {row["code"]: row["open_work_orders"] for row in crew_workload(session, unit)}
        assert board["C-01"] == 0

    def test_workload_excludes_other_units_crews(self, session: Session, units, crews):
        codes = {row["code"] for row in crew_workload(session, units["GYE"])}
        assert codes == {"C-01", "C-02"}

    def test_priority_ordering_puts_critical_first(self, session: Session, unit: BusinessUnit):
        """Ordering by the stored string would be alphabetical, which is backwards.

        'alta' < 'baja' < 'critica' < 'media' sorts low priority above critical, so the
        query ranks explicitly. This test is what keeps that from regressing.
        """
        make_order(session, unit, priority=Priority.LOW)
        make_order(session, unit, priority=Priority.MEDIUM)
        make_order(session, unit, priority=Priority.CRITICAL)
        make_order(session, unit, priority=Priority.HIGH)
        found = in_bounding_box(session, unit, west=-80.1, south=-2.4, east=-79.7, north=-1.9)
        assert [o.priority for o in found] == [
            Priority.CRITICAL,
            Priority.HIGH,
            Priority.MEDIUM,
            Priority.LOW,
        ]
