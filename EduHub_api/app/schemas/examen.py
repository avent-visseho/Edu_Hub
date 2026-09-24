"""Schémas des examens, concours, candidatures, résultats et diplômes."""

from __future__ import annotations

import uuid
from datetime import date, time

from pydantic import EmailStr, Field

from app.core.enums import Sexe, StatutPaiement, TypeHandicap
from app.models.examen import (
    DecisionExamen,
    MotifRejetPiece,
    NatureExamen,
    RoleSurveillance,
    StatutContentieux,
    StatutDossier,
    StatutNoteExamen,
    StatutPiece,
    StatutSession,
    TypeCandidature,
    TypeContentieux,
    TypeSession,
)
from app.schemas.base import SchemaBase, SchemaEntree

# ------------------------------------------------------------------
#  Examens et sessions
# ------------------------------------------------------------------


class ExamenLecture(SchemaBase):
    id: uuid.UUID
    code: str
    nom: str
    sigle: str | None = None
    nature: NatureExamen
    type_examen_id: uuid.UUID | None = None
    ministere_id: uuid.UUID | None = None
    direction_responsable_id: uuid.UUID | None = None
    conditions_admission: str | None = None
    frais_officiel: float
    frais_candidat_libre: float
    moyenne_admission: float
    note_eliminatoire: float | None = None
    places_offertes: int | None = None
    actif: bool


class ExamenEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    nom: str = Field(min_length=1, max_length=255)
    sigle: str | None = Field(default=None, max_length=32)
    nature: NatureExamen = NatureExamen.EXAMEN
    type_examen_id: uuid.UUID | None = None
    ministere_id: uuid.UUID | None = None
    direction_responsable_id: uuid.UUID | None = None
    niveau_requis_id: uuid.UUID | None = None
    diplome_delivre_id: uuid.UUID | None = None
    conditions_admission: str | None = None
    reglement: str | None = None
    frais_officiel: float = Field(default=0.0, ge=0)
    frais_candidat_libre: float = Field(default=0.0, ge=0)
    age_minimum: int | None = Field(default=None, ge=3, le=99)
    age_maximum: int | None = Field(default=None, ge=3, le=99)
    moyenne_admission: float = Field(default=10.0, ge=0, le=20)
    note_eliminatoire: float | None = Field(default=None, ge=0, le=20)
    places_offertes: int | None = Field(default=None, ge=0)


class SessionLecture(SchemaBase):
    id: uuid.UUID
    examen_id: uuid.UUID
    code: str
    libelle: str
    type_session: TypeSession
    annee: int
    statut: StatutSession
    inscriptions_debut: date | None = None
    inscriptions_fin: date | None = None
    date_debut: date | None = None
    date_fin: date | None = None
    date_publication_resultats: date | None = None
    nombre_inscrits: int
    nombre_presents: int
    nombre_absents: int
    nombre_admis: int
    taux_reussite: float | None = None
    moyenne_generale: float | None = None


class SessionCreation(SchemaEntree):
    examen_id: uuid.UUID
    annee_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=255)
    type_session: TypeSession = TypeSession.NORMALE
    annee: int = Field(ge=1990, le=2100)
    inscriptions_debut: date | None = None
    inscriptions_fin: date | None = None
    date_debut: date | None = None
    date_fin: date | None = None
    series: list[uuid.UUID] = Field(default_factory=list)


class SessionMiseAJour(SchemaEntree):
    libelle: str | None = None
    statut: StatutSession | None = None
    inscriptions_debut: date | None = None
    inscriptions_fin: date | None = None
    date_debut: date | None = None
    date_fin: date | None = None
    date_publication_resultats: date | None = None
    date_limite_contentieux: date | None = None
    observations: str | None = None


class EpreuveLecture(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    serie_id: uuid.UUID | None = None
    matiere_id: uuid.UUID
    code: str
    libelle: str
    date_epreuve: date | None = None
    heure_debut: time | None = None
    duree_minutes: int
    bareme: float
    coefficient: float
    note_eliminatoire: float | None = None
    obligatoire: bool
    facultative: bool
    sujet_url: str | None = None


class EpreuveEcriture(SchemaEntree):
    session_id: uuid.UUID
    serie_id: uuid.UUID | None = None
    matiere_id: uuid.UUID
    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=255)
    date_epreuve: date | None = None
    heure_debut: time | None = None
    duree_minutes: int = Field(default=120, ge=15, le=480)
    bareme: float = Field(default=20.0, gt=0, le=100)
    coefficient: float = Field(default=1.0, gt=0, le=20)
    note_eliminatoire: float | None = Field(default=None, ge=0, le=20)
    obligatoire: bool = True
    facultative: bool = False
    instructions: str | None = None


