# -*- coding: utf-8 -*-
"""Tests for the as-built batch applier (RF-347, RF-348, RF-353).

Run against tools/arcpy-double, so they need neither arcpy nor ArcMap. The double
reproduces the failure that shapes the whole design: InsertCursor raises SystemError
on geometric-network classes (H13).
"""

from __future__ import unicode_literals

import arcpy
import pytest

from sigec_agent.apply_batch import (
    APPLIED,
    ERROR,
    REQUIRES_ARCFM,
    BatchApplier,
)
from sigec_agent.guards import GuardViolation

STAGING = "AsBuiltStaging"
TARGET = "TargetNetworkClass"
FIELDS = ["CODIGO", "MATERIAL", "ALTURA"]


@pytest.fixture(autouse=True)
def clean_double():
    arcpy._reset()
    # The target participates in the geometric network; the staging class does not.
    arcpy._register_network_class(TARGET)
    yield
    arcpy._reset()


@pytest.fixture
def applier():
    return BatchApplier("sde_connection.sde", arcpy_module=arcpy)


def batch(proposals, geometric_network="Electric_Network"):
    return {
        "staging_class": STAGING,
        "target_class": TARGET,
        "field_names": FIELDS,
        "geometric_network": geometric_network,
        "proposals": proposals,
    }


def proposal(pid, requires_arcfm=False, attributes=None):
    return {
        "proposal_id": pid,
        "requires_arcfm": requires_arcfm,
        "attributes": attributes or {"CODIGO": pid, "MATERIAL": "HORMIGON", "ALTURA": 11},
    }


class TestRf347StagingPlusAppend(object):
    """The staging + Append path, forced by H13."""

    def test_proposals_reach_the_target_through_staging(self, applier):
        outcomes = applier.apply(batch([proposal("p1"), proposal("p2")]))
        assert [o.status for o in outcomes] == [APPLIED, APPLIED]
        # Rows landed in the target via Append, not via a direct insert.
        assert len(arcpy._APPENDED[TARGET]) == 2

    def test_direct_insert_into_the_network_class_would_fail(self):
        """Guards the premise: this is why staging exists (H13)."""
        with pytest.raises(SystemError):
            arcpy.da.InsertCursor(TARGET, FIELDS)

    def test_staging_class_accepts_direct_insert(self):
        cursor = arcpy.da.InsertCursor(STAGING, FIELDS)
        cursor.insertRow(("P-1", "HORMIGON", 11))
        assert len(arcpy.da._rows_of(STAGING)) == 1

    def test_field_order_is_preserved(self, applier):
        applier.apply(batch([proposal("p1")]))
        assert arcpy._APPENDED[TARGET][0] == ("p1", "HORMIGON", 11)

    def test_missing_attribute_becomes_none(self, applier):
        applier.apply(batch([proposal("p1", attributes={"CODIGO": "p1"})]))
        assert arcpy._APPENDED[TARGET][0] == ("p1", None, None)


class TestRf348NeverWritesConnectivity(object):
    """Connectivity fields are refused even when they arrive inside a batch."""

    def test_connectivity_field_in_field_names_is_refused(self, applier):
        bad = batch([proposal("p1")])
        bad["field_names"] = ["CODIGO", "ENABLED"]
        with pytest.raises(GuardViolation):
            applier.apply(bad)

    def test_connectivity_field_in_attributes_is_refused(self, applier):
        bad = batch([proposal("p1", attributes={"CODIGO": "p1", "ANCILLARYROLE": 1})])
        with pytest.raises(GuardViolation):
            applier.apply(bad)

    def test_nothing_is_appended_when_a_guard_trips(self, applier):
        bad = batch([proposal("p1")])
        bad["field_names"] = ["CODIGO", "CIRCUITSOURCEGUID"]
        with pytest.raises(GuardViolation):
            applier.apply(bad)
        assert TARGET not in arcpy._APPENDED


class TestRequiresArcfmIsNeverAppliedAutomatically(object):
    """H15 — the agent does not run ArcFM auto-updaters and does not pretend to."""

    def test_flagged_proposal_is_reported_not_applied(self, applier):
        outcomes = applier.apply(batch([proposal("p1", requires_arcfm=True)]))
        assert [o.status for o in outcomes] == [REQUIRES_ARCFM]
        assert TARGET not in arcpy._APPENDED

    def test_mixed_batch_applies_only_the_rest(self, applier):
        outcomes = applier.apply(
            batch([proposal("p1", requires_arcfm=True), proposal("p2")])
        )
        by_id = dict((o.proposal_id, o.status) for o in outcomes)
        assert by_id == {"p1": REQUIRES_ARCFM, "p2": APPLIED}
        assert len(arcpy._APPENDED[TARGET]) == 1

    def test_batch_of_only_flagged_proposals_touches_nothing(self, applier):
        outcomes = applier.apply(
            batch([proposal("p1", requires_arcfm=True), proposal("p2", requires_arcfm=True)])
        )
        assert all(o.status == REQUIRES_ARCFM for o in outcomes)
        assert arcpy.da._rows_of(STAGING) == []


