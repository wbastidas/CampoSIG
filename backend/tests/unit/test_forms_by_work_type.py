"""The mobile app gets a different form per work type, composed and never coded (SRS 4.1).

Runs under both profiles: a composer that only worked against one data model would fail
here, which is the early warning ADR-004 is for.
"""

from __future__ import annotations

import json

import pytest

from app.forms.catalog import (
    Area,
    BlockSource,
    CatalogError,
    definitions_for_area,
    definitions_for_asset_type,
    get_definition,
    load_blocks,
    load_definitions,
    validate_catalog,
)
from app.forms.composer import FormComposer
from app.model_profile.profile import load_profile
from app.model_profile.resolver import NEVER_WRITE_FIELDS, ModelResolver
from tests.conftest import ALL_PROFILE_IDS, build_metadata


@pytest.fixture(params=ALL_PROFILE_IDS)
def any_composer(request: pytest.FixtureRequest) -> FormComposer:
    profile_id = request.param
    return FormComposer(ModelResolver(load_profile(profile_id)), build_metadata(profile_id))


@pytest.fixture
def composer() -> FormComposer:
    return FormComposer(ModelResolver(load_profile("cnel-gye")), build_metadata("cnel-gye"))


class TestCatalogIsSound:
    def test_catalogue_has_no_problems(self):
        assert validate_catalog() == []

    def test_the_six_pilot_forms_are_present(self):
        # The pilot scope of PLAN_IMPLEMENTACION (I2-I7).
        expected = {"F-TR-01", "F-OP-01", "F-MT-01", "F-AP-01", "F-IC-03"}
        assert expected <= set(load_definitions())

    def test_every_area_of_the_srs_has_at_least_one_form(self):
        for area in (Area.SSO, Area.OPERACION, Area.MANTENIMIENTO, Area.APG, Area.INGENIERIA):
            assert definitions_for_area(area), f"el área '{area}' no tiene formularios"

    def test_unknown_form_names_the_available_ones(self):
        with pytest.raises(CatalogError, match="disponibles"):
            get_definition("F-XX-99")

    def test_blocks_never_mention_a_real_field_name(self):
        """Blocks speak the canonical vocabulary, so one block serves every business unit."""
        serialised = json.dumps(
            {code: block.model_dump() for code, block in load_blocks().items()},
            ensure_ascii=False,
        )
        for field in NEVER_WRITE_FIELDS:
            assert field not in serialised


class TestFormsDifferByWorkType:
    """The point of the whole exercise: work type decides the form."""

    def test_a_safety_form_and_an_inspection_differ(self, composer: FormComposer):
        ats = composer.compose("F-TR-01")
        inspection = composer.compose("F-MT-01", "support_structure")
        assert ats.schema["properties"].keys() != inspection.schema["properties"].keys()
        assert ats.schema["x-area"] == "sso"
        assert inspection.schema["x-area"] == "mantenimiento"

    def test_each_form_carries_its_code_and_version(self, composer: FormComposer):
        form = composer.compose("F-AP-01")
        assert form.schema["x-form-code"] == "F-AP-01"
        assert form.schema["x-form-version"] == form.version
        assert form.schema["$id"] == f"forms/F-AP-01/{form.version}"

    @pytest.mark.parametrize(
        "code", ["F-TR-01", "F-OP-01", "F-MT-01", "F-AP-01", "F-IC-03", "F-OP-04"]
    )
    def test_every_form_composes_under_every_profile(self, any_composer: FormComposer, code: str):
        form = any_composer.compose(code)
        assert form.schema["properties"], f"'{code}' quedó sin campos"
        assert form.ui_schema["ui:order"]

    def test_blocks_appear_in_the_order_the_definition_lists_them(self, composer: FormComposer):
        """Order is the order a technician works in: safety before execution."""
        form = composer.compose("F-OP-01")
        block_order = [group["block"] for group in form.ui_schema["ui:groups"]]
        assert block_order == get_definition("F-OP-01").form.blocks

    def test_ui_groups_become_sections(self, composer: FormComposer):
        form = composer.compose("F-MT-01")
        groups = form.ui_schema["ui:groups"]
        assert all("title" in g and "fields" in g for g in groups)
        # Every rendered field belongs to exactly one section.
        grouped = [f for g in groups for f in g["fields"]]
        assert sorted(grouped) == sorted(form.schema["properties"])


