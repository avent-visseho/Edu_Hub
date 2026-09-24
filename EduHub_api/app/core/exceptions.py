"""Exceptions métier et leur traduction en réponses HTTP."""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


class EduHubError(Exception):
    """Erreur applicative de base."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "erreur_application"
    message: str = "Une erreur est survenue."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        super().__init__(self.message)

    def to_payload(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


class NotFoundError(EduHubError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "ressource_introuvable"
    message = "La ressource demandée est introuvable."


class ConflictError(EduHubError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflit"
    message = "La ressource existe déjà ou est en conflit avec l'état courant."


class ValidationError(EduHubError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "donnees_invalides"
    message = "Les données fournies sont invalides."


class AuthenticationError(EduHubError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentification_requise"
    message = "Authentification requise ou identifiants invalides."


class PermissionDeniedError(EduHubError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "acces_refuse"
    message = "Vous n'avez pas les droits nécessaires pour cette action."


class WorkflowError(EduHubError):
    status_code = status.HTTP_409_CONFLICT
    code = "transition_invalide"
    message = "Cette transition de statut n'est pas autorisée."


class BusinessRuleError(EduHubError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "regle_metier"
    message = "Une règle métier empêche cette opération."


async def eduhub_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Traduit une `EduHubError` en réponse JSON normalisée."""
    assert isinstance(exc, EduHubError)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.to_payload()})
