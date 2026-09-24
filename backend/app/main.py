"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api import (
    analytics,
    audit,
    catalogs,
    dispatch,
    forms,
    gis,
    health,
    integrations,
    model_profile,
    planning,
    policy,
    proposals,
    regulatory,
    reports,
    review,
    voice,
    zones,
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
    app.include_router(model_profile.router)
    app.include_router(planning.router)
    app.include_router(voice.router)
    app.include_router(dispatch.router)
    app.include_router(regulatory.router)
    app.include_router(integrations.router)
    app.include_router(reports.router)
    # La página pública de verificación del acta (RF-115): la abre quien escanea el QR,
    # que es el cliente y no tiene cuenta corporativa.
    app.include_router(reports.public_router)
    app.include_router(review.router)
    app.include_router(analytics.router)
    app.include_router(audit.router)
    app.include_router(zones.router)
    app.include_router(policy.router)
    app.include_router(forms.router)
    app.include_router(catalogs.router)
    app.include_router(proposals.router)
    return app


app = create_app()
