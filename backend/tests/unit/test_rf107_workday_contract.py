"""El corpus de la jornada (RF-107), en el backend.

La otra mitad del contrato está en `core:field`'s `PositionScheduleTest.kt`: el teléfono decide
cuándo reportar y el servidor decide qué guardar, y si discreparan el servidor rechazaría lo que el
teléfono mandó enviar.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from app.policy.service import EffectivePolicy, EffectiveValue, within_workday

CORPUS = json.loads(
    (Path(__file__).resolve().parents[3] / "forms" / "contract" / "workday-cases.json").read_text(
        encoding="utf-8"
    )
)
CASES: list[dict[str, Any]] = CORPUS["cases"]


def policy(case: dict[str, Any]) -> EffectivePolicy:
    values = {
        "workday_start": case["start"],
        "workday_end": case["end"],
        "workdays": case["days"],
    }
    return EffectivePolicy(
        business_unit="GYE",
        zone_code=None,
        values={name: EffectiveValue(value, "corpus") for name, value in values.items()},
    )


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_rf_107_el_servidor_cumple_el_corpus_de_jornada(case: dict[str, Any]) -> None:
    at = datetime.fromisoformat(case["at"].replace("Z", "+00:00"))
    assert within_workday(policy(case), at) is case["inside"]


def test_el_corpus_esta_sano() -> None:
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))
    assert any(case["inside"] for case in CASES) and any(not case["inside"] for case in CASES)
