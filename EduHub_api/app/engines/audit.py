"""Moteur d'audit — trace des opérations sensibles."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import Action
from app.models.systeme import JournalAudit


def _serialiser(valeurs: dict[str, Any] | None) -> dict[str, Any] | None:
    """Rend un dictionnaire compatible JSONB."""
    if valeurs is None:
        return None
    resultat: dict[str, Any] = {}
    for cle, valeur in valeurs.items():
        if isinstance(valeur, uuid.UUID):
            resultat[cle] = str(valeur)
        elif hasattr(valeur, "isoformat"):
            resultat[cle] = valeur.isoformat()
        elif isinstance(valeur, int | float | str | bool | type(None)):
            resultat[cle] = valeur
        else:
            resultat[cle] = str(valeur)
    return resultat


async def journaliser(
    session: AsyncSession,
    *,
    action: Action | str,
    entite_type: str,
    entite_id: uuid.UUID | None = None,
    entite_libelle: str | None = None,
    utilisateur_id: uuid.UUID | None = None,
    utilisateur_email: str | None = None,
    valeurs_avant: dict[str, Any] | None = None,
    valeurs_apres: dict[str, Any] | None = None,
    adresse_ip: str | None = None,
    agent_utilisateur: str | None = None,
    succes: bool = True,
    message: str | None = None,
) -> JournalAudit:
    """Enregistre une entrée dans le journal d'audit."""
    entree = JournalAudit(
        utilisateur_id=utilisateur_id,
        utilisateur_email=utilisateur_email,
        action=action.value if isinstance(action, Action) else action,
        entite_type=entite_type,
        entite_id=entite_id,
        entite_libelle=entite_libelle,
        valeurs_avant=_serialiser(valeurs_avant),
        valeurs_apres=_serialiser(valeurs_apres),
        adresse_ip=adresse_ip,
        agent_utilisateur=agent_utilisateur,
        succes=succes,
        message=message,
    )
    session.add(entree)
    return entree


def diff(avant: dict[str, Any], apres: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Réduit deux états à leurs seules différences."""
    cles = {cle for cle in set(avant) | set(apres) if avant.get(cle) != apres.get(cle)}
    return ({c: avant.get(c) for c in cles}, {c: apres.get(c) for c in cles})
