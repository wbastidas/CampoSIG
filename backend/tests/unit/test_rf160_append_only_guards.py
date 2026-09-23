"""La bitácora no se puede editar ni borrar, y eso se comprueba en el código (RF-160).

El criterio de aceptación de RF-160 tiene dos mitades: «sin endpoint de edición o borrado» y «se
verifica con una cadena de hashes». La segunda vive en los datos y se prueba contra base real. Esta
es la primera, y es estructural a propósito.

Lo que protege no es el código de hoy. Es el día en que alguien tenga que «arreglar un registro que
quedó mal» —con toda la buena intención del mundo— y encuentre que la forma de hacerlo no existe.
Una bitácora que se puede corregir no sirve como prueba de nada, y la corrección siempre parece
razonable en el momento.

Tres guardas, a tres distancias distintas de quien tendría que vencerlas:

1. la base rechaza UPDATE y DELETE con un disparador (se prueba contra PostgreSQL);
2. nada del código escribe en la tabla salvo la función de escritura (se prueba aquí, recorriendo el
   árbol de sintaxis de toda la aplicación);
3. el router de auditoría solo tiene GET (también aquí).

Y las guardas están probadas en negativo: se les da código que viola cada regla y se comprueba que
lo detectan.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"

#: The only module allowed to write to the trail.
THE_WRITER = "app/audit/service.py"

#: Names that mean "the audit table".
TABLE_NAMES = ("AuditEvent", "audit_event")

WRITE_CALLS = ("delete", "update")

METHODS_THAT_CHANGE_THINGS = ("post", "put", "patch", "delete")


def modules() -> list[Path]:
    return sorted(path for path in APP.rglob("*.py") if "__pycache__" not in str(path))


def relative(path: Path) -> str:
    return str(path.relative_to(APP.parent))


def parsed(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def writes_to_the_trail(tree: ast.Module) -> list[str]:
    """Statements that would change or remove an audit row."""
    found: list[str] = []
    for node in ast.walk(tree):
        # `session.delete(event)` / `delete(AuditEvent)` / `update(AuditEvent)`
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            if name in WRITE_CALLS:
                text = ast.dump(node)
                if any(table in text for table in TABLE_NAMES):
                    found.append(f"línea {node.lineno}: {name}() sobre la bitácora")
        # `event.hash = ...`, `row.payload = ...` on something named like an audit event
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in ("event", "audit_event", "entry")
                    and target.attr in ("hash", "prev_hash", "sequence", "payload", "occurred_at")
                ):
                    found.append(f"línea {node.lineno}: asigna {target.attr} de un evento")
    return found


class TestNothingButTheWriterWrites:
    def test_rf_160_ningún_módulo_edita_ni_borra_la_bitácora(self) -> None:
        offenders: dict[str, list[str]] = {}
        for path in modules():
            if relative(path) == THE_WRITER:
                continue
            problems = writes_to_the_trail(parsed(path))
            if problems:
                offenders[relative(path)] = problems
        assert offenders == {}, offenders

    def test_la_guarda_detecta_un_borrado(self) -> None:
        """Sin esto, «ningún módulo la borra» no significa nada."""
        tree = ast.parse("from app.audit.models import AuditEvent\nsession.delete(AuditEvent)\n")
        assert writes_to_the_trail(tree)

    def test_la_guarda_detecta_un_update(self) -> None:
        tree = ast.parse("update(AuditEvent).values(hash='x')\n")
        assert writes_to_the_trail(tree)

    def test_la_guarda_detecta_una_asignación_al_hash(self) -> None:
        tree = ast.parse("event.hash = 'lo que me convenga'\n")
        assert writes_to_the_trail(tree)

    def test_la_guarda_no_se_queja_del_código_normal(self) -> None:
        tree = ast.parse("rows = session.scalars(select(AuditEvent)).all()\nprint(rows)\n")
        assert writes_to_the_trail(tree) == []


class TestTheRouterOnlyReads:
    @pytest.fixture
    def router(self) -> ast.Module:
        return parsed(APP / "api" / "audit.py")

    def test_rf_160_el_router_de_auditoría_no_tiene_ningún_método_que_cambie_algo(
        self, router: ast.Module
    ) -> None:
        offenders = decorated_methods(router) - {"get"}
        assert offenders == set(), offenders

    def test_la_guarda_detecta_un_delete_añadido(self) -> None:
        """Es el fallo que importa: no que hoy no exista, sino que no aparezca mañana."""
        tree = ast.parse(
            '@router.delete("/units/{unit_code}/trail")\ndef purge() -> None:\n    pass\n'
        )
        assert "delete" in decorated_methods(tree)


def decorated_methods(tree: ast.Module) -> set[str]:
    """HTTP methods the module's route decorators declare."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            call = decorator.func if isinstance(decorator, ast.Call) else decorator
            if isinstance(call, ast.Attribute) and call.attr in (
                *METHODS_THAT_CHANGE_THINGS,
                "get",
            ):
                found.add(call.attr)
    return found
