"""Moteur d'identité — authentification, rôles, permissions et portées."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.enums import Action, NiveauScope, RoleCode
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.identity import Permission, Role, SessionUtilisateur, Utilisateur, UtilisateurRole

MAX_TENTATIVES = 5
DUREE_VERROUILLAGE = timedelta(minutes=15)

#: Rôles disposant implicitement de toutes les permissions.
ROLES_OMNIPOTENTS = {RoleCode.SUPER_ADMIN.value}


class ContexteUtilisateur:
    """Vue applicative des droits d'un utilisateur authentifié."""

    def __init__(self, utilisateur: Utilisateur) -> None:
        self.utilisateur = utilisateur
        self.roles: set[str] = set()
        self.permissions: set[str] = set()
        self.structures: set[uuid.UUID] = set()
        self.etablissements: set[uuid.UUID] = set()
        self.niveau_max: NiveauScope = NiveauScope.PERSONNEL

        ordre = {
            NiveauScope.PERSONNEL: 0,
            NiveauScope.ETABLISSEMENT: 1,
            NiveauScope.DEPARTEMENT: 2,
            NiveauScope.DIRECTION: 3,
            NiveauScope.MINISTERE: 4,
            NiveauScope.NATIONAL: 5,
        }

        for affectation in utilisateur.affectations:
            if not affectation.actif or affectation.role is None:
                continue
            self.roles.add(affectation.role.code)
            for permission in affectation.role.permissions:
                self.permissions.add(f"{permission.ressource}:{permission.action.value}")
            if affectation.structure_id:
                self.structures.add(affectation.structure_id)
            if affectation.etablissement_id:
                self.etablissements.add(affectation.etablissement_id)
            if ordre[affectation.role.niveau_scope] > ordre[self.niveau_max]:
                self.niveau_max = affectation.role.niveau_scope

    @property
    def id(self) -> uuid.UUID:
        return self.utilisateur.id

    @property
    def email(self) -> str:
        return self.utilisateur.email

    @property
    def est_omnipotent(self) -> bool:
        return bool(self.roles & ROLES_OMNIPOTENTS)

    def a_role(self, *codes: str) -> bool:
        return bool(self.roles & set(codes))

    def a_permission(self, ressource: str, action: Action | str) -> bool:
        if self.est_omnipotent:
            return True
        valeur = action.value if isinstance(action, Action) else action
        return f"{ressource}:{valeur}" in self.permissions

    def exiger(self, ressource: str, action: Action | str) -> None:
        if not self.a_permission(ressource, action):
            valeur = action.value if isinstance(action, Action) else action
            raise PermissionDeniedError(
                f"Permission « {ressource}:{valeur} » requise.",
                details={"ressource": ressource, "action": valeur},
            )

    def peut_acceder_etablissement(self, etablissement_id: uuid.UUID | None) -> bool:
        """Un utilisateur au-dessus du niveau établissement voit tout son périmètre."""
        if self.est_omnipotent or self.niveau_max != NiveauScope.ETABLISSEMENT:
            return True
        return etablissement_id is not None and etablissement_id in self.etablissements


async def charger_utilisateur(session: AsyncSession, utilisateur_id: uuid.UUID) -> Utilisateur:
    stmt = (
        select(Utilisateur)
        .where(Utilisateur.id == utilisateur_id, Utilisateur.supprime.is_(False))
        .options(
            selectinload(Utilisateur.affectations)
            .selectinload(UtilisateurRole.role)
            .selectinload(Role.permissions)
        )
    )
    utilisateur = (await session.execute(stmt)).scalar_one_or_none()
    if utilisateur is None:
        raise AuthenticationError("Compte introuvable.", code="compte_introuvable")
    if not utilisateur.actif:
        raise AuthenticationError("Compte désactivé.", code="compte_desactive")
    return utilisateur


