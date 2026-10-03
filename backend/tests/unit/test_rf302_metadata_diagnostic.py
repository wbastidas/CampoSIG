"""RF-302 — the completeness diagnostic is what makes "configure, don't program" checkable.

These run without a database: the diagnostic is pure logic over a profile and a metadata
payload, which is where the value is. The persistence paths are covered by the integration
tests in tests/integration/.
"""

from __future__ import annotations

import pytest

from app.gis_gateway.ingest import (
    SUPPORTED_CONTRACT_VERSIONS,
    _metadata_problems,
    _parse_timestamp,
)
from app.model_profile.profile import DataModelProfile, load_profile
from tests.conftest import ALL_PROFILE_IDS, build_metadata


def only_support_structure(profile_id: str) -> DataModelProfile:
    """A copy of the profile narrowed to one asset type.

    A copy, not the original: `load_profile` is cached and hands out a shared object, so
    narrowing it in place would change what other tests see.
    """
    profile = load_profile(profile_id).model_copy(deep=True)
    profile.bindings = {"support_structure": profile.bindings["support_structure"]}
    return profile


class TestCleanMetadataHasNoProblems:
    @pytest.mark.parametrize("profile_id", ALL_PROFILE_IDS)
    def test_matching_metadata_reports_nothing(self, profile_id: str):
        # The fixture derives its names from the profile, so a clean run must be silent.
        profile = load_profile(profile_id)
        metadata = build_metadata(profile_id)
        assert _metadata_problems(metadata, profile) == []


class TestMissingLayerIsReported:
    def test_unexported_layer_is_reported(self):
        profile = load_profile("cnel-gye")
        metadata = build_metadata("cnel-gye")
        metadata.layers.clear()
        problems = _metadata_problems(metadata, profile)
        assert any("no exportó" in p for p in problems)

    def test_every_unmapped_asset_type_is_reported(self):
        """A single missing layer must not mask the others."""
        profile = load_profile("cnel-gye")
        metadata = build_metadata("cnel-gye")
        metadata.layers.clear()
        problems = _metadata_problems(metadata, profile)
        # Six asset types in the pilot scope, none of them exported.
        assert len([p for p in problems if "no exportó" in p]) == len(profile.bindings)


class TestMissingFieldIsReported:
    def test_field_absent_from_the_exported_layer_is_reported(self):
        profile = only_support_structure("cnel-gye")
        metadata = build_metadata("cnel-gye")
        layer = metadata.layer(profile.bindings["support_structure"].layer)
        assert layer is not None
        layer.fields = layer.fields[:1]  # keep only the business key
        problems = _metadata_problems(metadata, profile)
        assert any("campo ausente" in p for p in problems)

    def test_field_matching_is_case_insensitive(self):
        """Field casing from arcpy Describe is not guaranteed to match the profile."""
        profile = only_support_structure("cnel-gye")
        metadata = build_metadata("cnel-gye")
        layer = metadata.layer(profile.bindings["support_structure"].layer)
        assert layer is not None
        for field in layer.fields:
            field.name = field.name.lower()
        assert _metadata_problems(metadata, profile) == []

    def test_layer_matching_is_case_insensitive(self):
        profile = only_support_structure("cnel-gye")
        metadata = build_metadata("cnel-gye")
        layer = metadata.layer(profile.bindings["support_structure"].layer)
        assert layer is not None
        layer.name = layer.name.upper()
        assert _metadata_problems(metadata, profile) == []


class TestRf304MissingVolatileDomainIsReported:
    """A volatile domain that failed to export is worse than a missing stable one.

    The form would silently fall back to a stale catalogue, which in another business
    unit means offering feeders that do not exist there.
    """

    def test_missing_volatile_domain_is_reported(self):
        profile = only_support_structure("cnel-gye")
        metadata = build_metadata("cnel-gye")
        volatile = [d for d in metadata.domains if d.volatile_by_business_unit]
        assert volatile, "the fixture must contain a volatile domain for this test to mean anything"
        metadata.domains = [d for d in metadata.domains if not d.volatile_by_business_unit]
        problems = _metadata_problems(metadata, profile)
        assert any("dominio volátil" in p and "caché" in p for p in problems)

    def test_present_volatile_domain_is_not_reported(self):
        profile = only_support_structure("cnel-gye")
        metadata = build_metadata("cnel-gye")
        problems = _metadata_problems(metadata, profile)
        assert not any("dominio volátil" in p for p in problems)


class TestContractVersioning:
    def test_version_one_is_supported(self):
        assert 1 in SUPPORTED_CONTRACT_VERSIONS

    def test_supported_versions_is_immutable(self):
        # A mutable set here would let a caller widen what the backend accepts at runtime.
        with pytest.raises(AttributeError):
            SUPPORTED_CONTRACT_VERSIONS.add(99)  # type: ignore[attr-defined]


class TestTimestampParsing:
    def test_iso_with_offset(self):
        assert _parse_timestamp("2026-09-21T10:30:00+00:00") is not None

    def test_iso_with_zulu_suffix(self):
        # arcpy and .NET commonly emit 'Z' rather than '+00:00'.
        parsed = _parse_timestamp("2026-09-21T10:30:00Z")
        assert parsed is not None
        assert parsed.tzinfo is not None

    def test_none_is_passed_through(self):
        assert _parse_timestamp(None) is None

    def test_empty_string_is_passed_through(self):
        assert _parse_timestamp("") is None

    def test_malformed_timestamp_does_not_reject_the_export(self):
        """A bad clock string must not throw away an otherwise valid metadata export."""
        assert _parse_timestamp("ayer por la tarde") is None
