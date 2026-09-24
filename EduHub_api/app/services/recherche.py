"""Recherche transverse : registre des entités interrogeables et exécution."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.engines.search import (
    Conjonction,
    ConstructeurRequete,
    Critere,
    DescripteurChamp,
    Operateur,
    compter,
)
from app.models.apprenant import Apprenant
from app.models.diplome import DiplomeDelivre
from app.models.etablissement import Etablissement
from app.models.evaluation import Bulletin, MoyenneMatiere
from app.models.examen import Candidat, ResultatExamen, SessionExamen
from app.models.pedagogie import SyntheseAssiduite
from app.models.personnel import Enseignant
from app.models.projet import Projet
from app.models.referentiel import Commune, Departement, TypeEtablissement
from app.models.scolarite import Classe, Matiere


@dataclass(frozen=True, slots=True)
class Colonne:
    """Colonne restituée dans les résultats de recherche."""

    cle: str
    libelle: str
    expression: Any


@dataclass
class EntiteRecherchable:
    """Entité exposée au moteur de recherche avancée."""

    cle: str
    libelle: str
    ressource: str
    base: Any
    colonnes: Sequence[Colonne]
    champs: Sequence[DescripteurChamp]
    jointures: Sequence[Any] = ()
    champs_libres: Sequence[Any] = ()

    @property
    def constructeur(self) -> ConstructeurRequete:
        return ConstructeurRequete(self.cle, self.champs)

    def statement(self) -> Select:
        stmt = select(*[colonne.expression for colonne in self.colonnes]).select_from(self.base)
        for jointure in self.jointures:
            stmt = (
                stmt.outerjoin(*jointure)
                if isinstance(jointure, tuple)
                else stmt.outerjoin(jointure)
            )
        return stmt


def _entites() -> dict[str, EntiteRecherchable]:
    """Construit le registre des entités interrogeables."""
    apprenants = EntiteRecherchable(
        cle="apprenants",
        libelle="Apprenants",
        ressource="apprenants",
        base=Apprenant,
        jointures=(
            (Etablissement, Etablissement.id == Apprenant.etablissement_actuel_id),
            (Commune, Commune.id == Apprenant.commune_id),
            (Departement, Departement.id == Commune.departement_id),
            (TypeEtablissement, TypeEtablissement.id == Etablissement.type_etablissement_id),
        ),
        colonnes=(
            Colonne("id", "Identifiant", Apprenant.id),
            Colonne("identifiant_educatif", "Identifiant éducatif", Apprenant.identifiant_educatif),
            Colonne("nom", "Nom", Apprenant.nom),
            Colonne("prenoms", "Prénoms", Apprenant.prenoms),
            Colonne("sexe", "Sexe", Apprenant.sexe),
            Colonne("date_naissance", "Date de naissance", Apprenant.date_naissance),
            Colonne("etablissement", "Établissement", Etablissement.nom),
            Colonne("type_etablissement", "Type", TypeEtablissement.code),
            Colonne("commune", "Commune", Commune.libelle),
            Colonne("departement", "Département", Departement.libelle),
            Colonne("statut", "Statut", Apprenant.statut),
            Colonne("handicap", "Besoin spécifique", Apprenant.type_handicap),
        ),
        champs=(
            DescripteurChamp("nom", "Nom", Apprenant.nom),
            DescripteurChamp("prenoms", "Prénoms", Apprenant.prenoms),
            DescripteurChamp(
                "identifiant_educatif", "Identifiant éducatif", Apprenant.identifiant_educatif
            ),
            DescripteurChamp("sexe", "Sexe", Apprenant.sexe, "liste", ("MASCULIN", "FEMININ")),
            DescripteurChamp(
                "date_naissance", "Date de naissance", Apprenant.date_naissance, "date"
            ),
            DescripteurChamp("statut", "Statut", Apprenant.statut, "liste"),
            DescripteurChamp("handicap", "Besoin spécifique", Apprenant.type_handicap, "liste"),
            DescripteurChamp("tiers_temps", "Tiers temps", Apprenant.tiers_temps, "booleen"),
            DescripteurChamp("etablissement", "Établissement", Etablissement.nom),
            DescripteurChamp(
                "type_etablissement", "Type d'établissement", TypeEtablissement.code, "liste"
            ),
            DescripteurChamp("commune", "Commune", Commune.libelle),
            DescripteurChamp("departement", "Département", Departement.libelle),
            DescripteurChamp(
                "effectif_etablissement",
                "Effectif de l'établissement",
                Etablissement.effectif_actuel,
                "nombre",
            ),
        ),
        champs_libres=(Apprenant.nom, Apprenant.prenoms, Apprenant.identifiant_educatif),
    )

    etablissements = EntiteRecherchable(
        cle="etablissements",
        libelle="Établissements",
        ressource="etablissements",
        base=Etablissement,
        jointures=(
            (Commune, Commune.id == Etablissement.commune_id),
            (Departement, Departement.id == Commune.departement_id),
            (TypeEtablissement, TypeEtablissement.id == Etablissement.type_etablissement_id),
        ),
        colonnes=(
            Colonne("id", "Identifiant", Etablissement.id),
            Colonne("code", "Code", Etablissement.code),
            Colonne("nom", "Nom", Etablissement.nom),
            Colonne("type_etablissement", "Type", TypeEtablissement.code),
            Colonne("commune", "Commune", Commune.libelle),
            Colonne("departement", "Département", Departement.libelle),
            Colonne("effectif", "Effectif", Etablissement.effectif_actuel),
            Colonne("capacite", "Capacité", Etablissement.capacite_accueil),
            Colonne("accessibilite", "Accessibilité", Etablissement.accessibilite),
            Colonne("latitude", "Latitude", Etablissement.latitude),
            Colonne("longitude", "Longitude", Etablissement.longitude),
        ),
        champs=(
            DescripteurChamp("code", "Code", Etablissement.code),
            DescripteurChamp("nom", "Nom", Etablissement.nom),
            DescripteurChamp(
                "type_etablissement", "Type d'établissement", TypeEtablissement.code, "liste"
            ),
            DescripteurChamp("commune", "Commune", Commune.libelle),
            DescripteurChamp("departement", "Département", Departement.libelle),
            DescripteurChamp("effectif", "Effectif", Etablissement.effectif_actuel, "nombre"),
            DescripteurChamp("capacite", "Capacité", Etablissement.capacite_accueil, "nombre"),
            DescripteurChamp("zone_rurale", "Zone rurale", Etablissement.zone_rurale, "booleen"),
            DescripteurChamp(
                "est_centre_examen", "Centre d'examen", Etablissement.est_centre_examen, "booleen"
            ),
            DescripteurChamp("electricite", "Électricité", Etablissement.electricite, "booleen"),
            DescripteurChamp("eau_potable", "Eau potable", Etablissement.eau_potable, "booleen"),
            DescripteurChamp(
                "connexion_internet", "Internet", Etablissement.connexion_internet, "booleen"
            ),
            DescripteurChamp(
                "accessibilite", "Accessibilité", Etablissement.accessibilite, "liste"
            ),
            DescripteurChamp(
                "annee_creation", "Année de création", Etablissement.annee_creation, "nombre"
            ),
        ),
        champs_libres=(Etablissement.nom, Etablissement.code),
    )

    enseignants = EntiteRecherchable(
        cle="enseignants",
        libelle="Enseignants",
        ressource="enseignants",
        base=Enseignant,
        jointures=((Etablissement, Etablissement.id == Enseignant.etablissement_principal_id),),
        colonnes=(
            Colonne("id", "Identifiant", Enseignant.id),
            Colonne("matricule", "Matricule", Enseignant.matricule),
            Colonne("nom", "Nom", Enseignant.nom),
            Colonne("prenoms", "Prénoms", Enseignant.prenoms),
            Colonne("sexe", "Sexe", Enseignant.sexe),
            Colonne("grade", "Grade", Enseignant.grade),
            Colonne("specialite", "Spécialité", Enseignant.specialite),
            Colonne("etablissement", "Établissement", Etablissement.nom),
            Colonne("situation", "Situation", Enseignant.situation),
        ),
        champs=(
            DescripteurChamp("matricule", "Matricule", Enseignant.matricule),
            DescripteurChamp("nom", "Nom", Enseignant.nom),
            DescripteurChamp("sexe", "Sexe", Enseignant.sexe, "liste"),
            DescripteurChamp("grade", "Grade", Enseignant.grade),
            DescripteurChamp("specialite", "Spécialité", Enseignant.specialite),
            DescripteurChamp("statut_agent", "Statut", Enseignant.statut_agent, "liste"),
            DescripteurChamp("situation", "Situation", Enseignant.situation, "liste"),
            DescripteurChamp("etablissement", "Établissement", Etablissement.nom),
            DescripteurChamp("peut_corriger", "Peut corriger", Enseignant.peut_corriger, "booleen"),
        ),
        champs_libres=(Enseignant.nom, Enseignant.prenoms, Enseignant.matricule),
    )

    bulletins = EntiteRecherchable(
        cle="bulletins",
        libelle="Bulletins",
        ressource="bulletins",
        base=Bulletin,
        jointures=(
            (Apprenant, Apprenant.id == Bulletin.apprenant_id),
            (Classe, Classe.id == Bulletin.classe_id),
            (Etablissement, Etablissement.id == Bulletin.etablissement_id),
            (Commune, Commune.id == Etablissement.commune_id),
            (Departement, Departement.id == Commune.departement_id),
            (TypeEtablissement, TypeEtablissement.id == Etablissement.type_etablissement_id),
        ),
        colonnes=(
            Colonne("id", "Identifiant", Bulletin.id),
            Colonne("numero", "Numéro", Bulletin.numero),
            Colonne("apprenant", "Apprenant", Apprenant.nom),
            Colonne("prenoms", "Prénoms", Apprenant.prenoms),
            Colonne("identifiant_educatif", "Identifiant", Apprenant.identifiant_educatif),
            Colonne("classe", "Classe", Classe.libelle),
            Colonne("etablissement", "Établissement", Etablissement.nom),
            Colonne("departement", "Département", Departement.libelle),
            Colonne("moyenne_generale", "Moyenne générale", Bulletin.moyenne_generale),
            Colonne("rang", "Rang", Bulletin.rang),
            Colonne("mention", "Mention", Bulletin.mention),
        ),
        champs=(
            DescripteurChamp(
                "moyenne_generale", "Moyenne générale", Bulletin.moyenne_generale, "nombre"
            ),
            DescripteurChamp("rang", "Rang", Bulletin.rang, "nombre"),
            DescripteurChamp("mention", "Mention", Bulletin.mention, "liste"),
            DescripteurChamp("decision", "Décision", Bulletin.decision, "liste"),
            DescripteurChamp("apprenant", "Nom de l'apprenant", Apprenant.nom),
            DescripteurChamp("sexe", "Sexe", Apprenant.sexe, "liste"),
            DescripteurChamp("handicap", "Besoin spécifique", Apprenant.type_handicap, "liste"),
            DescripteurChamp("classe", "Classe", Classe.libelle),
            DescripteurChamp("etablissement", "Établissement", Etablissement.nom),
            DescripteurChamp(
                "type_etablissement", "Type d'établissement", TypeEtablissement.code, "liste"
            ),
            DescripteurChamp("commune", "Commune", Commune.libelle),
            DescripteurChamp("departement", "Département", Departement.libelle),
            DescripteurChamp("absences_heures", "Absences", Bulletin.absences_heures, "nombre"),
        ),
        champs_libres=(Apprenant.nom, Apprenant.prenoms, Bulletin.numero),
    )

    candidats = EntiteRecherchable(
        cle="candidats",
        libelle="Candidats",
        ressource="candidats",
        base=Candidat,
        jointures=(
            (SessionExamen, SessionExamen.id == Candidat.session_id),
            (ResultatExamen, ResultatExamen.candidat_id == Candidat.id),
            (Etablissement, Etablissement.id == Candidat.etablissement_id),
            (Departement, Departement.id == Candidat.departement_id),
        ),
        colonnes=(
            Colonne("id", "Identifiant", Candidat.id),
            Colonne("numero_candidat", "Numéro", Candidat.numero_candidat),
            Colonne("numero_table", "Table", Candidat.numero_table),
            Colonne("nom", "Nom", Candidat.nom),
            Colonne("prenoms", "Prénoms", Candidat.prenoms),
            Colonne("sexe", "Sexe", Candidat.sexe),
            Colonne("session", "Session", SessionExamen.libelle),
            Colonne("etablissement", "Établissement", Etablissement.nom),
            Colonne("departement", "Département", Departement.libelle),
            Colonne("statut_dossier", "Statut du dossier", Candidat.statut_dossier),
            Colonne("moyenne", "Moyenne", ResultatExamen.moyenne),
            Colonne("decision", "Décision", ResultatExamen.decision),
            Colonne("mention", "Mention", ResultatExamen.mention),
        ),
        champs=(
            DescripteurChamp("numero_candidat", "Numéro de candidat", Candidat.numero_candidat),
            DescripteurChamp("numero_table", "Numéro de table", Candidat.numero_table),
            DescripteurChamp("nom", "Nom", Candidat.nom),
            DescripteurChamp("sexe", "Sexe", Candidat.sexe, "liste"),
            DescripteurChamp("session", "Session", SessionExamen.libelle),
            DescripteurChamp("annee", "Année", SessionExamen.annee, "nombre"),
            DescripteurChamp(
                "statut_dossier", "Statut du dossier", Candidat.statut_dossier, "liste"
            ),
            DescripteurChamp(
                "type_candidature", "Type de candidature", Candidat.type_candidature, "liste"
            ),
            DescripteurChamp("handicap", "Besoin spécifique", Candidat.type_handicap, "liste"),
            DescripteurChamp("etablissement", "Établissement", Etablissement.nom),
            DescripteurChamp("departement", "Département", Departement.libelle),
            DescripteurChamp("moyenne", "Moyenne", ResultatExamen.moyenne, "nombre"),
            DescripteurChamp("decision", "Décision", ResultatExamen.decision, "liste"),
            DescripteurChamp("mention", "Mention", ResultatExamen.mention, "liste"),
        ),
        champs_libres=(Candidat.nom, Candidat.prenoms, Candidat.numero_candidat),
    )

    classes = EntiteRecherchable(
        cle="classes",
        libelle="Classes",
        ressource="classes",
        base=Classe,
        jointures=(
            (Etablissement, Etablissement.id == Classe.etablissement_id),
            (Commune, Commune.id == Etablissement.commune_id),
            (Departement, Departement.id == Commune.departement_id),
        ),
        colonnes=(
            Colonne("id", "Identifiant", Classe.id),
            Colonne("code", "Code", Classe.code),
            Colonne("libelle", "Libellé", Classe.libelle),
            Colonne("etablissement", "Établissement", Etablissement.nom),
            Colonne("departement", "Département", Departement.libelle),
            Colonne("effectif", "Effectif", Classe.effectif),
            Colonne("moyenne_classe", "Moyenne", Classe.moyenne_classe),
        ),
        champs=(
            DescripteurChamp("code", "Code", Classe.code),
            DescripteurChamp("libelle", "Libellé", Classe.libelle),
            DescripteurChamp("effectif", "Effectif", Classe.effectif, "nombre"),
            DescripteurChamp("moyenne_classe", "Moyenne", Classe.moyenne_classe, "nombre"),
            DescripteurChamp("etablissement", "Établissement", Etablissement.nom),
            DescripteurChamp("departement", "Département", Departement.libelle),
        ),
        champs_libres=(Classe.libelle, Classe.code),
    )

    projets = EntiteRecherchable(
        cle="projets",
        libelle="Projets",
        ressource="projets",
        base=Projet,
        jointures=((Etablissement, Etablissement.id == Projet.etablissement_id),),
        colonnes=(
            Colonne("id", "Identifiant", Projet.id),
            Colonne("code", "Code", Projet.code),
            Colonne("titre", "Titre", Projet.titre),
            Colonne("domaine", "Domaine", Projet.domaine),
            Colonne("statut", "Statut", Projet.statut),
            Colonne("etablissement", "Établissement", Etablissement.nom),
            Colonne("avancement", "Avancement", Projet.avancement_pourcentage),
        ),
        champs=(
            DescripteurChamp("titre", "Titre", Projet.titre),
            DescripteurChamp("domaine", "Domaine", Projet.domaine),
            DescripteurChamp("statut", "Statut", Projet.statut, "liste"),
            DescripteurChamp("avancement", "Avancement", Projet.avancement_pourcentage, "nombre"),
            DescripteurChamp("etablissement", "Établissement", Etablissement.nom),
        ),
        champs_libres=(Projet.titre, Projet.code),
    )

    diplomes = EntiteRecherchable(
        cle="diplomes",
        libelle="Diplômes",
        ressource="diplomes",
        base=DiplomeDelivre,
        colonnes=(
            Colonne("id", "Identifiant", DiplomeDelivre.id),
            Colonne("numero", "Numéro", DiplomeDelivre.numero),
            Colonne("titulaire", "Titulaire", DiplomeDelivre.titulaire_nom),
            Colonne("intitule", "Intitulé", DiplomeDelivre.intitule),
            Colonne("annee", "Année", DiplomeDelivre.annee),
            Colonne("mention", "Mention", DiplomeDelivre.mention),
            Colonne("statut", "Statut", DiplomeDelivre.statut),
        ),
        champs=(
            DescripteurChamp("numero", "Numéro", DiplomeDelivre.numero),
            DescripteurChamp("titulaire", "Titulaire", DiplomeDelivre.titulaire_nom),
            DescripteurChamp("annee", "Année", DiplomeDelivre.annee, "nombre"),
            DescripteurChamp("mention", "Mention", DiplomeDelivre.mention, "liste"),
            DescripteurChamp("statut", "Statut", DiplomeDelivre.statut, "liste"),
        ),
        champs_libres=(DiplomeDelivre.numero, DiplomeDelivre.titulaire_nom),
    )

    return {
        entite.cle: entite
        for entite in (
            apprenants,
            etablissements,
            enseignants,
            bulletins,
            candidats,
            classes,
            projets,
            diplomes,
        )
    }


REGISTRE: dict[str, EntiteRecherchable] = _entites()


def obtenir_entite(cle: str) -> EntiteRecherchable:
    entite = REGISTRE.get(cle)
    if entite is None:
        raise ValidationError(
            f"Entité « {cle} » inconnue du moteur de recherche.",
            details={"entites_disponibles": sorted(REGISTRE)},
        )
    return entite


#: Entités dont chaque ligne se rapporte à un apprenant, et colonne de rattachement.
CLE_APPRENANT = {
    "apprenants": Apprenant.id,
    "bulletins": Bulletin.apprenant_id,
}


def est_champ_calcule(champ: str) -> bool:
    """Indique si un champ est résolu par une sous-requête plutôt que par une colonne."""
    return champ.startswith("moyenne_matiere:") or champ in {
        "moyenne_generale",
        "taux_absence",
        "taux_presence",
    }


def _sous_requete_moyenne_matiere(code_matiere: str) -> Select:
    """Moyenne d'un apprenant dans une matière donnée, toutes périodes confondues."""
    return (
        select(
            MoyenneMatiere.apprenant_id.label("apprenant_id"),
            func.avg(MoyenneMatiere.moyenne).label("valeur"),
        )
        .join(Matiere, Matiere.id == MoyenneMatiere.matiere_id)
        .where(Matiere.code == code_matiere.upper(), MoyenneMatiere.moyenne.isnot(None))
        .group_by(MoyenneMatiere.apprenant_id)
        .subquery()
    )