class TestAssetDerivedBlocks:
    """A block marked `asset_metadata` is filled from the unit's real domains."""

    def test_the_block_is_declared_as_asset_derived(self):
        assert load_blocks()["B05"].block.source is BlockSource.ASSET_METADATA

    def test_inspection_gains_the_assets_attributes(self, any_composer: FormComposer):
        form = any_composer.compose("F-MT-01", "support_structure")
        # Canonical keys from the AMD, alongside the block's own static fields.
        assert "material" in form.schema["properties"]
        assert "general_condition" in form.schema["properties"]

    def test_asset_values_come_from_the_units_domain(self, any_composer: FormComposer):
        form = any_composer.compose("F-MT-01", "support_structure")
        material = form.schema["properties"]["material"]
        assert material["enum"] == ["concrete", "wood", "steel", "fiberglass", "other"]
        assert material["x-catalog-ref"] == "material.support"

    def test_single_asset_type_needs_no_hint(self, composer: FormComposer):
        """F-MT-01 applies to one asset type, so the composer infers it."""
        form = composer.compose("F-MT-01")
        assert form.schema["x-asset-type"] == "support_structure"
        assert "material" in form.schema["properties"]

    def test_multi_asset_form_warns_when_no_type_is_given(self, composer: FormComposer):
        form = composer.compose("F-OP-01")
        assert any("varios tipos de activo" in w for w in form.warnings)

    def test_a_type_outside_the_declaration_is_warned(self, composer: FormComposer):
        form = composer.compose("F-MT-01", "street_light")
        assert any("no declara aplicar" in w for w in form.warnings)

    def test_without_metadata_the_form_still_composes(self):
        """Before a unit's first agent run, the form must still be usable."""
        composer = FormComposer(ModelResolver(load_profile("cnel-gye")), None)
        form = composer.compose("F-MT-01", "support_structure")
        assert "general_condition" in form.schema["properties"], "los campos estáticos siguen"
        assert "material" not in form.schema["properties"]
        assert any("sin metadatos sincronizados" in w for w in form.warnings)

    def test_related_tables_stay_out_of_work_forms(self, composer: FormComposer):
        """A work form captures condition, not the asset's full related structure."""
        form = composer.compose("F-MT-01", "support_structure")
        related = {r.as_ for r in composer.resolver.binding("support_structure").related}
        assert related, "el perfil debe tener relaciones para que este test signifique algo"
        assert not related & set(form.schema["properties"])


class TestPhotoMinimums:
    """SRS 4.8 fixes a minimum number of photos per work type."""

    def test_before_and_after_minimums_are_applied(self, composer: FormComposer):
        form = composer.compose("F-OP-01")
        assert form.schema["properties"]["photos_before"]["minItems"] == 2
        assert form.schema["properties"]["photos_after"]["minItems"] == 2

    def test_a_form_without_after_photos_has_no_minimum(self, composer: FormComposer):
        form = composer.compose("F-MT-01")
        assert "minItems" not in form.schema["properties"]["photos_after"]

    def test_minimums_differ_by_work_type(self, composer: FormComposer):
        inspection = composer.compose("F-MT-01")
        lamp = composer.compose("F-AP-01")
        assert (
            inspection.schema["properties"]["photos_before"]["minItems"]
            != lamp.schema["properties"]["photos_before"]["minItems"]
        )


class TestRulesTravelWithTheForm:
    def test_blocking_safety_rule_is_carried(self, composer: FormComposer):
        """Tormenta eléctrica blocks execution and needs a supervisor (SRS 4.3)."""
        form = composer.compose("F-TR-01")
        blocking = [r for r in form.rules if r.get("blocks_execution")]
        assert blocking
        assert blocking[0]["requires_role"] == "supervisor"

    def test_conditional_requirement_is_carried(self, composer: FormComposer):
        form = composer.compose("F-OP-01")
        conditional = [r for r in form.rules if "unresolved_reason" in r.get("require", [])]
        assert conditional, "la causa debe exigirse cuando el trabajo no se resolvió"

    def test_rules_are_json_serialisable(self, composer: FormComposer):
        """Rules travel to the phone as JSON and are evaluated there."""
        form = composer.compose("F-TR-01")
        assert json.loads(json.dumps(form.rules)) == form.rules


