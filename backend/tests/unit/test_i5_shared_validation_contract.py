"""El corpus común de validación condicional, en el backend (I5, SRS 7.2).

Este archivo es un tercio de un contrato. Los otros dos están en
`web/src/forms/rules.test.ts` y en `core/sync/.../FormRulesTest.kt`, y los tres ejecutan el
**mismo** `forms/contract/validation-cases.json`.

Por qué un corpus y no tres suites cuidadosas: escribir el mismo algoritmo tres veces no produce
acuerdo, produce tres algoritmos que coinciden en los casos que a alguien se le ocurrieron. El
fallo que esto impide es caro en campo y en las dos direcciones — el teléfono acepta lo que el
servidor rechaza y el trabajo de la cuadrilla vuelve al día siguiente, o el teléfono exige lo que
el servidor no pide y la OT no se puede cerrar con la red caída.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.forms.rules import (
    MissingRequirement,
    evaluate_condition,
    is_answered,
    missing_requirements,
)

CORPUS_PATH = Path(__file__).resolve().parents[3] / "forms" / "contract" / "validation-cases.json"


def load_corpus() -> dict[str, Any]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


CORPUS = load_corpus()
CASES: list[dict[str, Any]] = CORPUS["cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_i5_el_backend_cumple_el_contrato_compartido(case: dict[str, Any]) -> None:
    """Cada caso del corpus, contra el evaluador del servidor."""
    found = missing_requirements(case["rules"], case["answers"])
    assert [item.field for item in found] == case["expect"], case.get("why", case["id"])


def test_el_corpus_esta_sano() -> None:
    """Un corpus con ids repetidos o casos vacíos es un corpus que no compara nada.

    Se comprueba aquí y en las otras dos suites: si el archivo se edita mal, las tres lo dicen.
    """
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids)), "hay ids repetidos en el corpus"
    assert len(CASES) >= 25, "el corpus se quedó corto; el contrato deja de cubrir"
    for case in CASES:
        assert isinstance(case["rules"], list)
        assert isinstance(case["answers"], dict)
        assert isinstance(case["expect"], list)


#: Las tres suites que ejecutan el corpus. Relativas a la raíz del monorepo.
CONTRACT_SUITES = (
    "backend/tests/unit/test_i5_shared_validation_contract.py",
    "web/src/forms/rules.test.ts",
    "android/core/sync/src/test/kotlin/ec/sigec/campo/sync/FormRulesTest.kt",
)


def test_las_tres_suites_del_contrato_siguen_existiendo_y_leyendo_el_corpus() -> None:
    """Un contrato de tres partes deja de serlo en silencio si una desaparece.

    Borrar la suite de Kotlin dejaría CI en verde y el contrato reducido a dos plataformas, que es
    precisamente el estado del que el corpus existe para sacarnos. Esta guarda corre en la suite
    del backend porque es la que siempre se ejecuta.
    """
    root = CORPUS_PATH.parents[2]
    missing = [name for name in CONTRACT_SUITES if not (root / name).exists()]
    assert not missing, f"faltan suites del contrato compartido: {', '.join(missing)}"

    not_reading = [
        name
        for name in CONTRACT_SUITES
        if "validation-cases.json" not in (root / name).read_text(encoding="utf-8")
    ]
    assert not not_reading, "estas suites ya no leen el corpus compartido: " + ", ".join(
        not_reading
    )


def test_el_corpus_cubre_los_operadores_que_la_biblioteca_usa() -> None:
    """Y que cubra lo que hay: un contrato que no menciona `in` no protege `in`."""
    operators: set[str] = set()
    for case in CASES:
        for rule in case["rules"]:
            operators.update(key for key in (rule.get("when") or {}))
    assert {"==", "!=", "in", "and", "or"} <= operators


def test_el_corpus_incluye_un_caso_que_la_implementacion_ingenua_falla() -> None:
    """La prueba de que el corpus discrimina.

    Un corpus que cualquier implementación razonable pasa no está midiendo nada. Este evaluador
    ingenuo —el que se escribe de primera intención— trata el cero y el falso como ausencia y
    compara con coerción; el corpus tiene que rechazarlo.
    """

    def naive(rules: list[dict[str, Any]], answers: dict[str, Any]) -> list[str]:
        problems: list[str] = []
        for rule in rules:
            condition = rule.get("when") or {}
            if "==" not in condition:
                continue
            left, right = condition["=="]
            resolve = lambda t: answers.get(t["var"]) if isinstance(t, dict) else t  # noqa: E731
            if resolve(left) != resolve(right):
                continue
            for field in rule.get("require") or []:
                if not answers.get(field):  # aquí está el error: 0 y False son "vacío"
                    problems.append(field)
        return problems

    disagreements = [
        case["id"] for case in CASES if naive(case["rules"], case["answers"]) != case["expect"]
    ]
    assert disagreements, "el corpus no distingue una implementación ingenua de la correcta"


# --- lo que el corpus no puede expresar, y por eso se prueba aquí --------------------
def test_el_mensaje_de_la_regla_viaja_con_el_campo() -> None:
    """El contrato son los campos; el mensaje es presentación y no está en el corpus."""
    found = missing_requirements(
        [
            {
                "when": {"==": [{"var": "final_state"}, "no_resuelto"]},
                "require": ["cause"],
                "message": "Indique la causa cuando el trabajo no quedó resuelto",
            }
        ],
        {"final_state": "no_resuelto"},
    )
    assert found == [
        MissingRequirement(
            field="cause", message="Indique la causa cuando el trabajo no quedó resuelto"
        )
    ]


@pytest.mark.parametrize(
    ("value", "answered"),
    [
        (0, True),
        (0.0, True),
        (False, True),
        (True, True),
        ("x", True),
        ("", False),
        ("  ", False),
        (None, False),
        ([], False),
        ([1], True),
        ({}, False),
        ({"a": 1}, True),
    ],
)
def test_que_cuenta_como_respuesta(value: Any, answered: bool) -> None:
    assert is_answered(value) is answered


def test_un_booleano_no_se_compara_igual_a_cero_ni_a_uno() -> None:
    """En Python `True == 1`, y eso haría coincidir «¿señalizado?» con un conteo."""
    assert evaluate_condition({"==": [{"var": "signposted"}, 1]}, {"signposted": True}) is False
    assert evaluate_condition({"==": [{"var": "count"}, True]}, {"count": 1}) is False


def test_una_regla_que_no_es_un_objeto_se_ignora() -> None:
    """Un catálogo corrupto no puede impedirle a la cuadrilla enviar el día de trabajo."""
    assert missing_requirements([None, "texto", 3], {}) == []  # type: ignore[list-item]