def _sous_requete_moyenne_generale() -> Select:
    """Moyenne générale d'un apprenant, consolidée sur l'ensemble de ses bulletins."""
    return (
        select(
            Bulletin.apprenant_id.label("apprenant_id"),
            func.avg(Bulletin.moyenne_generale).label("valeur"),
        )
        .where(Bulletin.moyenne_generale.isnot(None))
        .group_by(Bulletin.apprenant_id)
        .subquery()
    )


def _sous_requete_assiduite(inverser: bool) -> Select:
    """Taux de présence — ou d'absence — moyen d'un apprenant."""
    expression = (
        (100 - func.avg(SyntheseAssiduite.taux_presence))
        if inverser
        else func.avg(SyntheseAssiduite.taux_presence)
    )
    return (
        select(
            SyntheseAssiduite.apprenant_id.label("apprenant_id"),
            expression.label("valeur"),
        )
        .group_by(SyntheseAssiduite.apprenant_id)
        .subquery()
    )


#: Comparaisons applicables à une valeur calculée.
_COMPARAISONS = {
    Operateur.EGAL: lambda colonne, valeur: colonne == valeur,
    Operateur.DIFFERENT: lambda colonne, valeur: colonne != valeur,
    Operateur.SUPERIEUR: lambda colonne, valeur: colonne > valeur,
    Operateur.SUPERIEUR_EGAL: lambda colonne, valeur: colonne >= valeur,
    Operateur.INFERIEUR: lambda colonne, valeur: colonne < valeur,
    Operateur.INFERIEUR_EGAL: lambda colonne, valeur: colonne <= valeur,
    Operateur.ENTRE: lambda colonne, valeur: colonne.between(valeur[0], valeur[1]),
}


