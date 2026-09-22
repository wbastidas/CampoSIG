"""Application settings.

Note on the database: the platform runs on PostgreSQL only. The corporate Oracle
instance hosts the ArcSDE geodatabase and is reached exclusively through the arcpy
agent (ADR-006, ADR-008) — there is deliberately no Oracle connection setting here,
and adding one would violate rule 7 of CLAUDE.md.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SIGEC_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "development"
    debug: bool = False

    database_url: str = "postgresql+psycopg://sigec:sigec@localhost:5432/sigec"
    redis_url: str = "redis://localhost:6379/0"

    # Identity (Keycloak / OIDC) — RF-001.
    oidc_issuer: str = "http://localhost:8080/realms/sigec"
    oidc_audience: str = "sigec-backend"
    #: Development escape hatch for the `X-SIGEC-Dev-Identity` header. Off by default, and
    #: refused outside a development environment even when on — an API that could ship with
    #: authentication silently disabled is an API that eventually does.
    allow_dev_identity: bool = False

    # Corporate systems the integration adapters talk to (RF-120, RF-124). Empty means the
    # connector is not configured, and the worker skips it instead of failing every event
    # against a URL nobody set — a connector that is not deployed yet is not an error.
    work_order_system_url: str = ""
    call_centre_url: str = ""
    #: How many events one worker pass delivers. Bounded so a backlog is drained in visible
    #: chunks rather than in one pass that either finishes or dies holding everything.
    integration_batch_size: int = 50

    #: Where a person scanning the QR of an acta lands (RF-115). Has to be the address the
    #: platform is reachable at from a phone, not from inside the container network: a QR
    #: pointing at `localhost` is a QR that works only on the server that printed it.
    public_base_url: str = "http://localhost:8000"

    # Object storage for evidence (SeaweedFS, S3 API).
    s3_endpoint_url: str = "http://localhost:8333"
    s3_bucket: str = "sigec-evidence"

    # Active data-model profile (ADR-004). Switching this must be enough to run
    # against a different geodatabase schema, which the CI suite verifies.
    profile: str = Field(default="cnel-gye", description="Data-model profile id under profiles/")
    profiles_dir: str = "../profiles"


@lru_cache
def get_settings() -> Settings:
    return Settings()
