"""La compuerta de licencias de terceros (SRS 0.7, CLAUDE.md regla 10).

Esta compuerta llevaba tiempo en verde sin que nadie la hubiera visto fallar, y al añadir
WeasyPrint apareció por qué importa: `pyphen` se ofrece bajo **GPL o LGPL o MPL 1.1**, y la
compuerta lo dejaba pasar por un accidente del regex —el patrón prohibido llevaba un
`(?!.*Lesser)` y se evaluaba contra la lista de licencias **unida**, así que cualquier paquete
que mencionara «Lesser» en algún sitio dejaba de ser una coincidencia de GPL—. El veredicto
resultó defendible; el mecanismo no lo era.

Así que ahora cada licencia se evalúa por separado, un paquete con varias se **elige** y la
elección se imprime, y una licencia que la compuerta no sabe leer **falla** en vez de avisar:
un aviso al final de una build verde es un aviso que nadie lee.

Cada caso de abajo es una forma de colarse, y el cierre de dependencias real tiene el suyo.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_licenses.py"


def _load_gate() -> Any:
    """Import the CI script as a module, so the test exercises what CI runs."""
    spec = importlib.util.spec_from_file_location("check_licenses", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


class FakeMetadata:
    """The slice of `importlib.metadata` metadata the gate reads."""

    def __init__(self, name: str, classifiers: list[str], **fields: str) -> None:
        self._name = name
        self._classifiers = classifiers
        self._fields = fields

    def get(self, key: str, default: str | None = None) -> str | None:
        if key == "Name":
            return self._name
        return self._fields.get(key, default)

    def get_all(self, key: str) -> list[str] | None:
        return self._classifiers if key == "Classifier" else None


class FakeDist:
    def __init__(self, metadata: FakeMetadata) -> None:
        self.metadata = metadata


def dist(name: str, classifiers: list[str], **fields: str) -> FakeDist:
    return FakeDist(FakeMetadata(name, classifiers, **fields))


def classifier(text: str) -> str:
    return f"License :: OSI Approved :: {text}"


# --- lo que tiene que rechazar --------------------------------------------------------
def test_una_dependencia_solo_gpl_falla() -> None:
    verdict = gate.classify(
        gate.licences_of(dist("copyleft", [classifier("GNU General Public License v3 (GPLv3)")]))
    )
    assert verdict.violates
    assert verdict.elected is None


def test_una_dependencia_agpl_falla() -> None:
    verdict = gate.classify(
        gate.licences_of(dist("nube", [classifier("GNU Affero General Public License v3")]))
    )
    assert verdict.violates


def test_la_palabra_lesser_en_otro_sitio_ya_no_enmascara_una_gpl() -> None:
    """La regresión exacta que el regex anterior permitía.

    `(?!.*Lesser)` aplicado a la lista unida significaba que bastaba con que «Lesser»
    apareciera en cualquier parte —otra licencia, un texto libre— para que la GPL dejara de
    contar. Aquí la única licencia es GPL, y el texto libre menciona «Lesser»: tiene que
    fallar igual.
    """
    verdict = gate.classify(
        gate.licences_of(
            dist(
                "tramposo",
                [classifier("GNU General Public License v2 (GPLv2)")],
                License="GPL-2.0, not to be confused with the Lesser variant",
            )
        )
    )
    assert verdict.violates


def test_mpl_1_1_a_secas_no_es_una_licencia_aprobada() -> None:
    """La regla 10 admite MPL 2.0, no la 1.1, y la diferencia no se redondea."""
    verdict = gate.classify(
        gate.licences_of(dist("viejo", [classifier("Mozilla Public License 1.1 (MPL 1.1)")]))
    )
    assert verdict.elected is None
    assert not verdict.violates, "no es prohibida, es no aprobada: son cosas distintas"


def test_una_licencia_ilegible_no_pasa_como_aprobada() -> None:
    verdict = gate.classify(gate.licences_of(dist("opaco", [])))
    assert verdict.licences == ["UNKNOWN"]
    assert verdict.elected is None


# --- lo que tiene que aceptar ---------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "MIT License",
        "BSD License",
        "Apache Software License",
        "Apache-2.0",
        "ISC License (ISCL)",
        "Mozilla Public License 2.0 (MPL 2.0)",
        "Python Software Foundation License",
        # El sufijo de versión: `\\bLGPL\\b` fallaba contra `LGPLv2+`, que es exactamente cómo
        # lo escribe PyPI.
        "GNU Lesser General Public License v2 or later (LGPLv2+)",
        "GNU Lesser General Public License v3 (LGPLv3)",
    ],
)
def test_las_licencias_permitidas_se_reconocen(text: str) -> None:
    verdict = gate.classify(gate.licences_of(dist("permisivo", [classifier(text)])))
    assert verdict.elected is not None, f"'{text}' debería estar permitida"
    assert not verdict.violates


def test_un_paquete_con_varias_licencias_se_elige_y_la_eleccion_se_ve() -> None:
    """El caso de `pyphen`: GPL o LGPL o MPL 1.1.

    Multi-licenciar existe para que quien distribuye elija. Lo que la compuerta tiene que
    rechazar es el paquete que no deja elección.
    """
    verdict = gate.classify(
        gate.licences_of(
            dist(
                "tri",
                [
                    classifier("GNU General Public License v2 or later (GPLv2+)"),
                    classifier("GNU Lesser General Public License v2 or later (LGPLv2+)"),
                    classifier("Mozilla Public License 1.1 (MPL 1.1)"),
                ],
            )
        )
    )
    assert not verdict.violates
    assert verdict.elected is not None and "Lesser" in verdict.elected
    assert verdict.elected_from_several
    assert "elegida entre" in verdict.summary


def test_una_sola_licencia_no_se_presenta_como_una_eleccion() -> None:
    verdict = gate.classify(gate.licences_of(dist("simple", [classifier("MIT License")])))
    assert not verdict.elected_from_several
    assert verdict.summary == "MIT License"


# --- de dónde sale la licencia --------------------------------------------------------
def test_la_expresion_de_licencia_moderna_se_lee_y_se_parte_por_or() -> None:
    """PEP 639: los paquetes nuevos declaran `License-Expression`, a veces con un OR."""
    licences = gate.licences_of(dist("moderno", [], **{"License-Expression": "Apache-2.0 OR MIT"}))
    assert licences == ["Apache-2.0", "MIT"]


def test_un_texto_de_licencia_entero_no_se_toma_por_el_nombre_de_la_licencia() -> None:
    """El campo `License` a veces trae el cuerpo completo; eso no es un nombre."""
    licences = gate.licences_of(dist("verboso", [], License="x" * 500))
    assert licences == ["UNKNOWN"]


def test_los_overrides_manuales_ganan_y_son_pocos() -> None:
    """Una lista de excepciones que crece es una lista que dejó de significar algo."""
    assert len(gate.MANUAL_OVERRIDES) <= 5
    name = next(iter(gate.MANUAL_OVERRIDES))
    assert gate.licences_of(dist(name, [classifier("GNU General Public License v3")])) == [
        gate.MANUAL_OVERRIDES[name]
    ]


# --- y el cierre de dependencias real -------------------------------------------------
def test_el_cierre_real_no_tiene_ninguna_licencia_sin_clasificar() -> None:
    """Si esto falla, alguien añadió una dependencia cuya licencia nadie leyó.

    Corre aquí y no solo en CI porque el momento de enterarse es antes de empujar.
    """
    from importlib import metadata as importlib_metadata

    closure = gate.dependency_closure(gate.declared_dependencies())
    if not closure:
        pytest.skip("sin cierre de dependencias resoluble en este entorno")

    unclassified: list[str] = []
    forbidden: list[str] = []
    for distribution in importlib_metadata.distributions():
        name = distribution.metadata.get("Name")
        if not name or gate.normalize(name) not in closure:
            continue
        verdict = gate.classify(gate.licences_of(distribution))
        if verdict.violates:
            forbidden.append(f"{name}: {'; '.join(verdict.forbidden)}")
        elif verdict.elected is None:
            unclassified.append(f"{name}: {verdict.summary}")

    assert not forbidden, "licencias prohibidas en el cierre: " + "; ".join(forbidden)
    assert not unclassified, (
        "licencias que la compuerta no sabe leer: "
        + "; ".join(unclassified)
        + ". Lea la licencia y añada el paquete a MANUAL_OVERRIDES"
    )