def _critere_special(
    statement: Select, critere: Critere, entite: EntiteRecherchable
) -> tuple[Select, Any] | None:
    """Résout un champ calculé : moyenne par matière, moyenne générale, assiduité.

    Ces champs n'existent dans aucune table : ils sont reconstruits par une
    sous-requête agrégée, jointe à l'entité interrogée.
    """
    cle_jointure = CLE_APPRENANT.get(entite.cle)
    if cle_jointure is None or not est_champ_calcule(critere.champ):
        return None

    if critere.champ.startswith("moyenne_matiere:"):
        sous_requete = _sous_requete_moyenne_matiere(critere.champ.split(":", 1)[1])
    elif critere.champ == "moyenne_generale":
        sous_requete = _sous_requete_moyenne_generale()
    else:
        sous_requete = _sous_requete_assiduite(critere.champ == "taux_absence")

    statement = statement.outerjoin(sous_requete, sous_requete.c.apprenant_id == cle_jointure)

    fabrique = _COMPARAISONS.get(critere.operateur)
    if fabrique is None:
        raise ValidationError(
            f"Opérateur « {critere.operateur.value} » non applicable au champ calculé "
            f"« {critere.champ} »."
        )
    return statement, fabrique(sous_requete.c.valeur, critere.valeur)


