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
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent

#: No trailing `\b` after the copyleft names: PyPI classifiers write `LGPLv2+` and
#: `MPL-2.0`, and a trailing word boundary fails on the version suffix. That is why `pyphen`
#: — offered under GPL **or** LGPL **or** MPL — used to land in the "review by hand" list
#: instead of being elected under LGPL, which is the licence this project actually takes it
#: under (rule 10: LGPL with dynamic linking; pyphen is imported, never combined).
#: "Apache Software License" without a version is accepted: every Apache licence on PyPI is
#: 2.0 in practice, and all Apache versions are permissive either way.
ALLOWED = re.compile(
    r"\b(MIT|BSD|Apache(\s|-)?(Software\s)?(License)?((\s|-)?2\.0)?|ISC|"
    r"MPL(\s|-)?2\.0|Mozilla Public License 2\.0|Python Software Foundation|PSF|"
    r"LGPL|Lesser General Public|CC-BY-4\.0|Unlicense|Zlib|Historical Permission Notice)",
    re.IGNORECASE,
)
#: Applied to **one** licence at a time, never to a joined list. The earlier version matched
#: against the whole concatenated set with a `(?!.*Lesser)` lookahead, so any package whose
#: metadata mentioned "Lesser" anywhere — a tri-licensed one, or a GPL-only one with a stray
#: word in its free-text field — stopped being a GPL match at all. That is how `pyphen` first
#: entered this project's closure without anybody deciding anything.
#: No trailing `\b` here either, and this one was not cosmetic: the standard PyPI classifier
#: is "GNU General Public License v3 (GPLv3)", where `GPL` is followed by `v`. With a trailing
#: word boundary the pattern never matched it, so the mandatory licence gate was blind to the
#: most common spelling of the licence it exists to refuse. Found by the negative test below,
#: not by a build.
FORBIDDEN = re.compile(r"\b(AGPL|Affero|(?<!L)GPL)", re.IGNORECASE)

#: The weak-copyleft forms that are not what FORBIDDEN is looking for. Checked explicitly so
#: the distinction is a rule and not a lookahead.
LESSER = re.compile(r"\b(LGPL|Lesser General Public)\b", re.IGNORECASE)

# Packages whose metadata omits or garbles the licence, verified by hand.
# Each entry is a deliberate assertion, not a way to silence the check.
MANUAL_OVERRIDES = {
    "typing-extensions": "PSF-2.0",
    "certifi": "MPL-2.0",
}


#: The project's own distributions. They are not third parties, so they belong in neither the
#: inventory nor the verdict — and with unreadable licences now fatal, leaving ours in made
#: `--all` fail on us.
OWN_DISTRIBUTIONS = {"sigec-backend"}


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


#: How a free-text licence field spells "you may pick one of these".
_OR_SEPARATORS = re.compile(r"\s+OR\s+|\s+or\s+|\s*\|\s*", re.IGNORECASE)


def licences_of(dist: metadata.Distribution) -> list[str]:
    """Every licence a package offers, as separate strings.

    Separate, not joined, because the decision differs: a package offering three licences is
    one we **choose** from, and collapsing them into one line is what let a GPL classifier and
    an LGPL classifier cancel each other out.
    """
    meta = dist.metadata
    name = (meta.get("Name") or "").lower()
    if name in MANUAL_OVERRIDES:
        return [MANUAL_OVERRIDES[name]]

    # Classifiers are more reliable than the free-text License field, which often contains an
    # entire licence body.
    classifiers = [c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    if classifiers:
        return [c.split("::")[-1].strip() for c in classifiers]

    expression = (meta.get("License-Expression") or "").strip()
    declared = expression or (meta.get("License") or "").strip()
    if declared and len(declared) < 200:
        parts = [part.strip() for part in _OR_SEPARATORS.split(declared) if part.strip()]
        return parts or [declared]
    return ["UNKNOWN"]


def is_allowed(licence: str) -> bool:
    """Whether this one licence is one the project may distribute under."""
    if FORBIDDEN.search(licence) and not LESSER.search(licence):
        return False
    return bool(ALLOWED.search(licence))


def is_forbidden(licence: str) -> bool:
    return bool(FORBIDDEN.search(licence)) and not LESSER.search(licence)


class Verdict(NamedTuple):
    """What the gate decided about one package, and why."""

    licences: list[str]
    #: The licence the project distributes under. Set when at least one is allowed.
    elected: str | None
    forbidden: list[str]

    @property
    def violates(self) -> bool:
        """A violation is a package with no allowed licence and at least one forbidden one.

        Not "any forbidden licence": a package offered under GPL **or** LGPL **or** MPL is one
        the project takes under LGPL, which is what multi-licensing is for. What the gate has
        to refuse is the package that leaves no choice.
        """
        return self.elected is None and bool(self.forbidden)

    @property
    def elected_from_several(self) -> bool:
        """Whether an election happened, which is a decision worth printing."""
        return self.elected is not None and len(self.licences) > 1

    @property
    def summary(self) -> str:
        """What goes in the inventory: the election first, then everything on offer."""
        if self.elected_from_several:
            offered = "; ".join(self.licences)
            return f"{self.elected} (elegida entre: {offered})"
        return "; ".join(self.licences)


def classify(licences: list[str]) -> Verdict:
    allowed = [lic for lic in licences if is_allowed(lic)]
    return Verdict(
        licences=licences,
        elected=allowed[0] if allowed else None,
        forbidden=[lic for lic in licences if is_forbidden(lic)],
    )


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
    elections: list[tuple[str, str, list[str]]] = []
    skipped = 0

    for dist in sorted(metadata.distributions(), key=lambda d: (d.metadata.get("Name") or "").lower()):
        name = dist.metadata.get("Name")
        if not name:
            continue
        if normalize(name) in OWN_DISTRIBUTIONS:
            continue
        if not args.all and normalize(name) not in closure:
            skipped += 1
            continue
        verdict = classify(licences_of(dist))
        rows.append((name, dist.version, verdict.summary))
        if verdict.violates:
            violations.append((name, "; ".join(verdict.forbidden)))
        elif verdict.elected is None:
            unknown.append(f"{name} ({verdict.summary})")
        elif verdict.elected_from_several:
            elections.append((name, verdict.elected, verdict.licences))

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
        "Un paquete ofrecido bajo varias licencias se distribuye bajo la que aparece como",
        "«elegida»: es una decisión del proyecto, no un detalle de metadatos. Las otras se",
        "listan para que la elección se pueda revisar.",
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

    if elections:
        # Printed, not silent: choosing LGPL over GPL for a tri-licensed package is a decision
        # the project takes, and a decision nobody can see is one nobody reviews.
        print(f"\nELECCIÓN — {len(elections)} paquetes ofrecen varias licencias:")
        for name, elected, offered in elections:
            print(f"  {name}: se distribuye bajo {elected} (ofrecidas: {'; '.join(offered)})")

    if unknown:
        # A failure, not a warning. Rule 10 says the project ships under approved licences;
        # a package whose licence the gate cannot name is a package nobody approved, and a
        # warning at the end of a green build is a warning nobody reads. The way out is an
        # entry in MANUAL_OVERRIDES, which is somebody having actually looked.
        print(f"\nFALLA — {len(unknown)} paquetes con licencia que la compuerta no puede leer:")
        for item in unknown:
            print(f"  {item}")
        print(
            "\nLea la licencia del paquete y añádalo a MANUAL_OVERRIDES en este script, o "
            "quítelo de las dependencias. Ver SRS 0.7 y CLAUDE.md regla 10."
        )
        return 1

    print("\nOK — sin licencias prohibidas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
