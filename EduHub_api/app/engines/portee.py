"""Restriction des données au périmètre de celui qui les demande.

Le modèle de droits distingue depuis l'origine six niveaux de portée, du
personnel au national, et chaque rôle en porte un. Mais ce niveau ne servait
qu'à documenter : aucune requête ne s'en servait pour filtrer. Un élève
disposant de « apprenants:READ » listait donc les douze mille apprenants du
pays, et « bulletins:READ » lui ouvrait les bulletins de tous les autres.

Ce module fournit la pièce manquante : à partir du contexte de l'appelant et
d'une déclaration attachée à chaque entité, il produit la condition SQL qui
restreint les lignes visibles.

Le principe retenu est celui du refus par défaut. Une entité dont la portée
n'est pas déclarée reste inaccessible aux rôles personnels : mieux vaut une
page vide, qu'on remarque et qu'on corrige, qu'une fuite qu'on ne remarque pas.
Les catalogues sans données personnelles — le fonds de la bibliothèque, les
lignes de transport — se déclarent explicitement ouverts, ce qui oblige à se
poser la question pour chacun.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import ColumnElement, Select, false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import NiveauScope
from app.engines.identity import ContexteUtilisateur
from app.models.apprenant import Apprenant, ApprenantParent, Parent
from app.models.personnel import Enseignant
from app.models.scolarite import Inscription


@dataclass(slots=True)
class PerimetrePersonnel:
    """Ce à quoi un compte est rattaché, une fois les liens résolus.

    Un parent porte les identifiants de ses enfants ; un élève le sien ; un
    enseignant son établissement principal. Les ensembles sont vides quand le
    compte n'est rattaché à rien, ce qui suffit à ne rien lui montrer.
    """

    apprenants: set[uuid.UUID] = field(default_factory=set)
    classes: set[uuid.UUID] = field(default_factory=set)
    etablissements: set[uuid.UUID] = field(default_factory=set)
    enseignants: set[uuid.UUID] = field(default_factory=set)

    @property
    def vide(self) -> bool:
        return not (self.apprenants or self.classes or self.etablissements or self.enseignants)


async def resoudre_perimetre(
    session: AsyncSession, contexte: ContexteUtilisateur
) -> PerimetrePersonnel:
    """Résout les rattachements réels d'un compte, par une poignée de requêtes."""
    perimetre = PerimetrePersonnel(etablissements=set(contexte.etablissements))

    # L'apprenant que ce compte incarne, le cas échéant.
    identifiant = await session.scalar(
        select(Apprenant.id).where(
            Apprenant.utilisateur_id == contexte.id, Apprenant.supprime.is_(False)
        )
    )
    if identifiant is not None:
        perimetre.apprenants.add(identifiant)

    # Les enfants, si le compte est celui d'un parent.
    parent_id = await session.scalar(
        select(Parent.id).where(Parent.utilisateur_id == contexte.id, Parent.supprime.is_(False))
    )
    if parent_id is not None:
        enfants = await session.scalars(
            select(ApprenantParent.apprenant_id).where(ApprenantParent.parent_id == parent_id)
        )
        perimetre.apprenants.update(enfants)

    # L'enseignant, et l'établissement où il exerce.
    enseignant = (
        await session.execute(
            select(Enseignant.id, Enseignant.etablissement_principal_id).where(
                Enseignant.utilisateur_id == contexte.id, Enseignant.supprime.is_(False)
            )
        )
    ).first()
    if enseignant is not None:
        perimetre.enseignants.add(enseignant[0])
        if enseignant[1] is not None:
            perimetre.etablissements.add(enseignant[1])

    # Les classes et établissements que fréquentent les apprenants du périmètre.
    if perimetre.apprenants:
        # Toutes les entités ne portent pas la suppression logique : on ne
        # filtre dessus que lorsqu'elle existe.
        requete = select(Inscription.classe_id, Inscription.etablissement_id).where(
            Inscription.apprenant_id.in_(perimetre.apprenants)
        )
        if hasattr(Inscription, "supprime"):
            requete = requete.where(Inscription.supprime.is_(False))
        lignes = await session.execute(requete)
        for classe_id, etablissement_id in lignes:
            if classe_id is not None:
                perimetre.classes.add(classe_id)
            if etablissement_id is not None:
                perimetre.etablissements.add(etablissement_id)

    return perimetre


