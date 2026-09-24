"""The criticality matrix of Annex C (RF-013).

    Criticidad = Severidad del defecto (1 a 5) por Consecuencia (1 a 5)

with «un ajuste por exposición (zona urbana o escolar, vía principal: +1 nivel)» and the bands
20 o más → P1, de 12 a 19 → P2, de 6 a 11 → P3, 5 o menos → P4.

The arithmetic is the easy half. What these tests protect is the honesty of the number: a priority
whose inputs were defaults has to *look* different from one whose inputs were known, because a
supervisor who cannot tell them apart will stop trusting the tray — and then the whole requirement
is decoration.
"""

from __future__ import annotations

import pytest

from app.proposals.criticality import (
    ANNEX_LABEL,
    DEFAULT_CONSEQUENCE,
    DEFAULT_SEVERITY,
    compute,
    priority_for,
    suggested_deadline_hours,
)
from app.workorders.models import Priority


class TestTheBands:
    @pytest.mark.parametrize(
        ("score", "priority"),
        [
            (25, Priority.CRITICAL.value),
            (20, Priority.CRITICAL.value),
            (19, Priority.HIGH.value),
            (12, Priority.HIGH.value),
            (11, Priority.MEDIUM.value),
            (6, Priority.MEDIUM.value),
            (5, Priority.LOW.value),
            (1, Priority.LOW.value),
        ],
    )
    def test_the_annex_bands_are_respected_at_their_edges(self, score: int, priority: str):
        assert priority_for(score) == priority

    def test_every_priority_has_its_annex_label(self):
        """The areas speak in P-numbers and the platform stores its own enum."""
        assert set(ANNEX_LABEL) == {item.value for item in Priority}


class TestTheArithmetic:
    def test_severity_times_consequence(self):
        found = compute(
            defect_attributes={"severity": 5},
            asset_attributes={"consequence": 4},
        )
        assert (found.severity, found.consequence, found.score) == (5, 4, 20)
        assert found.priority == Priority.CRITICAL.value
        assert found.annex_band == "P1"

    def test_the_explanation_shows_the_arithmetic(self):
        """So a supervisor can redo it rather than take it."""
        found = compute(defect_attributes={"severity": 3}, asset_attributes={"consequence": 4})
        assert "severidad 3" in found.explain()
        assert "= 12" in found.explain()
        assert "P2" in found.explain()

    def test_exposure_raises_the_consequence_by_one_level(self):
        plain = compute(defect_attributes={"severity": 4}, asset_attributes={"consequence": 3})
        exposed = compute(
            defect_attributes={"severity": 4}, asset_attributes={"consequence": 3}, exposed=True
        )
        assert plain.consequence == 3
        assert exposed.consequence == 4
        assert exposed.score > plain.score
        assert exposed.exposed is True
        assert "exposición" in exposed.explain()

    def test_exposure_cannot_push_a_factor_past_five(self):
        """«+1 nivel» on a scale that ends at five."""
        found = compute(
            defect_attributes={"severity": 5}, asset_attributes={"consequence": 5}, exposed=True
        )
        assert found.consequence == 5
        assert found.score == 25

    def test_the_adjustment_applies_to_the_consequence_and_not_to_the_score(self):
        """The annex says «nivel». Adding to the score would move a P3 to P1 in one step."""
        found = compute(
            defect_attributes={"severity": 2}, asset_attributes={"consequence": 3}, exposed=True
        )
        assert found.score == 2 * 4


class TestWhatItCouldNotKnow:
    def test_a_defect_with_no_severity_says_so_and_uses_the_default(self):
        found = compute(
            defect_attributes={}, asset_attributes={"consequence": 3}, defect_code="raro"
        )
        assert found.severity == DEFAULT_SEVERITY
        assert found.is_estimated is True
        assert any("raro" in line and "severidad" in line for line in found.caveats)

    def test_an_asset_type_with_no_consequence_says_so(self):
        found = compute(
            defect_attributes={"severity": 4},
            asset_attributes=None,
            asset_type_key="algo_nuevo",
        )
        assert found.consequence == DEFAULT_CONSEQUENCE
        assert any("algo_nuevo" in line for line in found.caveats)

    def test_the_catalogues_own_caveat_travels_with_the_number(self):
        """«Se asume ramal de media tensión» has to reach the supervisor, or a 4 reads as a
        measurement."""
        found = compute(
            defect_attributes={"severity": 5},
            asset_attributes={"consequence": 4, "caveat": "Se asume ramal de media tensión"},
        )
        assert found.caveats == ["Se asume ramal de media tensión"]
        assert found.is_estimated is True

    def test_a_fully_known_computation_carries_no_caveats(self):
        found = compute(defect_attributes={"severity": 4}, asset_attributes={"consequence": 3})
        assert found.caveats == []
        assert found.is_estimated is False

    def test_a_severity_outside_the_scale_is_treated_as_missing(self):
        """A hand-edited `severity: 9` would score 45 and flood the tray with emergencies."""
        found = compute(defect_attributes={"severity": 9}, asset_attributes={"consequence": 3})
        assert found.severity == DEFAULT_SEVERITY
        assert found.is_estimated is True

    def test_a_zero_or_negative_level_is_treated_as_missing(self):
        assert compute(defect_attributes={"severity": 0}, asset_attributes={}).severity == (
            DEFAULT_SEVERITY
        )
        assert compute(defect_attributes={"severity": -2}, asset_attributes={}).severity == (
            DEFAULT_SEVERITY
        )

    def test_a_boolean_is_not_a_level(self):
        """True is 1 in Python and would score as a severity of one."""
        assert compute(defect_attributes={"severity": True}, asset_attributes={}).severity == (
            DEFAULT_SEVERITY
        )

    def test_a_string_level_is_treated_as_missing(self):
        assert compute(defect_attributes={"severity": "5"}, asset_attributes={}).severity == (
            DEFAULT_SEVERITY
        )

    def test_the_payload_carries_everything_a_screen_needs(self):
        found = compute(
            defect_attributes={"severity": 5},
            asset_attributes={"consequence": 4, "caveat": "ojo"},
            exposed=True,
        )
        payload = found.as_dict()
        assert payload["annex_band"] == "P1"
        assert payload["estimated"] is True
        assert payload["caveats"] == ["ojo"]
        assert "severidad 5" in payload["explanation"]


class TestTheDeadline:
    def test_the_hours_come_from_the_priority_catalogue(self):
        assert suggested_deadline_hours({"sla_hours": 72}) == 72

    def test_p1_is_immediate_and_that_is_zero_hours_not_none(self):
        assert suggested_deadline_hours({"sla_hours": 0}) == 0

    def test_p4_has_no_deadline_and_that_is_a_real_answer(self):
        """The annex says «plan de mantenimiento», which is not a deadline. Inventing hours would
        put maintenance work on a clock nobody agreed to."""
        assert suggested_deadline_hours({"annex_c": "P4"}) is None
        assert suggested_deadline_hours(None) is None

    def test_a_nonsense_value_is_no_deadline_rather_than_a_wrong_one(self):
        assert suggested_deadline_hours({"sla_hours": "72"}) is None
        assert suggested_deadline_hours({"sla_hours": -5}) is None
