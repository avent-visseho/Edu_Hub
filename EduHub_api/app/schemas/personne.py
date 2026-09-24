"""Schémas des apprenants, parents, enseignants et personnels."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import EmailStr, Field

from app.core.enums import Langue, Sexe, TypeHandicap
from app.models.apprenant import LienParente, StatutApprenant
from app.models.personnel import CategoriePersonnel, SituationAgent, StatutAgent
from app.schemas.base import SchemaBase, SchemaEntree

# ------------------------------------------------------------------
#  Apprenants
# ------------------------------------------------------------------


class ApprenantLecture(SchemaBase):
    id: uuid.UUID
    identifiant_educatif: str
    matricule: str | None = None
    nom: str
    prenoms: str
    nom_complet: str
    sexe: Sexe
    date_naissance: date
    lieu_naissance: str | None = None
    nationalite: str
    commune_id: uuid.UUID | None = None
    adresse: str | None = None
    telephone: str | None = None
    photo_url: str | None = None
    etablissement_actuel_id: uuid.UUID | None = None
    statut: StatutApprenant
    langue_principale: Langue
    type_handicap: TypeHandicap
    besoins_specifiques: str | None = None
    amenagements_examen: str | None = None
    tiers_temps: bool
    orphelin: bool
    situation_vulnerable: bool


class ApprenantCreation(SchemaEntree):
    nom: str = Field(min_length=1, max_length=120)
    prenoms: str = Field(min_length=1, max_length=180)
    sexe: Sexe
    date_naissance: date
    lieu_naissance: str | None = Field(default=None, max_length=180)
    nationalite: str = "Béninoise"
    numero_acte_naissance: str | None = None
    commune_id: uuid.UUID | None = None
    adresse: str | None = None
    telephone: str | None = None
    email: EmailStr | None = None
    etablissement_actuel_id: uuid.UUID | None = None
    langue_principale: Langue = Langue.FR
    type_handicap: TypeHandicap = TypeHandicap.AUCUN
    besoins_specifiques: str | None = None
    amenagements_examen: str | None = None
    tiers_temps: bool = False
    orphelin: bool = False
    situation_vulnerable: bool = False
    creer_compte: bool = Field(
        default=False, description="Crée un compte d'accès associé à l'apprenant."
    )


class ApprenantMiseAJour(SchemaEntree):
    nom: str | None = Field(default=None, max_length=120)
    prenoms: str | None = Field(default=None, max_length=180)
    lieu_naissance: str | None = None
    commune_id: uuid.UUID | None = None
    adresse: str | None = None
    telephone: str | None = None
    email: EmailStr | None = None
    photo_url: str | None = None
    etablissement_actuel_id: uuid.UUID | None = None
    statut: StatutApprenant | None = None
    langue_principale: Langue | None = None
    type_handicap: TypeHandicap | None = None
    besoins_specifiques: str | None = None
    amenagements_examen: str | None = None
    tiers_temps: bool | None = None
    orphelin: bool | None = None
    situation_vulnerable: bool | None = None
    observations: str | None = None


class LigneParcours(SchemaBase):
    """Élément du dossier scolaire d'un apprenant."""

    annee: str
    etablissement: str | None = None
    classe: str | None = None
    statut: str
    moyenne_annuelle: float | None = None
    rang: int | None = None
    decision: str | None = None


class LigneBulletinResume(SchemaBase):
    id: uuid.UUID
    numero: str
    periode: str
    classe: str
    moyenne_generale: float | None = None
    rang: int | None = None
    effectif_classe: int | None = None
    mention: str | None = None
    decision: str | None = None
    publie: bool


class LigneExamenResume(SchemaBase):
    numero_candidat: str
    examen: str
    session: str
    serie: str | None = None
    statut_dossier: str
    moyenne: float | None = None
    mention: str | None = None
    decision: str | None = None
    centre: str | None = None


class DossierApprenant(SchemaBase):
    """Vue consolidée du parcours complet d'un apprenant."""

    apprenant: ApprenantLecture
    parents: list[dict] = Field(default_factory=list)
    parcours: list[LigneParcours] = Field(default_factory=list)
    bulletins: list[LigneBulletinResume] = Field(default_factory=list)
    examens: list[LigneExamenResume] = Field(default_factory=list)
    diplomes: list[dict] = Field(default_factory=list)
    assiduite: dict | None = None
    bourses: list[dict] = Field(default_factory=list)
    projets: list[dict] = Field(default_factory=list)
    stages: list[dict] = Field(default_factory=list)
    competences: list[dict] = Field(default_factory=list)
    transport: list[dict] = Field(default_factory=list)


