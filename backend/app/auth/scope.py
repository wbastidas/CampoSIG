"""Ámbito enforcement: narrowing what a principal's queries return (RF-002).

RF-002 asks for scope by área, zona, agencia and contratista, on top of the business-unit
isolation ADR-009 already enforces at the door. `Principal.may_see` is the rule, stated once in
plain Python so it can be unit-tested without a database; the two functions here are that same
rule translated into a `WHERE` clause, for the listing queries where filtering in Python after
the fact would defeat the pagination and counts those queries exist for.

**A dimension the principal is not restricted on narrows nothing.** Empty `areas`/`zones`/
`agencies` and a null `contractor` are the common case — most accounts carry no ámbito claim at
all — and `None` comes back from both functions below so a caller can tell at a glance that
nothing narrows, rather than ANDing in a clause that always evaluates true.

**A record that does not carry a dimension is not excluded by it.** A work order with no zone,
or a form code the catalogue does not categorise into any área, is not hidden from a zone- or
área-scoped supervisor — it is simply not an answer that axis can give. Contractor is the one
exception: an account scoped to one contractor sees only that contractor's own crews, so a work
order with no crew assigned yet, or a crew with no contractor set, answers "not mine".
"""

from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.auth.principal import Principal
from app.forms.catalog import area_of_form_code, load_definitions
from app.workorders.models import Crew, WorkOrder


def work_order_scope(principal: Principal) -> ColumnElement[bool] | None:
    """A `WHERE` clause narrowing `WorkOrder` rows to this principal's ámbito, or `None`."""
    if principal.is_corporate:
        return None
    clauses: list[ColumnElement[bool]] = []
    if principal.areas:
        wanted = {area.lower() for area in principal.areas}
        excluded_codes = {
            code
            for code, definition in load_definitions().items()
            if str(definition.form.area).lower() not in wanted
        }
        if excluded_codes:
            clauses.append(WorkOrder.form_code.not_in(excluded_codes))
    if principal.zones:
        clauses.append(or_(WorkOrder.zone.is_(None), WorkOrder.zone.in_(principal.zones)))
    if principal.agencies:
        clauses.append(or_(WorkOrder.agency.is_(None), WorkOrder.agency.in_(principal.agencies)))
    if principal.contractor is not None:
        clauses.append(
            WorkOrder.assigned_crew_id.in_(
                select(Crew.id).where(Crew.contractor == principal.contractor)
            )
        )
    return and_(*clauses) if clauses else None


def crew_scope(principal: Principal) -> ColumnElement[bool] | None:
    """The same ámbito, as a `WHERE` clause over `Crew` rows directly.

    No área clause: a crew is not itself the area of any one work order, its members' work is.
    """
    if principal.is_corporate:
        return None
    clauses: list[ColumnElement[bool]] = []
    if principal.zones:
        clauses.append(or_(Crew.zone.is_(None), Crew.zone.in_(principal.zones)))
    if principal.agencies:
        clauses.append(or_(Crew.agency.is_(None), Crew.agency.in_(principal.agencies)))
    if principal.contractor is not None:
        clauses.append(Crew.contractor == principal.contractor)
    return and_(*clauses) if clauses else None


def may_see_order(principal: Principal | None, order: WorkOrder) -> bool:
    """`Principal.may_see` for one work order — the single-object counterpart of
    `work_order_scope`, for endpoints that take an id. `None` (no principal, a service call)
    narrows nothing, the same as the listing helpers do."""
    if principal is None:
        return True
    return principal.may_see(
        area=area_of_form_code(order.form_code),
        zone=order.zone,
        agency=order.agency,
        contractor=order.crew.contractor if order.crew is not None else None,
    )


def may_see_crew(principal: Principal | None, crew: Crew) -> bool:
    """The same for one crew: `crew_scope` for an id."""
    if principal is None:
        return True
    return principal.may_see(zone=crew.zone, agency=crew.agency, contractor=crew.contractor)
