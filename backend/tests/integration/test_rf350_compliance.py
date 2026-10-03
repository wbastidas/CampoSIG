"""Cumplimiento normativo determinista (ADR-007, RF-350, RF-351).

El sentido de este módulo es que un veredicto de cumplimiento sea **verificable**: sale de
una comparación aritmética contra un valor con vigencia y referencia a la norma. Así que los
tests se concentran en las tres formas en que eso se rompe —un hecho ausente tomado por
cumplimiento, un límite ausente tomado por cumplimiento, y una cifra sin verificar citada
como si viniera del texto oficial— y en que un expediente viejo siga explicándose con el
límite que regía entonces.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.gis_gateway.ingest import ingest_metadata
from app.org.models import BusinessUnit, Organization
from app.regulatory import rules as compliance
from app.regulatory.facts import facts_from
from app.regulatory.loader import apply_seed, load_seed, unverified_codes
from app.regulatory.rules import Facts, Outcome, Severity
from app.regulatory.service import (
    OverlappingPeriodError,
    UnknownParameterError,
    UnverifiedParameterError,
    history,
    parameter_in_force,
    set_parameter,
    value_in_force,
)
from app.responses.service import save_answers
from app.review.service import approval_blockers, compliance_findings
from app.workorders.models import WorkOrderState
from app.workorders.service import create_work_order
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

NORM = "Regulación de prueba"


@pytest.fixture
def unit(session: Session) -> BusinessUnit:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created = BusinessUnit(
        organization_id=org.id, code="GYE", name="Unidad Guayaquil", profile_id="cnel-gye"
    )
    session.add(created)
    session.flush()
    ingest_metadata(session, created, build_metadata("cnel-gye"))
    return created


class TestPeriodsOfForce:
    def test_rf_350_a_new_resolution_closes_the_previous_period(self, session) -> None:
        """Una aprobación de marzo tiene que seguir explicándose con el límite de marzo."""
        set_parameter(
            session,
            code="apg.max_restoration_hours",
            value=72,
            norm_ref=NORM,
            effective_from=date(2025, 1, 1),
            verified_by="analista.1",
        )
        set_parameter(
            session,
            code="apg.max_restoration_hours",
            value=48,
            norm_ref=NORM,
            effective_from=date(2026, 1, 1),
            verified_by="analista.1",
        )

        periods = history(session, "apg.max_restoration_hours")
        assert len(periods) == 2
        assert periods[0].effective_to == date(2025, 12, 31)
        assert periods[1].effective_to is None

        assert value_in_force(session, "apg.max_restoration_hours", on=date(2025, 6, 1)) == 72
        assert value_in_force(session, "apg.max_restoration_hours", on=date(2026, 6, 1)) == 48

    def test_rf_350_correcting_the_same_resolution_updates_it(self, session) -> None:
        set_parameter(session, code="x.y", value=10, norm_ref=NORM, effective_from=date(2026, 1, 1))
        set_parameter(session, code="x.y", value=11, norm_ref=NORM, effective_from=date(2026, 1, 1))
        assert len(history(session, "x.y")) == 1
        assert value_in_force(session, "x.y", on=date(2026, 5, 1)) == 11

    def test_rf_350_an_overlap_is_refused_rather_than_resolved(self, session) -> None:
        """Dos límites vigentes el mismo día significa una importación mal hecha."""
        set_parameter(
            session,
            code="x.y",
            value=10,
            norm_ref=NORM,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        with pytest.raises(OverlappingPeriodError):
            set_parameter(
                session, code="x.y", value=20, norm_ref=NORM, effective_from=date(2026, 6, 1)
            )

    def test_rf_350_a_date_nothing_covers_is_an_error_not_a_default(self, session) -> None:
        set_parameter(session, code="x.y", value=10, norm_ref=NORM, effective_from=date(2026, 1, 1))
        with pytest.raises(UnknownParameterError):
            parameter_in_force(session, "x.y", on=date(2025, 1, 1))

    def test_rf_350_a_strict_unverified_limit_is_not_evaluated(self, session) -> None:
        """Un riesgo para las personas no se juzga con una cifra que nadie leyó."""
        set_parameter(
            session,
            code="grounding.max_resistance_ohm",
            value=25,
            norm_ref=NORM,
            effective_from=date(2026, 1, 1),
            strict=True,
        )
        with pytest.raises(UnverifiedParameterError):
            parameter_in_force(session, "grounding.max_resistance_ohm", on=date(2026, 6, 1))


class TestTheRulesCompare:
    def test_rf_350_a_restoration_inside_the_deadline_complies(self, session) -> None:
        set_parameter(
            session,
            code="apg.max_restoration_hours",
            value=48,
            unit="h",
            norm_ref=NORM,
            article_ref="Art. 12",
            effective_from=date(2026, 1, 1),
            verified_by="analista.1",
        )
        reported = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)
        facts = Facts(
            reported_at=reported,
            restored_at=reported + timedelta(hours=30),
            evaluated_on=date(2026, 6, 2),
        )
        finding = compliance.ApgRestorationRule().evaluate(session, facts)
        assert finding.outcome is Outcome.COMPLIES
        assert finding.measured == 30.0
        assert finding.limit == 48.0
        assert finding.norm_ref == NORM
        assert finding.article_ref == "Art. 12"
        assert finding.limit_verified
        assert not finding.blocking

    def test_rf_350_a_late_restoration_breaches_and_blocks(self, session) -> None:
        set_parameter(
            session,
            code="apg.max_restoration_hours",
            value=48,
            norm_ref=NORM,
            effective_from=date(2026, 1, 1),
            verified_by="analista.1",
        )
        reported = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)
        finding = compliance.ApgRestorationRule().evaluate(
            session,
            Facts(
                reported_at=reported,
                restored_at=reported + timedelta(hours=72),
                evaluated_on=date(2026, 6, 4),
            ),
        )
        assert finding.outcome is Outcome.BREACHES
        assert finding.severity is Severity.HIGH
        assert finding.blocking

    def test_rf_350_a_zone_keyed_limit_wins_over_the_default(self, session) -> None:
        for code, value in (
            ("apg.max_restoration_hours", 96),
            ("apg.max_restoration_hours.urbano", 48),
        ):
            set_parameter(
                session,
                code=code,
                value=value,
                norm_ref=NORM,
                effective_from=date(2026, 1, 1),
                verified_by="analista.1",
            )
        reported = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)
        facts = Facts(
            reported_at=reported,
            restored_at=reported + timedelta(hours=72),
            zone_class="urbano",
            evaluated_on=date(2026, 6, 4),
        )
        finding = compliance.ApgRestorationRule().evaluate(session, facts)
        assert finding.limit == 48.0
        assert finding.outcome is Outcome.BREACHES

    def test_rf_350_without_a_zone_the_unkeyed_limit_applies(self, session) -> None:
        """La plataforma no reporta un incumplimiento por no saber si la zona es urbana."""
        for code, value in (
            ("apg.max_restoration_hours", 96),
            ("apg.max_restoration_hours.urbano", 48),
        ):
            set_parameter(
                session,
                code=code,
                value=value,
                norm_ref=NORM,
                effective_from=date(2026, 1, 1),
                verified_by="analista.1",
            )
        reported = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)
        finding = compliance.ApgRestorationRule().evaluate(
            session,
            Facts(
                reported_at=reported,
                restored_at=reported + timedelta(hours=72),
                evaluated_on=date(2026, 6, 4),
            ),
        )
        assert finding.limit == 96.0
        assert finding.outcome is Outcome.COMPLIES

    def test_rf_350_a_missing_fact_is_not_a_pass(self, session) -> None:
        finding = compliance.EarthResistanceRule().evaluate(session, Facts())
        assert finding.outcome is Outcome.NOT_APPLICABLE
        assert not finding.blocking
        assert "no registra" in finding.message

    def test_rf_350_a_missing_limit_is_not_a_pass_either(self, session) -> None:
        finding = compliance.EarthResistanceRule().evaluate(
            session, Facts(earth_resistance_ohm=30.0, evaluated_on=date(2026, 6, 1))
        )
        assert finding.outcome is Outcome.UNDETERMINED
        assert "no hay un límite vigente" in finding.message
        # No bloquea: el parámetro que falta es una omisión de la oficina, no de la cuadrilla.
        assert not finding.blocking

    def test_rf_350_an_unverified_limit_gives_a_provisional_verdict(self, session) -> None:
        set_parameter(
            session,
            code="grounding.max_resistance_ohm",
            value=25,
            norm_ref=NORM,
            effective_from=date(2026, 1, 1),
        )
        finding = compliance.EarthResistanceRule().evaluate(
            session, Facts(earth_resistance_ohm=40.0, evaluated_on=date(2026, 6, 1))
        )
        assert finding.outcome is Outcome.BREACHES
        assert finding.limit_verified is False
        # La comparación vale; la cita no. Así que no bloquea una aprobación.
        assert not finding.blocking

    def test_rf_351_a_short_interruption_is_classified_not_condemned(self, session) -> None:
        set_parameter(
            session,
            code="interruption.non_computable_seconds",
            value=180,
            unit="s",
            norm_ref=NORM,
            effective_from=date(2026, 1, 1),
            verified_by="analista.1",
        )
        short = compliance.NonComputableInterruptionRule().evaluate(
            session, Facts(interruption_seconds=120, evaluated_on=date(2026, 6, 1))
        )
        assert short.outcome is Outcome.COMPLIES
        assert "no computable" in short.message

        long = compliance.NonComputableInterruptionRule().evaluate(
            session, Facts(interruption_seconds=600, evaluated_on=date(2026, 6, 1))
        )
        assert "computable" in long.message and "no computable" not in long.message

    def test_rf_350_evaluate_keeps_the_rules_that_did_not_apply(self, session) -> None:
        """Ver que la plataforma miró y no encontró nada es distinto de que no mirara."""
        findings = compliance.evaluate(session, Facts(evaluated_on=date(2026, 6, 1)))
        assert len(findings) == len(compliance.RULES)
        assert all(f.outcome is Outcome.NOT_APPLICABLE for f in findings)


class TestFactsComeFromTheCapture:
    def test_rf_350_facts_are_read_from_the_answers(self, session, unit) -> None:
        order = create_work_order(
            session,
            unit,
            work_type="atencion_falla",
            form_code="F-OP-01",
            asset_type_key="support_structure",
            longitude=-79.9,
            latitude=-2.17,
            zone="Urbano",
        )
        facts = facts_from(
            order,
            {
                "claim_at": "2026-06-01T08:00:00Z",
                "restored_at": "2026-06-01T20:30:00Z",
                "earth_resistance_ohm": 18.5,
                "grounding_context": "Poste",
                "interruption_seconds": "240",
            },
        )
        assert facts.reported_at == datetime(2026, 6, 1, 8, 0, tzinfo=UTC)
        assert facts.earth_resistance_ohm == 18.5
        assert facts.grounding_context == "poste"
        assert facts.interruption_seconds == 240.0
        assert facts.zone_class == "urbano"
        # La fecha de evaluación es la de la reposición, no hoy: así el veredicto es estable.
        assert facts.evaluated_on == date(2026, 6, 1)

    def test_rf_350_a_malformed_timestamp_is_a_missing_fact_not_a_zero(self, session, unit) -> None:
        order = create_work_order(
            session,
            unit,
            work_type="atencion_falla",
            form_code="F-OP-01",
            asset_type_key="support_structure",
            longitude=-79.9,
            latitude=-2.17,
        )
        facts = facts_from(order, {"claim_at": "ayer por la tarde", "restored_at": None})
        assert facts.reported_at is None
        assert facts.restored_at is None


class TestApprovalUsesTheFindings:
    @pytest.fixture
    def order(self, session, unit):
        created = create_work_order(
            session,
            unit,
            work_type="atencion_falla",
            form_code="F-OP-01",
            asset_type_key="support_structure",
            longitude=-79.9,
            latitude=-2.17,
            zone="Urbano",
        )
        created.state = WorkOrderState.SYNCED
        created.form_version = "1.0.0"
        session.flush()
        return created

    def test_rf_350_a_verified_breach_blocks_the_approval_with_its_citation(
        self, session, unit, order
    ) -> None:
        set_parameter(
            session,
            code="grounding.max_resistance_ohm.poste",
            value=25,
            unit="ohm",
            norm_ref=NORM,
            article_ref="Numeral 5.3",
            effective_from=date(2020, 1, 1),
            verified_by="analista.1",
            strict=True,
        )
        response = save_answers(
            session,
            unit,
            order,
            answers={"earth_resistance_ohm": 90.0, "grounding_context": "poste"},
        )
        blockers = approval_blockers(session, unit, order, response)
        assert any("incumplimiento normativo" in reason for reason in blockers)
        assert any("Numeral 5.3" in reason for reason in blockers)

    def test_rf_350_a_missing_parameter_does_not_block_the_crew(self, session, unit, order) -> None:
        response = save_answers(session, unit, order, answers={"earth_resistance_ohm": 90.0})
        findings = compliance_findings(session, order, response)
        assert any(f.outcome is Outcome.UNDETERMINED for f in findings)
        assert not any(
            "incumplimiento normativo" in r
            for r in approval_blockers(session, unit, order, response)
        )

    def test_rf_350_findings_are_reproducible_from_stored_data(self, session, unit, order) -> None:
        """Se recalculan, no se guardan: los hechos y el límite con vigencia ya están."""
        set_parameter(
            session,
            code="grounding.max_resistance_ohm.poste",
            value=25,
            norm_ref=NORM,
            effective_from=date(2020, 1, 1),
            verified_by="analista.1",
            strict=True,
        )
        response = save_answers(
            session,
            unit,
            order,
            answers={"earth_resistance_ohm": 10.0, "grounding_context": "poste"},
        )
        first = [f.as_dict() for f in compliance_findings(session, order, response)]
        second = [f.as_dict() for f in compliance_findings(session, order, response)]
        assert first == second


class TestTheSeedLoads:
    def test_rf_350_the_shipped_seed_applies(self, session) -> None:
        written = apply_seed(session, load_seed())
        assert len(written) == 7
        assert unverified_codes(session) == sorted(row.code for row in written)

    def test_rf_350_only_verified_skips_everything_unverified(self, session) -> None:
        """Una instalación de producción no carga cifras que nadie confirmó."""
        assert apply_seed(session, load_seed(), only_verified=True) == []

    def test_rf_350_the_loader_will_not_certify_on_its_own(self, session) -> None:
        """`--verified-by` no convierte en verificado lo que el archivo marca como no."""
        written = apply_seed(session, load_seed(), verified_by="alguien.apurado")
        assert all(not row.is_verified for row in written)

    def test_rf_350_applying_the_seed_twice_is_idempotent(self, session) -> None:
        first = apply_seed(session, load_seed())
        second = apply_seed(session, load_seed())
        assert {row.id for row in first} == {row.id for row in second}
