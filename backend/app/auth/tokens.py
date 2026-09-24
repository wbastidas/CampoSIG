"""Token verification against the corporate identity provider (RF-001).

Verification is real: signature against the issuer's published keys, issuer, audience, and
expiry. Everything else in the platform depends on this being true, so the failure modes are
handled explicitly rather than collapsed into "invalid token":

* **An unknown key id** triggers exactly one key refresh, then fails. Keycloak rotates keys,
  and a cache that never refreshed would reject every token after a rotation; one that
  refreshed on every failure would let an attacker turn a bad token into a request to the
  identity provider.
* **A token with no expiry** is refused. `python-jose` will happily accept one if asked not to
  verify, and a token that never expires is a password in a header.
* **A wrong audience** is refused rather than warned about. A token minted for the web client
  is not a token for this API, and accepting it is how a cross-client confusion becomes an
  authorisation bug.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import httpx
from jose import jwt
from jose.exceptions import JWTError

from app.auth.principal import Principal
from app.settings import get_settings


class AuthenticationError(Exception):
    """Raised when a token cannot be trusted. The message never contains the token."""


#: How long a fetched key set is trusted before it is fetched again.
JWKS_TTL_SECONDS = 3600

#: Floor between refreshes triggered by an unknown key id, so a stream of forged tokens
#: cannot be turned into a stream of requests to the identity provider.
JWKS_MIN_REFRESH_SECONDS = 30

#: Claims the platform reads for business-unit scope. Keycloak can be configured to emit
#: either; both are accepted so the mapper can be named the obvious thing.
UNIT_CLAIMS = ("business_units", "unidades_negocio")


class KeySet:
    """The issuer's public keys, cached with a TTL and a rate-limited refresh."""

    def __init__(self, *, ttl: int = JWKS_TTL_SECONDS) -> None:
        self._ttl = ttl
        self._keys: dict[str, dict[str, Any]] = {}
        self._fetched_at = 0.0
        self._lock = threading.Lock()

    @property
    def jwks_url(self) -> str:
        issuer = get_settings().oidc_issuer.rstrip("/")
        return f"{issuer}/protocol/openid-connect/certs"

    def key_for(self, key_id: str) -> dict[str, Any]:
        """The key with this id, refreshing once if it is unknown.

        :raises AuthenticationError: if the key is still unknown after a refresh.
        """
        with self._lock:
            stale = time.monotonic() - self._fetched_at > self._ttl
            unknown = key_id not in self._keys
            # The floor is what stops a stream of forged tokens from becoming a stream of
            # requests to the identity provider; the `not self._keys` clause is the cold start,
            # where there is nothing to rate-limit against yet.
            may_refresh = (
                time.monotonic() - self._fetched_at > JWKS_MIN_REFRESH_SECONDS or not self._keys
            )
            if (unknown or stale) and may_refresh:
                self._refresh()
            key = self._keys.get(key_id)
        if key is None:
            raise AuthenticationError(
                "el token está firmado con una clave que el proveedor de identidad no publica"
            )
        return key

    def _refresh(self) -> None:
        try:
            answer = httpx.get(self.jwks_url, timeout=5.0)
            answer.raise_for_status()
            document = answer.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthenticationError(
                f"no se pudieron obtener las claves del proveedor de identidad: {exc}"
            ) from exc
        keys = {key["kid"]: key for key in document.get("keys", []) if "kid" in key}
        if not keys:
            raise AuthenticationError("el proveedor de identidad no publicó ninguna clave")
        self._keys = keys
        self._fetched_at = time.monotonic()

    def preload(self, keys: list[dict[str, Any]]) -> None:
        """Install keys directly. For tests, and for an air-gapped deployment."""
        with self._lock:
            self._keys = {key["kid"]: key for key in keys if "kid" in key}
            self._fetched_at = time.monotonic()


#: Module-level so the cache is shared. Replaced wholesale in tests.
key_set = KeySet()


def verify(token: str) -> Principal:
    """Verify a bearer token and build the principal it describes.

    :raises AuthenticationError: on any reason the token cannot be trusted.
    """
    settings = get_settings()
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise AuthenticationError("el encabezado del token no se puede leer") from exc

    key_id = header.get("kid")
    if not key_id:
        raise AuthenticationError("el token no declara el identificador de su clave (kid)")

    key = key_set.key_for(str(key_id))

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256", "RS512", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={
                # Every one of these is on deliberately. `require_exp` in particular: a token
                # with no expiry is a password in a header.
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
                "require_exp": True,
            },
        )
    except JWTError as exc:
        raise AuthenticationError(f"el token no es válido: {exc}") from exc

    return principal_from_claims(claims)


def principal_from_claims(claims: dict[str, Any]) -> Principal:
    """Build a principal from verified claims.

    Separate from :func:`verify` so the mapping can be tested without minting a token, and so
    an air-gapped deployment with a different identity provider can reuse it.
    """
    subject = claims.get("sub")
    if not subject:
        raise AuthenticationError("el token no identifica a un sujeto")

    realm_roles = claims.get("realm_access", {}).get("roles", [])
    resource_roles: list[str] = []
    for client in claims.get("resource_access", {}).values():
        resource_roles.extend(client.get("roles", []))

    units: list[str] = []
    for claim in UNIT_CLAIMS:
        value = claims.get(claim)
        if isinstance(value, str):
            units.extend(part.strip() for part in value.split(",") if part.strip())
        elif isinstance(value, list):
            units.extend(str(part).strip() for part in value if str(part).strip())

    return Principal(
        subject=str(subject),
        username=claims.get("preferred_username"),
        display_name=claims.get("name"),
        roles=frozenset(str(role) for role in [*realm_roles, *resource_roles]),
        business_units=frozenset(units),
        token_id=claims.get("jti"),
    )