class ParentLecture(SchemaBase):
    id: uuid.UUID
    nom: str
    prenoms: str
    nom_complet: str
    sexe: Sexe | None = None
    profession: str | None = None
    telephone: str | None = None
    email: str | None = None
    adresse: str | None = None
    niveau_alphabetisation: str | None = None


class ParentEcriture(SchemaEntree):
    nom: str = Field(min_length=1, max_length=120)
    prenoms: str = Field(min_length=1, max_length=180)
    sexe: Sexe | None = None
    profession: str | None = None
    telephone: str | None = None
    email: EmailStr | None = None
    adresse: str | None = None
    commune_id: uuid.UUID | None = None
    niveau_alphabetisation: str | None = None


class LienParenteEcriture(SchemaEntree):
    parent_id: uuid.UUID
    lien: LienParente = LienParente.TUTEUR
    contact_principal: bool = False
    autorise_sortie: bool = True


# ------------------------------------------------------------------
#  Enseignants et personnels
# ------------------------------------------------------------------


class EnseignantLecture(SchemaBase):
    id: uuid.UUID
    matricule: str
    nom: str
    prenoms: str
    nom_complet: str
    sexe: Sexe
    date_naissance: date | None = None
    telephone: str | None = None
    email: str | None = None
    diplome_le_plus_eleve: str | None = None
    specialite: str | None = None
    grade: str | None = None
    echelon: int | None = None
    statut_agent: StatutAgent
    situation: SituationAgent
    date_prise_service: date | None = None
    etablissement_principal_id: uuid.UUID | None = None
    heures_hebdomadaires: int
    peut_surveiller: bool
    peut_corriger: bool
    peut_presider_jury: bool
    anciennete_annees: int = 0


class EnseignantCreation(SchemaEntree):
    matricule: str | None = Field(default=None, max_length=64)
    nom: str = Field(min_length=1, max_length=120)
    prenoms: str = Field(min_length=1, max_length=180)
    sexe: Sexe
    date_naissance: date | None = None
    telephone: str | None = None
    email: EmailStr | None = None
    diplome_le_plus_eleve: str | None = None
    specialite: str | None = None
    grade: str | None = None
    echelon: int | None = Field(default=None, ge=1, le=20)
    statut_agent: StatutAgent = StatutAgent.CONTRACTUEL_ETAT
    date_recrutement: date | None = None
    date_prise_service: date | None = None
    etablissement_principal_id: uuid.UUID | None = None
    heures_hebdomadaires: int = Field(default=18, ge=0, le=40)
    matieres: list[uuid.UUID] = Field(default_factory=list)
    creer_compte: bool = False


class EnseignantMiseAJour(SchemaEntree):
    nom: str | None = None
    prenoms: str | None = None
    telephone: str | None = None
    email: EmailStr | None = None
    diplome_le_plus_eleve: str | None = None
    specialite: str | None = None
    grade: str | None = None
    echelon: int | None = Field(default=None, ge=1, le=20)
    statut_agent: StatutAgent | None = None
    situation: SituationAgent | None = None
    etablissement_principal_id: uuid.UUID | None = None
    heures_hebdomadaires: int | None = Field(default=None, ge=0, le=40)
    peut_surveiller: bool | None = None
    peut_corriger: bool | None = None
    peut_presider_jury: bool | None = None
    observations: str | None = None


class PersonnelLecture(SchemaBase):
    id: uuid.UUID
    matricule: str
    nom: str
    prenoms: str
    nom_complet: str
    sexe: Sexe
    categorie: CategoriePersonnel
    fonction: str
    statut_agent: StatutAgent
    situation: SituationAgent
    etablissement_id: uuid.UUID | None = None
    telephone: str | None = None
    email: str | None = None
    date_prise_service: date | None = None
    peut_saisir_notes: bool


class PersonnelEcriture(SchemaEntree):
    matricule: str | None = None
    nom: str = Field(min_length=1, max_length=120)
    prenoms: str = Field(min_length=1, max_length=180)
    sexe: Sexe
    categorie: CategoriePersonnel = CategoriePersonnel.ADMINISTRATIF
    fonction: str = Field(min_length=1, max_length=180)
    statut_agent: StatutAgent = StatutAgent.CONTRACTUEL_LOCAL
    etablissement_id: uuid.UUID | None = None
    structure_id: uuid.UUID | None = None
    telephone: str | None = None
    email: EmailStr | None = None
    date_prise_service: date | None = None
    peut_saisir_notes: bool = False
