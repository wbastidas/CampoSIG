#!/usr/bin/env python3
"""RF-305 — fail the build if real data-model identifiers leak into source code.

The platform must not depend on one data model (ADR-004). Class, field and domain
names from the customer's geodatabase belong in `profiles/` only; everywhere else
the code speaks the canonical vocabulary and resolves real names at runtime through
`model_profile/resolver.py`.

This check is deliberately blunt: a build that fails here is cheap to fix, while a
leak that ships turns "configuration" into "programming" for the next installation.

Usage:  python scripts/check_data_model_leak.py [--list]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Two categories, because they leak for different reasons and have different homes.
#
# 1) CUSTOMER_MODEL — feature classes, tables and domain-bearing fields specific to this
#    customer's geodatabase (docs/modelo-datos-cnel/). These belong in profiles/ only.
#    Generic words (CODIGO, VOLTAJE) are excluded on purpose: they would produce false
#    positives without proving anything.
CUSTOMER_MODEL_IDENTIFIERS = [
    # Feature classes / tables
    "EstructuraSoporte", "ESTRUCTURAENPOSTE", "EstructuraANivel", "CATALOGOESTRUCTURA",
    "PuestoTransfDistribucion", "UNIDADTRANSFDISTRIBUCION", "PuestoTransfPotencia",
    "UNIDADTRANSFPOTENCIA", "PuestoSeccionador", "PuestoSeccionadorFusible",
    "PuestoProteccionDinamico", "UNIDADPROTECCIONDINAMICO", "PuestoProteccionBajaTension",
    "PuestoReguladorTension", "UNIDADREGULADORTENSION", "PuestoCorrectorFactorPotencia",
    "UNIDADCAPACITOR", "TramoDistribucionAereo", "TramoDistribucionSubterraneo",
    "TramoBajaTensionAereo", "TramoBajaTensionSubterraneo", "TramoSubtransmisionAereo",
    "TramoSubtransmisionSubterraneo", "CIRCUITOFUENTE", "CONEXIONCONSUMIDOR",
    "ATRIBUTOSCONSUMIDOR", "PuntoCarga", "PuntoApertura", "PuntoMiscelaneo",
    "GeneradorDistribuido", "OPERADORAENPOSTE", "INSTITUCIONENPOSTE", "DATOSOPERADORA",
    "Electrico_RedGeom", "Electrico_Complementos",
    # Volatile-by-business-unit domain field (01_Dominios.md warning).
    "ALIMENTADORID",
]

# 2) CONNECTIVITY — Esri's own geometric-network fields. These are NOT customer schema:
#    they are identical in every geometric network, in every utility. So they are not a
#    data-model leak, and the safety guard that refuses them must name them literally.
#    Making that guard read the list from a profile would let a bad profile switch the
#    safety off, which is strictly worse. They are still forbidden everywhere else,
#    because writing them is the failure mode ADR-001 exists to prevent.
#    Note: ENABLED is a connectivity field too (ADR-001) but is NOT watched here. It is
#    an ordinary English word that appears in unrelated identifiers, so grepping for it
#    would produce constant false positives and train people to ignore this check. It is
#    enforced where it actually matters — at runtime, by ModelResolver.assert_writable
#    and the agent's guards, both of which include it and are covered by tests.
CONNECTIVITY_IDENTIFIERS = [
    "ANCILLARYROLE", "CIRCUITSOURCEGUID", "PARENTCIRCUITSOURCEGUID",
    "ELECTRICTRACEWEIGHT",
]

FORBIDDEN_IDENTIFIERS = CUSTOMER_MODEL_IDENTIFIERS + CONNECTIVITY_IDENTIFIERS

# Where customer-model names are legitimate: profiles map canonical keys to real names,
# docs describe the model, and the checker itself must list them.
ALLOWED_PREFIXES = ("profiles/", "docs/", "scripts/check_data_model_leak.py", ".git/")

# Where connectivity field names are legitimate: ONLY code whose purpose is to refuse
# them, plus the tests proving it does. Each entry is a deliberate exception, and the
# list is short on purpose — if it grows, the refusal logic has been duplicated and
# should be consolidated instead of exempted again.
CONNECTIVITY_ALLOWED_PATHS = (
    # The agent's guard and its tests (ADR-008).
    "gis-agent/sigec_agent/guards.py",
    "gis-agent/tests/test_guards.py",
    "gis-agent/tests/test_apply_batch.py",
    # The backend resolver's write-safety check and its tests (ADR-001).
    "backend/app/model_profile/resolver.py",
    "backend/tests/unit/test_rf301_profile_resolution.py",
    # The ArcGIS mock, which must reproduce the real service's rejection so that a
    # regression in write safety fails against the fixture, not against production.
    "tools/arcgis-mock/app.py",
)

SCANNED_SUFFIXES = {".py", ".kt", ".kts", ".ts", ".tsx", ".js", ".jsx", ".sql", ".java"}


def is_exempt(rel_path: str) -> bool:
    return any(rel_path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def is_allowed_identifier(rel_path: str, identifier: str) -> bool:
    """Whether this specific identifier is legitimate in this specific file."""
    if identifier in CONNECTIVITY_IDENTIFIERS:
        return rel_path in CONNECTIVITY_ALLOWED_PATHS
    return False


def scan() -> list[tuple[str, int, str]]:
    pattern = re.compile("|".join(re.escape(name) for name in FORBIDDEN_IDENTIFIERS))
    findings: list[tuple[str, int, str]] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if is_exempt(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in pattern.finditer(line):
                identifier = match.group(0)
                if is_allowed_identifier(rel, identifier):
                    continue
                findings.append((rel, lineno, identifier))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="print the forbidden identifiers")
    args = parser.parse_args()

    if args.list:
        for name in FORBIDDEN_IDENTIFIERS:
            print(name)
        return 0

    findings = scan()
    if not findings:
        print(
        f"OK — sin fugas del modelo de datos "
        f"({len(CUSTOMER_MODEL_IDENTIFIERS)} identificadores del cliente + "
        f"{len(CONNECTIVITY_IDENTIFIERS)} campos de conectividad vigilados)"
    )
        return 0

    print("FALLA RF-305 — identificadores del modelo de datos real fuera de profiles/:\n")
    for rel, lineno, name in findings:
        print(f"  {rel}:{lineno}  ->  {name}")
    print(
        "\nLos nombres del modelo del cliente solo pueden vivir en profiles/: use el "
        "vocabulario canónico (AMD) y resuelva el nombre real con model_profile/resolver.py "
        "(ADR-004, CLAUDE.md regla 4).\nLos campos de conectividad solo pueden aparecer en el "
        "guard que los rechaza (ADR-001, CLAUDE.md regla 5)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
