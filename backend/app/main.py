"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api import health
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
    return app


app = create_app()
