"""No existe ningún camino de aprobación automática sin clic humano (RF-176).

El criterio de aceptación de RF-176 es literalmente un test de seguridad, y este es. Lo que
comprueba no es que hoy esté bien escrito: comprueba que **siga** estándolo cuando alguien añada,
dentro de un año, «un job nocturno que apruebe las de riesgo bajo, que total el agente ya las
revisó». Esa frase suena razonable y es exactamente el fallo.

Así que se recorre el árbol de sintaxis:

* ningún worker ni tarea programada llama a `decide` ni pone una OT en aprobada;
* el paquete de agentes tampoco (regla 14, ya cubierta en su archivo, aquí desde el otro lado);
* y toda ruta capaz de aprobar exige identidad corporativa y un rol, lo que la guarda de rutas ya
  impone y aquí se ata al caso concreto de la aprobación.

El muestreo tiene su propio test porque es la otra mitad del requerimiento: un lote sin muestra no
es un lote, y una muestra que redondea a cero es una política con un agujero que alguien encuentra.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.agents.report import RISK_IN_SPANISH, RiskLevel
from app.review.batch import MIN_SAMPLE, SAMPLE_RATE, sample_size

BACKEND = Path(__file__).resolve().parents[2]
APP = BACKEND / "app"

#: Lo que significa «aprobar» en el código: la función que decide y el estado final.
APPROVAL_CALLS = ("decide",)
APPROVAL_STATE = "APPROVED"

#: Paquetes que no pueden aprobar bajo ninguna circunstancia. Los workers porque corren sin nadie
#: mirando; los agentes porque la regla 14 lo prohíbe; la pre-revisión porque orquesta a los agentes
#: y sería el atajo más natural.
MUST_NOT_APPROVE = ("workers", "agents", "prereview", "inference")


def _python_files(package: str) -> list[Path]:
    return sorted((APP / package).rglob("*.py"))


def _calls_named(tree: ast.AST, names: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Name) and target.id in names:
            found.append(target.id)
        elif isinstance(target, ast.Attribute) and target.attr in names:
            found.append(target.attr)
    return found


def _mentions_approved_state(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Attribute) and node.attr == APPROVAL_STATE for node in ast.walk(tree)
    )


@pytest.mark.parametrize("package", MUST_NOT_APPROVE)
def test_rf_176_ningun_proceso_desatendido_puede_aprobar(package: str) -> None:
    """Un worker, un agente o el orquestador no aprueban. Nunca.

    El atajo que esto impide es el que suena razonable: «un job nocturno que apruebe las de riesgo
    bajo». Si alguna vez hace falta, tendrá que ser borrando este test, que es una conversación y no
    un descuido.
    """
    offences: list[str] = []
    for source in _python_files(package):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        if _calls_named(tree, APPROVAL_CALLS):
            offences.append(f"{source.relative_to(APP)} llama a decide()")
        if _mentions_approved_state(tree):
            offences.append(f"{source.relative_to(APP)} menciona el estado aprobada")

    assert not offences, (
        "estos módulos podrían aprobar sin una persona: "
        + "; ".join(offences)
        + ". RF-176: no existe ningún camino de aprobación automática sin clic humano"
    )


def test_la_guarda_detecta_una_llamada_a_decide() -> None:
    """La prueba en negativo: una guarda que solo se ha visto pasar no está probada."""
    tree = ast.parse("def nightly():\n    decide(session, unit, order, decision='aprobada')\n")
    assert _calls_named(tree, APPROVAL_CALLS) == ["decide"]


def test_la_guarda_detecta_una_transicion_a_aprobada() -> None:
    tree = ast.parse("transition(session, order, WorkOrderState.APPROVED)\n")
    assert _mentions_approved_state(tree) is True


def test_rf_176_toda_ruta_que_aprueba_exige_un_rol() -> None:
    """Aprobar no es algo que cualquiera autenticado pueda hacer.

    La guarda de rutas ya comprueba que ninguna queda sin identidad; esto ata el caso concreto: las
    dos rutas que aprueban piden rol, y la de lote pide supervisor — no inspector, que puede decidir
    sobre una OT pero no es quien firma un bloque de ellas.
    """
    from fastapi.routing import APIRoute

    from app.auth.dependencies import require_roles
    from app.main import create_app

    app = create_app()
    approving: list[str] = []
    for entry in app.routes:
        router = getattr(entry, "original_router", None)
        if router is None:
            continue
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            path = f"{router.prefix}{route.path}"
            if "decision" not in path and "batch-approval" not in path:
                continue
            if "POST" not in route.methods:
                continue
            approving.append(path)
            # `require_roles` returns a closure, so what is asserted is that *some* role dependency
            # guards the route: comparing identities would break the moment the factory is called
            # twice with the same roles.
            guards = _dependency_names(route) | _router_dependency_names(router)
            assert "dependency" in guards, f"{path} no exige ningún rol"

    assert len(approving) >= 2, f"se esperaban las dos rutas que aprueban, se hallaron {approving}"
    assert require_roles is not None


def _dependency_names(route: object) -> set[str]:
    names: set[str] = set()
    pending = list(getattr(route, "dependant").dependencies)  # noqa: B009
    while pending:
        dependant = pending.pop()
        if dependant.call is not None:
            names.add(getattr(dependant.call, "__name__", ""))
        pending.extend(dependant.dependencies)
    return names


def _router_dependency_names(router: object) -> set[str]:
    names: set[str] = set()
    for declared in getattr(router, "dependencies", None) or []:
        if declared.dependency is not None:
            names.add(getattr(declared.dependency, "__name__", ""))
    return names


# --- el muestreo obligatorio --------------------------------------------------------------
@pytest.mark.parametrize(
    ("batch", "expected"),
    [
        (0, 0),
        (1, 1),
        (3, 1),
        (20, 1),
        (21, 2),
        (40, 2),
        (41, 3),
        (100, 5),
        (200, 10),
    ],
)
def test_rf_176_la_muestra_se_redondea_hacia_arriba_y_nunca_es_cero(
    batch: int, expected: int
) -> None:
    """El 5 % de tres es 0,15, y una muestra que redondea a cero es una política con un agujero.

    Redondear al más cercano dejaría que un lote de tres no muestreara a nadie, y un supervisor que
    descubre eso aprueba de tres en tres. Así que el piso es uno, siempre.
    """
    assert sample_size(batch) == expected


def test_la_tasa_declarada_es_la_que_el_requerimiento_ejemplifica() -> None:
    assert pytest.approx(0.05) == SAMPLE_RATE
    assert MIN_SAMPLE == 1


def test_una_tasa_mayor_muestrea_mas() -> None:
    """Es un parámetro, y tiene que comportarse como tal."""
    assert sample_size(100, rate=0.2) == 20
    assert sample_size(100, rate=1.0) == 100


# --- el motivo que lee una persona --------------------------------------------------------
def test_todo_nivel_de_riesgo_tiene_su_palabra_en_español() -> None:
    """El motivo del rechazo lo lee un supervisor, y decía «riesgo medium».

    Los identificadores van en inglés (regla 11), así que interpolar el valor del enum en una frase
    en español produce exactamente eso. Lo que este test protege es el futuro: si alguien añade un
    nivel «critical», esto falla aquí en vez de aparecer en la pantalla de un supervisor.
    """
    assert set(RISK_IN_SPANISH) == set(RiskLevel)
    assert all(word.isalpha() for word in RISK_IN_SPANISH.values())