async def executer(
    session: AsyncSession,
    entite_cle: str,
    criteres: Sequence[Critere],
    *,
    conjonction: Conjonction = Conjonction.ET,
    tri: str | None = None,
    sens: str = "asc",
    page: int = 1,
    taille: int = 25,
    recherche_libre: str | None = None,
) -> dict[str, Any]:
    """Exécute une requête du constructeur et renvoie les lignes restituées."""
    entite = obtenir_entite(entite_cle)
    statement = entite.statement()

    if hasattr(entite.base, "supprime"):
        statement = statement.where(entite.base.supprime.is_(False))

    if recherche_libre and entite.champs_libres:
        statement = statement.where(
            or_(*[champ.ilike(f"%{recherche_libre}%") for champ in entite.champs_libres])
        )

    constructeur = entite.constructeur
    ordinaires: list[Critere] = []
    for critere in criteres:
        special = _critere_special(statement, critere, entite)
        if special is None:
            ordinaires.append(critere)
        else:
            statement, clause = special
            statement = statement.where(clause)

    statement = constructeur.appliquer(statement, ordinaires, conjonction)
    statement = constructeur.trier(statement, tri, sens)

    total = await compter(session, statement)
    resultat = await session.execute(statement.offset((page - 1) * taille).limit(taille))

    lignes = []
    for ligne in resultat.all():
        enregistrement: dict[str, Any] = {}
        for colonne, valeur in zip(entite.colonnes, ligne, strict=False):
            if isinstance(valeur, uuid.UUID):
                enregistrement[colonne.cle] = str(valeur)
            elif hasattr(valeur, "value"):
                enregistrement[colonne.cle] = valeur.value
            elif hasattr(valeur, "isoformat"):
                enregistrement[colonne.cle] = valeur.isoformat()
            else:
                enregistrement[colonne.cle] = valeur
        lignes.append(enregistrement)

    return {
        "entite": entite.cle,
        "total": total,
        "page": page,
        "taille": taille,
        "pages": (total + taille - 1) // taille if taille else 0,
        "colonnes": [
            {"cle": colonne.cle, "libelle": colonne.libelle} for colonne in entite.colonnes
        ],
        "lignes": lignes,
    }
