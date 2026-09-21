"""Vision: taxonomy, prefill and the before/after comparison (I11, RF-140, RF-048).

No model runs here, and that is the point: the predictions are the input, so every path a
real model could take — including the ones that only happen when the model is wrong, stale
or absent — can be exercised deterministically.
"""

from __future__ import annotations

import copy

import pytest

from app.forms.generator import FormGenerator
from app.model_profile.amd import load_asset_model
from app.model_profile.profile import load_profile
from app.model_profile.resolver import ModelResolver
from app.vision.comparator import Verdict, compare
from app.vision.contracts import BoundingBox, ImageAnalysis, Prediction
from app.vision.prefill import prefill_from_analysis
from app.vision.taxonomy import TaxonomyError, load_taxonomy, validate_against_amd
from tests.conftest import ALL_PROFILE_IDS, build_metadata


@pytest.fixture
def taxonomy():
    return load_taxonomy()


@pytest.fixture(params=ALL_PROFILE_IDS)
def pole_schema(request: pytest.FixtureRequest) -> dict:
    """A generated support-structure form, for whichever profile is under test."""
    profile_id = str(request.param)
    resolver = ModelResolver(load_profile(profile_id))
    return FormGenerator(resolver, build_metadata(profile_id)).generate("support_structure").schema


class TestTheTaxonomyIsTiedToTheCanonicalVocabulary:
    def test_the_shipped_taxonomy_reconciles(self, taxonomy) -> None:
        assert validate_against_amd(taxonomy) == []

    def test_every_classifier_value_exists_in_its_enumeration(self, taxonomy) -> None:
        amd = load_asset_model()
        for classifier in taxonomy.attribute_classifiers:
            attribute = amd.asset_type(classifier.asset_type).attribute(classifier.attribute)
            assert attribute is not None and attribute.enum_ref
            canonical = set(amd.enums[attribute.enum_ref])
            assert set(classifier.values.values()) <= canonical

    def test_a_classifier_pointing_at_a_value_that_does_not_exist_is_caught(self, taxonomy) -> None:
        """A value nothing can store would surface as an unexplainable rejection later."""
        broken = copy.deepcopy(taxonomy)
        broken.attribute_classifiers[0].values["bamboo"] = "bamboo"
        problems = validate_against_amd(broken)
        assert any("bamboo" in problem for problem in problems)

    def test_a_classifier_pointing_at_a_missing_attribute_is_caught(self, taxonomy) -> None:
        broken = copy.deepcopy(taxonomy)
        broken.attribute_classifiers[0].attribute = "no_existe"
        assert any("no existe" in problem for problem in validate_against_amd(broken))

    def test_a_resolution_pair_over_an_unknown_class_is_caught(self, taxonomy) -> None:
        broken = copy.deepcopy(taxonomy)
        broken.resolution_pairs[0].before = "clase_inventada"
        assert any("clase_inventada" in problem for problem in validate_against_amd(broken))

    def test_loading_an_incoherent_taxonomy_raises(self, tmp_path) -> None:
        """This one raises rather than reports: starting in that state hides the failure."""
        bad = tmp_path / "vision.yaml"
        bad.write_text(
            "version: 1\ndomain: ground_distribution\n"
            "attribute_classifiers:\n"
            "  - {key: k, label: l, asset_type: no_existe, attribute: material, values: {}}\n",
            encoding="utf-8",
        )
        with pytest.raises(TaxonomyError):
            load_taxonomy(str(bad))

    def test_an_undeclared_class_has_no_threshold_it_can_clear(self, taxonomy) -> None:
        assert taxonomy.threshold("clase_que_nadie_declaro") > 1.0


