"""Input and output guardrails for the agent layer (RF-182).

The criterion is «los informes no contienen cédulas ni teléfonos de clientes (test con datos
sembrados)», so that is what most of this file is: real Ecuadorian identifiers planted in an
observation and a summary, and the assertion that they do not come out the other side.

What the tests are really protecting is the *shape* of the response to each defect:

* personal data is **redacted**, because deleting the observation would cost a real finding;
* a non-neutral sentence is **dropped**, because a reworded accusation is still an accusation;
* nothing is **silent**, so a node that starts producing either is visible on the next run;
* and the cédula check is the real algorithm, because a guard that redacted every ten-digit run
  would eat asset codes and get switched off within a week.
"""

from __future__ import annotations

import pytest

from app.agents.guardrails import (
    ACCUSATORY_TERMS,
    MAX_INPUT_CHARS,
    MAX_MESSAGE_CHARS,
    MAX_REASKS,
    MAX_SUMMARY_CHARS,
    REDACTION,
    clamp_input,
    enforce,
    is_ecuadorian_id,
    is_neutral,
    redact,
    validate_report,
    with_reask,
)
from app.agents.report import (
    AgentReport,
    Category,
    EvidenceRef,
    EvidenceType,
    Observation,
    RiskLevel,
    RunStatus,
    Severity,
)

#: Valid cédulas: Guayas (09), Pichincha (17) and one registered abroad (30). Check digits computed
#: with the published algorithm, and `test_the_fixtures_are_valid` proves they are not typos.
VALID_IDS = ("0926687856", "1710034065", "3000000012")

#: Ten digits that are **not** a cédula: an asset code, a meter number, a bad province, a bad third
#: digit, a wrong check digit. Redacting these is the false positive that gets a guard removed.
#: Ten digits that are **not** a cédula, and are not phone-shaped either: an asset code, a meter
#: number, a bad province, a wrong check digit. Redacting these is the false positive that gets a
#: guard removed. A «09…» run is left out on purpose — that shape *is* a mobile number and the
#: phone rule takes it, which `test_a_09_run_is_taken_as_a_phone` covers.
NOT_IDS = ("9999999999", "0000000000", "1710034066", "2512345678", "8891234567")


def observation(
    message: str, *, identifier: str = "OBS-1", action: str | None = None
) -> Observation:
    return Observation(
        id=identifier,
        category=Category.COHERENCE,
        severity=Severity.MEDIUM,
        message=message,
        evidence=[EvidenceRef(type=EvidenceType.FIELD, json_path="$.answers.note")],
        suggested_action=action,
    )


def report(
    *observations: Observation, summary: str = "Captura sin novedades relevantes."
) -> AgentReport:
    return AgentReport(
        work_order_id="ot-1",
        graph_version="1.0.0",
        hardware_profile="A",
        risk_level=RiskLevel.LOW,
        status=RunStatus.COMPLETE,
        summary=summary,
        observations=list(observations),
    )


class TestTheIdentifierCheck:
    def test_the_fixtures_are_valid(self):
        """If these were typos the whole file would be testing nothing."""
        for value in VALID_IDS:
            assert is_ecuadorian_id(value), value

    def test_ten_digits_are_not_enough(self):
        for value in NOT_IDS:
            assert not is_ecuadorian_id(value), value

    def test_a_province_out_of_range_is_refused(self):
        assert not is_ecuadorian_id("2512345678")

    def test_a_third_digit_of_six_or_more_is_refused(self):
        """Six and up is a legal person or a public entity, not a citizen's cédula.

        The fixture has a **valid** check digit on purpose: with an invalid one the test would pass
        for the wrong reason and the rule it is about would be free to disappear. It was written the
        wrong way first, and the sabotage check is what said so.
        """
        assert not is_ecuadorian_id("1766878563")
        # Valid but for the third digit: the same number with a 1 there is a real cédula.
        assert is_ecuadorian_id("1716878564")

    def test_the_wrong_length_or_letters_are_refused(self):
        assert not is_ecuadorian_id("092668785")
        assert not is_ecuadorian_id("09266878567")
        assert not is_ecuadorian_id("09266878x6")


