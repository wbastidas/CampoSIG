"""El archivo de parámetros y su validación (SRS 1.4, ADR-007).

Lo que estos tests protegen no es el cargador: es la regla de que **ningún límite regulatorio
se codifica**. Si alguien escribe un 48 en el código, o anota en un formulario un parámetro
que ninguna regla lee, aquí se ve.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest
import yaml

from app.forms.catalog import load_blocks
from app.regulatory import rules as compliance
from app.regulatory.loader import SeedError, default_seed_path, load_seed, validate_seed

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def seed() -> dict:
    return load_seed()


class TestTheSeedFileIsTrustworthy:
    def test_it_loads_and_validates(self, seed) -> None:
        assert seed["jurisdiction"] == "EC"
        assert seed["parameters"]

    def test_every_parameter_cites_a_norm(self, seed) -> None:
        """Un límite sin norma detrás no se puede citar, y una observación sin cita es una
        opinión (SRS 10.4)."""
        for entry in seed["parameters"]:
            assert entry.get("norm_ref"), entry["code"]

    def test_nothing_ships_marked_as_verified(self, seed) -> None:
        """Nadie de este equipo leyó el texto oficial, así que nada puede venir verificado.

        Cuando alguien verifique de verdad, este test se actualiza junto con el archivo — y
        ese cambio es exactamente el que un revisor debe mirar con atención.
        """
        unverified = [e["code"] for e in seed["parameters"] if not e.get("verified")]
        assert len(unverified) == len(seed["parameters"])

    def test_the_limits_with_legal_consequence_are_strict(self, seed) -> None:
        """Una puesta a tierra fuera de norma es un riesgo para las personas."""
        grounding = [e for e in seed["parameters"] if e["code"].startswith("grounding.")]
        assert grounding
        assert all(e.get("strict") for e in grounding)

    def test_every_rule_has_a_parameter_in_the_seed(self, seed) -> None:
        """Una regla sin parámetro cargado no evalúa nada, y lo dice — pero mejor no llegar."""
        codes = {e["code"] for e in seed["parameters"]}
        for required in compliance.REQUIRED_PARAMETER_CODES:
            assert any(code == required or code.startswith(f"{required}.") for code in codes), (
                required
            )


class TestValidationDetects:
    def test_a_parameter_without_a_norm_is_refused(self, seed) -> None:
        broken = {**seed, "parameters": [{**seed["parameters"][0], "norm_ref": None}]}
        assert any("norm" in problem for problem in validate_seed(broken))

    def test_a_parameter_without_a_value_is_refused(self, seed) -> None:
        entry = {k: v for k, v in seed["parameters"][0].items() if k != "value"}
        assert any("value" in problem for problem in validate_seed({**seed, "parameters": [entry]}))

    def test_a_missing_effective_date_is_refused(self, seed) -> None:
        entry = {**seed["parameters"][0], "effective_from": "el año pasado"}
        assert any("effective_from" in p for p in validate_seed({**seed, "parameters": [entry]}))

    def test_a_duplicate_code_and_date_is_refused(self, seed) -> None:
        entry = seed["parameters"][0]
        assert any("repetido" in p for p in validate_seed({**seed, "parameters": [entry, entry]}))

    def test_an_empty_file_is_refused(self) -> None:
        assert validate_seed({}) == ["el archivo no declara 'parameters'"]

    def test_loading_a_broken_file_raises(self, tmp_path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("version: 1\nparameters: []\n", encoding="utf-8")
        with pytest.raises(SeedError):
            load_seed(bad)


class TestNoLimitIsHardCoded:
    """RF-350/351 y ADR-007: todo límite sale de `regulatory_parameter`, ninguno del código."""

    def test_the_rules_module_contains_no_numeric_limit(self) -> None:
        """Las reglas comparan; no llevan la cifra contra la que comparan.

        Se inspecciona el código fuente a propósito: es la forma de detectar que alguien
        "arregló" una regla escribiendo el número que faltaba.
        """
        source = (REPO_ROOT / "backend" / "app" / "regulatory" / "rules.py").read_text(
            encoding="utf-8"
        )
        # Fuera comentarios, docstrings y literales de confianza/redondeo.
        code_lines = [
            line
            for line in source.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        body = "\n".join(code_lines)
        body = re.sub(r'""".*?"""', "", body, flags=re.S)
        # Los únicos números admitidos son los de conversión de unidades y redondeo.
        allowed = {"3600", "2", "0", "1"}
        found = set(re.findall(r"\b\d+\b", body)) - allowed
        assert not found, (
            f"la lógica de reglas contiene números que parecen límites: {sorted(found)}. "
            "Todo límite viene de regulatory_parameter"
        )

    def test_every_form_annotation_points_at_a_known_rule(self) -> None:
        """Un `x-regulatory-parameter` que ninguna regla lee es una promesa sin cumplir."""
        annotated: dict[str, str] = {}
        for block in load_blocks().values():
            for field_name, schema in block.fields.items():
                if isinstance(schema, dict) and "x-regulatory-parameter" in schema:
                    annotated[field_name] = str(schema["x-regulatory-parameter"])
        assert annotated, "los formularios deberían declarar contra qué límite se evalúan"

        for field_name, code in annotated.items():
            assert any(
                code == required or code.startswith(f"{required}.")
                for required in compliance.REQUIRED_PARAMETER_CODES
            ), f"'{field_name}' se evalúa contra '{code}', que ninguna regla conoce"

    def test_every_form_annotation_exists_in_the_seed(self) -> None:
        codes = {e["code"] for e in yaml.safe_load(default_seed_path().read_text())["parameters"]}
        for block in load_blocks().values():
            for field_name, schema in block.fields.items():
                if not isinstance(schema, dict):
                    continue
                code = schema.get("x-regulatory-parameter")
                if code is None:
                    continue
                assert any(
                    existing == code or existing.startswith(f"{code}.") for existing in codes
                ), f"'{field_name}' cita '{code}', que no está en seeds/regulatory-ec.yaml"


def test_the_seed_dates_are_real_dates() -> None:
    parsed = yaml.safe_load(default_seed_path().read_text(encoding="utf-8"))
    for entry in parsed["parameters"]:
        assert isinstance(entry["effective_from"], date)
