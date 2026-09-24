"""Endpoints d'authentification et de session."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import ContexteDep, MetadonneesDep, SessionDep
from app.core.enums import Action
from app.engines import identity as moteur_identite
from app.engines.audit import journaliser
from app.schemas.base import MessageReponse
from app.schemas.identity import (
    ChangementMotDePasse,
    ConnexionDemande,
    JetonsReponse,
    PreferencesAccessibilite,
    RafraichissementDemande,
    UtilisateurDetail,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])


def _detail_utilisateur(contexte) -> UtilisateurDetail:
    """Compose la vue détaillée d'un utilisateur et de ses droits."""
    detail = UtilisateurDetail.model_validate(contexte.utilisateur)
    detail.roles = sorted(contexte.roles)
    detail.permissions = sorted(contexte.permissions)
    detail.niveau_scope = contexte.niveau_max
    return detail


@router.post(
    "/connexion",
    response_model=JetonsReponse,
    summary="Se connecter",
    description="Authentifie un utilisateur et émet un couple de jetons.",
)
async def connexion(
    donnees: ConnexionDemande,
    session: SessionDep,
    metadonnees: MetadonneesDep,
) -> JetonsReponse:
    utilisateur = await moteur_identite.authentifier(session, donnees.email, donnees.mot_de_passe)
    acces, rafraichissement = await moteur_identite.ouvrir_session(
        session,
        utilisateur,
        adresse_ip=metadonnees["adresse_ip"],
        agent_utilisateur=metadonnees["agent_utilisateur"],
    )
    await journaliser(
        session,
        action="CONNEXION",
        entite_type="utilisateur",
        entite_id=utilisateur.id,
        entite_libelle=utilisateur.nom_complet,
        utilisateur_id=utilisateur.id,
        utilisateur_email=utilisateur.email,
        adresse_ip=metadonnees["adresse_ip"],
        agent_utilisateur=metadonnees["agent_utilisateur"],
    )
    return JetonsReponse(access_token=acces, refresh_token=rafraichissement)


@router.post(
    "/token",
    response_model=JetonsReponse,
    include_in_schema=False,
    summary="Se connecter (formulaire OAuth2)",
)
async def connexion_formulaire(
    formulaire: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
    metadonnees: MetadonneesDep,
) -> JetonsReponse:
    """Variante compatible avec le formulaire d'essai de la documentation."""
    utilisateur = await moteur_identite.authentifier(
        session, formulaire.username, formulaire.password
    )
    acces, rafraichissement = await moteur_identite.ouvrir_session(
        session,
        utilisateur,
        adresse_ip=metadonnees["adresse_ip"],
        agent_utilisateur=metadonnees["agent_utilisateur"],
    )
    return JetonsReponse(access_token=acces, refresh_token=rafraichissement)


@router.post(
    "/rafraichir",
    response_model=JetonsReponse,
    summary="Rafraîchir la session",
    description="Échange un jeton de rafraîchissement contre un nouveau couple de jetons.",
)
async def rafraichir(
    donnees: RafraichissementDemande,
    session: SessionDep,
) -> JetonsReponse:
    acces, rafraichissement = await moteur_identite.rafraichir_session(
        session, donnees.refresh_token
    )
    return JetonsReponse(access_token=acces, refresh_token=rafraichissement)


@router.post(
    "/deconnexion",
    response_model=MessageReponse,
    summary="Se déconnecter",
    description="Révoque toutes les sessions actives de l'utilisateur courant.",
)
async def deconnexion(contexte: ContexteDep, session: SessionDep) -> MessageReponse:
    revoquees = await moteur_identite.revoquer_sessions(session, contexte.id)
    return MessageReponse(
        message="Déconnexion effectuée.", details={"sessions_revoquees": revoquees}
    )


@router.get(
    "/moi",
    response_model=UtilisateurDetail,
    summary="Profil de l'utilisateur courant",
    description="Retourne l'identité, les rôles, les permissions et les préférences.",
)
async def profil(contexte: ContexteDep) -> UtilisateurDetail:
    return _detail_utilisateur(contexte)


@router.patch(
    "/moi/accessibilite",
    response_model=UtilisateurDetail,
    summary="Modifier ses préférences d'accessibilité",
)
async def modifier_accessibilite(
    preferences: PreferencesAccessibilite,
    contexte: ContexteDep,
    session: SessionDep,
) -> UtilisateurDetail:
    utilisateur = contexte.utilisateur
    for champ, valeur in preferences.model_dump(exclude_none=True).items():
        setattr(utilisateur, champ, valeur)
    await session.flush()
    await journaliser(
        session,
        action=Action.UPDATE,
        entite_type="utilisateur.accessibilite",
        entite_id=utilisateur.id,
        utilisateur_id=utilisateur.id,
        utilisateur_email=utilisateur.email,
        valeurs_apres=preferences.model_dump(exclude_none=True),
    )
    return _detail_utilisateur(contexte)


@router.post(
    "/moi/mot-de-passe",
    response_model=MessageReponse,
    status_code=status.HTTP_200_OK,
    summary="Changer son mot de passe",
    description="Vérifie le mot de passe actuel, applique le nouveau et révoque les sessions.",
)
async def changer_mot_de_passe(
    donnees: ChangementMotDePasse,
    contexte: ContexteDep,
    session: SessionDep,
) -> MessageReponse:
    await moteur_identite.changer_mot_de_passe(
        session,
        contexte.utilisateur,
        donnees.ancien_mot_de_passe,
        donnees.nouveau_mot_de_passe,
    )
    await journaliser(
        session,
        action="CHANGEMENT_MOT_DE_PASSE",
        entite_type="utilisateur",
        entite_id=contexte.id,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
    )
    return MessageReponse(
        message="Mot de passe modifié. Veuillez vous reconnecter.",
    )