class TestRedaction:
    @pytest.mark.parametrize("identifier", VALID_IDS)
    def test_a_cedula_is_removed(self, identifier: str):
        text, kinds = redact(f"El cliente {identifier} reportó la falla")
        assert identifier not in text
        assert REDACTION in text
        assert kinds == ["cédula"]

    @pytest.mark.parametrize("value", NOT_IDS)
    def test_ten_digits_that_are_not_a_cedula_survive(self, value: str):
        """An asset code is ten digits too, and mangling one is how a guard gets disabled."""
        text, kinds = redact(f"El activo {value} presenta el defecto")
        assert value in text
        assert kinds == []

    @pytest.mark.parametrize(
        "phone",
        ["0991234567", "+593991234567", "00593991234567", "042345678", "099 123 4567"],
    )
    def test_a_phone_number_is_removed(self, phone: str):
        text, kinds = redact(f"Llamó al {phone} para avisar")
        assert "teléfono" in kinds
        assert REDACTION in text

    def test_an_email_is_removed(self):
        text, kinds = redact("Escribió a cliente.ejemplo@correo.com sobre el caso")
        assert "cliente.ejemplo@correo.com" not in text
        assert kinds == ["correo"]

    def test_an_email_with_digits_is_not_cut_in_half(self):
        """Why the e-mail goes first: its local part can hold a digit run the phone pattern eats."""
        text, kinds = redact("Escribió a 0991234567@correo.com sobre el caso")
        assert "correo.com" not in text
        assert kinds == ["correo"]

    def test_a_09_run_that_is_not_a_cedula_is_still_taken_as_a_phone(self):
        """The two shapes overlap in Ecuador; both are personal data, so either rule removing it is
        the right outcome. The label is what differs."""
        text, kinds = redact("Llamó del 0996687856 esta mañana")
        assert "0996687856" not in text
        assert kinds == ["teléfono"]

    def test_several_kinds_in_one_text_are_all_reported(self):
        text, kinds = redact(f"El cliente {VALID_IDS[0]} llamó al 0991234567 y escribió a a@b.co")
        assert set(kinds) == {"cédula", "teléfono", "correo"}
        assert VALID_IDS[0] not in text

    def test_an_asset_code_and_a_kva_reading_survive(self):
        """The ordinary content of an observation must pass through untouched."""
        text, kinds = redact("El transformador T-4521 de 50 kVA en el poste 8891234")
        assert kinds == []
        assert text == "El transformador T-4521 de 50 kVA en el poste 8891234"


class TestNeutrality:
    def test_a_plain_observation_is_neutral(self):
        assert is_neutral("La hora declarada no coincide con la del envío")

    @pytest.mark.parametrize("term", ACCUSATORY_TERMS)
    def test_every_listed_term_is_caught(self, term: str):
        assert not is_neutral(f"El técnico {term} en la captura")

    def test_the_check_is_accent_and_case_insensitive_where_it_matters(self):
        assert not is_neutral("El técnico MINTIÓ")
        assert not is_neutral("El técnico mintio")


class TestTheInputCap:
    def test_a_normal_dictation_passes_untouched(self):
        text = "El poste está inclinado y la cruceta deteriorada. " * 10
        clamped, cut = clamp_input(text)
        assert clamped == text
        assert cut is False

    def test_a_pasted_document_is_cut_and_says_so(self):
        clamped, cut = clamp_input("x" * (MAX_INPUT_CHARS + 500))
        assert len(clamped) == MAX_INPUT_CHARS
        assert cut is True

    def test_nothing_is_not_an_error(self):
        assert clamp_input(None) == ("", False)