async def authentifier(
    session: AsyncSession,
    email: str,
    mot_de_passe: str,
) -> Utilisateur:
    """Vérifie les identifiants et gère le verrouillage après échecs répétés."""
    stmt = (
        select(Utilisateur)
        .where(Utilisateur.email == email.lower().strip(), Utilisateur.supprime.is_(False))
        .options(
            selectinload(Utilisateur.affectations)
            .selectinload(UtilisateurRole.role)
            .selectinload(Role.permissions)
        )
    )
    utilisateur = (await session.execute(stmt)).scalar_one_or_none()

    if utilisateur is None:
        raise AuthenticationError("Identifiants invalides.", code="identifiants_invalides")

    maintenant = datetime.now(UTC)
    if utilisateur.verrouille_jusqu_a and utilisateur.verrouille_jusqu_a > maintenant:
        raise AuthenticationError(
            "Compte temporairement verrouillé après plusieurs échecs.",
            code="compte_verrouille",
        )

    if not verify_password(mot_de_passe, utilisateur.mot_de_passe):
        utilisateur.tentatives_echouees += 1
        if utilisateur.tentatives_echouees >= MAX_TENTATIVES:
            utilisateur.verrouille_jusqu_a = maintenant + DUREE_VERROUILLAGE
            utilisateur.tentatives_echouees = 0
        await session.flush()
        raise AuthenticationError("Identifiants invalides.", code="identifiants_invalides")

    if not utilisateur.actif:
        raise AuthenticationError("Compte désactivé.", code="compte_desactive")

    utilisateur.tentatives_echouees = 0
    utilisateur.verrouille_jusqu_a = None
    utilisateur.derniere_connexion = maintenant
    await session.flush()
    return utilisateur


async def ouvrir_session(
    session: AsyncSession,
    utilisateur: Utilisateur,
    *,
    adresse_ip: str | None = None,
    agent_utilisateur: str | None = None,
) -> tuple[str, str]:
    """Émet un couple (jeton d'accès, jeton de rafraîchissement)."""
    contexte = ContexteUtilisateur(utilisateur)
    acces = create_access_token(
        str(utilisateur.id),
        extra={
            "email": utilisateur.email,
            "nom": utilisateur.nom_complet,
            "roles": sorted(contexte.roles),
            "scope": contexte.niveau_max.value,
        },
    )
    rafraichissement = create_refresh_token(str(utilisateur.id))
    charge = decode_token(rafraichissement, "refresh")

    session.add(
        SessionUtilisateur(
            utilisateur_id=utilisateur.id,
            jeton_id=charge["jti"],
            adresse_ip=adresse_ip,
            agent_utilisateur=agent_utilisateur,
            expire_le=datetime.fromtimestamp(charge["exp"], tz=UTC),
        )
    )
    await session.flush()
    return acces, rafraichissement


async def rafraichir_session(session: AsyncSession, jeton: str) -> tuple[str, str]:
    """Valide un jeton de rafraîchissement, le révoque et en émet un nouveau."""
    charge = decode_token(jeton, "refresh")
    stmt = select(SessionUtilisateur).where(
        SessionUtilisateur.jeton_id == charge["jti"],
        SessionUtilisateur.revoquee.is_(False),
    )
    session_utilisateur = (await session.execute(stmt)).scalar_one_or_none()
    if session_utilisateur is None:
        raise AuthenticationError("Session révoquée ou inconnue.", code="session_invalide")

    session_utilisateur.revoquee = True
    utilisateur = await charger_utilisateur(session, uuid.UUID(charge["sub"]))
    return await ouvrir_session(session, utilisateur)


async def revoquer_sessions(session: AsyncSession, utilisateur_id: uuid.UUID) -> int:
    """Révoque toutes les sessions actives d'un utilisateur."""
    stmt = select(SessionUtilisateur).where(
        SessionUtilisateur.utilisateur_id == utilisateur_id,
        SessionUtilisateur.revoquee.is_(False),
    )
    sessions = list((await session.execute(stmt)).scalars())
    for item in sessions:
        item.revoquee = True
    await session.flush()
    return len(sessions)


async def changer_mot_de_passe(
    session: AsyncSession,
    utilisateur: Utilisateur,
    ancien: str,
    nouveau: str,
) -> None:
    if not verify_password(ancien, utilisateur.mot_de_passe):
        raise AuthenticationError("Mot de passe actuel incorrect.", code="mot_de_passe_incorrect")
    if len(nouveau) < settings.password_min_length:
        raise AuthenticationError(
            f"Le mot de passe doit contenir au moins {settings.password_min_length} caractères.",
            code="mot_de_passe_faible",
        )
    utilisateur.mot_de_passe = hash_password(nouveau)
    utilisateur.doit_changer_mot_de_passe = False
    await session.flush()
    await revoquer_sessions(session, utilisateur.id)


async def permissions_du_role(session: AsyncSession, code_role: str) -> list[Permission]:
    stmt = select(Role).where(Role.code == code_role).options(selectinload(Role.permissions))
    role = (await session.execute(stmt)).scalar_one_or_none()
    return list(role.permissions) if role else []
