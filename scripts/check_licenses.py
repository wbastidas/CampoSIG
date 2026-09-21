#!/usr/bin/env python3
"""SRS 0.7 — verify third-party licences and generate THIRD_PARTY_LICENSES.md.

Allowed: MIT, BSD (2/3-clause), Apache 2.0, MPL 2.0, LGPL (dynamically linked),
ISC, PSF, and CC-BY-4.0 for model weights only.

Forbidden in anything we distribute: AGPL and GPL. The exception the SRS grants is
narrow — self-hosted infrastructure services, unmodified and not linked to our code
(Grafana, Loki) — and those are not Python dependencies, so they never appear here.

Reads installed distribution metadata, so it reflects what would actually ship.

Only the project's own dependency closure is checked, resolved transitively from the
runtime dependencies declared in backend/pyproject.toml. That is precisely "what would
ship": packages merely present in the interpreter (Debian's python-apt is GPL, for
instance) are not ours to distribute. Run with --all to audit everything installed.

Usage:  python scripts/check_licenses.py [--output THIRD_PARTY_LICENSES.md] [--all]
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ALLOWED = re.compile(
    r"\b(MIT|BSD|Apache(\s|-)?(Software\s)?(License)?(\s|-)?2\.0|Apache-2\.0|ISC|"
    r"MPL(\s|-)?2\.0|Mozilla Public License 2\.0|Python Software Foundation|PSF|"
    r"LGPL|CC-BY-4\.0|Unlicense|Zlib|Historical Permission Notice)\b",
    re.IGNORECASE,
)
# Matched first: AGPL/GPL without the LGPL prefix and without "or later" exceptions.
FORBIDDEN = re.compile(r"\b(AGPL|Affero|(?<!L)GPL(?!.*Lesser))\b", re.IGNORECASE)

# Packages whose metadata omits or garbles the licence, verified by hand.
# Each entry is a deliberate assertion, not a way to silence the check.
MANUAL_OVERRIDES = {
    "typing-extensions": "PSF-2.0",
    "certifi": "MPL-2.0",
}


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str | None:
    """Extract the distribution name from a PEP 508 requirement string."""
    # Drop environment markers and extras before the version specifier.
    head = requirement.split(";")[0].strip()
    match = re.match(r"^([A-Za-z0-9._-]+)", head)
    return normalize(match.group(1)) if match else None


def declared_dependencies() -> list[str]:
    """Runtime dependencies declared in backend/pyproject.toml.

    Optional dev extras are excluded: linters and test runners are not distributed,
    so their licences do not constrain us.
    """
    pyproject = REPO_ROOT / "backend" / "pyproject.toml"
    if not pyproject.exists():
        return []
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies", []) or []
    return [name for name in (requirement_name(d) for d in deps) if name]


def dependency_closure(roots: list[str]) -> set[str]:
    """Transitively resolve installed dependencies starting from the declared roots."""
    closure: set[str] = set()
    queue = list(roots)
    while queue:
        name = queue.pop()
        if name in closure:
            continue
        closure.add(name)
        try:
            requires = metadata.requires(name) or []
        except metadata.PackageNotFoundError:
            # Declared but not installed: reported by the caller, not fatal here.
            continue
        for requirement in requires:
            # Skip requirements gated behind an extra we do not install.
            if "extra ==" in requirement:
                continue
            dep = requirement_name(requirement)
            if dep and dep not in closure:
                queue.append(dep)
    return closure


def licence_of(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    declared = (meta.get("License") or "").strip()
    classifiers = [c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    name = (meta.get("Name") or "").lower()
    if name in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[name]
    # Classifiers are more reliable than the free-text License field, which often
    # contains an entire licence body.
    if classifiers:
        return "; ".join(c.split("::")[-1].strip() for c in classifiers)
    if declared and len(declared) < 200:
        return declared
    return "UNKNOWN"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="THIRD_PARTY_LICENSES.md")
    parser.add_argument(
        "--all",
        action="store_true",
        help="include distributions outside the environment (system packages)",
    )
    args = parser.parse_args()

    roots = declared_dependencies()
    closure = set() if args.all else dependency_closure(roots)
    if not args.all and not closure:
        print(
            "AVISO — no se pudo resolver el cierre de dependencias "
            "(¿backend/pyproject.toml ausente?). Nada que verificar."
        )
        return 0

    rows: list[tuple[str, str, str]] = []
    violations: list[tuple[str, str]] = []
    unknown: list[str] = []
    skipped = 0

    for dist in sorted(metadata.distributions(), key=lambda d: (d.metadata.get("Name") or "").lower()):
        name = dist.metadata.get("Name")
        if not name:
            continue
        if not args.all and normalize(name) not in closure:
            skipped += 1
            continue
        lic = licence_of(dist)
        rows.append((name, dist.version, lic))
        if FORBIDDEN.search(lic) and not ALLOWED.search(lic):
            violations.append((name, lic))
        elif lic == "UNKNOWN" or not ALLOWED.search(lic):
            unknown.append(f"{name} ({lic})")

    out = REPO_ROOT / args.output
    lines = [
        "# Licencias de terceros",
        "",
        "Generado automáticamente por `scripts/check_licenses.py`. No editar a mano.",
        "",
        "Política: SRS sección 0.7 y CLAUDE.md regla 10. Permitidas MIT, BSD, Apache 2.0,",
        "MPL 2.0, ISC, PSF y LGPL con enlace dinámico. Prohibidas AGPL y GPL en lo que se",
        "distribuye. CC-BY-4.0 se admite solo para pesos de modelos, con atribución.",
        "",
        "| Paquete | Versión | Licencia |",
        "|---|---|---|",
    ]
    lines += [f"| {n} | {v} | {lic} |" for n, v, lic in rows]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Inventario escrito en {args.output} ({len(rows)} paquetes)")
    if skipped:
        print(
            f"Omitidos {skipped} paquetes ajenos al cierre de dependencias del proyecto "
            "(use --all para auditarlos)"
        )
    missing = sorted(n for n in roots if normalize(n) not in {normalize(r[0]) for r in rows})
    if missing and not args.all:
        print(f"AVISO — dependencias declaradas no instaladas: {', '.join(missing)}")

    if violations:
        print("\nFALLA — licencias prohibidas (AGPL/GPL) en dependencias distribuidas:\n")
        for name, lic in violations:
            print(f"  {name}: {lic}")
        print("\nVer SRS 0.7 y CLAUDE.md regla 10.")
        return 1

    if unknown:
        print(f"\nAVISO — {len(unknown)} paquetes con licencia no reconocida, revisar a mano:")
        for item in unknown[:20]:
            print(f"  {item}")
        if len(unknown) > 20:
            print(f"  ... y {len(unknown) - 20} más")

    print("\nOK — sin licencias prohibidas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
