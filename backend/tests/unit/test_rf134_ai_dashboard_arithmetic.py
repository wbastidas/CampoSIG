"""La aritmética del tablero de IA (RF-134).

Un tablero es una herramienta de decisión: alguien mira un número y decide publicar un modelo,
pedir un lote de etiquetado o dejar las cosas como están. Así que lo que se prueba aquí no es que
las cuentas salgan —eso es lo fácil— sino las tres reglas que evitan que el tablero invite a la
decisión equivocada:

* una tasa sin su denominador no es una medición: «100 % de aceptación» sobre dos propuestas es
  ruido con signo de porcentaje, y la decisión que invita es la cara;
* el error de palabras dice qué mide, porque quien lea el número lo va a citar;
* lo que no se pudo medir se cuenta, porque una tasa calculada sobre tres campos de cuatrocientos
  no es la tasa de nada y la única forma de que el lector lo sepa es que el tablero lo diga.
"""

from __future__ import annotations

import pytest

from app.analytics.ai_dashboard import (
    MIN_FOR_A_RATE,
    ClassCorrections,
    FieldAcceptance,
    VoiceAdoption,
    WordErrors,
    rate,
    word_distance,
    words_of,
)


class TestARateNeedsADenominator:
    def test_una_tasa_sobre_pocas_propuestas_no_se_reporta(self) -> None:
        assert rate(2, 2) is None
        assert rate(1, MIN_FOR_A_RATE - 1) is None

    def test_con_suficientes_si(self) -> None:
        assert rate(4, MIN_FOR_A_RATE) == pytest.approx(0.8)

    def test_el_minimo_no_es_uno(self) -> None:
        """Con un mínimo de uno, una sola corrección se leería como «50 % de error»."""
        assert MIN_FOR_A_RATE > 1

    def test_el_campo_lleva_su_cuenta_aunque_no_lleve_tasa(self) -> None:
        """Ocultar también la cuenta dejaría al analista sin saber si el campo se usa."""
        few = FieldAcceptance(
            field_key="material", proposals=3, accepted=3, corrected=0, mean_confidence=0.9
        )
        assert few.acceptance is None
        body = few.as_dict()
        assert body["proposals"] == 3
        assert body["accepted"] == 3
        assert body["acceptance"] is None

    def test_la_confianza_media_viaja_con_la_aceptación(self) -> None:
        """Una aceptación baja con confianza alta y una con confianza baja son problemas
        distintos: el primero es un modelo equivocado y seguro, que es el peor."""
        rows = FieldAcceptance(
            field_key="material", proposals=20, accepted=6, corrected=14, mean_confidence=0.95
        )
        assert rows.acceptance == pytest.approx(0.3)
        assert rows.as_dict()["mean_confidence"] == pytest.approx(0.95)


class TestTheWordDistance:
    def test_dos_frases_iguales_no_tienen_distancia(self) -> None:
        assert word_distance(["poste", "de", "hormigón"], ["poste", "de", "hormigón"]) == 0

    def test_una_palabra_cambiada_es_una_sustitución(self) -> None:
        assert word_distance(["poste", "de", "hormigón"], ["poste", "de", "madera"]) == 1

    def test_una_palabra_de_más_es_un_error(self) -> None:
        assert (
            word_distance(["poste", "de", "hormigón"], ["poste", "de", "hormigón", "armado"]) == 1
        )

    def test_una_palabra_de_menos_también(self) -> None:
        assert word_distance(["poste", "de", "hormigón"], ["poste", "hormigón"]) == 1

    def test_contra_una_referencia_vacía_todo_es_inserción(self) -> None:
        assert word_distance([], ["poste", "de", "hormigón"]) == 3

    def test_la_distancia_es_por_palabras_y_no_por_caracteres(self) -> None:
        """Por palabras porque es la unidad que cuenta un WER. Por caracteres, «hormigon» contra
        «hormigón» puntuaría una décima de error donde hay un error entero de extracción."""
        assert word_distance(["hormigón"], ["hormigon"]) == 1

    def test_mayúsculas_y_puntuación_no_son_errores(self) -> None:
        """«Hormigón.» y «hormigón» son la misma respuesta, y contarlas como error infla la
        estimación con una diferencia que ninguna persona llamaría así."""
        assert words_of("Hormigón.") == words_of("hormigón")
        assert words_of("  Poste de HORMIGÓN  ") == ["poste", "de", "hormigón"]

    def test_lo_que_no_es_texto_no_tiene_palabras(self) -> None:
        assert words_of(12) is None
        assert words_of(None) is None
        assert words_of(["a", "b"]) is None
        assert words_of("") is None
        assert words_of("   ") is None


class TestTheWordErrorEstimate:
    def test_dice_qué_mide(self) -> None:
        """Quien lea este número lo va a citar, y debería citar lo que mide: la cadena completa,
        no el reconocimiento solo. Un WER de verdad compara contra una transcripción de referencia
        del mismo audio, y nadie transcribe estas grabaciones dos veces."""
        said = WordErrors(
            reference_words=100, errors=8, measured_fields=20, unmeasurable_fields=3
        ).as_dict()["measures"]
        assert isinstance(said, str)
        assert "no es un wer" in said.lower()
        assert "extracción" in said

    def test_cuenta_lo_que_no_pudo_medir(self) -> None:
        rows = WordErrors(reference_words=30, errors=3, measured_fields=6, unmeasurable_fields=400)
        assert rows.as_dict()["unmeasurable_fields"] == 400
        # La tasa sale, pero el lector puede ver que cubre seis campos de cuatrocientos seis.
        assert rows.error_rate == pytest.approx(0.1)

    def test_con_pocos_campos_medidos_no_se_reporta_tasa(self) -> None:
        assert WordErrors(10, 1, MIN_FOR_A_RATE - 1, 0).error_rate is None

    def test_sin_palabras_de_referencia_no_hay_división(self) -> None:
        assert WordErrors(0, 0, 50, 0).error_rate is None


class TestTheOtherPanels:
    def test_una_clase_visual_dice_en_qué_se_corrigió(self) -> None:
        """Una clase que siempre se corrige a la misma es una confusión que se arregla en la
        taxonomía o en el set; una que se corrige a cinco distintas es un detector adivinando."""
        rows = ClassCorrections(
            proposed_class="concrete",
            proposals=20,
            corrected=8,
            became=[("wood", 6), ("metal", 2)],
        )
        assert rows.correction_rate == pytest.approx(0.4)
        assert rows.as_dict()["became"][0] == {"value": "wood", "times": 6}

    def test_la_adopción_de_la_voz_no_puede_pasar_del_cien_por_ciento(self) -> None:
        rows = VoiceAdoption(
            user="tecnico.1", responses=10, responses_with_voice=10, voice_fields=44
        )
        assert rows.adoption == pytest.approx(1.0)

    def test_quien_no_dicta_aparece_con_cero_y_no_desaparece(self) -> None:
        """Es el dato que importa: quien no adopta la función es justo el que no genera filas de
        procedencia, y un tablero que solo mira esas filas reporta su mejor caso."""
        rows = VoiceAdoption(user="tecnico.9", responses=12, responses_with_voice=0, voice_fields=0)
        assert rows.adoption == pytest.approx(0.0)
        assert rows.as_dict()["responses"] == 12
