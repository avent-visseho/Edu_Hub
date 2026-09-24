"""Configuration applicative centralisée."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "staging", "demo", "production"]
SeedScale = Literal["tiny", "small", "medium", "large"]


class Settings(BaseSettings):
    """Paramètres de l'application, chargés depuis l'environnement."""

    model_config = SettingsConfigDict(
        env_prefix="EDUHUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- Application ----------
    project_name: str = "EduHub"
    project_description: str = (
        "Système intégré de gestion de l'éducation — apprenants, enseignants, "
        "établissements, scolarité, examens, concours, vie étudiante et gouvernance."
    )
    version: str = "0.1.0"
    environment: Environment = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # ---------- Sécurité ----------
    secret_key: str = "change-me-in-production-0000000000000000"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    password_min_length: int = 8

    # ---------- Base de données ----------
    database_url: str = "postgresql+asyncpg://eduhub:eduhub@localhost:5432/eduhub"
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ---------- Redis ----------
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    # ---------- Stockage objet ----------
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "eduhub"
    s3_secret_key: str = "eduhub123"
    s3_bucket: str = "eduhub"
    s3_region: str = "us-east-1"
    storage_local_fallback: str = "storage"

    # ---------- CORS ----------
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # ---------- Pagination ----------
    default_page_size: int = 25
    max_page_size: int = 200

    # ---------- Simulation ----------
    seed_scale: SeedScale = "medium"
    seed_random_seed: int = 2026

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accepte une liste JSON ou une chaîne séparée par des virgules."""
        if isinstance(value, str):
            brut = value.strip()
            if brut.startswith("["):
                import json

                return json.loads(brut)
            return [origin.strip() for origin in brut.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def sync_database_url(self) -> str:
        """URL synchrone, utilisée par Alembic et les outils d'administration."""
        return self.database_url.replace("+asyncpg", "+psycopg")

    @property
    def postgres_admin_url(self) -> str:
        """URL synchrone pointant sur la base `postgres` (création/suppression)."""
        base, _, _ = self.sync_database_url.rpartition("/")
        return f"{base}/postgres"

    @property
    def database_name(self) -> str:
        return self.sync_database_url.rpartition("/")[2].split("?")[0]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
