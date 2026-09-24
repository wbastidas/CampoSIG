"""RF-301 / RF-305 — a different data model is configuration, not programming.

These tests are the teeth behind ADR-004. They run under whichever profile CI selects,
and the `any_resolver` ones run under every profile, so a dependency on one schema fails
the build rather than surfacing at the next installation.
"""

from __future__ import annotations

import pytest

from app.model_profile.amd import AttributeRole, Capability
from app.model_profile.resolver import (
    ConnectivityWriteError,
    ModelResolver,
    ResolutionError,
)


class TestProfileCompleteness:
    def test_active_profile_has_no_problems(self, resolver: ModelResolver):
        assert resolver.problems() == []

    def test_every_shipped_profile_is_complete(self, any_resolver: ModelResolver):
        problems = any_resolver.problems()
        assert problems == [], f"perfil '{any_resolver.profile.id}': {problems}"


class TestResolutionByRole:
    def test_business_key_resolves_in_every_profile(self, any_resolver: ModelResolver):
        # The point of roles: the caller never learns the real field name.
        field = any_resolver.field_for_role("support_structure", AttributeRole.BUSINESS_KEY)
        assert isinstance(field, str) and field

    def test_business_key_differs_between_profiles(self):
        """Proves the indirection is doing work, not passing a constant through."""
        from app.model_profile.profile import load_profile

        cnel = ModelResolver(load_profile("cnel-gye"))
        alt = ModelResolver(load_profile("alt-synthetic"))
        assert cnel.field_for_role(
            "support_structure", AttributeRole.BUSINESS_KEY
        ) != alt.field_for_role("support_structure", AttributeRole.BUSINESS_KEY)

    def test_layer_resolves_in_every_profile(self, any_resolver: ModelResolver):
        assert any_resolver.layer("distribution_transformer")

    def test_unknown_asset_type_is_a_clear_error(self, resolver: ModelResolver):
        with pytest.raises(KeyError, match="unknown asset type"):
            resolver.asset_type("flux_capacitor")

    def test_unmapped_attribute_names_the_profile(self, resolver: ModelResolver):
        with pytest.raises(ResolutionError, match="no está mapeado"):
            resolver.field("support_structure", "colour")


class TestValueMapping:
    def test_round_trip_in_every_profile(self, any_resolver: ModelResolver):
        source = any_resolver.to_source_value("support_structure", "material", "concrete")
        back = any_resolver.to_canonical_value("support_structure", "material", source)
        assert back == "concrete"

    def test_value_codes_differ_between_profiles(self):
        """cnel-gye uses Spanish mnemonics, alt-synthetic uses integers."""
        from app.model_profile.profile import load_profile

        cnel = ModelResolver(load_profile("cnel-gye"))
        alt = ModelResolver(load_profile("alt-synthetic"))
        assert cnel.to_source_value("support_structure", "material", "wood") != alt.to_source_value(
            "support_structure", "material", "wood"
        )

    def test_every_canonical_value_maps(self, any_resolver: ModelResolver, amd):
        for value in amd.enums["material.support"]:
            assert any_resolver.to_source_value("support_structure", "material", value) is not None

    def test_unknown_canonical_value_is_rejected(self, resolver: ModelResolver):
        with pytest.raises(ResolutionError, match="no está en el value_map"):
            resolver.to_source_value("support_structure", "material", "unobtainium")

    def test_non_enum_attribute_is_rejected(self, resolver: ModelResolver):
        with pytest.raises(ResolutionError, match="no es un enum"):
            resolver.to_source_value("support_structure", "height_m", "11")


class TestWriteSafety:
    """ADR-001 — connectivity is never written, whatever the profile says."""

    @pytest.mark.parametrize(
        "field",
        ["ANCILLARYROLE", "ENABLED", "ELECTRICTRACEWEIGHT", "ancillaryrole"],
    )
    def test_connectivity_writes_are_refused(self, any_resolver: ModelResolver, field: str):
        with pytest.raises(ConnectivityWriteError):
            any_resolver.assert_writable(["some_code", field])

    def test_ordinary_writes_are_allowed(self, any_resolver: ModelResolver):
        any_resolver.assert_writable(list(any_resolver.fields("support_structure").values()))

    def test_network_participants_are_always_staging_only(self, any_resolver: ModelResolver):
        """A profile cannot opt a network class into direct writes."""
        for key in any_resolver.profile.bindings:
            if any_resolver.participates_in_geometric_network(key):
                assert any_resolver.write_path(key) == "staging_only"

    def test_cnel_transformer_is_staging_only(self):
        from app.model_profile.profile import load_profile

        cnel = ModelResolver(load_profile("cnel-gye"))
        assert cnel.participates_in_geometric_network("distribution_transformer")
        assert cnel.write_path("distribution_transformer") == "staging_only"


class TestVolatileDomains:
    """RF-304 — domains that vary per business unit are never treated as constants."""

    def test_feeder_code_is_marked_volatile_in_every_profile(self, any_resolver: ModelResolver):
        volatile = any_resolver.volatile_domain_fields("support_structure")
        feeder_field = any_resolver.field("support_structure", "feeder_code")
        assert feeder_field in volatile


class TestCapabilityQueries:
    def test_vision_capable_types_are_mapped(self, any_resolver: ModelResolver):
        types = any_resolver.asset_types_with(Capability.AI_VISION)
        assert "support_structure" in types

    def test_capability_query_is_restricted_to_mapped_types(self, any_resolver: ModelResolver):
        for key in any_resolver.asset_types_with(Capability.WORK_TARGET):
            assert key in any_resolver.profile.bindings


class TestEnabledIsEnforcedAtRuntime:
    """ENABLED is a connectivity field but is not statically greppable.

    scripts/check_data_model_leak.py deliberately does not watch it: it is an ordinary
    English word and would produce constant false positives. So the runtime refusal is
    the only thing standing between a careless write and the geometric network, and it
    gets its own test.
    """

    def test_enabled_is_refused(self, any_resolver: ModelResolver):
        with pytest.raises(ConnectivityWriteError):
            any_resolver.assert_writable(["code", "ENABLED"])

    def test_lowercase_enabled_is_refused(self, any_resolver: ModelResolver):
        with pytest.raises(ConnectivityWriteError):
            any_resolver.assert_writable(["enabled"])
