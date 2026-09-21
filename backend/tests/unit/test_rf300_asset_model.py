"""RF-300 — the canonical vocabulary is valid and says nothing about any real schema."""

from __future__ import annotations

from app.model_profile.amd import AttributeRole, Capability


class TestCanonicalVocabulary:
    def test_loads_and_validates(self, amd):
        assert amd.version == 1
        assert len(amd.asset_types) >= 6

    def test_pilot_asset_types_are_present(self, amd):
        # The six types the pilot covers (PLAN_IMPLEMENTACION, I2-I7 scope).
        expected = {
            "support_structure",
            "distribution_transformer",
            "street_light",
            "fuse_switch",
            "line_segment",
            "service_point",
        }
        assert expected <= set(amd.asset_type_keys)

    def test_every_asset_type_has_a_business_key(self, amd):
        # Without it, work cannot be tied to an asset at all.
        for asset_type in amd.asset_types:
            assert asset_type.attribute_with_role(AttributeRole.BUSINESS_KEY) is not None, (
                f"{asset_type.key} has no business_key attribute"
            )

    def test_every_enum_attribute_resolves_to_a_declared_enum(self, amd):
        for asset_type in amd.asset_types:
            for attribute in asset_type.attributes:
                if attribute.enum_ref:
                    assert attribute.enum_ref in amd.enums, (
                        f"{asset_type.key}.{attribute.key} -> unknown enum {attribute.enum_ref}"
                    )

    def test_vocabulary_contains_no_real_field_names(self, amd):
        """The AMD must be installation-neutral.

        Guarded here as well as by the CI leak check, because a real name creeping into
        the canonical vocabulary is the most damaging place for it to hide: it would look
        legitimate and quietly make every profile depend on one customer's schema.
        """
        canonical_keys = {
            attribute.key for asset_type in amd.asset_types for attribute in asset_type.attributes
        } | set(amd.asset_type_keys)
        for key in canonical_keys:
            assert key.islower(), f"'{key}' is not lower_snake_case; suspect a real field name"
            assert key.isascii(), f"'{key}' is not ASCII; canonical keys are English"

    def test_capabilities_drive_behaviour(self, amd):
        vision = [t.key for t in amd.asset_types if t.has(Capability.AI_VISION)]
        assert "support_structure" in vision
        # Not everything is photographable; the distinction must be real, not decorative.
        assert len(vision) < len(amd.asset_types)
