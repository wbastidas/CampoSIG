"""Load the regulatory seed from a console (RF-150, ADR-007).

    python -m app.regulatory.cli --verified-by "maria.perez" --only-verified

Why this exists as a command and not only as an endpoint: loading the limits is the first thing a
deployment does, before anybody has a session, and the person doing it is at a terminal. It is also
the operation that most needs a dry run — a seed file with a wrong `effective_from` would close the
period that is in force today.

Two properties the command keeps:

* **The file decides what counts as verified; the operator only says who they are.** Passing
  ``--verified-by`` does not certify anything the file has not marked ``verified: true``. One
  careless flag must not certify seven numbers nobody read.
* **Nothing is written until the whole file validates.** A seed half applied leaves the platform
  evaluating some rules against this year's limits and others against last year's, which is worse
  than not loading it at all.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from app.infra.database import get_session_factory, import_all_models
from app.regulatory.loader import apply_seed, load_seed, unverified_codes, validate_seed
from app.regulatory.rules import REQUIRED_PARAMETER_CODES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.regulatory.cli",
        description="Carga los parámetros regulatorios desde el archivo de semilla.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Archivo de semilla. Por omisión, seeds/regulatory-ec.yaml del repositorio.",
    )
    parser.add_argument(
        "--verified-by",
        default=None,
        help=(
            "Quién leyó el texto oficial. Solo certifica las entradas que el propio archivo "
            "marca «verified: true»."
        ),
    )
    parser.add_argument(
        "--only-verified",
        action="store_true",
        help="Cargar únicamente las entradas verificadas. Lo que usa una instalación productiva.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validar y mostrar lo que haría, sin escribir nada.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        seed = load_seed(args.path)
    except (OSError, yaml.YAMLError) as exc:
        # A traceback is the wrong answer to a mistyped path: the person is at a terminal and the
        # useful output is one line saying which file could not be read.
        print(f"No se pudo leer el archivo de semilla: {exc}", file=sys.stderr)
        return 2

    problems = validate_seed(seed)
    if problems:
        print("El archivo de semilla tiene problemas y no se cargó nada:", file=sys.stderr)
        for problem in problems:
            print(f"  · {problem}", file=sys.stderr)
        return 2

    entries = seed["parameters"]
    verified = [entry for entry in entries if entry.get("verified")]
    print(
        f"{len(entries)} parámetro(s) en el archivo; {len(verified)} marcado(s) como verificado(s)."
    )
    if args.only_verified:
        print(f"Con --only-verified se cargarían {len(verified)}.")
    if args.verified_by and not verified:
        # Decirlo en voz alta: quien pasó --verified-by cree estar certificando algo.
        print(
            "Aviso: se indicó --verified-by pero el archivo no marca ninguna entrada como "
            "verificada, así que no se certificará ningún valor.",
            file=sys.stderr,
        )

    if args.dry_run:
        for entry in entries:
            mark = "✓" if entry.get("verified") else " "
            print(
                f"  [{mark}] {entry['code']} desde {entry['effective_from']} · {entry['norm_ref']}"
            )
        print("Simulación: no se escribió nada.")
        return 0

    import_all_models()
    with get_session_factory()() as session:
        written = apply_seed(
            session,
            seed,
            verified_by=args.verified_by,
            only_verified=args.only_verified,
            actor=args.verified_by,
        )
        session.commit()
        pending = unverified_codes(session)

    print(f"Escritos {len(written)} parámetro(s).")
    if pending:
        # La lista que una lista de verificación de despliegue tiene que tener vacía.
        print(f"Sin verificar contra el texto oficial ({len(pending)}):")
        for code in pending:
            print(f"  · {code}")
    missing = sorted(set(REQUIRED_PARAMETER_CODES) - {str(entry["code"]) for entry in entries})
    if missing:
        print(f"Códigos que alguna regla necesita y el archivo no trae ({len(missing)}):")
        for code in missing:
            print(f"  · {code}")
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())
