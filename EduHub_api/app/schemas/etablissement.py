"""Schémas des établissements, infrastructures et structures institutionnelles."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import Field

from app.core.enums import NiveauScope
from app.models.etablissement import EtatEquipement, NiveauAccessibilite, TypeEquipement
from app.models.organisation import CategorieStructure
from app.schemas.base import SchemaBase, SchemaEntree


class StructureLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    sigle: str | None = None
    categorie: CategorieStructure
    niveau_scope: NiveauScope
    parent_id: uuid.UUID | None = None
    departement_id: uuid.UUID | None = None
    responsable_nom: str | None = None
    telephone: str | None = None
    email: str | None = None
    adresse: str | None = None
    missions: str | None = None
    actif: bool = True


class StructureEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=255)
    sigle: str | None = Field(default=None, max_length=40)
    categorie: CategorieStructure
    niveau_scope: NiveauScope = NiveauScope.MINISTERE
    parent_id: uuid.UUID | None = None
    departement_id: uuid.UUID | None = None
    responsable_nom: str | None = None
    telephone: str | None = None
    email: str | None = None
    adresse: str | None = None
    missions: str | None = None
    actif: bool = True


class StructureNoeud(StructureLecture):
    """Nœud de l'arbre institutionnel, avec ses enfants."""

    enfants: list[StructureNoeud] = Field(default_factory=list)


class EtablissementLecture(SchemaBase):
    id: uuid.UUID
    code: str
    nom: str
    sigle: str | None = None
    type_etablissement_id: uuid.UUID | None = None
    statut_etablissement_id: uuid.UUID | None = None
    ministere_id: uuid.UUID | None = None
    direction_departementale_id: uuid.UUID | None = None
    commune_id: uuid.UUID | None = None
    adresse: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    zone_rurale: bool = False
    directeur_nom: str | None = None
    telephone: str | None = None
    email: str | None = None
    annee_creation: int | None = None
    capacite_accueil: int = 0
    effectif_actuel: int = 0
    est_centre_examen: bool = False
    internat: bool = False
    cantine: bool = False
    electricite: bool = True
    eau_potable: bool = True
    connexion_internet: bool = False
    accessibilite: NiveauAccessibilite
    actif: bool = True


class EtablissementDetail(EtablissementLecture):
    """Établissement enrichi de ses libellés et de ses compteurs."""

    type_libelle: str | None = None
    statut_libelle: str | None = None
    commune_libelle: str | None = None
    departement_libelle: str | None = None
    nombre_salles: int = 0
    nombre_batiments: int = 0
    nombre_classes: int = 0
    nombre_enseignants: int = 0


class EtablissementCreation(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    nom: str = Field(min_length=1, max_length=255)
    sigle: str | None = Field(default=None, max_length=40)
    type_etablissement_id: uuid.UUID | None = None
    statut_etablissement_id: uuid.UUID | None = None
    ministere_id: uuid.UUID | None = None
    direction_departementale_id: uuid.UUID | None = None
    commune_id: uuid.UUID | None = None
    arrondissement_id: uuid.UUID | None = None
    adresse: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    zone_rurale: bool = False
    directeur_nom: str | None = None
    directeur_telephone: str | None = None
    telephone: str | None = None
    email: str | None = None
    annee_creation: int | None = Field(default=None, ge=1800, le=2100)
    capacite_accueil: int = Field(default=0, ge=0)
    est_centre_examen: bool = False
    internat: bool = False
    cantine: bool = False
    electricite: bool = True
    eau_potable: bool = True
    connexion_internet: bool = False
    accessibilite: NiveauAccessibilite = NiveauAccessibilite.NON_ACCESSIBLE


class EtablissementMiseAJour(SchemaEntree):
    nom: str | None = Field(default=None, max_length=255)
    sigle: str | None = None
    adresse: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    directeur_nom: str | None = None
    directeur_telephone: str | None = None
    telephone: str | None = None
    email: str | None = None
    capacite_accueil: int | None = Field(default=None, ge=0)
    est_centre_examen: bool | None = None
    internat: bool | None = None
    cantine: bool | None = None
    electricite: bool | None = None
    eau_potable: bool | None = None
    connexion_internet: bool | None = None
    accessibilite: NiveauAccessibilite | None = None
    actif: bool | None = None


class BatimentLecture(SchemaBase):
    id: uuid.UUID
    etablissement_id: uuid.UUID
    code: str
    nom: str
    nombre_etages: int
    annee_construction: int | None = None
    etat: EtatEquipement
    accessibilite: NiveauAccessibilite


class BatimentEcriture(SchemaEntree):
    etablissement_id: uuid.UUID
    code: str = Field(min_length=1, max_length=64)
    nom: str = Field(min_length=1, max_length=180)
    nombre_etages: int = Field(default=1, ge=1, le=20)
    annee_construction: int | None = Field(default=None, ge=1800, le=2100)
    etat: EtatEquipement = EtatEquipement.BON
    accessibilite: NiveauAccessibilite = NiveauAccessibilite.NON_ACCESSIBLE


class SalleLecture(SchemaBase):
    id: uuid.UUID
    etablissement_id: uuid.UUID
    batiment_id: uuid.UUID | None = None
    type_salle_id: uuid.UUID | None = None
    code: str
    nom: str
    etage: int
    capacite: int
    capacite_examen: int
    superficie_m2: float | None = None
    disponible: bool
    accessibilite: NiveauAccessibilite
    equipement_resume: str | None = None


class SalleEcriture(SchemaEntree):
    etablissement_id: uuid.UUID
    batiment_id: uuid.UUID | None = None
    type_salle_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=64)
    nom: str = Field(min_length=1, max_length=180)
    etage: int = Field(default=0, ge=0, le=20)
    capacite: int = Field(default=0, ge=0, le=1000)
    capacite_examen: int = Field(default=0, ge=0, le=1000)
    superficie_m2: float | None = Field(default=None, ge=0)
    disponible: bool = True
    accessibilite: NiveauAccessibilite = NiveauAccessibilite.NON_ACCESSIBLE
    equipement_resume: str | None = None


class EquipementLecture(SchemaBase):
    id: uuid.UUID
    etablissement_id: uuid.UUID
    salle_id: uuid.UUID | None = None
    reference: str
    designation: str
    type_equipement: TypeEquipement
    quantite: int
    etat: EtatEquipement
    date_acquisition: date | None = None
    valeur_acquisition: float | None = None
    adapte_handicap: bool = False


class EquipementEcriture(SchemaEntree):
    etablissement_id: uuid.UUID
    salle_id: uuid.UUID | None = None
    reference: str = Field(min_length=1, max_length=80)
    designation: str = Field(min_length=1, max_length=255)
    type_equipement: TypeEquipement = TypeEquipement.AUTRE
    quantite: int = Field(default=1, ge=1)
    etat: EtatEquipement = EtatEquipement.BON
    date_acquisition: date | None = None
    valeur_acquisition: float | None = Field(default=None, ge=0)
    adapte_handicap: bool = False
