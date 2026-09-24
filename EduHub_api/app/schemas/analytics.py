"""Schémas de la gouvernance : tableaux de bord, recherche et cartographie."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field

from app.engines.search import Conjonction
from app.schemas.base import SchemaBase, SchemaEntree


class IndicateurReponse(SchemaBase):
    code: str
    libelle: str
    valeur: float
    unite: str | None = None
    variation: float | None = None
    detail: dict[str, Any] | None = None


class TableauBord(SchemaBase):
    """Tableau de bord générique, adapté au rôle de l'utilisateur."""

    perimetre: str
    perimetre_libelle: str
    indicateurs: list[IndicateurReponse] = Field(default_factory=list)
    graphiques: dict[str, list[dict]] = Field(default_factory=dict)
    alertes: list[dict] = Field(default_factory=list)


class CritereRecherche(SchemaEntree):
    champ: str = Field(min_length=1, max_length=120)
    operateur: str = Field(min_length=1, max_length=20)
    valeur: Any = None


class RequeteAvancee(SchemaEntree):
    """Requête produite par le constructeur visuel."""

    entite: str = Field(min_length=1, max_length=64)
    criteres: list[CritereRecherche] = Field(default_factory=list)
    conjonction: Conjonction = Conjonction.ET
    tri: str | None = None
    sens: str = Field(default="asc", pattern="^(asc|desc)$")
    page: int = Field(default=1, ge=1)
    taille: int = Field(default=25, ge=1, le=200)


class ResultatRecherche(SchemaBase):
    entite: str
    total: int
    page: int
    taille: int
    pages: int
    colonnes: list[dict[str, str]] = Field(default_factory=list)
    lignes: list[dict[str, Any]] = Field(default_factory=list)


class QuestionNaturelle(SchemaEntree):
    """Question posée en français à l'assistant de recherche."""

    question: str = Field(min_length=3, max_length=500)
    executer: bool = Field(
        default=True, description="Exécute la requête déduite et renvoie les résultats."
    )
    taille: int = Field(default=25, ge=1, le=200)


class ReponseNaturelle(SchemaBase):
    question: str
    entite: str
    confiance: float
    explications: list[str] = Field(default_factory=list)
    filtres: list[dict[str, Any]] = Field(default_factory=list)
    resultat: ResultatRecherche | None = None


class RechercheGlobaleResultat(SchemaBase):
    """Élément d'une recherche transverse."""

    type: str
    id: uuid.UUID
    libelle: str
    description: str | None = None
    lien: str


class PointCarte(SchemaBase):
    """Point géolocalisé affiché sur la carte nationale."""

    id: uuid.UUID
    libelle: str
    type: str
    latitude: float
    longitude: float
    commune: str | None = None
    departement: str | None = None
    effectif: int | None = None
    moyenne: float | None = None
    taux_reussite: float | None = None
    accessibilite: str | None = None


class SyntheseTerritoriale(SchemaBase):
    code: str
    libelle: str
    etablissements: int = 0
    apprenants: int = 0
    enseignants: int = 0
    candidats: int = 0
    admis: int = 0
    taux_reussite: float | None = None
    moyenne: float | None = None


class DemandeRapport(SchemaEntree):
    """Génération d'un rapport."""

    type_rapport: str = Field(min_length=1, max_length=64)
    titre: str | None = None
    annee_id: uuid.UUID | None = None
    etablissement_id: uuid.UUID | None = None
    structure_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    format_export: str = Field(default="PDF", pattern="^(PDF|CSV|JSON)$")


class AlerteLecture(SchemaBase):
    id: uuid.UUID
    code: str
    titre: str
    message: str
    niveau: str
    domaine: str
    entite_type: str | None = None
    entite_id: uuid.UUID | None = None
    etablissement_id: uuid.UUID | None = None
    valeur_mesuree: float | None = None
    seuil: float | None = None
    traitee: bool


class RegleMetierLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    description: str | None = None
    domaine: str
    entite_cible: str
    conditions: dict[str, Any]
    consequences: dict[str, Any]
    priorite: int
    active: bool
    nombre_declenchements: int


class RegleMetierEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=255)
    description: str | None = None
    domaine: str = Field(min_length=1, max_length=64)
    entite_cible: str = Field(min_length=1, max_length=64)
    conditions: dict[str, Any]
    consequences: dict[str, Any]
    priorite: int = Field(default=0, ge=0, le=100)
    active: bool = True


class RequeteEnregistreeLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    description: str | None = None
    entite_cible: str
    filtres: dict[str, Any]
    partagee: bool
    requete_naturelle: str | None = None
    nombre_executions: int


class RequeteEnregistreeEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=255)
    description: str | None = None
    entite_cible: str = Field(min_length=1, max_length=64)
    filtres: dict[str, Any]
    partagee: bool = False
    requete_naturelle: str | None = None
