"""Health and readiness endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.infra.database import get_engine
from app.settings import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    environment: str
    profile: str


class ReadinessResponse(BaseModel):
    status: str
    database: str
    postgis: str | None = None


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", environment=settings.environment, profile=settings.profile)


@router.get("/ready", response_model=ReadinessResponse)
def ready() -> ReadinessResponse:
    """Readiness probe: confirms the database answers and PostGIS is installed.

    PostGIS is checked explicitly because the network cache and every spatial query
    depend on it; a database without it would fail later, at a much worse moment.
    """
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
            version = conn.execute(text("SELECT postgis_version()")).scalar_one()
    except Exception as exc:
        return ReadinessResponse(status="unavailable", database=f"error: {exc}")
    return ReadinessResponse(status="ok", database="ok", postgis=str(version))
