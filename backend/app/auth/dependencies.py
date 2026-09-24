"""FastAPI dependencies for identity and authorisation (RF-001, RF-002, ADR-009).

Three of them, and the split matters:

* :func:`current_principal` — who is calling. Fails with 401 when it cannot be established.
* :func:`require_roles` — whether they hold a role this endpoint needs. 403.
* :func:`unit_scope` — whether they may act in *this* business unit. 403, and it is the one
  that makes ADR-009 hold at the door rather than in each service function.

The development escape hatch is deliberate and loud. Without a Keycloak running, the whole API
would be untestable and undemonstrable; with a silent escape hatch, a deployment could ship
with authentication off and nobody would notice. So it is opt-in by setting, refuses to engage
outside a development environment, and every request it lets through is marked as such.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Path, Query, status

from app.auth.principal import Principal, Role
from app.auth.tokens import AuthenticationError, verify
from app.settings import get_settings

#: Header the development escape hatch reads. Never consulted in production, because
#: `allow_dev_identity` cannot be true there.
DEV_IDENTITY_HEADER = "X-SIGEC-Dev-Identity"


def _dev_principal(raw: str) -> Principal:
    """Build a principal from ``usuario:rol,rol|UNIDAD,UNIDAD``. Development only."""
    identity, _, units = raw.partition("|")
    username, _, roles = identity.partition(":")
    if not username.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "la identidad de desarrollo está vacía")
    return Principal(
        subject=f"dev:{username.strip()}",
        username=username.strip(),
        display_name=username.strip(),
        roles=frozenset(role.strip() for role in roles.split(",") if role.strip()),
        business_units=frozenset(unit.strip() for unit in units.split(",") if unit.strip()),
        token_id=None,
    )


def current_principal(
    authorization: Annotated[str | None, Header()] = None,
    dev_identity: Annotated[str | None, Header(alias=DEV_IDENTITY_HEADER)] = None,
) -> Principal:
    """The authenticated caller.

    :raises HTTPException: 401 when no trustworthy identity can be established.
    """
    settings = get_settings()

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "se espera un encabezado 'Authorization: Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            return verify(token.strip())
        except AuthenticationError as exc:
            # The reason travels; the token never does.
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, str(exc), headers={"WWW-Authenticate": "Bearer"}
            ) from exc

    if dev_identity:
        if not settings.allow_dev_identity or settings.environment != "development":
            # Not 401: the caller did present something. Saying it is refused *here* rather
            # than "invalid token" is what stops somebody spending an afternoon on the wrong
            # question in a staging environment.
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "la identidad de desarrollo solo funciona con SIGEC_ALLOW_DEV_IDENTITY=1 en "
                "un entorno de desarrollo",
            )
        return _dev_principal(dev_identity)

    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "esta operación requiere autenticación corporativa",
        headers={"WWW-Authenticate": "Bearer"},
    )


PrincipalDep = Annotated[Principal, Depends(current_principal)]


def require_roles(*roles: Role | str) -> Callable[[Principal], Principal]:
    """A dependency that demands at least one of these roles.

    Any-of rather than all-of: the realm's roles are job titles, and a person holds one.
    """
    wanted = tuple(str(role) for role in roles)

    def dependency(principal: PrincipalDep) -> Principal:
        if not principal.has(*wanted):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"esta operación requiere uno de estos roles: {', '.join(sorted(wanted))}",
            )
        return principal

    return dependency


def unit_scope(
    principal: PrincipalDep,
    unit_code: Annotated[str, Path()],
) -> Principal:
    """Confirm the caller may act in the business unit named in the path (ADR-009).

    Applied as a route dependency, so an endpoint cannot forget it: the check happens before
    the handler runs, not somewhere inside it.
    """
    if not principal.may_act_in(unit_code):
        # Deliberately says the unit is out of scope rather than whether it exists: a person
        # from one unit should not be able to enumerate the others.
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"'{principal.describe()}' no puede actuar en la unidad de negocio '{unit_code}'",
        )
    return principal


UnitScopeDep = Annotated[Principal, Depends(unit_scope)]


def unit_scope_query(
    principal: PrincipalDep,
    business_unit: Annotated[str, Query()],
) -> Principal:
    """The same check for routers whose unit travels as a query parameter.

    Two functions rather than one that guesses: FastAPI resolves a parameter's source from its
    declaration, and a dependency that tried to read either would end up reading neither.
    """
    if not principal.may_act_in(business_unit):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"'{principal.describe()}' no puede actuar en la unidad de negocio '{business_unit}'",
        )
    return principal


UnitScopeQueryDep = Annotated[Principal, Depends(unit_scope_query)]
