"""El corpus de cédulas (RF-046), en el backend.

Un tercio de un contrato: los otros dos están en `web/src/forms/identification.test.ts` y en
`core:sync`'s `CedulaTest.kt`, y los tres ejecutan `forms/contract/identification-cases.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.forms.identification import is_valid_cedula

CORPUS = json.loads(
    (
        Path(__file__).resolve().parents[3] / "forms" / "contract" / "identification-cases.json"
    ).read_text(encoding="utf-8")
)
CASES: list[dict[str, Any]] = CORPUS["cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_rf_046_el_backend_cumple_el_corpus_de_cedulas(case: dict[str, Any]) -> None:
    assert is_valid_cedula(case["value"]) is case["valid"], case.get("why", case["id"])


def test_el_corpus_esta_sano() -> None:
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))
    assert sum(case["valid"] for case in CASES) >= 5
    assert sum(not case["valid"] for case in CASES) >= 10


def test_un_valor_que_no_es_texto_no_es_cedula() -> None:
    assert is_valid_cedula(912345675) is False  # type: ignore[arg-type]