@dataclass(frozen=True, slots=True)
class Portee:
    """Comment une entité se rattache au périmètre de l'appelant.

    Chaque champ nomme la colonne qui porte le lien, quand elle existe. Une
    entité peut en déclarer plusieurs : la condition les combine par « ou »,
    car un bulletin appartient à son apprenant comme à son établissement.
    """

    #: Colonne portant l'identifiant de l'apprenant concerné.
    apprenant: str | None = None
    #: Colonne portant l'identifiant de la classe.
    classe: str | None = None
    #: Colonne portant l'identifiant de l'établissement.
    etablissement: str | None = None
    #: Colonne portant l'identifiant de l'enseignant.
    enseignant: str | None = None
    #: L'entité elle-même est un apprenant : on filtre sur sa clé primaire.
    est_apprenant: bool = False
    #: Données non personnelles, consultables par tous — décision explicite.
    catalogue: bool = False

    @staticmethod
    def ouverte() -> Portee:
        """Catalogue sans données personnelles : fonds documentaire, lignes de bus."""
        return Portee(catalogue=True)


def condition_portee(
    modele: type,
    portee: Portee | None,
    perimetre: PerimetrePersonnel,
) -> ColumnElement[bool] | None:
    """Condition restreignant les lignes au périmètre, ou None si tout est visible."""
    if portee is not None and portee.catalogue:
        return None

    if portee is None:
        # Portée non déclarée : on refuse plutôt que d'exposer.
        return false()

    conditions: list[ColumnElement[bool]] = []

    if portee.est_apprenant and perimetre.apprenants:
        conditions.append(modele.id.in_(perimetre.apprenants))
    if portee.apprenant and perimetre.apprenants and hasattr(modele, portee.apprenant):
        conditions.append(getattr(modele, portee.apprenant).in_(perimetre.apprenants))
    if portee.classe and perimetre.classes and hasattr(modele, portee.classe):
        conditions.append(getattr(modele, portee.classe).in_(perimetre.classes))
    if portee.enseignant and perimetre.enseignants and hasattr(modele, portee.enseignant):
        conditions.append(getattr(modele, portee.enseignant).in_(perimetre.enseignants))

    if not conditions:
        return false()

    if len(conditions) == 1:
        return conditions[0]
    return or_(*conditions)


def appliquer_portee(
    statement: Select,
    modele: type,
    portee: Portee | None,
    contexte: ContexteUtilisateur,
    perimetre: PerimetrePersonnel,
) -> Select:
    """Restreint une requête au périmètre de l'appelant, selon son niveau.

    Au-dessus du niveau établissement — direction, ministère, national — aucune
    restriction n'est appliquée : ces rôles ont vocation à voir l'ensemble. Au
    niveau établissement, on restreint aux établissements de rattachement quand
    l'entité en déclare un. Au niveau personnel, on s'en tient strictement aux
    personnes concernées.
    """
    if contexte.est_omnipotent:
        return statement
    if contexte.niveau_max not in (NiveauScope.PERSONNEL, NiveauScope.ETABLISSEMENT):
        return statement
    if portee is not None and portee.catalogue:
        return statement

    if contexte.niveau_max is NiveauScope.ETABLISSEMENT:
        rattachable = (
            portee is not None
            and bool(portee.etablissement)
            and hasattr(modele, portee.etablissement)
        )
        if rattachable:
            if not perimetre.etablissements:
                return statement.where(false())
            colonne = getattr(modele, portee.etablissement)
            return statement.where(colonne.in_(perimetre.etablissements))
        # Le rattachement à l'établissement n'est pas encore déclaré sur cette
        # entité. On laisse passer plutôt que de vider la page : le niveau
        # établissement reste à traiter entité par entité, alors que le niveau
        # personnel — le cas où la confidentialité est réellement en jeu — est
        # traité ci-dessous.
        return statement

    condition = condition_portee(modele, portee, perimetre)
    return statement if condition is None else statement.where(condition)
