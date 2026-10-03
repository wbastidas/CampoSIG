"""La compuerta de licencias de datasets (addendum 6.2, guía §14).

Una compuerta que solo se ha visto aprobar no está probada. El modo de fallo real no es que
alguien elija mal hoy: es que alguien añada un dataset dentro de seis meses y nadie vuelva a
leer la licencia. Así que cada forma de colarse tiene su test, y el registro real tiene el
suyo — si cambia a algo que no se puede publicar, esta suite lo dice antes que CI.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "ml" / "datasets" / "registry.yaml"
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_dataset_licenses.py"


def _load_gate() -> Any:
    """Import the CI script as a module, so the test exercises what CI runs."""
    spec = importlib.util.spec_from_file_location("check_dataset_licenses", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


@pytest.fixture
def registry() -> dict[str, Any]:
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))


def dataset(registry: dict[str, Any], dataset_id: str) -> dict[str, Any]:
    return next(item for item in registry["datasets"] if item["id"] == dataset_id)


class TestTheRealRegistryIsPublishable:
    def test_the_registry_passes(self, registry) -> None:
        assert gate.check(registry) == []

    def test_only_owned_data_trains_the_deployed_model(self, registry) -> None:
        """The conclusion of the dataset research, asserted rather than written down.

        Every public electrical dataset found is either NonCommercial, copyleft, restricted
        or undeclared. The model that ships is trained on the utility's own images.
        """
        deployed = [d for d in registry["datasets"] if "deployed" in d["allowed_uses"]]
        assert deployed, "algún dataset tiene que poder entrenar el modelo desplegado"
        assert all(d["license"] == "proprietary-owned" for d in deployed)

    def test_every_public_dataset_has_been_looked_at(self, registry) -> None:
        for entry in registry["datasets"]:
            assert entry.get("notes"), f"'{entry['id']}' sin nota que explique su estado"
            assert entry.get("url"), f"'{entry['id']}' sin fuente"


class TestTheGateDetects:
    def test_a_noncommercial_dataset_cannot_train_the_deployed_model(self, registry) -> None:
        altered = copy.deepcopy(registry)
        dataset(altered, "insplad")["allowed_uses"] = ["benchmark", "deployed"]
        problems = gate.check(altered)
        assert any("NonCommercial" in problem for problem in problems)

    def test_copyleft_cannot_even_pretrain(self, registry) -> None:
        """Pre-training is still training: the weights carry the obligation into the APK."""
        altered = copy.deepcopy(registry)
        dataset(altered, "stn-plad")["allowed_uses"] = ["pretraining"]
        problems = gate.check(altered)
        assert any("copyleft" in problem for problem in problems)

    def test_an_undeclared_license_is_forbidden_not_assumed_permissive(self, registry) -> None:
        altered = copy.deepcopy(registry)
        dataset(altered, "cplid")["allowed_uses"] = ["pretraining"]
        assert any("sin licencia" in problem for problem in gate.check(altered))

    def test_an_unverified_license_blocks_any_use(self, registry) -> None:
        altered = copy.deepcopy(registry)
        dataset(altered, "ttpla")["allowed_uses"] = ["benchmark"]
        assert any("sin verificar" in problem for problem in gate.check(altered))

    def test_a_permissive_license_outside_the_allowed_list_is_refused(self, registry) -> None:
        """Share-alike is permissive and still not deployable. The list is the authority."""
        altered = copy.deepcopy(registry)
        altered["datasets"].append(
            {
                "id": "nuevo",
                "name": "Nuevo",
                "url": "https://example.org",
                "content": "x",
                "domain": "ground_distribution",
                "license": "CC-BY-SA-4.0",
                "license_verified_on": "2026-09-21",
                "allowed_uses": ["deployed"],
                "notes": "x",
            }
        )
        assert any("deployable_licenses" in problem for problem in gate.check(altered))

    def test_an_invented_use_is_refused(self, registry) -> None:
        altered = copy.deepcopy(registry)
        dataset(altered, "insplad")["allowed_uses"] = ["produccion"]
        assert any("no reconocidos" in problem for problem in gate.check(altered))

    def test_a_duplicate_id_is_refused(self, registry) -> None:
        altered = copy.deepcopy(registry)
        altered["datasets"].append(copy.deepcopy(dataset(altered, "insplad")))
        assert any("duplicado" in problem for problem in gate.check(altered))

    def test_a_dataset_without_a_license_field_is_refused(self, registry) -> None:
        altered = copy.deepcopy(registry)
        del dataset(altered, "insplad")["license"]
        assert any("sin campo 'license'" in problem for problem in gate.check(altered))

    def test_a_registry_without_a_deployable_list_is_refused(self, registry) -> None:
        altered = copy.deepcopy(registry)
        del altered["deployable_licenses"]
        assert any("deployable_licenses" in problem for problem in gate.check(altered))


@pytest.mark.parametrize(
    "license_id",
    ["GPL-3.0", "AGPL-3.0", "LGPL-2.1", "CC-BY-NC-4.0", "restricted", "undeclared", "unverified"],
)
def test_forbidden_license_families_are_recognised(license_id: str) -> None:
    assert gate.forbidden_reason(license_id) is not None


@pytest.mark.parametrize("license_id", ["MIT", "Apache-2.0", "BSD-3-Clause", "proprietary-owned"])
def test_permissive_licenses_are_not_flagged(license_id: str) -> None:
    assert gate.forbidden_reason(license_id) is None
