"""Dépendances FastAPI partagées par tous les endpoints."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.enums import Action, RoleCode
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_token
from app.engines.identity import ContexteUtilisateur, charger_utilisateur

oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/connexion",
    auto_error=False,
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def contexte_courant(
    session: SessionDep,
    jeton: Annotated[str | None, Depends(oauth2)] = None,
) -> ContexteUtilisateur:
    """Résout l'utilisateur authentifié et ses droits effectifs."""
    if not jeton:
        raise AuthenticationError("Jeton d'accès requis.", code="jeton_absent")
    charge = decode_token(jeton, "access")
    try:
        utilisateur_id = uuid.UUID(charge["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Jeton invalide.", code="jeton_invalide") from exc
    utilisateur = await charger_utilisateur(session, utilisateur_id)
    return ContexteUtilisateur(utilisateur)


ContexteDep = Annotated[ContexteUtilisateur, Depends(contexte_courant)]


async def contexte_optionnel(
    session: SessionDep,
    jeton: Annotated[str | None, Depends(oauth2)] = None,
) -> ContexteUtilisateur | None:
    """Contexte utilisateur si un jeton valide est fourni, `None` sinon.

    Utile pour les routes publiques qui enrichissent leur réponse quand
    l'appelant est connecté — consultation de résultats, vérification de
    diplôme, catalogue de ressources.
    """
    if not jeton:
        return None
    try:
        return await contexte_courant(session, jeton)
    except AuthenticationError:
        return None


ContexteOptionnelDep = Annotated[ContexteUtilisateur | None, Depends(contexte_optionnel)]


def exiger_permission(
    ressource: str, action: Action
) -> Callable[[ContexteUtilisateur], Coroutine[Any, Any, ContexteUtilisateur]]:
    """Dépendance exigeant une permission précise."""

    async def verificateur(contexte: ContexteDep) -> ContexteUtilisateur:
        contexte.exiger(ressource, action)
        return contexte

    return verificateur


def exiger_roles(
    *codes: RoleCode | str,
) -> Callable[[ContexteUtilisateur], Coroutine[Any, Any, ContexteUtilisateur]]:
    """Dépendance exigeant l'un des rôles indiqués."""
    attendus = {code.value if isinstance(code, RoleCode) else code for code in codes}

    async def verificateur(contexte: ContexteDep) -> ContexteUtilisateur:
        if contexte.est_omnipotent or contexte.roles & attendus:
            return contexte
        raise PermissionDeniedError(
            f"Rôle requis parmi : {', '.join(sorted(attendus))}.",
            details={"roles_requis": sorted(attendus)},
        )

    return verificateur


def metadonnees_requete(request: Request) -> dict[str, str | None]:
    """Adresse IP et agent utilisateur, pour l'audit et les sessions."""
    client = request.client
    return {
        "adresse_ip": client.host if client else None,
        "agent_utilisateur": request.headers.get("user-agent"),
    }


MetadonneesDep = Annotated[dict[str, str | None], Depends(metadonnees_requete)]