class TestPrefill:
    def test_rf_140_a_classifier_fills_the_field_that_declares_the_source(
        self, pole_schema, taxonomy
    ) -> None:
        analysis = ImageAnalysis(
            "ev-1",
            (
                Prediction(
                    class_key="concrete",
                    classifier_key="pole_material",
                    confidence=0.91,
                    box=BoundingBox(0.3, 0.2, 0.2, 0.6),
                    model_name="mobilenetv3-pole",
                    model_version="2026.09",
                ),
            ),
        )
        result = prefill_from_analysis(analysis, pole_schema, taxonomy=taxonomy)
        assert result.values == {"material": "concrete"}
        proposal = result.proposals[0]
        assert proposal.evidence_key == "ev-1"
        assert proposal.box is not None
        assert proposal.model_name == "mobilenetv3-pole"

    def test_rf_140_a_low_confidence_prediction_is_dropped_and_said_so(
        self, pole_schema, taxonomy
    ) -> None:
        """Silence would read as "the model saw nothing", which is a different claim."""
        analysis = ImageAnalysis(
            "ev-1",
            (Prediction(class_key="concrete", classifier_key="pole_material", confidence=0.5),),
        )
        result = prefill_from_analysis(analysis, pole_schema, taxonomy=taxonomy)
        assert result.proposals == []
        assert any("umbral" in reason for reason in result.discarded)

    def test_rf_140_thresholds_are_per_class(self, taxonomy) -> None:
        """Lamp technology is hardest of all in daylight, so it demands the most."""
        assert taxonomy.threshold("lamp_technology") > taxonomy.threshold("pole")

    def test_rf_140_a_device_without_models_says_so_instead_of_returning_nothing(
        self, pole_schema, taxonomy
    ) -> None:
        analysis = ImageAnalysis("ev-1", (), models_unavailable=True)
        result = prefill_from_analysis(analysis, pole_schema, taxonomy=taxonomy)
        assert result.proposals == []
        assert any("paquete de modelos" in warning for warning in result.warnings)

    def test_rf_140_a_class_outside_the_taxonomy_is_reported(self, pole_schema, taxonomy) -> None:
        """It means the phone runs a model version the platform does not know."""
        analysis = ImageAnalysis("ev-1", (Prediction(class_key="dron", confidence=0.99),))
        result = prefill_from_analysis(analysis, pole_schema, taxonomy=taxonomy)
        assert any("taxonomía" in warning for warning in result.warnings)

    def test_rf_140_a_classifier_label_with_no_canonical_value_is_reported(
        self, pole_schema, taxonomy
    ) -> None:
        analysis = ImageAnalysis(
            "ev-1",
            (Prediction(class_key="bamboo", classifier_key="pole_material", confidence=0.95),),
        )
        result = prefill_from_analysis(analysis, pole_schema, taxonomy=taxonomy)
        assert result.proposals == []
        assert any("desalineados" in warning for warning in result.warnings)

    def test_rf_140_a_field_the_form_does_not_ask_for_is_silently_skipped(self, taxonomy) -> None:
        """A maintenance form may simply not ask for the material. That is not a problem."""
        analysis = ImageAnalysis(
            "ev-1",
            (Prediction(class_key="concrete", classifier_key="pole_material", confidence=0.95),),
        )
        result = prefill_from_analysis(analysis, {"properties": {}}, taxonomy=taxonomy)
        assert result.proposals == []
        assert result.warnings == []

    def test_rf_140_findings_are_not_field_values(self, pole_schema, taxonomy) -> None:
        analysis = ImageAnalysis("ev-1", (Prediction(class_key="leaning_pole", confidence=0.85),))
        result = prefill_from_analysis(analysis, pole_schema, taxonomy=taxonomy)
        assert result.proposals == []
        assert [finding.key for finding in result.findings] == ["leaning_pole"]
        assert result.findings[0].severity == "alta"


class TestBoundingBoxes:
    def test_a_box_outside_the_image_is_refused(self) -> None:
        with pytest.raises(ValueError, match="fuera de"):
            BoundingBox(0.1, 0.1, 1.5, 0.2)

    def test_a_confidence_outside_zero_to_one_is_refused(self) -> None:
        with pytest.raises(ValueError, match="confianza"):
            Prediction(class_key="pole", confidence=1.4)


