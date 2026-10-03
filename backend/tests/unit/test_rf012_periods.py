"""Las etiquetas de periodo y las fechas de disparo de un plan preventivo (RF-012).

Toda la idempotencia de RF-012 se apoya en una cosa: dos corridas dentro del mismo periodo producen
la **misma etiqueta**. Si eso falla, un plan mensual emite dos veces septiembre y una cuadrilla
maneja hasta un poste que ya inspeccionó — y el error no se ve hasta que alguien cuenta las OT.

Lo segundo que se prueba es el día 28, que es una decisión y no un límite técnico: «el 31 de cada
mes» no existe en febrero, y las dos formas de arreglarlo sobre la marcha —disparar el 28 o saltarse
el mes— dan un conteo anual distinto del que el área reporta.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.plans.models import Cadence
from app.plans.periods import MAX_DAY_OF_MONTH, is_due, period_of

ANCHOR = date(2026, 1, 5)


def label(cadence: Cadence, on: date, *, days: int | None = None, anchor: date = ANCHOR) -> str:
    return period_of(cadence.value, days, on, anchor=anchor)


class TestTheLabel:
    def test_rf_012_un_plan_mensual_etiqueta_el_mes(self) -> None:
        assert label(Cadence.MONTHLY, date(2026, 9, 3)) == "2026-09"

    def test_rf_012_dos_corridas_del_mismo_mes_son_el_mismo_periodo(self) -> None:
        """Lo que impide que septiembre se emita dos veces."""
        assert label(Cadence.MONTHLY, date(2026, 9, 3)) == label(Cadence.MONTHLY, date(2026, 9, 27))

    def test_rf_012_meses_distintos_son_periodos_distintos(self) -> None:
        assert label(Cadence.MONTHLY, date(2026, 9, 30)) != label(
            Cadence.MONTHLY, date(2026, 10, 1)
        )

    def test_rf_012_el_mes_va_con_cero_delante_para_que_ordene_como_texto(self) -> None:
        """El historial se ordena por la etiqueta, y «2026-9» quedaría después de «2026-10»."""
        assert label(Cadence.MONTHLY, date(2026, 9, 1)) < label(Cadence.MONTHLY, date(2026, 10, 1))

    def test_rf_012_el_trimestre_se_nombra_como_lo_nombra_el_area(self) -> None:
        for month, expected in ((1, "2026-T1"), (3, "2026-T1"), (4, "2026-T2"), (12, "2026-T4")):
            assert label(Cadence.QUARTERLY, date(2026, month, 10)) == expected

    def test_rf_012_el_semestre_igual(self) -> None:
        assert label(Cadence.SEMIANNUAL, date(2026, 6, 30)) == "2026-S1"
        assert label(Cadence.SEMIANNUAL, date(2026, 7, 1)) == "2026-S2"

    def test_rf_012_el_anual_es_el_ano(self) -> None:
        assert label(Cadence.ANNUAL, date(2026, 2, 1)) == "2026"
        assert label(Cadence.ANNUAL, date(2027, 2, 1)) == "2027"

    def test_rf_012_el_plan_por_dias_cuenta_desde_su_inicio_y_no_del_calendario(self) -> None:
        """«Cada 45 días» no significa nada en el calendario: el ancla honesto es el inicio."""
        start = date(2026, 1, 5)
        assert label(Cadence.CUSTOM_DAYS, start, days=45, anchor=start) == "2026-01-05"
        # Día 44: mismo periodo. Día 45: el siguiente.
        assert label(Cadence.CUSTOM_DAYS, date(2026, 2, 18), days=45, anchor=start) == "2026-01-05"
        assert label(Cadence.CUSTOM_DAYS, date(2026, 2, 19), days=45, anchor=start) == "2026-02-19"

    def test_rf_012_antes_del_inicio_la_etiqueta_no_se_va_hacia_atras(self) -> None:
        """No debería consultarse, y si se consulta no puede inventar un periodo negativo."""
        start = date(2026, 1, 5)
        assert label(Cadence.CUSTOM_DAYS, date(2025, 12, 1), days=30, anchor=start) == "2026-01-05"


class TestWhenItFires:
    def due(self, cadence: Cadence, on: date, *, day: int = 5, days: int | None = None) -> bool:
        return is_due(cadence.value, days, day, on, anchor=ANCHOR)

    def test_rf_012_antes_de_su_fecha_de_inicio_un_plan_no_dispara(self) -> None:
        assert self.due(Cadence.MONTHLY, date(2025, 12, 5)) is False

    def test_rf_012_un_mensual_dispara_su_dia_del_mes(self) -> None:
        assert self.due(Cadence.MONTHLY, date(2026, 3, 5)) is True

    def test_rf_012_antes_de_su_dia_no_dispara(self) -> None:
        assert self.due(Cadence.MONTHLY, date(2026, 3, 4)) is False

    def test_rf_012_si_el_job_no_corrio_ese_dia_alcanza_al_siguiente(self) -> None:
        """Una máquina caída el día 5 no puede costarle al área un mes de preventivo.

        Es seguro porque la etiqueta impide el doble: ser generoso aquí no duplica, y ser estricto
        sí perdería el periodo entero.
        """
        assert self.due(Cadence.MONTHLY, date(2026, 3, 6)) is True

    def test_rf_012_un_trimestral_dispara_en_el_trimestre_del_area_y_no_en_enero(self) -> None:
        """Un plan que arranca en febrero corre en febrero, mayo, agosto y noviembre."""
        anchor = date(2026, 2, 1)
        for month, expected in (
            (2, True),
            (3, False),
            (5, True),
            (8, True),
            (11, True),
            (12, False),
        ):
            assert (
                is_due(Cadence.QUARTERLY.value, None, 1, date(2026, month, 10), anchor=anchor)
                is expected
            ), month

    def test_rf_012_un_anual_dispara_una_vez_al_ano(self) -> None:
        anchor = date(2026, 4, 2)
        assert is_due(Cadence.ANNUAL.value, None, 2, date(2026, 4, 2), anchor=anchor) is True
        assert is_due(Cadence.ANNUAL.value, None, 2, date(2026, 5, 2), anchor=anchor) is False
        assert is_due(Cadence.ANNUAL.value, None, 2, date(2027, 4, 2), anchor=anchor) is True

    def test_rf_012_un_dia_del_mes_imposible_se_recorta_en_vez_de_no_disparar_nunca(self) -> None:
        """La validación del servicio ya lo rechaza al guardar; esto es el cinturón del cinturón.

        Un plan que quedara guardado con el día 31 —una carga directa a la base, una migración— no
        puede dejar de disparar en silencio para siempre.
        """
        assert is_due(Cadence.MONTHLY.value, None, 31, date(2026, 2, 28), anchor=ANCHOR) is True

    def test_rf_012_el_tope_del_dia_del_mes_es_28(self) -> None:
        assert MAX_DAY_OF_MONTH == 28


@pytest.mark.parametrize("cadence", list(Cadence))
def test_rf_012_toda_frecuencia_produce_una_etiqueta_no_vacia(cadence: Cadence) -> None:
    """Ninguna frecuencia puede quedarse sin etiqueta: sin ella no hay guarda de idempotencia."""
    assert label(cadence, date(2026, 9, 15), days=30)