# ------------------------------------------------------------------
#  Candidatures
# ------------------------------------------------------------------


class CandidatLecture(SchemaBase):
    id: uuid.UUID
    numero_candidat: str
    numero_table: str | None = None
    session_id: uuid.UUID
    serie_id: uuid.UUID | None = None
    apprenant_id: uuid.UUID | None = None
    etablissement_id: uuid.UUID | None = None
    departement_id: uuid.UUID | None = None
    nom: str
    prenoms: str
    nom_complet: str
    sexe: Sexe
    date_naissance: date
    lieu_naissance: str | None = None
    telephone: str | None = None
    type_candidature: TypeCandidature
    statut_dossier: StatutDossier
    montant_frais: float
    statut_paiement: StatutPaiement
    centre_id: uuid.UUID | None = None
    salle_composition_id: uuid.UUID | None = None
    numero_place: int | None = None
    type_handicap: TypeHandicap
    tiers_temps: bool
    motif_rejet: str | None = None


class CandidatCreation(SchemaEntree):
    session_id: uuid.UUID
    serie_id: uuid.UUID | None = None
    apprenant_id: uuid.UUID | None = None
    etablissement_id: uuid.UUID | None = None
    departement_id: uuid.UUID | None = None
    nom: str = Field(min_length=1, max_length=120)
    prenoms: str = Field(min_length=1, max_length=180)
    sexe: Sexe
    date_naissance: date
    lieu_naissance: str | None = None
    nationalite: str = "Béninoise"
    telephone: str | None = None
    email: EmailStr | None = None
    type_candidature: TypeCandidature = TypeCandidature.OFFICIEL
    type_handicap: TypeHandicap = TypeHandicap.AUCUN
    amenagements_demandes: str | None = None
    tiers_temps: bool = False


class CandidatMiseAJour(SchemaEntree):
    serie_id: uuid.UUID | None = None
    telephone: str | None = None
    email: EmailStr | None = None
    lieu_naissance: str | None = None
    photo_url: str | None = None
    type_handicap: TypeHandicap | None = None
    amenagements_demandes: str | None = None
    tiers_temps: bool | None = None
    observations: str | None = None


class InscriptionMasse(SchemaEntree):
    """Inscription d'une classe entière à une session d'examen."""

    session_id: uuid.UUID
    classe_id: uuid.UUID
    serie_id: uuid.UUID | None = None


class DocumentCandidatLecture(SchemaBase):
    id: uuid.UUID
    candidat_id: uuid.UUID
    type_document_id: uuid.UUID | None = None
    nom_fichier: str
    type_mime: str | None = None
    taille_octets: int
    version: int
    statut: StatutPiece
    motif_rejet: MotifRejetPiece | None = None
    commentaire: str | None = None


class ValidationPiece(SchemaEntree):
    statut: StatutPiece
    motif_rejet: MotifRejetPiece | None = None
    commentaire: str | None = Field(default=None, max_length=1000)


# ------------------------------------------------------------------
#  Centres et répartition
# ------------------------------------------------------------------


class CentreLecture(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    etablissement_id: uuid.UUID | None = None
    departement_id: uuid.UUID | None = None
    code: str
    nom: str
    adresse: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    capacite: int
    nombre_candidats: int
    nombre_salles: int
    chef_centre_nom: str | None = None
    chef_centre_telephone: str | None = None
    accessible_handicap: bool
    actif: bool


class CentreEcriture(SchemaEntree):
    session_id: uuid.UUID
    etablissement_id: uuid.UUID | None = None
    departement_id: uuid.UUID | None = None
    commune_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=64)
    nom: str = Field(min_length=1, max_length=255)
    adresse: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    chef_centre_id: uuid.UUID | None = None
    chef_centre_nom: str | None = None
    chef_centre_telephone: str | None = None
    accessible_handicap: bool = False


class SalleCompositionLecture(SchemaBase):
    id: uuid.UUID
    centre_id: uuid.UUID
    salle_id: uuid.UUID | None = None
    code: str
    nom: str
    batiment: str | None = None
    capacite: int
    nombre_candidats: int
    place_debut: int | None = None
    place_fin: int | None = None
    accessible_handicap: bool
    salle_amenagee: bool


