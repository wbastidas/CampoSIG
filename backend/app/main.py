"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api import (
    dispatch,
    gis,
    health,
    integrations,
    planning,
    regulatory,
    review,
    voice,
)
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SIGEC-Campo API",
        version="0.1.0",
        description="Field work management platform for an electric distribution utility.",
        debug=settings.debug,
    )
    app.include_router(health.router)
    app.include_router(gis.router)
    app.include_router(planning.router)
    app.include_router(voice.router)
    app.include_router(dispatch.router)
    app.include_router(regulatory.router)
    app.include_router(integrations.router)
    app.include_router(review.router)
    return app


app = create_app()
