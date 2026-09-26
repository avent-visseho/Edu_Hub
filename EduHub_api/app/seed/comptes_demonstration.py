"""Adresses mémorables pour les comptes de démonstration de chaque acteur.

Le générateur crée déjà des comptes pour toute la chaîne — quatre mille élèves,
deux mille six cents parents, quatorze cents enseignants, deux cent cinquante
chefs d'établissement — mais leurs adresses sont dérivées de données engendrées
au hasard : « ablam.adjovi.635@enseignant.bj » n'est ni devinable ni stable d'un
jeu de données à l'autre. Impossible, donc, de les proposer sur la page de
connexion.

Plutôt que de créer des comptes supplémentaires qui feraient doublon, on
renomme un compte existant de chaque rôle. Le compte conserve son rattachement
— l'élève reste inscrit dans sa classe, l'enseignant garde ses matières, le
parent ses enfants — et gagne une adresse qu'on peut écrire dans une
documentation.

Le choix est déterministe : pour chaque rôle, le compte dont l'adresse vient en
premier dans l'ordre alphabétique. Deux exécutions sur le même jeu de données
désignent donc le même compte.
"""

from __future__ import annotations

from sqlalchemy import select, text, update

from app.core.enums import RoleCode
from app.core.logging import get_logger
from app.models.identity import Role, Utilisateur, UtilisateurRole
from app.seed.contexte import ContexteSeed

logger = get_logger("seed")

#: Rôle visé → (adresse retenue, libellé affiché sur la page de connexion).
COMPTES_ACTEURS: tuple[tuple[RoleCode, str, str], ...] = (
    (RoleCode.SCHOOL_ADMIN, "directeur@eduhub.bj", "Chef d'établissement"),
    (RoleCode.TEACHER, "enseignant@eduhub.bj", "Enseignant"),
    (RoleCode.STUDENT, "eleve@eduhub.bj", "Élève"),
    (RoleCode.PARENT, "parent@eduhub.bj", "Parent d'élève"),
)


async def generer(ctx: ContexteSeed) -> None:
    """Renomme un compte par rôle, en préservant tous ses rattachements."""
    for role_code, adresse, libelle in COMPTES_ACTEURS:
        identifiant = await _premier_compte(ctx, role_code)
        if identifiant is None:
            logger.warning("  aucun compte %s à renommer en %s", role_code, adresse)
            continue

        # L'adresse visée peut déjà exister si le générateur a produit la même
        # par hasard, ou si l'étape a déjà tourné : on la libère d'abord.
        await ctx.session.execute(
            text("UPDATE utilisateurs SET email = :libre WHERE email = :adresse AND id <> :ident"),
            {"libre": f"ancien.{adresse}", "adresse": adresse, "ident": identifiant},
        )
        await ctx.session.execute(
            update(Utilisateur).where(Utilisateur.id == identifiant).values(email=adresse)
        )
        logger.info("  compte de démonstration %s : %s", libelle, adresse)


async def _premier_compte(ctx: ContexteSeed, role_code: RoleCode) -> object | None:
    """Compte le plus ancien alphabétiquement pour ce rôle, pour un choix stable."""
    requete = (
        select(Utilisateur.id)
        .join(UtilisateurRole, UtilisateurRole.utilisateur_id == Utilisateur.id)
        .join(Role, Role.id == UtilisateurRole.role_id)
        .where(Role.code == role_code.value)
        .order_by(Utilisateur.email)
        .limit(1)
    )
    return (await ctx.session.execute(requete)).scalar_one_or_none()
