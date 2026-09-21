# -*- coding: utf-8 -*-
"""Tests for the ADR-008 invariants.

Named after the requirements they protect, per CLAUDE.md rule 2. These run without
arcpy and without ArcMap, which is what lets the agent be developed and verified in CI
before the Windows machine (decision D2) exists.
"""

from __future__ import unicode_literals

import pytest

from sigec_agent.guards import (
    CONNECTIVITY_FIELDS,
    GuardViolation,
    assert_no_autoupdater_suppression,
    assert_no_connectivity_fields,
    assert_not_geometric_network_insert,
    assert_within_profile_scope,
    writable_attributes,
)


class TestRf348NeverWritesConnectivity(object):
    """RF-348 — connectivity fields are read, never written (ADR-001, H5)."""

    def test_plain_attributes_pass(self):
        assert_no_connectivity_fields(["CODIGO", "MATERIAL", "ALTURA"])

    @pytest.mark.parametrize("field", sorted(CONNECTIVITY_FIELDS))
    def test_each_connectivity_field_is_rejected(self, field):
        with pytest.raises(GuardViolation) as excinfo:
            assert_no_connectivity_fields(["CODIGO", field])
        assert field in str(excinfo.value)

    def test_rejection_is_case_insensitive(self):
        # Field names arrive from profiles and from arcpy describe output, whose
        # casing is not guaranteed to match.
        with pytest.raises(GuardViolation):
            assert_no_connectivity_fields(["ancillaryrole"])

    def test_all_offending_fields_are_reported(self):
        with pytest.raises(GuardViolation) as excinfo:
            assert_no_connectivity_fields(["ENABLED", "CODIGO", "ANCILLARYROLE"])
        message = str(excinfo.value)
        assert "ENABLED" in message
        assert "ANCILLARYROLE" in message

    def test_empty_and_none_names_are_ignored(self):
        assert_no_connectivity_fields(["", None, "CODIGO"])

    def test_writable_attributes_passes_mapping_through(self):
        attributes = {"CODIGO": "P-452", "MATERIAL": "HORMIGON"}
        assert writable_attributes(attributes) == attributes

    def test_writable_attributes_blocks_connectivity(self):
        with pytest.raises(GuardViolation):
            writable_attributes({"CODIGO": "P-452", "ENABLED": 1})


class TestRf347StagingPlusAppend(object):
    """RF-347 — never InsertCursor into a geometric-network class (H13)."""

    def test_class_outside_the_network_allows_direct_insert(self):
        assert_not_geometric_network_insert("SupportStructureStaging", False)

    def test_class_inside_the_network_is_rejected(self):
        with pytest.raises(GuardViolation) as excinfo:
            assert_not_geometric_network_insert("SomeNetworkClass", True)
        message = str(excinfo.value)
        assert "staging" in message.lower()
        assert "Append" in message


class TestRf348NeverTouchesArcfmCom(object):
    """RF-348 — never suppress ArcFM auto-updaters, never use COM (H15)."""

    def test_ordinary_modules_pass(self):
        assert_no_autoupdater_suppression(["arcpy", "json", "requests"])

    @pytest.mark.parametrize(
        "name",
        [
            "Miner.Framework.Dispatch.MMAutoupdaterDispatch",
            "mmAutoUpdaterMode",
            "ArcFM.Something",
        ],
    )
    def test_arcfm_com_entry_points_are_rejected(self, name):
        with pytest.raises(GuardViolation) as excinfo:
            assert_no_autoupdater_suppression([name])
        assert "requiere ArcFM" in str(excinfo.value)


class TestD11ProfileDefinesWriteScope(object):
    """D11 — the agent writes process fields only; the profile is the scope.

    Fields computed by ArcFM's auto-updaters are out of scope by decision, and the way
    that is enforced is simply that they are not in the profile.
    """

    def test_mapped_fields_pass(self):
        assert_within_profile_scope(
            ["CODIGO", "MATERIAL"], ["CODIGO", "MATERIAL", "ALTURA"]
        )

    def test_unmapped_field_is_refused(self):
        with pytest.raises(GuardViolation) as excinfo:
            assert_within_profile_scope(["CODIGO", "AU_CALCULADO"], ["CODIGO"])
        assert "AU_CALCULADO" in str(excinfo.value)
        assert "D11" in str(excinfo.value)

    def test_all_unmapped_fields_are_reported(self):
        with pytest.raises(GuardViolation) as excinfo:
            assert_within_profile_scope(["A", "B", "C"], ["A"])
        message = str(excinfo.value)
        assert "B" in message and "C" in message

    def test_empty_scope_refuses_everything(self):
        with pytest.raises(GuardViolation):
            assert_within_profile_scope(["CODIGO"], [])

    def test_writing_nothing_is_allowed(self):
        assert_within_profile_scope([], ["CODIGO"])