class TestTheOutputGuardrail:
    def test_a_cedula_in_an_observation_is_redacted_and_the_finding_survives(self):
        """Deleting the observation would cost a real finding; the number is incidental."""
        original = report(observation(f"El cliente {VALID_IDS[0]} reportó la falla el martes"))
        validated, result = enforce(original)
        assert len(validated.observations) == 1
        assert VALID_IDS[0] not in validated.observations[0].message
        assert "reportó la falla el martes" in validated.observations[0].message
        assert result.redactions == ["cédula en OBS-1"]

    def test_a_phone_in_the_summary_is_redacted(self):
        original = report(summary="El cliente al 0991234567 confirmó la reposición")
        validated, result = enforce(original)
        assert "0991234567" not in validated.summary
        assert result.summary_redacted is True

    def test_a_non_neutral_observation_is_dropped_with_its_reason(self):
        original = report(
            observation("El técnico mintió sobre la hora", identifier="OBS-ACUSA"),
            observation("La hora declarada no coincide con la del envío", identifier="OBS-OK"),
        )
        validated, result = enforce(original)
        assert [item.id for item in validated.observations] == ["OBS-OK"]
        assert result.dropped[0].observation_id == "OBS-ACUSA"
        assert "no acusa" in result.dropped[0].reason

    def test_a_drop_is_counted_in_the_reports_own_discarded(self):
        """One number for one idea: «the guardrail refused something»."""
        original = report(observation("El técnico mintió", identifier="X"))
        validated, _ = enforce(original)
        assert validated.discarded == 1

    def test_the_suggested_action_is_redacted_too(self):
        original = report(
            observation("Falta confirmar con el cliente", action="Llamar al 0991234567")
        )
        validated, result = enforce(original)
        assert "0991234567" not in (validated.observations[0].suggested_action or "")
        assert any("acción sugerida" in item for item in result.redactions)

    def test_a_very_long_message_is_cut_and_reported(self):
        original = report(observation("x" * (MAX_MESSAGE_CHARS + 100)))
        validated, result = enforce(original)
        assert len(validated.observations[0].message) == MAX_MESSAGE_CHARS
        assert any("recortado" in item for item in result.redactions)

    def test_a_very_long_summary_is_cut_and_reported(self):
        original = report(summary="x" * (MAX_SUMMARY_CHARS + 100))
        validated, result = enforce(original)
        assert len(validated.summary) == MAX_SUMMARY_CHARS
        assert result.summary_truncated is True

    def test_a_clean_report_passes_untouched_and_says_so(self):
        original = report(observation("La hora declarada no coincide con la del envío"))
        validated, result = enforce(original)
        assert result.ok is True
        assert result.as_dict()["redactions"] == []
        assert validated.observations == original.observations
        assert validated.discarded == 0

    def test_validating_does_not_mutate_the_original(self):
        """So a screen or a test can inspect a report without rewriting it."""
        original = report(observation(f"Cliente {VALID_IDS[0]}"))
        validate_report(original)
        assert VALID_IDS[0] in original.observations[0].message


class TestTheReask:
    def test_a_clean_first_attempt_is_not_repeated(self):
        calls: list[int] = []

        def produce(attempt: int) -> AgentReport:
            calls.append(attempt)
            return report(observation("La hora declarada no coincide"))

        _, result, attempts = with_reask(produce)
        assert calls == [1]
        assert attempts == 1
        assert result.ok is True

    def test_a_producer_that_improves_is_asked_again(self):
        def produce(attempt: int) -> AgentReport:
            if attempt == 1:
                return report(observation("El técnico mintió", identifier="X"))
            return report(observation("La hora declarada no coincide", identifier="X"))

        validated, result, attempts = with_reask(produce)
        assert attempts == 2
        assert result.ok is True
        assert len(validated.observations) == 1

    def test_a_deterministic_producer_is_not_asked_twice_for_the_same_output(self):
        """The deterministic graph is a pure function of its facts: retrying spends the budget to
        receive the same refusals."""
        calls: list[int] = []

        def produce(attempt: int) -> AgentReport:
            calls.append(attempt)
            return report(observation("El técnico mintió", identifier="X"))

        _, result, attempts = with_reask(produce)
        assert calls == [1, 2]
        assert attempts == 2
        assert result.ok is False

    def test_a_producer_that_keeps_failing_differently_stops_at_the_limit(self):
        calls: list[int] = []

        def produce(attempt: int) -> AgentReport:
            calls.append(attempt)
            return report(observation(f"El técnico mintió, intento {attempt}", identifier="X"))

        _, result, attempts = with_reask(produce)
        assert attempts == MAX_REASKS
        assert len(calls) == MAX_REASKS
        assert result.ok is False

    def test_the_attempt_number_reaches_the_producer(self):
        """A future LLM node puts the previous failure in its prompt; «no personal data» works
        better as a correction than as a standing instruction."""
        seen: list[int] = []

        def produce(attempt: int) -> AgentReport:
            seen.append(attempt)
            return report(observation(f"mintió {attempt}", identifier="X"))

        with_reask(produce)
        assert seen == [1, 2, 3]


class TestItDoesNotEatOrdinaryText:
    """The false positives that would get the guard switched off, each one named.

    Written as its own class because this is the half that decides whether a guardrail survives in
    production: a rule that mangles an asset code will be removed by whoever has to explain the
    mangled report, and then nothing protects anything.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "El transformador T-4521 de 50 kVA",
            "Medidor 8891234 con lectura 004512",
            "Poste 1024 del alimentador 04BH07T11",
            "Resistencia de 23,4 ohmios medida a las 14:35",
            "Se instalaron 12 luminarias de 70 W en 340 metros",
            "La OT 2026-000101 quedó cerrada",
            "Coordenadas -2.170000, -79.900000",
        ],
    )
    def test_it_passes_through_untouched(self, text: str):
        cleaned, kinds = redact(text)
        assert kinds == []
        assert cleaned == text