class TestRf353OutcomePerProposal(object):
    """RF-353 — every proposal gets an outcome reported back."""

    def test_every_proposal_is_accounted_for(self, applier):
        proposals = [proposal("p1"), proposal("p2", requires_arcfm=True), proposal("p3")]
        outcomes = applier.apply(batch(proposals))
        assert sorted(o.proposal_id for o in outcomes) == ["p1", "p2", "p3"]

    def test_append_failure_is_reported_for_each_staged_proposal(self, applier, monkeypatch):
        def explode(inputs, target, schema_type="TEST"):
            raise arcpy.ExecuteError("network is locked")

        monkeypatch.setattr(arcpy, "Append_management", explode)
        outcomes = applier.apply(batch([proposal("p1"), proposal("p2")]))
        assert [o.status for o in outcomes] == [ERROR, ERROR]
        assert "network is locked" in outcomes[0].message

    def test_outcome_serializes_for_the_backend(self, applier):
        outcomes = applier.apply(batch([proposal("p1")]))
        payload = outcomes[0].as_dict()
        assert set(payload) == {"proposal_id", "status", "message"}
        assert payload["status"] == APPLIED


class TestRebuildConnectivity(object):
    """H14 — connectivity is rebuilt after Append, and a missing rebuild is visible."""

    def test_rebuild_is_attempted_when_a_network_is_declared(self, applier):
        calls = []
        applier.arcpy.RebuildConnectivity_management = lambda net, ext: calls.append(net)
        applier.apply(batch([proposal("p1")]))
        assert calls == ["Electric_Network"]
        del applier.arcpy.RebuildConnectivity_management

    def test_missing_rebuild_tool_is_reported_not_swallowed(self, applier):
        # The double does not implement the tool; the method must say so rather than
        # silently succeed, so an un-rebuilt network is never invisible.
        assert applier.rebuild_connectivity("Electric_Network") is False

    def test_no_rebuild_when_target_is_outside_any_network(self, applier):
        calls = []
        applier.arcpy.RebuildConnectivity_management = lambda net, ext: calls.append(net)
        applier.apply(batch([proposal("p1")], geometric_network=None))
        assert calls == []
        del applier.arcpy.RebuildConnectivity_management


class TestEditSession(object):
    """Network classes cannot be modified outside an edit session."""

    def test_session_is_closed_after_a_successful_apply(self, applier):
        applier.apply(batch([proposal("p1")]))
        assert arcpy.da.Editor.session_open is False

    def test_session_is_closed_after_a_failed_append(self, applier, monkeypatch):
        def explode(inputs, target, schema_type="TEST"):
            raise arcpy.ExecuteError("boom")

        monkeypatch.setattr(arcpy, "Append_management", explode)
        applier.apply(batch([proposal("p1")]))
        # A leaked edit session would hold locks on the production geodatabase.
        assert arcpy.da.Editor.session_open is False


class TestD11WriteScopeInBatches(object):
    """The write scope applies to whole batches, not just to individual calls."""

    def test_batch_within_scope_applies(self, applier):
        payload = batch([proposal("p1")])
        payload["profile_fields"] = FIELDS
        outcomes = applier.apply(payload)
        assert [o.status for o in outcomes] == [APPLIED]

    def test_batch_outside_scope_is_refused(self, applier):
        payload = batch([proposal("p1")])
        payload["field_names"] = FIELDS + ["AU_CALCULADO"]
        payload["profile_fields"] = FIELDS
        with pytest.raises(GuardViolation):
            applier.apply(payload)
        assert TARGET not in arcpy._APPENDED

    def test_scope_is_optional_for_backwards_compatibility(self, applier):
        # Omitting profile_fields keeps the older behaviour; the connectivity and
        # network guards still apply, so nothing unsafe becomes possible.
        outcomes = applier.apply(batch([proposal("p1")]))
        assert [o.status for o in outcomes] == [APPLIED]