class SalleCompositionEcriture(SchemaEntree):
    centre_id: uuid.UUID
    salle_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=64)
    nom: str = Field(min_length=1, max_length=180)
    batiment: str | None = None
    capacite: int = Field(default=30, ge=1, le=500)
    accessible_handicap: bool = False
    salle_amenagee: bool = False


class RepartitionDemande(SchemaEntree):
    """Paramètres de la répartition automatique des candidats."""

    par_departement: bool = True
    prioriser_amenagements: bool = True
    melanger_etablissements: bool = Field(
        default=True,
        description="Évite de regrouper les candidats d'un même établissement dans une salle.",
    )


class RepartitionResultat(SchemaBase):
    candidats_affectes: int
    candidats_non_affectes: int
    centres_utilises: int
    salles_utilisees: int
    details: list[dict] = Field(default_factory=list)


class AffectationSurveillanceLecture(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    centre_id: uuid.UUID
    salle_composition_id: uuid.UUID | None = None
    enseignant_id: uuid.UUID | None = None
    role: RoleSurveillance
    nom_complet: str
    telephone: str | None = None
    indemnite: float
    present: bool | None = None


class AffectationSurveillanceEcriture(SchemaEntree):
    session_id: uuid.UUID
    centre_id: uuid.UUID
    salle_composition_id: uuid.UUID | None = None
    enseignant_id: uuid.UUID | None = None
    role: RoleSurveillance
    nom_complet: str = Field(min_length=1, max_length=180)
    telephone: str | None = None
    indemnite: float = Field(default=0.0, ge=0)


class CorrecteurLecture(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    epreuve_id: uuid.UUID | None = None
    enseignant_id: uuid.UUID | None = None
    matiere_id: uuid.UUID | None = None
    code_correcteur: str
    nom_complet: str
    est_chef_correcteur: bool
    copies_attribuees: int
    copies_corrigees: int
    indemnite: float
    actif: bool


class CopieLecture(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    epreuve_id: uuid.UUID
    candidat_id: uuid.UUID
    correcteur_id: uuid.UUID | None = None
    code_anonymat: str
    lot: str | None = None
    note_correcteur: float | None = None
    note_second_correcteur: float | None = None
    note_finale: float | None = None
    double_correction: bool
    ecart_significatif: bool
    corrigee: bool
    validee: bool


class NoteExamenSaisie(SchemaEntree):
    candidat_id: uuid.UUID
    valeur: float | None = Field(default=None, ge=0, le=100)
    statut: StatutNoteExamen = StatutNoteExamen.SAISIE


class SaisieNotesExamen(SchemaEntree):
    epreuve_id: uuid.UUID
    notes: list[NoteExamenSaisie] = Field(min_length=1)


class NoteExamenLecture(SchemaBase):
    id: uuid.UUID
    candidat_id: uuid.UUID
    epreuve_id: uuid.UUID
    valeur: float | None = None
    valeur_sur_20: float | None = None
    coefficient: float
    points: float | None = None
    statut: StatutNoteExamen
    validee: bool
    # La copie est anonymée, la note ne l'est plus : elle est rattachée au
    # candidat une fois la correction terminée.
    numero_candidat: str | None = None
    nom_complet: str | None = None


# ------------------------------------------------------------------
#  Jurys, résultats, contentieux
# ------------------------------------------------------------------


class JuryLecture(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    centre_id: uuid.UUID | None = None
    code: str
    libelle: str
    president_nom: str | None = None
    date_deliberation: date | None = None
    lieu: str | None = None
    nombre_candidats: int
    nombre_admis: int
    cloture: bool


class JuryEcriture(SchemaEntree):
    session_id: uuid.UUID
    centre_id: uuid.UUID | None = None
    serie_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=255)
    president_nom: str | None = None
    president_enseignant_id: uuid.UUID | None = None
    date_deliberation: date | None = None
    lieu: str | None = None


class MembreJuryEcriture(SchemaEntree):
    enseignant_id: uuid.UUID | None = None
    nom_complet: str = Field(min_length=1, max_length=180)
    qualite: str | None = None
    est_president: bool = False
    est_rapporteur: bool = False
    indemnite: float = Field(default=0.0, ge=0)


class DeliberationDemande(SchemaEntree):
    """Paramètres de la délibération d'une session."""

    moyenne_admission: float | None = Field(default=None, ge=0, le=20)
    repechage_maximum: float = Field(
        default=0.5, ge=0, le=2, description="Points de jury accordables au maximum."
    )
    appliquer_note_eliminatoire: bool = True
    publier: bool = False


class ResultatLecture(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    candidat_id: uuid.UUID
    jury_id: uuid.UUID | None = None
    serie_id: uuid.UUID | None = None
    etablissement_id: uuid.UUID | None = None
    departement_id: uuid.UUID | None = None
    total_points: float | None = None
    total_coefficients: float | None = None
    moyenne: float | None = None
    mention: str | None = None
    decision: DecisionExamen
    rang_national: int | None = None
    rang_departemental: int | None = None
    rang_etablissement: int | None = None
    repeche: bool
    publie: bool
    code_verification: str | None = None


class ResultatPublic(SchemaBase):
    """Résultat consultable publiquement par numéro de table."""

    numero_candidat: str
    numero_table: str | None = None
    nom_complet: str
    examen: str
    session: str
    serie: str | None = None
    centre: str | None = None
    moyenne: float | None = None
    mention: str | None = None
    decision: DecisionExamen
    rang_national: int | None = None
    code_verification: str | None = None


class ContentieuxLecture(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    candidat_id: uuid.UUID
    epreuve_id: uuid.UUID | None = None
    numero: str
    type_contentieux: TypeContentieux
    objet: str
    expose: str
    statut: StatutContentieux
    date_depot: date
    date_decision: date | None = None
    conclusion: str | None = None
    note_avant: float | None = None
    note_apres: float | None = None
    decision_revisee: DecisionExamen | None = None


class ContentieuxCreation(SchemaEntree):
    session_id: uuid.UUID
    candidat_id: uuid.UUID
    epreuve_id: uuid.UUID | None = None
    type_contentieux: TypeContentieux
    objet: str = Field(min_length=1, max_length=500)
    expose: str = Field(min_length=10)


class ContentieuxInstruction(SchemaEntree):
    statut: StatutContentieux
    conclusion: str | None = None
    note_apres: float | None = Field(default=None, ge=0, le=20)
    decision_revisee: DecisionExamen | None = None
    instructeur_nom: str | None = None


class DiplomeLecture(SchemaBase):
    id: uuid.UUID
    numero: str
    code_verification: str
    titulaire_nom: str
    titulaire_date_naissance: date | None = None
    titulaire_lieu_naissance: str | None = None
    intitule: str
    serie_libelle: str | None = None
    session_libelle: str | None = None
    annee: int
    moyenne: float | None = None
    mention: str | None = None
    statut: str
    date_delivrance: date


class VerificationDiplomeReponse(SchemaBase):
    """Réponse au contrôle d'authenticité d'un document."""

    valide: bool
    message: str
    type_document: str | None = None
    numero: str | None = None
    titulaire: str | None = None
    intitule: str | None = None
    session: str | None = None
    annee: int | None = None
    mention: str | None = None
    date_delivrance: date | None = None


class ArchiveEpreuveLecture(SchemaBase):
    id: uuid.UUID
    reference: str
    titre: str
    examen_id: uuid.UUID | None = None
    matiere_id: uuid.UUID | None = None
    serie_id: uuid.UUID | None = None
    filiere_id: uuid.UUID | None = None
    niveau_id: uuid.UUID | None = None
    nature: NatureExamen
    annee: int
    duree_minutes: int | None = None
    coefficient: float | None = None
    sujet_url: str | None = None
    corrige_url: str | None = None
    mots_cles: str | None = None
    nombre_telechargements: int
    public: bool


class BudgetLecture(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    code: str
    libelle: str
    montant_prevu: float
    montant_engage: float
    montant_paye: float
    recettes_inscriptions: float
    devise: str
    valide: bool
    exercice: int | None = None


class TableauBordSession(SchemaBase):
    """Vue de pilotage d'une session d'examen."""

    session: SessionLecture
    dossiers: dict[str, int] = Field(default_factory=dict)
    centres: int = 0
    salles: int = 0
    surveillants: int = 0
    correcteurs: int = 0
    copies_corrigees: int = 0
    copies_totales: int = 0
    jurys: int = 0
    contentieux: dict[str, int] = Field(default_factory=dict)
    budget: dict[str, float] = Field(default_factory=dict)
    resultats_par_departement: list[dict] = Field(default_factory=list)
