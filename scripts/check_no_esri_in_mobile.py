#!/usr/bin/env python3
"""ADR-003 — fail the build if any Esri artifact reaches the Android app.

The mobile app must carry no proprietary component and no per-device Esri licence.
It talks only to our own API; the geodatabase is reached by the arcpy agent on the
server side (ADR-008).

Scans Gradle build files and version catalogs under android/ for Esri coordinates
and for the Esri Maven repository, which is the other way such a dependency gets in.

Usage:  python scripts/check_no_esri_in_mobile.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANDROID_DIR = REPO_ROOT / "android"

# Coordinates and repositories that would introduce a proprietary SDK.
FORBIDDEN_PATTERNS = [
    (r"com\.esri[.:]", "dependencia Maven de Esri"),
    (r"arcgis-maps-kotlin", "ArcGIS Maps SDK for Kotlin"),
    (r"arcgis-android", "ArcGIS Runtime SDK for Android"),
    (r"esri\.com/arcgis/repository", "repositorio Maven de Esri"),
    (r"esri\.com/arcgis/repository/arcgis", "repositorio Maven de Esri"),
]

SCANNED_NAMES = {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"}
SCANNED_SUFFIXES = {".toml"}  # Gradle version catalogs (libs.versions.toml)


def scan() -> list[tuple[str, int, str, str]]:
    if not ANDROID_DIR.exists():
        return []
    compiled = [(re.compile(p, re.IGNORECASE), why) for p, why in FORBIDDEN_PATTERNS]
    findings: list[tuple[str, int, str, str]] = []
    for path in ANDROID_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.name not in SCANNED_NAMES and path.suffix not in SCANNED_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, why in compiled:
                if pattern.search(line):
                    findings.append((rel, lineno, line.strip(), why))
    return findings


def main() -> int:
    findings = scan()
    if not findings:
        if not ANDROID_DIR.exists():
            print("OK — módulo Android aún no existe (se crea en I4)")
        else:
            print("OK — sin artefactos de Esri en el módulo Android")
        return 0

    print("FALLA ADR-003 — artefactos de Esri en el módulo Android:\n")
    for rel, lineno, line, why in findings:
        print(f"  {rel}:{lineno}  ->  {why}")
        print(f"      {line}")
    print(
        "\nEl móvil no lleva componentes propietarios ni licencias Esri por dispositivo. "
        "Use MapLibre Native para el mapa y la API propia para los datos. Ver ADR-003 y "
        "CLAUDE.md regla 6."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
