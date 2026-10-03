"""RF-303 — forms are generated from GIS metadata, not written by hand.

The `any_generator` tests run under every profile: a generator that only works against
one data model would fail them, which is the early warning ADR-004 exists to give.
"""

from __future__ import annotations

import json

import pytest

from app.forms.generator import JSON_SCHEMA_DIALECT, FormGenerator


class TestGeneratedSchemaShape:
    def test_schema_is_valid_json_schema_2020_12(self, generator: FormGenerator):
        form = generator.generate("support_structure")
        assert form.schema["$schema"] == JSON_SCHEMA_DIALECT
        assert form.schema["type"] == "object"
        assert form.schema["properties"]

    def test_schema_is_serialisable(self, generator: FormGenerator):
        # Forms are stored and shipped as JSON; anything unserialisable breaks sync.
        form = generator.generate("support_structure")
        assert json.loads(json.dumps(form.schema)) == form.schema

    def test_schema_records_its_provenance(self, generator: FormGenerator):
        form = generator.generate("support_structure")
        assert form.schema["x-asset-type"] == "support_structure"
        assert form.schema["x-profile"] == generator.resolver.profile.id
        assert form.schema["x-generated"] is True

    def test_generates_for_every_profile(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        assert set(form.schema["properties"]) >= {"code", "material", "height_m"}

    def test_ui_schema_orders_every_property(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        assert set(form.ui_schema["ui:order"]) == set(form.schema["properties"])


class TestPropertiesUseCanonicalKeys:
    """The form speaks the canonical vocabulary, so one definition fits any profile."""

    def test_properties_are_canonical_not_real_field_names(
        self, any_generator: FormGenerator, metadata_spec: dict
    ):
        form = any_generator.generate("support_structure")
        # Guarded explicitly: a real field name leaking into a form definition would
        # tie every installation to one customer's schema.
        for real_name in (metadata_spec["code_field"], metadata_spec["material_field"]):
            assert real_name not in form.schema["properties"]
        assert "code" in form.schema["properties"]

    def test_canonical_attributes_are_identical_across_profiles(self):
        """Different schemas in, the same canonical attributes out — the whole point.

        Related tables are excluded from the comparison deliberately: they reflect the
        data model's own structure. cnel-gye has the Puesto/Unidad pattern and the
        synthetic model does not, so a difference there is correct, not a defect.
        """
        from app.model_profile.profile import load_profile
        from app.model_profile.resolver import ModelResolver
        from tests.conftest import build_metadata

        forms = {}
        resolvers = {}
        for profile_id in ("cnel-gye", "alt-synthetic"):
            resolvers[profile_id] = ModelResolver(load_profile(profile_id))
            gen = FormGenerator(resolvers[profile_id], build_metadata(profile_id))
            forms[profile_id] = gen.generate("support_structure")

        def canonical_only(profile_id: str) -> set[str]:
            binding = resolvers[profile_id].binding("support_structure")
            related = {r.as_ for r in binding.related}
            return set(forms[profile_id].schema["properties"]) - related

        assert canonical_only("cnel-gye") == canonical_only("alt-synthetic")
        assert (
            forms["cnel-gye"].schema["properties"]["material"]["enum"]
            == forms["alt-synthetic"].schema["properties"]["material"]["enum"]
        )


class TestDomainsBecomeEnums:
    def test_coded_domain_becomes_enum_with_catalog_ref(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        material = form.schema["properties"]["material"]
        assert material["enum"] == ["concrete", "wood", "steel", "fiberglass", "other"]
        assert material["x-catalog-ref"] == "material.support"

    def test_enum_values_are_canonical_not_domain_codes(self, any_generator: FormGenerator):
        """Domain codes are resolved at write time, never baked into the form."""
        form = any_generator.generate("support_structure")
        material = form.schema["properties"]["material"]
        assert "HORMIGON" not in material["enum"]
        assert "1" not in material["enum"]

    def test_domain_name_is_recorded_for_the_renderer(
        self, generator: FormGenerator, metadata_spec: dict
    ):
        form = generator.generate("support_structure")
        material = form.schema["properties"]["material"]
        assert material["x-domain"] == metadata_spec["material_domain"]

    def test_range_domain_becomes_minimum_and_maximum(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        height = form.schema["properties"]["height_m"]
        assert height["minimum"] == 6.0
        assert height["maximum"] == 20.0


class TestRf304VolatileDomains:
    """Domains that vary per business unit must never be cached as constants."""

    def test_volatile_domain_is_flagged_for_refresh(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        assert form.schema["properties"]["feeder_code"]["x-volatile-catalog"] is True

    def test_stable_domain_is_not_flagged(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        assert "x-volatile-catalog" not in form.schema["properties"]["material"]

    def test_volatile_domain_values_are_not_inlined(self, any_generator: FormGenerator):
        """A feeder list baked into a form would go stale silently in another unit."""
        form = any_generator.generate("support_structure")
        serialised = json.dumps(form.schema)
        assert "04BH070T11" not in serialised


class TestRequiredFields:
    def test_core_field_becomes_required(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        assert "code" in form.schema["required"]
        assert "material" in form.schema["required"]

    def test_non_core_field_is_not_required(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        assert "height_m" not in form.schema["required"]


class TestExcludedFieldCategories:
    """CONNECTIVITY and SYSTEM fields never reach a form (ADR-001)."""

    def test_connectivity_field_is_absent(self, any_generator: FormGenerator):
        from app.model_profile.resolver import NEVER_WRITE_FIELDS

        form = any_generator.generate("support_structure")
        serialised = json.dumps(form.schema)
        for field in NEVER_WRITE_FIELDS:
            assert field not in serialised

    def test_system_field_is_absent(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        assert "AUDIT_USER" not in json.dumps(form.schema)

    def test_only_canonical_attributes_appear(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        canonical = {
            a.key for a in any_generator.resolver.asset_type("support_structure").attributes
        }
        related = {r.as_ for r in any_generator.resolver.binding("support_structure").related}
        assert set(form.schema["properties"]) <= canonical | related


class TestVoiceAndVisionAnnotations:
    """SRS 4.1 — every field declares whether voice and vision can fill it."""

    def test_fields_declare_voice(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        assert form.schema["properties"]["material"]["x-voice"] is True

    def test_vision_capable_type_declares_a_vision_source(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        assert "x-vision-source" in form.schema["properties"]["material"]

    def test_non_vision_type_declares_no_vision_source(self, any_generator: FormGenerator):
        form = any_generator.generate("service_point")
        assert "x-vision-source" not in form.schema["properties"]["code"]


class TestRelationshipsBecomeTables:
    """One-to-many relationships become repeatable tables (the Puesto/Unidad case)."""

    def test_declared_relationship_becomes_a_repeatable_table(self):
        from app.model_profile.profile import load_profile
        from app.model_profile.resolver import ModelResolver
        from tests.conftest import build_metadata

        gen = FormGenerator(ModelResolver(load_profile("cnel-gye")), build_metadata("cnel-gye"))
        form = gen.generate("support_structure")
        table = form.schema["properties"]["pole_structures"]
        assert table["type"] == "array"
        assert table["x-repeatable-table"] is True

    def test_relationship_missing_from_metadata_is_warned_not_dropped(self):
        """A silent omission here would lose data entry the process depends on."""
        from app.model_profile.profile import load_profile
        from app.model_profile.resolver import ModelResolver
        from tests.conftest import build_metadata

        metadata = build_metadata("cnel-gye")
        metadata.relationships.clear()
        gen = FormGenerator(ModelResolver(load_profile("cnel-gye")), metadata)
        form = gen.generate("support_structure")
        assert any("no aparece en los metadatos" in w for w in form.warnings)
        # Still generated, so the administrator can decide.
        assert "pole_structures" in form.schema["properties"]


class TestWarningsSurfaceRealGaps:
    """The generator proposes; warnings are what a human must look at (SRS 0.5)."""

    def test_clean_metadata_produces_no_warnings(self, any_generator: FormGenerator):
        form = any_generator.generate("support_structure")
        assert form.warnings == []
        assert form.requires_review is False

    def test_missing_layer_is_warned(self, generator: FormGenerator):
        generator.metadata.layers.clear()
        form = generator.generate("support_structure")
        assert any("no está en los metadatos" in w for w in form.warnings)
        assert form.requires_review is True

    def test_missing_domain_is_warned(self, generator: FormGenerator, metadata_spec: dict):
        generator.metadata.domains = [
            d for d in generator.metadata.domains if d.name != metadata_spec["material_domain"]
        ]
        form = generator.generate("support_structure")
        assert any("ausente de los metadatos" in w for w in form.warnings)

    def test_unmappable_domain_code_is_warned(self, generator: FormGenerator, metadata_spec: dict):
        """A domain code the profile cannot translate is a real gap, not a rounding error."""
        domain = generator.metadata.domain(metadata_spec["material_domain"])
        domain.coded_values["XXX"] = "Código nuevo sin mapear"
        form = generator.generate("support_structure")
        assert any("sin valor canónico" in w and "XXX" in w for w in form.warnings)

    def test_as_dict_carries_warnings(self, generator: FormGenerator):
        generator.metadata.layers.clear()
        payload = generator.generate("support_structure").as_dict()
        assert payload["warnings"]
        assert payload["asset_type"] == "support_structure"


class TestAllPilotAssetTypesGenerate:
    """The six types in the pilot scope must all generate under both profiles."""

    @pytest.mark.parametrize(
        "asset_type",
        [
            "support_structure",
            "distribution_transformer",
            "street_light",
            "fuse_switch",
            "line_segment",
            "service_point",
        ],
    )
    def test_generates_without_raising(self, any_generator: FormGenerator, asset_type: str):
        form = any_generator.generate(asset_type)
        assert form.schema["properties"]
        assert "code" in form.schema["properties"]
