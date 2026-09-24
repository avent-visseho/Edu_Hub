"""Assemblage des routeurs de l'API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, etablissements, personnes, referentiels

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(referentiels.router)
api_router.include_router(etablissements.router)
api_router.include_router(personnes.router)
