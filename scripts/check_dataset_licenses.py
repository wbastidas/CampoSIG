#!/usr/bin/env python3
"""Cuarta verificación obligatoria: licencias de datasets de visión (addendum 6.2).

La publicación de un paquete de modelos falla si un dataset cuya licencia no lo permite
participó en el entrenamiento del modelo que se despliega. Eso no se resuelve leyendo un
README antes de empezar: se resuelve con una compuerta que corre cada vez, porque el modo
de fallo real no es "alguien eligió mal", es "alguien añadió un dataset seis meses después
y nadie volvió a mirar la licencia".

Comprueba tres cosas sobre `ml/datasets/registry.yaml`:

1. Ningún dataset declara `deployed` con una licencia que no esté en `deployable_licenses`.
2. Ninguna licencia prohibida —copyleft fuerte, NonCommercial, sin declarar, sin verificar—
   aparece con permisos de entrenamiento de ningún tipo.
3. Todo dataset con algún uso permitido tiene fecha de verificación de licencia. Una
   licencia sin verificar no es permisiva: es desconocida, y se trata como prohibida.

Uso:
    python scripts/check_dataset_licenses.py [ruta/al/registry.yaml]

Sale con 1 y explica el problema si algo no cuadra.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = REPO_ROOT / "ml" / "datasets" / "registry.yaml"

#: Usos que implican que el dataset entra a un entrenamiento.
TRAINING_USES = frozenset({"pretraining", "deployed"})

#: Familias de licencia que nunca pueden entrenar nada que se entregue, con el motivo en
#: las palabras de la regla 10 de CLAUDE.md.
FORBIDDEN_PATTERNS: dict[str, str] = {
    "GPL": "copyleft fuerte: arrastraría la licencia al APK",
    "AGPL": "copyleft de red: prohibida en código propio y en el APK",
    "NC": "NonCommercial: no puede entrenar un modelo que se entrega a una empresa",
    "restricted": "acceso restringido: no permite uso derivado",
    "undeclared": "sin licencia declarada: sin licencia no hay permiso",
    "unverified": "licencia no verificada: desconocida se trata como prohibida",
}

VALID_USES = frozenset({"benchmark", "pretraining", "deployed"})


def forbidden_reason(license_id: str) -> str | None:
    """Por qué esta licencia no puede entrenar, o None si puede."""
    upper = license_id.upper()
    for pattern, reason in FORBIDDEN_PATTERNS.items():
        # 'GPL' coincide dentro de 'AGPL-3.0' y de 'LGPL', y así debe ser para este uso:
        # ninguna variante de copyleft entrena un modelo que se distribuye.
        if pattern.upper() in upper:
            return reason
    return None


def check(registry: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    deployable = {str(item) for item in registry.get("deployable_licenses", [])}
    if not deployable:
        problems.append("el registro no declara 'deployable_licenses'")

    seen_ids: set[str] = set()
    for entry in registry.get("datasets", []):
        dataset_id = str(entry.get("id", "<sin id>"))
        if dataset_id in seen_ids:
            problems.append(f"'{dataset_id}': id duplicado en el registro")
        seen_ids.add(dataset_id)

        license_id = str(entry.get("license", "")).strip()
        uses = {str(use) for use in entry.get("allowed_uses", [])}
        verified = entry.get("license_verified_on")

        if not license_id:
            problems.append(f"'{dataset_id}': sin campo 'license'")
            continue

        unknown = uses - VALID_USES
        if unknown:
            problems.append(
                f"'{dataset_id}': usos no reconocidos {sorted(unknown)}; "
                f"válidos: {sorted(VALID_USES)}"
            )

        reason = forbidden_reason(license_id)
        if reason and uses & TRAINING_USES:
            problems.append(
                f"'{dataset_id}' ({license_id}) declara {sorted(uses & TRAINING_USES)} "
                f"y no puede: {reason}"
            )

        if "deployed" in uses and license_id not in deployable:
            problems.append(
                f"'{dataset_id}' ({license_id}) entrena el modelo desplegado pero su "
                f"licencia no está en deployable_licenses: {sorted(deployable)}"
            )

        if uses and not verified:
            problems.append(
                f"'{dataset_id}' tiene usos permitidos {sorted(uses)} pero no tiene "
                "'license_verified_on'; una licencia sin verificar es desconocida"
            )

    return problems


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT_REGISTRY
    if not path.exists():
        print(f"ERROR: no existe el registro de datasets en {path}", file=sys.stderr)
        return 1

    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    problems = check(registry)

    if problems:
        print("ERROR — el registro de datasets no puede publicar un paquete de modelos:")
        for problem in problems:
            print(f"  · {problem}")
        return 1

    datasets = registry.get("datasets", [])
    deployed = [d["id"] for d in datasets if "deployed" in d.get("allowed_uses", [])]
    print(
        f"OK — {len(datasets)} datasets registrados; "
        f"{len(deployed)} pueden entrenar el modelo desplegado: {', '.join(deployed) or 'ninguno'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