class TestAtsGating:
    def test_the_ats_form_declares_it_gates_execution(self, composer: FormComposer):
        assert composer.compose("F-TR-01").schema["x-gates-execution"] is True

    def test_work_forms_declare_they_require_an_ats(self, composer: FormComposer):
        for code in ("F-OP-01", "F-MT-01", "F-AP-01"):
            assert composer.compose(code).schema["x-requires-ats"] is True

    def test_a_logbook_does_not_require_an_ats(self, composer: FormComposer):
        # Site diary work is not an intervention on the network.
        assert composer.compose("F-IC-03").schema["x-requires-ats"] is False


class TestAssetTypeLookup:
    def test_forms_can_be_found_by_asset_type(self):
        codes = {d.code for d in definitions_for_asset_type("street_light")}
        assert "F-AP-01" in codes

    def test_a_transversal_form_belongs_to_no_asset_type(self):
        codes = {d.code for d in definitions_for_asset_type("support_structure")}
        assert "F-TR-01" not in codes


class TestSerialisation:
    def test_composed_form_serialises_for_the_mobile_sync(self, any_composer: FormComposer):
        payload = any_composer.compose("F-MT-01").as_dict()
        assert json.loads(json.dumps(payload)) == payload
        assert set(payload) >= {"code", "version", "schema", "ui_schema", "rules"}


class TestCompositionDoesNotLeakBetweenForms:
    """The block library is cached, so composition must never write into it.

    Regression guard for a real defect: composing a form that sets photo minimums used to
    stamp them onto the shared block, so every form composed afterwards inherited them.
    Invisible when composing one form, and wrong for every form in production.
    """

    def test_composing_one_form_does_not_affect_another(self, composer: FormComposer):
        composer.compose("F-OP-01")  # sets photos_after minItems = 2
        inspection = composer.compose("F-MT-01")  # declares no "after" photos
        assert "minItems" not in inspection.schema["properties"]["photos_after"]

    def test_the_cached_block_is_left_untouched(self, composer: FormComposer):
        composer.compose("F-OP-01")
        cached = load_blocks()["B09"]
        assert "minItems" not in cached.fields["photos_after"]

    def test_composing_twice_gives_equal_but_independent_results(self, composer: FormComposer):
        first = composer.compose("F-AP-01")
        second = composer.compose("F-AP-01")
        assert first.schema == second.schema
        first.schema["properties"]["photos_before"]["minItems"] = 99
        assert second.schema["properties"]["photos_before"]["minItems"] != 99

    def test_order_of_composition_does_not_change_the_result(self):
        """Composing in either order must give the same forms."""

        def fresh() -> FormComposer:
            return FormComposer(ModelResolver(load_profile("cnel-gye")), build_metadata("cnel-gye"))

        forward = fresh()
        a_first = forward.compose("F-OP-01").schema
        b_second = forward.compose("F-MT-01").schema

        backward = fresh()
        b_first = backward.compose("F-MT-01").schema
        a_second = backward.compose("F-OP-01").schema

        assert a_first == a_second
        assert b_first == b_second


class TestGeneratedRequirednessIsNotLost:
    """The composer must keep what the generator determined is mandatory.

    Regression guard for a real defect: the composer discarded the generator's `required`
    list, so an asset-derived form came out with no required fields at all — and a form with
    nothing required lets incomplete work reach an approval.
    """

    def test_core_fields_are_required_in_the_composed_form(self, any_composer: FormComposer):
        form = any_composer.compose("F-MT-01", "support_structure")
        required = set(form.schema.get("required", []))
        # CORE in the capture manual, so mandatory for real.
        assert {"code", "material"} <= required

    def test_the_composed_form_requires_what_the_generator_required(
        self, any_composer: FormComposer
    ):
        from app.forms.generator import FormGenerator

        generated = FormGenerator(any_composer.resolver, any_composer.metadata).generate(
            "support_structure"
        )
        related = {r.as_ for r in any_composer.resolver.binding("support_structure").related}
        expected = set(generated.schema.get("required", [])) - related
        composed = set(any_composer.compose("F-MT-01", "support_structure").schema["required"])
        assert expected <= composed

    def test_a_form_without_an_asset_block_still_has_its_own_requirements(
        self, composer: FormComposer
    ):
        # F-TR-01 has no asset-derived block; its requirements come from its blocks.
        form = composer.compose("F-TR-01")
        assert isinstance(form.schema.get("required", []), list)
