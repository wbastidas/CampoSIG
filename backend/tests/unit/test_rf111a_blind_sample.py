"""La muestra ciega y el kappa, como funciones (RF-111a, RNF-060).

Lo que RF-111a mitiga es el anclaje: un supervisor que lee «riesgo bajo, sin observaciones» antes
de mirar la captura encuentra la captura bien. Cuando eso pasa por costumbre, la revisión es del
agente, el kappa es 1,00 y nadie puede notarlo — un número calculado sobre revisiones que vieron el
informe primero mide concordancia con una sugerencia, no entre dos juicios.

Así que lo que se prueba aquí no es que la aritmética del kappa esté bien (aunque también), sino las
tres propiedades que hacen que el número valga algo: que el sorteo no lo haga el cliente, que no se
recalcule, y que dos categorías indistinguibles no se reporten como acuerdo perfecto.
"""

from __future__ import annotations

import pytest

from app.agents.report import RiskLevel
from app.review.blind import (
    DEFAULT_BLIND_RATE,
    KAPPA_FLOOR,
    MIN_SAMPLE_FOR_KAPPA,
    Agreement,
    draw,
    verdict_of_decision,
    verdict_of_risk,
)
from app.review.models import Decision


def table(clear: int = 0, flagged: int = 0, supervisor: int = 0, agent: int = 0) -> Agreement:
    return Agreement(
        both_clear=clear,
        both_flagged=flagged,
        supervisor_only=supervisor,
        agent_only=agent,
        pending=0,
        unpaired=0,
    )


class TestTheTwoCategories:
    def test_aprobar_es_sin_problema_y_todo_lo_demás_es_con_problema(self) -> None:
        """No «qué botón» sino «tenía problema esta captura».

        Comparar tres botones contra tres niveles de riesgo sería comparar escalas que no significan
        lo mismo: devolver y anular difieren en la consecuencia, no en el hallazgo.
        """
        assert verdict_of_decision(Decision.APPROVED) == "sin_problema"
        assert verdict_of_decision(Decision.RETURNED) == "con_problema"
        assert verdict_of_decision(Decision.CANCELLED) == "con_problema"

    def test_riesgo_bajo_es_sin_problema_y_medio_y_alto_no(self) -> None:
        assert verdict_of_risk(RiskLevel.LOW) == "sin_problema"
        assert verdict_of_risk(RiskLevel.MEDIUM) == "con_problema"
        assert verdict_of_risk("high") == "con_problema"

    def test_el_umbral_del_agente_es_el_mismo_que_el_del_lote(self) -> None:
        """Si «bajo» significara aprobable en un sitio y no en el otro, la concordancia mediría la
        diferencia entre dos definiciones y no entre dos juicios."""
        from app.review.batch import BATCHABLE_RISK

        assert verdict_of_risk(BATCHABLE_RISK) == "sin_problema"


class TestTheDraw:
    def test_la_tasa_por_omisión_es_la_del_srs(self) -> None:
        assert pytest.approx(0.10) == DEFAULT_BLIND_RATE

    def test_tasa_cero_no_sortea_nada(self) -> None:
        """Apagar la medición es una decisión que un operador puede tomar; el tablero dirá que no
        hay muestra en vez de mostrar un kappa calculado sobre nada."""
        assert not any(draw(rate=0.0) for _ in range(50))

    def test_tasa_uno_sortea_todo(self) -> None:
        assert all(draw(rate=1.0) for _ in range(50))

    def test_la_tasa_se_respeta_a_grandes_rasgos(self) -> None:
        from random import Random

        rng = Random(11)
        drawn = sum(draw(rng, rate=0.10) for _ in range(4000))
        assert 250 < drawn < 550


class TestTheKappa:
    def test_concordancia_perfecta_da_uno(self) -> None:
        assert table(clear=20, flagged=20).kappa == pytest.approx(1.0)

    def test_desacuerdo_total_da_negativo(self) -> None:
        assert table(supervisor=20, agent=20).kappa == pytest.approx(-1.0)

    def test_un_acuerdo_altísimo_sobre_marginales_desbalanceados_no_es_un_kappa_altísimo(
        self,
    ) -> None:
        """Es la razón de usar kappa y no el porcentaje de acuerdo.

        Noventa y dos de cien coincidiendo suena a supervisor atento. Sobre una población donde el
        90 % de las capturas está bien, es apenas mejor que un revisor que no mira.
        """
        rows = table(clear=90, flagged=2, supervisor=4, agent=4)
        assert rows.observed == pytest.approx(0.92)
        assert rows.kappa is not None
        assert rows.kappa < 0.35

    def test_con_muestra_pequeña_no_se_reporta_kappa(self) -> None:
        """Un kappa sobre nueve casos es ruido con decimales, y RNF-060 pide compararlo con 0,6."""
        nine = table(clear=5, flagged=2, supervisor=1, agent=1)
        assert nine.paired == MIN_SAMPLE_FOR_KAPPA - 1
        assert nine.kappa is None
        # Con uno más sí se reporta: el corte es el tamaño, no la forma de la tabla.
        ten = table(clear=6, flagged=2, supervisor=1, agent=1)
        assert ten.paired == MIN_SAMPLE_FOR_KAPPA
        assert ten.kappa is not None

    def test_si_los_dos_usaron_una_sola_categoría_el_kappa_es_indefinido(self) -> None:
        """Y no 1,00. Reportar concordancia perfecta entre dos que nunca distinguieron nada es
        exactamente el número que el requerimiento existe para no creerse."""
        rows = table(clear=40)
        assert rows.observed == pytest.approx(1.0)
        assert rows.kappa is None
        assert rows.meets_floor is None

    def test_el_piso_de_rnf_060_se_compara_y_se_dice(self) -> None:
        assert pytest.approx(0.6) == KAPPA_FLOOR
        good = table(clear=30, flagged=25, supervisor=2, agent=3)
        assert good.kappa is not None and good.kappa >= KAPPA_FLOOR
        assert good.meets_floor is True
        poor = table(clear=30, flagged=5, supervisor=15, agent=10)
        assert poor.meets_floor is False

    def test_las_pendientes_y_las_sin_par_no_entran_en_el_denominador(self) -> None:
        """Una OT sorteada sin decidir todavía no dice nada, y una que los agentes nunca calificaron
        no puede medir concordancia con ellos."""
        rows = Agreement(
            both_clear=10,
            both_flagged=5,
            supervisor_only=1,
            agent_only=1,
            pending=7,
            unpaired=3,
        )
        assert rows.paired == 17
        assert rows.as_dict()["pending"] == 7
        assert rows.as_dict()["unpaired"] == 3

    def test_sin_pares_no_hay_ni_acuerdo_observado(self) -> None:
        empty = Agreement(0, 0, 0, 0, pending=4, unpaired=0)
        assert empty.observed is None
        assert empty.kappa is None
