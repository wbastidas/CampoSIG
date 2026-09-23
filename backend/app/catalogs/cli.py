"""Load the catalogue seeds from a console (RF-034).

    python -m app.catalogs.cli --dry-run
    python -m app.catalogs.cli

Like the regulatory loader, this exists as a command because it is the first thing a deployment
does, before anybody has a session. And like it, the dry run is the important half: a seed file that
lost a catalogue would otherwise be discovered by a technician whose picker went from twenty values
to three.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from app.catalogs.loader import apply_seeds, load_files, validate
from app.infra.database import get_session_factory, import_all_models


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.catalogs.cli",
        description="Carga los catálogos operativos desde seeds/catalogs/.",
    )
    parser.add_argument("--path", type=Path, default=None, help="Directorio de semillas.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validar y mostrar lo que haría, sin escribir."
    )
    parser.add_argument(
        "--retire-missing",
        action="store_true",
        help=(
            "Desactivar los valores que el archivo ya no trae. Apagado por omisión: un archivo "
            "incompleto no debe poder vaciar un catálogo en producción."
        ),
    )
    parser.add_argument("--actor", default=None, help="Quién ejecuta la carga.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        documents = load_files(args.path)
    except (OSError, yaml.YAMLError) as exc:
        print(f"No se pudieron leer las semillas: {exc}", file=sys.stderr)
        return 2

    if not documents:
        print("No hay ningún catálogo en el directorio de semillas.", file=sys.stderr)
        return 2

    problems = validate(documents)
    if problems:
        print("Las semillas tienen problemas y no se cargó nada:", file=sys.stderr)
        for problem in problems:
            print(f"  · {problem}", file=sys.stderr)
        return 2

    empty = [
        str(document["catalog"]["code"]) for document in documents if not document.get("entries")
    ]
    for document in documents:
        header = document["catalog"]
        count = len(document.get("entries") or [])
        print(f"  {header['code']:<28} {count:>4} valor(es)  [{header.get('source', 'manual')}]")
    if empty:
        # Deliberately loud: an empty catalogue is a picker with nothing in it, and the reason
        # has to reach whoever is deploying, not only the file's own comment.
        print(f"Vacíos a propósito, con su motivo declarado: {', '.join(empty)}")

    if args.dry_run:
        print("Simulación: no se escribió nada.")
        return 0

    import_all_models()
    with get_session_factory()() as session:
        written = apply_seeds(
            session,
            documents,
            actor=args.actor or "carga.semilla",
            retire_missing=args.retire_missing,
        )
        session.commit()
    print(f"Escritos {sum(written.values())} valor(es) en {len(written)} catálogo(s).")
    if not args.retire_missing:
        print(
            "No se retiró nada: use --retire-missing si el archivo es la lista completa y quiere "
            "desactivar lo que falta."
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())
