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
from app.models.examen import Candidat
from app.models.personnel import Enseignant
from app.models.scolarite import Classe, Inscription


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
    #: Colonne portant l'identifiant du candidat à un examen.
    candidat: str | None = None
    #: Colonne portant l'identifiant du compte, pour les entités qui en
    #: désignent un directement — un parent, un chercheur.
    utilisateur: str | None = None
    #: L'entité elle-même est un apprenant : on filtre sur sa clé primaire.
    est_apprenant: bool = False
    #: Données non personnelles, consultables par tous — décision explicite.
    catalogue: bool = False
    #: L'appartenance à l'établissement suffit-elle à y donner accès ?
    #:
    #: Vrai pour ce qui est offert à tous ses usagers : résidences, lignes de
    #: transport, projets, centres de santé. Faux par défaut, car la plupart des
    #: entités rattachées à un établissement décrivent autrui — les résultats
    #: d'examen de l'école ne regardent pas chacun de ses élèves.
    partage_etablissement: bool = False

    @staticmethod
    def ouverte() -> Portee:
        """Catalogue sans données personnelles : fonds documentaire, lignes de bus."""
        return Portee(catalogue=True)


def _apprenants_de(etablissements: set[uuid.UUID]) -> Select:
    """Sous-requête des apprenants inscrits dans ces établissements.

    La table des apprenants ne porte pas d'établissement : le rattachement
    passe par l'inscription, qui seule sait où l'élève est scolarisé et pour
    quelle année.
    """
    return select(Inscription.apprenant_id).where(Inscription.etablissement_id.in_(etablissements))


def _classes_de(etablissements: set[uuid.UUID]) -> Select:
    """Sous-requête des classes de ces établissements."""
    return select(Classe.id).where(Classe.etablissement_id.in_(etablissements))


def _candidats_de_apprenants(apprenants: set[uuid.UUID]) -> Select:
    """Sous-requête des candidatures à examen de ces apprenants.

    Résultats, copies et contentieux désignent un candidat, non un apprenant :
    la même personne porte deux identités selon qu'elle est scolarisée ou
    inscrite à un examen.
    """
    return select(Candidat.id).where(Candidat.apprenant_id.in_(apprenants))


def _candidats_de_etablissements(etablissements: set[uuid.UUID]) -> Select:
    """Sous-requête des candidatures présentées par ces établissements."""
    return select(Candidat.id).where(Candidat.etablissement_id.in_(etablissements))


def condition_etablissement(
    modele: type,
    portee: Portee,
    etablissements: set[uuid.UUID],
) -> ColumnElement[bool] | None:
    """Condition restreignant les lignes aux établissements de rattachement.

    Les mêmes colonnes déclarées pour la portée personnelle servent ici, mais
    l'ensemble de référence change : au lieu des apprenants que l'on est ou que
    l'on a pour enfants, ce sont ceux de l'établissement où l'on exerce.
    """
    conditions: list[ColumnElement[bool]] = []

    if portee.etablissement and hasattr(modele, portee.etablissement):
        conditions.append(getattr(modele, portee.etablissement).in_(etablissements))
    if portee.est_apprenant:
        conditions.append(modele.id.in_(_apprenants_de(etablissements)))
    if portee.apprenant and hasattr(modele, portee.apprenant):
        conditions.append(getattr(modele, portee.apprenant).in_(_apprenants_de(etablissements)))
    if portee.classe and hasattr(modele, portee.classe):
        conditions.append(getattr(modele, portee.classe).in_(_classes_de(etablissements)))
    if portee.candidat and hasattr(modele, portee.candidat):
        conditions.append(
            getattr(modele, portee.candidat).in_(_candidats_de_etablissements(etablissements))
        )

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return or_(*conditions)


def condition_portee(
    modele: type,
    portee: Portee | None,
    perimetre: PerimetrePersonnel,
    contexte_id: uuid.UUID | None = None,
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
    if portee.candidat and perimetre.apprenants and hasattr(modele, portee.candidat):
        conditions.append(
            getattr(modele, portee.candidat).in_(_candidats_de_apprenants(perimetre.apprenants))
        )
    if portee.utilisateur and contexte_id is not None and hasattr(modele, portee.utilisateur):
        conditions.append(getattr(modele, portee.utilisateur) == contexte_id)
    # L'appartenance à l'établissement n'ouvre l'accès que là où c'est
    # explicitement voulu : un élève accède aux résidences et aux lignes de bus
    # de son école, mais pas aux résultats d'examen de ses camarades.
    partage = (
        portee.partage_etablissement
        and portee.etablissement
        and perimetre.etablissements
        and hasattr(modele, portee.etablissement)
    )
    if partage:
        conditions.append(getattr(modele, portee.etablissement).in_(perimetre.etablissements))

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
        if portee is None:
            # Portée non déclarée : on laisse passer à ce niveau. Le périmètre
            # d'un personnel d'établissement n'expose pas d'inconnus, et fermer
            # d'un coup viderait ses écrans sans nécessité. Les entités se
            # déclarent au fur et à mesure.
            return statement
        if not perimetre.etablissements:
            return statement.where(false())
        condition = condition_etablissement(modele, portee, perimetre.etablissements)
        return statement if condition is None else statement.where(condition)

    condition = condition_portee(modele, portee, perimetre, contexte.id)
    return statement if condition is None else statement.where(condition)
