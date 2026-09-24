"""Assemblage des routeurs de l'API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    administration,
    auth,
    etablissements,
    evaluations,
    examens,
    gouvernance,
    personnes,
    public,
    referentiels,
    scolarite,
    vie,
)

api_router = APIRouter()

# --- Accès et services ouverts ---
api_router.include_router(auth.router)
api_router.include_router(public.router)

# --- Référentiels et organisation ---
api_router.include_router(referentiels.router)
api_router.include_router(etablissements.router)

# --- Acteurs ---
api_router.include_router(personnes.router)

# --- Scolarité et pédagogie ---
api_router.include_router(scolarite.router)
api_router.include_router(evaluations.router)

# --- Examens et concours ---
api_router.include_router(examens.router)

# --- Vie étudiante, projets et insertion ---
api_router.include_router(vie.router)

# --- Gouvernance et administration ---
api_router.include_router(gouvernance.router)
api_router.include_router(administration.router)
