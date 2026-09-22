"""Ninguna ruta queda sin autenticar por descuido (RF-001, RF-002).

El fallo que esta guarda impide no es escribir mal un chequeo: es **olvidarlo**. Se añade un
endpoint, se prueba lo que hace, se mezcla, y queda abierto. Nadie se da cuenta hasta que alguien
lo nota — o hasta que no lo nota.

Así que la lista de excepciones es explícita y corta, y cada una está justificada aquí mismo.
Añadir una ruta pública obliga a tocar este archivo, que es el punto.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute

from app.auth.dependencies import current_principal, unit_scope, unit_scope_query
from app.main import create_app

#: Rutas que no requieren identidad corporativa, con el motivo.
PUBLIC_ROUTES: dict[str, str] = {
    # Sondas de infraestructura: las consulta el orquestador, no una persona.
    "/health": "sonda de vida",
    "/ready": "sonda de disponibilidad",
    # Catálogo de constantes del propio código: no son datos de nadie.
    "/api/v1/planning/states": "enumeración de estados, sin datos",
    # Verificación pública del acta (RF-115): la abre quien escanea el QR impreso, que es el
    # cliente cuya luminaria se repuso y no tiene cuenta corporativa. Exigir identidad la haría
    # inútil. Lo que compensa es que revela lo mínimo —si el documento consta, de qué OT es,
    # cuándo se emitió y su huella— y nada de la persona, la dirección ni las respuestas; y que
    # el código es impredecible, así que no se puede enumerar lo emitido.
    "/verificar/{code}": "verificación pública del acta, sin datos personales",
    # Documentación de la API.
    "/openapi.json": "especificación",
    "/docs": "documentación",
    "/docs/oauth2-redirect": "documentación",
    "/redoc": "documentación",
}

#: El agente arcpy se autentica con su propia clave de registro, verificada en
#: `app/api/gis.py` (ADR-008): un proceso desatendido en una máquina Windows no hace un flujo
#: interactivo de OIDC. No es una ruta abierta; es otro mecanismo, con su propio test.
AGENT_KEY_PREFIX = "/api/v1/gis"

#: Las dependencias que cuentan como "esta ruta exige identidad".
IDENTITY_DEPENDENCIES = {current_principal, unit_scope, unit_scope_query}


def _api_routes(app: FastAPI | None = None) -> list[tuple[APIRoute, APIRouter]]:
    """Every real route, with the router that included it.

    This FastAPI version defers router inclusion: `app.routes` holds `_IncludedRouter`
    wrappers, not `APIRoute`s, and a naive `isinstance(route, APIRoute)` loop finds **nothing**
    and passes vacuously. A guard that passes because it inspected zero routes is worse than no
    guard, so this walks the included routers explicitly — and the negative test in
    `scripts/` proves the result actually detects.
    """
    app = app or create_app()
    found: list[tuple[APIRoute, APIRouter]] = []
    for entry in app.routes:
        router = getattr(entry, "original_router", None)
        if router is not None:
            found.extend((route, router) for route in router.routes if isinstance(route, APIRoute))
        elif isinstance(entry, APIRoute):
            found.append((entry, app.router))
    return found


def _identity_callables(route: APIRoute, router: APIRouter) -> set[object]:
    """Every dependency callable that guards a route, at any depth.

    Both sources matter: the route's own tree, and the dependencies the *router* declares.
    Router-level dependencies are applied when the router is included, so they do not appear in
    the route's dependant — which is precisely the place this guard was looking at first.
    """
    found: set[object] = set()
    pending = list(route.dependant.dependencies)
    while pending:
        dependant = pending.pop()
        if dependant.call is not None:
            found.add(dependant.call)
        pending.extend(dependant.dependencies)
    for declared in router.dependencies or []:
        if declared.dependency is not None:
            found.add(declared.dependency)
    return found


def _full_path(route: APIRoute, router: APIRouter) -> str:
    return route.path if route.path.startswith(router.prefix) else f"{router.prefix}{route.path}"


def unguarded_routes(app: FastAPI | None = None) -> list[str]:
    """Routes that demand no corporate identity. The guard, as a function.

    Extracted so it can be run against a deliberately broken app — see the negative test at
    the bottom. A guard nobody has watched fail is a guard nobody knows works.
    """
    unguarded: list[str] = []
    for route, router in _api_routes(app):
        path = _full_path(route, router)
        if path in PUBLIC_ROUTES or path.startswith(AGENT_KEY_PREFIX):
            continue
        if not (_identity_callables(route, router) & IDENTITY_DEPENDENCIES):
            unguarded.append(f"{sorted(route.methods)} {path}")
    return sorted(unguarded)


def test_rf_001_every_route_demands_an_identity() -> None:
    routes = _api_routes()
    # Si esto fuera cero, el test pasaría sin mirar nada. Es el fallo que tuvo esta guarda.
    assert len(routes) > 20, "la guarda no encontró rutas; no está inspeccionando nada"

    unguarded = unguarded_routes()
    assert not unguarded, (
        "estas rutas no exigen identidad corporativa: "
        + "; ".join(sorted(unguarded))
        + ". Añada la dependencia, o justifique la excepción en PUBLIC_ROUTES"
    )


def test_rf_002_every_unit_scoped_route_checks_the_scope() -> None:
    """Toda ruta que nombre una unidad de negocio comprueba que el llamante puede actuar ahí."""
    missing: list[str] = []
    for route, router in _api_routes():
        path = _full_path(route, router)
        if path.startswith(AGENT_KEY_PREFIX) or path in PUBLIC_ROUTES:
            continue
        names_a_unit = "{unit_code}" in path or any(
            field.name == "business_unit" for field in route.dependant.query_params
        )
        if not names_a_unit:
            continue
        if not (_identity_callables(route, router) & {unit_scope, unit_scope_query}):
            missing.append(f"{sorted(route.methods)} {path}")

    assert not missing, (
        "estas rutas nombran una unidad de negocio y no comprueban el ámbito: "
        + "; ".join(sorted(missing))
    )


def test_the_exception_list_stays_short() -> None:
    """Una lista de excepciones que crece es una lista que dejó de significar algo.

    Está justo en el tope, y eso es deliberado: la siguiente ruta pública obliga a mirar si
    alguna de las ocho sigue teniendo sentido antes de subir el número.
    """
    assert len(PUBLIC_ROUTES) <= 8


def test_the_guard_detects_an_unguarded_route() -> None:
    """La prueba en negativo, y la razón por la que existe.

    La primera versión de esta guarda recorría `app.routes` buscando `APIRoute`. Esta versión de
    FastAPI difiere la inclusión de routers, así que encontraba **cero** rutas y pasaba sin mirar
    nada. Una guarda que pasa porque no inspeccionó nada es peor que no tener guarda: da
    confianza y no la merece.
    """
    exposed = APIRouter(prefix="/api/v1/descuido", tags=["descuido"])

    @exposed.get("/abierto")
    def abierto() -> dict[str, str]:  # pragma: no cover - nunca se invoca
        return {}

    app = FastAPI()
    app.include_router(exposed)

    assert unguarded_routes(app) == ["['GET'] /api/v1/descuido/abierto"]


def test_the_guard_accepts_a_route_that_is_properly_guarded() -> None:
    guarded = APIRouter(prefix="/api/v1/cuidado", dependencies=[Depends(current_principal)])

    @guarded.get("/cerrado")
    def cerrado() -> dict[str, str]:  # pragma: no cover - nunca se invoca
        return {}

    app = FastAPI()
    app.include_router(guarded)

    assert unguarded_routes(app) == []