class TestBeforeAndAfter:
    def test_rf_048_a_declared_pair_supports_the_closure(self, taxonomy) -> None:
        before = ImageAnalysis("a", (Prediction(class_key="lamp_out", confidence=0.9),))
        after = ImageAnalysis("b", (Prediction(class_key="lamp_lit", confidence=0.92),))
        comparison = compare(before, after, taxonomy=taxonomy)
        assert comparison.verdict is Verdict.RESOLVED
        assert comparison.supports_closure

    def test_rf_048_a_finding_still_visible_does_not(self, taxonomy) -> None:
        before = ImageAnalysis("a", (Prediction(class_key="lamp_out", confidence=0.9),))
        after = ImageAnalysis("b", (Prediction(class_key="lamp_out", confidence=0.88),))
        comparison = compare(before, after, taxonomy=taxonomy)
        assert comparison.verdict is Verdict.UNCHANGED
        assert not comparison.supports_closure

    def test_rf_048_one_unresolved_finding_outweighs_a_resolved_one(self, taxonomy) -> None:
        """The unresolved one is the reason somebody has to go back."""
        before = ImageAnalysis(
            "a",
            (
                Prediction(class_key="lamp_out", confidence=0.9),
                Prediction(class_key="corrosion", confidence=0.8),
            ),
        )
        after = ImageAnalysis(
            "b",
            (
                Prediction(class_key="lamp_lit", confidence=0.9),
                Prediction(class_key="corrosion", confidence=0.82),
            ),
        )
        assert compare(before, after, taxonomy=taxonomy).verdict is Verdict.UNCHANGED

    def test_rf_048_the_same_file_twice_is_caught_without_a_model(self, taxonomy) -> None:
        before = ImageAnalysis("a", (Prediction(class_key="lamp_out", confidence=0.9),))
        after = ImageAnalysis("b", (Prediction(class_key="lamp_lit", confidence=0.9),))
        comparison = compare(before, after, taxonomy=taxonomy, before_hash="abc", after_hash="abc")
        assert comparison.identical_evidence
        assert comparison.verdict is Verdict.INCONCLUSIVE
        assert not comparison.supports_closure
        assert any("mismo archivo" in warning for warning in comparison.warnings)

    def test_rf_048_a_finding_that_merely_disappears_is_not_a_resolution(self, taxonomy) -> None:
        """It can disappear because the second photograph was taken from further away."""
        before = ImageAnalysis("a", (Prediction(class_key="corrosion", confidence=0.85),))
        after = ImageAnalysis("b", (Prediction(class_key="pole", confidence=0.9),))
        comparison = compare(before, after, taxonomy=taxonomy)
        assert comparison.verdict is Verdict.INCONCLUSIVE
        assert not comparison.supports_closure

    def test_rf_048_something_new_in_the_after_photo_is_surfaced(self, taxonomy) -> None:
        before = ImageAnalysis("a", (Prediction(class_key="pole", confidence=0.9),))
        after = ImageAnalysis("b", (Prediction(class_key="broken_insulator", confidence=0.88),))
        comparison = compare(before, after, taxonomy=taxonomy)
        assert comparison.verdict is Verdict.NEW_FINDING

    def test_rf_048_a_neutral_class_is_not_a_new_problem(self, taxonomy) -> None:
        before = ImageAnalysis("a", (Prediction(class_key="pole", confidence=0.9),))
        after = ImageAnalysis("b", (Prediction(class_key="lamp_lit", confidence=0.9),))
        assert compare(before, after, taxonomy=taxonomy).verdict is Verdict.INCONCLUSIVE

    def test_rf_048_an_unanalysed_photograph_is_inconclusive_not_clean(self, taxonomy) -> None:
        before = ImageAnalysis("a", (Prediction(class_key="lamp_out", confidence=0.9),))
        after = ImageAnalysis("b", (), models_unavailable=True)
        comparison = compare(before, after, taxonomy=taxonomy)
        assert comparison.verdict is Verdict.INCONCLUSIVE
        assert any("no se analizó" in warning for warning in comparison.warnings)
