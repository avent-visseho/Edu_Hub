"""Point d'entrée de l'API EduHub."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import EduHubError, eduhub_error_handler
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)

TAGS_METADATA = [
    {"name": "Système", "description": "Santé du service et métadonnées."},
    {"name": "Authentification", "description": "Connexion, jetons, session courante."},
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info("Démarrage de %s en environnement %s", settings.project_name, settings.environment)
    yield
    await engine.dispose()
    logger.info("Arrêt de %s", settings.project_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        description=settings.project_description,
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    app.add_exception_handler(EduHubError, eduhub_error_handler)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["Système"], summary="Racine de l'API")
    async def root() -> dict[str, str]:
        return {
            "nom": settings.project_name,
            "version": settings.version,
            "environnement": settings.environment,
            "documentation": "/docs",
        }

    @app.get("/health", tags=["Système"], summary="Sonde de santé")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
