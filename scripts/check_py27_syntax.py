#!/usr/bin/env python3
"""ADR-008 — verify the arcpy agent stays valid Python 2.7.

The agent runs on ArcMap 10.8.1's interpreter, which is Python 2.7.18 (finding H12):
it is the only arcpy that can edit geometric networks. CI has no Python 2.7, so this
parses each file with Python 3's ast and rejects constructs that 2.7 cannot parse.

It is a static approximation, not a substitute for running on 2.7 — it catches the
mistakes people actually make (f-strings, annotations, walrus) rather than proving
compatibility. The real check is the agent running on the ArcMap box in I1.

Usage:  python scripts/check_py27_syntax.py <path> [<path> ...]
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


class Py3OnlyVisitor(ast.NodeVisitor):
    """Collects constructs that Python 2.7 cannot parse."""

    def __init__(self) -> None:
        self.findings: list[tuple[int, str]] = []

    def _flag(self, node: ast.AST, what: str) -> None:
        self.findings.append((getattr(node, "lineno", 0), what))

    # --- syntax Python 2.7 lacks entirely -----------------------------------
    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        self._flag(node, "f-string (use '%' o .format())")
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._flag(node, "operador walrus ':='")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._flag(node, "anotación de variable (use un comentario de tipo)")
        self.generic_visit(node)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self._flag(node, "declaración 'nonlocal'")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._flag(node, "'async def'")
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await) -> None:
        self._flag(node, "'await'")
        self.generic_visit(node)

    def visit_MatchValue(self, node: ast.AST) -> None:  # pragma: no cover - 3.10+
        self._flag(node, "'match' statement")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.returns is not None:
            self._flag(node, "anotación de retorno en def")
        for arg in list(node.args.args) + list(node.args.kwonlyargs):
            if arg.annotation is not None:
                self._flag(node, "anotación de argumento '%s'" % arg.arg)
        if node.args.kwonlyargs:
            self._flag(node, "argumentos keyword-only")
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        # 'raise X from Y' is Python 3 only.
        if getattr(node, "cause", None) is not None:
            self._flag(node, "'raise ... from ...'")
        self.generic_visit(node)

    def visit_Starred(self, node: ast.Starred) -> None:
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.AST) -> None:
        self._flag(node, "'yield from'")


def check_file(path: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [(exc.lineno or 0, "no parsea: %s" % exc.msg)]
    visitor = Py3OnlyVisitor()
    visitor.visit(tree)
    return visitor.findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="files or directories to check")
    args = parser.parse_args()

    files: list[Path] = []
    for raw in args.paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.is_file():
            files.append(path)
        else:
            print("AVISO — no existe: %s" % raw)

    total = 0
    for path in files:
        findings = check_file(path)
        if findings:
            total += len(findings)
            print("\n%s:" % path)
            for lineno, what in findings:
                print("  línea %d: %s" % (lineno, what))

    if total:
        print(
            "\nFALLA ADR-008 — el agente debe ser Python 2.7 válido: es el único arcpy "
            "que edita redes geométricas (H12). %d problema(s) en %d archivo(s)."
            % (total, len(files))
        )
        return 1

    print("OK — %d archivo(s) compatibles con Python 2.7" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
