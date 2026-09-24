"""Autenticación corporativa (RF-001, RF-002, ADR-009).

Hasta que esto existió, **toda identidad se autodeclaraba**: el usuario del supervisor llegaba
en el cuerpo de la misma petición que registraba su aprobación, y quien confirmaba un valor de
IA era quien el llamante dijera. Eso vuelve ficción el rastro de auditoría completo: la
aprobación de un supervisor vale exactamente lo que valga la afirmación de que fue el supervisor.

Aquí se ejercita la dependencia **real**, con tokens firmados de verdad por una clave RSA que se
genera en el propio test. Casi todo lo que sigue es un rechazo, porque cada uno corresponde a una
forma concreta de colarse.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwk, jwt
from sqlalchemy.orm import Session

from app.auth.principal import Principal, Role
from app.auth.tokens import AuthenticationError, KeySet, principal_from_claims
from app.auth.tokens import key_set as live_key_set
from app.gis_gateway.ingest import ingest_metadata
from app.infra.database import get_session
from app.main import create_app
from app.org.models import BusinessUnit, Organization
from app.settings import get_settings
from tests.conftest import build_metadata

pytestmark = pytest.mark.integration

KEY_ID = "test-key-1"


@pytest.fixture(scope="module")
def signing_key() -> dict[str, Any]:
    """An RSA key pair, so the tokens in these tests are genuinely signed."""
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    from cryptography.hazmat.primitives import serialization

    pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_jwk = jwk.construct(
        private.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode(),
        algorithm="RS256",
    ).to_dict()
    public_jwk["kid"] = KEY_ID
    public_jwk = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in public_jwk.items()}
    return {"pem": pem, "jwk": public_jwk}


@pytest.fixture(autouse=True)
def installed_keys(signing_key):
    """Install the public key so verification can succeed, and restore afterwards."""
    original = dict(live_key_set.__dict__)
    live_key_set.preload([signing_key["jwk"]])
    yield
    live_key_set.__dict__.update(original)


def mint(
    signing_key,
    *,
    subject: str = "kc|supervisor.demo",
    roles: list[str] | None = None,
    units: list[str] | None = None,
    audience: str | None = None,
    issuer: str | None = None,
    expires_in: int = 900,
    include_exp: bool = True,
    key_id: str = KEY_ID,
) -> str:
    settings = get_settings()
    claims: dict[str, Any] = {
        "sub": subject,
        "preferred_username": subject.split("|")[-1],
        "name": "Supervisor Demo",
        "iss": issuer or settings.oidc_issuer,
        "aud": audience or settings.oidc_audience,
        "iat": int(datetime.now(UTC).timestamp()),
        "jti": str(uuid.uuid4()),
        "realm_access": {"roles": roles if roles is not None else [Role.SUPERVISOR.value]},
    }
    if include_exp:
        claims["exp"] = int((datetime.now(UTC) + timedelta(seconds=expires_in)).timestamp())
    if units is not None:
        claims["business_units"] = units
    return jwt.encode(claims, signing_key["pem"], algorithm="RS256", headers={"kid": key_id})


@pytest.fixture
def unit(session: Session) -> BusinessUnit:
    org = Organization(code="MATRIZ", name="Corporación Eléctrica Nacional")
    session.add(org)
    session.flush()
    created = BusinessUnit(
        organization_id=org.id, code="GYE", name="Unidad Guayaquil", profile_id="cnel-gye"
    )
    session.add(created)
    session.flush()
    ingest_metadata(session, created, build_metadata("cnel-gye"))
    return created


@pytest.fixture
def client(session: Session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as raw:
        yield raw
    app.dependency_overrides.clear()


def queue_url(unit_code: str = "GYE") -> str:
    return f"/api/v1/review/units/{unit_code}/queue"


class TestNoIdentityNoAccess:
    def test_rf_001_a_request_without_a_token_is_401(self, client, unit) -> None:
        answer = client.get(queue_url())
        assert answer.status_code == 401
        assert answer.headers["www-authenticate"] == "Bearer"

    def test_rf_001_a_non_bearer_scheme_is_401(self, client, unit) -> None:
        answer = client.get(queue_url(), headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert answer.status_code == 401

    def test_rf_001_an_empty_bearer_is_401(self, client, unit) -> None:
        assert client.get(queue_url(), headers={"Authorization": "Bearer "}).status_code == 401

    def test_rf_001_a_garbage_token_is_401_and_the_token_is_not_echoed(self, client, unit) -> None:
        secret = "no-es-un-token-pero-parece-un-secreto"
        answer = client.get(queue_url(), headers={"Authorization": f"Bearer {secret}"})
        assert answer.status_code == 401
        # El motivo viaja; el token nunca.
        assert secret not in answer.text


class TestTokensAreActuallyVerified:
    def test_rf_001_a_well_signed_token_is_accepted(self, client, unit, signing_key) -> None:
        token = mint(signing_key, units=["GYE"])
        answer = client.get(queue_url(), headers={"Authorization": f"Bearer {token}"})
        assert answer.status_code == 200

    def test_rf_001_a_token_signed_by_another_key_is_refused(
        self, client, unit, signing_key
    ) -> None:
        """Lo que impide que cualquiera emita sus propios tokens."""
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        from cryptography.hazmat.primitives import serialization

        pem = other.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        forged = jwt.encode(
            {
                "sub": "kc|intruso",
                "iss": get_settings().oidc_issuer,
                "aud": get_settings().oidc_audience,
                "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
                "realm_access": {"roles": [Role.SUPERVISOR.value]},
            },
            pem,
            algorithm="RS256",
            headers={"kid": KEY_ID},
        )
        answer = client.get(queue_url(), headers={"Authorization": f"Bearer {forged}"})
        assert answer.status_code == 401

    def test_rf_001_an_expired_token_is_refused(self, client, unit, signing_key) -> None:
        token = mint(signing_key, units=["GYE"], expires_in=-60)
        assert (
            client.get(queue_url(), headers={"Authorization": f"Bearer {token}"}).status_code == 401
        )

    def test_rf_001_a_token_with_no_expiry_is_refused(self, client, unit, signing_key) -> None:
        """Un token que no caduca es una contraseña en un encabezado."""
        token = mint(signing_key, units=["GYE"], include_exp=False)
        assert (
            client.get(queue_url(), headers={"Authorization": f"Bearer {token}"}).status_code == 401
        )

    def test_rf_001_a_token_for_another_audience_is_refused(
        self, client, unit, signing_key
    ) -> None:
        """Un token emitido para el cliente web no es un token para esta API."""
        token = mint(signing_key, units=["GYE"], audience="otra-api")
        assert (
            client.get(queue_url(), headers={"Authorization": f"Bearer {token}"}).status_code == 401
        )

    def test_rf_001_a_token_from_another_issuer_is_refused(self, client, unit, signing_key) -> None:
        token = mint(signing_key, units=["GYE"], issuer="https://idp-de-otra-empresa/realms/x")
        assert (
            client.get(queue_url(), headers={"Authorization": f"Bearer {token}"}).status_code == 401
        )

    def test_rf_001_an_unknown_key_id_is_refused(self, client, unit, signing_key) -> None:
        token = mint(signing_key, units=["GYE"], key_id="clave-que-nadie-publica")
        assert (
            client.get(queue_url(), headers={"Authorization": f"Bearer {token}"}).status_code == 401
        )


class TestScopeAndRoles:
    def test_rf_002_a_person_cannot_act_in_another_unit(self, client, unit, signing_key) -> None:
        token = mint(signing_key, units=["MAN"])
        answer = client.get(queue_url("GYE"), headers={"Authorization": f"Bearer {token}"})
        assert answer.status_code == 403
        assert "unidad de negocio" in answer.json()["detail"]

    def test_rf_002_a_corporate_role_acts_everywhere(self, client, unit, signing_key) -> None:
        token = mint(signing_key, roles=[Role.IT_ADMIN.value], units=["MAN"])
        assert (
            client.get(queue_url("GYE"), headers={"Authorization": f"Bearer {token}"}).status_code
            == 200
        )

    def test_rf_001_deciding_needs_a_supervisor_role(self, client, unit, signing_key) -> None:
        """Un técnico puede consultar su unidad y no puede aprobar su propio trabajo."""
        token = mint(signing_key, roles=[Role.TECHNICIAN.value], units=["GYE"])
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get(queue_url(), headers=headers).status_code == 200

        answer = client.post(
            f"/api/v1/review/units/GYE/work-orders/{uuid.uuid4()}/decision",
            json={"decision": "aprobada"},
            headers=headers,
        )
        assert answer.status_code == 403
        assert Role.SUPERVISOR.value in answer.json()["detail"]

    def test_rf_001_retrying_an_integration_needs_an_administrator(
        self, client, unit, signing_key
    ) -> None:
        token = mint(signing_key, roles=[Role.SUPERVISOR.value], units=["GYE"])
        answer = client.post(
            f"/api/v1/integrations/units/GYE/events/{uuid.uuid4()}/retry",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert answer.status_code == 403


class TestTheDevelopmentEscapeHatch:
    def test_it_is_refused_unless_deliberately_enabled(self, client, unit) -> None:
        """Una API que pudiera desplegarse con la autenticación apagada en silencio, lo hace."""
        answer = client.get(
            queue_url(), headers={"X-SIGEC-Dev-Identity": "supervisor.demo:supervisor|GYE"}
        )
        assert answer.status_code == 403
        assert "desarrollo" in answer.json()["detail"]

    def test_it_works_when_enabled_in_a_development_environment(
        self, client, unit, monkeypatch
    ) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "allow_dev_identity", True)
        monkeypatch.setattr(settings, "environment", "development")
        answer = client.get(
            queue_url(), headers={"X-SIGEC-Dev-Identity": "supervisor.demo:supervisor|GYE"}
        )
        assert answer.status_code == 200

    def test_it_still_honours_the_unit_scope(self, client, unit, monkeypatch) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "allow_dev_identity", True)
        monkeypatch.setattr(settings, "environment", "development")
        answer = client.get(
            queue_url("GYE"), headers={"X-SIGEC-Dev-Identity": "ajeno:supervisor|MAN"}
        )
        assert answer.status_code == 403

    def test_a_bearer_token_wins_over_the_dev_header(
        self, client, unit, signing_key, monkeypatch
    ) -> None:
        """Presentar las dos cosas no es una forma de esquivar la verificación."""
        settings = get_settings()
        monkeypatch.setattr(settings, "allow_dev_identity", True)
        monkeypatch.setattr(settings, "environment", "development")
        bad = mint(signing_key, units=["GYE"], expires_in=-60)
        answer = client.get(
            queue_url(),
            headers={
                "Authorization": f"Bearer {bad}",
                "X-SIGEC-Dev-Identity": "supervisor.demo:supervisor|GYE",
            },
        )
        assert answer.status_code == 401


class TestClaimMapping:
    def test_roles_come_from_the_realm_and_from_the_clients(self) -> None:
        principal = principal_from_claims(
            {
                "sub": "u1",
                "realm_access": {"roles": ["supervisor"]},
                "resource_access": {"sigec-web": {"roles": ["analista_ml"]}},
            }
        )
        assert principal.roles == frozenset({"supervisor", "analista_ml"})

    def test_units_accept_a_list_or_a_comma_separated_string(self) -> None:
        as_list = principal_from_claims({"sub": "u", "business_units": ["GYE", "MAN"]})
        as_text = principal_from_claims({"sub": "u", "unidades_negocio": "GYE, MAN"})
        assert as_list.business_units == as_text.business_units == frozenset({"GYE", "MAN"})

    def test_a_token_without_a_subject_is_refused(self) -> None:
        with pytest.raises(AuthenticationError):
            principal_from_claims({"preferred_username": "alguien"})

    def test_a_token_with_no_unit_claim_is_corporate(self) -> None:
        """Las cuentas de administración no están atadas a una unidad. Es deliberado."""
        assert principal_from_claims({"sub": "u"}).is_corporate

    def test_the_description_never_contains_a_token(self) -> None:
        principal = Principal(subject="kc|x", username="x", roles=frozenset({"supervisor"}))
        assert "eyJ" not in principal.describe()


class TestTheKeyCache:
    def test_an_unknown_key_fails_without_hammering_the_provider(self, monkeypatch) -> None:
        """Un flujo de tokens forjados no debe convertirse en un flujo de peticiones al IdP."""
        keys = KeySet()
        keys.preload([{"kid": "conocida", "kty": "RSA", "n": "x", "e": "AQAB"}])
        calls = {"n": 0}

        def counted() -> None:
            calls["n"] += 1

        monkeypatch.setattr(keys, "_refresh", counted)
        for _ in range(5):
            with pytest.raises(AuthenticationError):
                keys.key_for("desconocida")
        assert calls["n"] == 0
