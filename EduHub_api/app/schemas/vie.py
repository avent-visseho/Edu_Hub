"""Schémas de la vie étudiante, de l'apprentissage et de l'insertion."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import Field

from app.core.enums import Langue, StatutPaiement
from app.models.apprentissage import StatutPublication, TypeRessource
from app.models.orientation import StatutVoeu
from app.models.projet import RoleMembreProjet, StatutCandidature, StatutProjet, TypeContrat
from app.models.vie_etudiante import (
    StatutCandidatureBourse,
    StatutTrajet,
    StatutVehicule,
    TypeAideSociale,
    TypeVehicule,
)
from app.schemas.base import SchemaBase, SchemaEntree

# ------------------------------------------------------------------
#  Orientation
# ------------------------------------------------------------------


class FormationLecture(SchemaBase):
    id: uuid.UUID
    code: str
    intitule: str
    etablissement_id: uuid.UUID | None = None
    filiere_id: uuid.UUID | None = None
    diplome_id: uuid.UUID | None = None
    niveau_entree: str | None = None
    duree_annees: int
    places_offertes: int
    places_pourvues: int
    moyenne_minimale: float | None = None
    series_admises: str | None = None
    debouches: str | None = None
    frais_annuels: float
    ouverte: bool


class FormationEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    intitule: str = Field(min_length=1, max_length=255)
    etablissement_id: uuid.UUID | None = None
    filiere_id: uuid.UUID | None = None
    diplome_id: uuid.UUID | None = None
    type_formation_id: uuid.UUID | None = None
    niveau_entree: str | None = None
    duree_annees: int = Field(default=3, ge=1, le=10)
    places_offertes: int = Field(default=0, ge=0)
    moyenne_minimale: float | None = Field(default=None, ge=0, le=20)
    series_admises: str | None = None
    conditions: str | None = None
    debouches: str | None = None
    frais_annuels: float = Field(default=0.0, ge=0)
    ouverte: bool = True


class VoeuEcriture(SchemaEntree):
    formation_id: uuid.UUID
    rang: int = Field(ge=1, le=20)


class DossierOrientationCreation(SchemaEntree):
    campagne_id: uuid.UUID
    apprenant_id: uuid.UUID
    serie_id: uuid.UUID | None = None
    moyenne_bac: float | None = Field(default=None, ge=0, le=20)
    voeux: list[VoeuEcriture] = Field(default_factory=list)


class DossierOrientationLecture(SchemaBase):
    id: uuid.UUID
    campagne_id: uuid.UUID
    apprenant_id: uuid.UUID
    moyenne_bac: float | None = None
    mention: str | None = None
    profil_detecte: str | None = None
    formation_affectee_id: uuid.UUID | None = None
    date_affectation: date | None = None
    statut: StatutVoeu


# ------------------------------------------------------------------
#  Bourses et aides
# ------------------------------------------------------------------


class ProgrammeBourseLecture(SchemaBase):
    id: uuid.UUID
    code: str
    intitule: str
    type_bourse_id: uuid.UUID | None = None
    description: str | None = None
    criteres_eligibilite: str | None = None
    montant_mensuel: float
    duree_mois: int
    places: int
    places_attribuees: int
    moyenne_minimale: float | None = None
    date_ouverture: date
    date_cloture: date
    ouvert: bool
    reserve_handicap: bool


class ProgrammeBourseEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    intitule: str = Field(min_length=1, max_length=255)
    type_bourse_id: uuid.UUID | None = None
    structure_id: uuid.UUID | None = None
    annee_id: uuid.UUID | None = None
    description: str | None = None
    criteres_eligibilite: str | None = None
    montant_mensuel: float = Field(default=0.0, ge=0)
    duree_mois: int = Field(default=12, ge=1, le=60)
    places: int = Field(default=0, ge=0)
    moyenne_minimale: float | None = Field(default=None, ge=0, le=20)
    date_ouverture: date
    date_cloture: date
    ouvert: bool = True
    reserve_handicap: bool = False


class CandidatureBourseLecture(SchemaBase):
    id: uuid.UUID
    numero: str
    programme_id: uuid.UUID
    apprenant_id: uuid.UUID
    statut: StatutCandidatureBourse
    moyenne_reference: float | None = None
    score_evaluation: float | None = None
    rang: int | None = None
    montant_attribue: float
    date_soumission: date | None = None
    date_decision: date | None = None
    motif_rejet: str | None = None


class CandidatureBourseCreation(SchemaEntree):
    programme_id: uuid.UUID
    apprenant_id: uuid.UUID
    moyenne_reference: float | None = Field(default=None, ge=0, le=20)
    revenu_familial_declare: float | None = Field(default=None, ge=0)
    motivation: str | None = None


class AideSocialeLecture(SchemaBase):
    id: uuid.UUID
    numero: str
    apprenant_id: uuid.UUID
    type_aide: TypeAideSociale
    libelle: str
    montant: float
    en_nature: bool
    date_demande: date
    date_attribution: date | None = None
    statut: StatutCandidatureBourse


# ------------------------------------------------------------------
#  Transport
# ------------------------------------------------------------------


class LigneTransportLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    etablissement_id: uuid.UUID | None = None
    origine: str
    destination: str
    distance_km: float | None = None
    duree_minutes: int | None = None
    tarif: float
    tarif_abonnement: float
    couleur: str | None = None
    active: bool


class LigneTransportEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=32)
    libelle: str = Field(min_length=1, max_length=255)
    etablissement_id: uuid.UUID | None = None
    commune_id: uuid.UUID | None = None
    origine: str = Field(min_length=1, max_length=180)
    destination: str = Field(min_length=1, max_length=180)
    distance_km: float | None = Field(default=None, ge=0)
    duree_minutes: int | None = Field(default=None, ge=0)
    tarif: float = Field(default=0.0, ge=0)
    tarif_abonnement: float = Field(default=0.0, ge=0)
    couleur: str | None = None
    active: bool = True


class ArretLecture(SchemaBase):
    id: uuid.UUID
    ligne_id: uuid.UUID
    code: str
    nom: str
    ordre: int
    latitude: float | None = None
    longitude: float | None = None
    heure_passage_aller: time | None = None
    heure_passage_retour: time | None = None
    abri: bool
    accessible_handicap: bool


class VehiculeLecture(SchemaBase):
    id: uuid.UUID
    immatriculation: str
    code: str
    type_vehicule: TypeVehicule
    marque: str | None = None
    modele: str | None = None
    places: int
    places_pmr: int
    statut: StatutVehicule
    climatise: bool


class TrajetTempsReel(SchemaBase):
    """Suivi simulé d'un trajet, tel qu'affiché à l'apprenant."""

    id: uuid.UUID
    ligne: str
    ligne_code: str
    vehicule: str | None = None
    conducteur: str | None = None
    sens: str
    statut: StatutTrajet
    heure_depart_prevue: time
    prochain_arret: str | None = None
    minutes_avant_prochain_arret: int | None = None
    places_occupees: int
    places_disponibles: int | None = None
    retard_minutes: int
    latitude: float | None = None
    longitude: float | None = None


class AbonnementLecture(SchemaBase):
    id: uuid.UUID
    apprenant_id: uuid.UUID
    ligne_id: uuid.UUID
    numero_carte: str
    date_debut: date
    date_fin: date
    montant: float
    statut_paiement: StatutPaiement
    actif: bool


class AbonnementCreation(SchemaEntree):
    apprenant_id: uuid.UUID
    ligne_id: uuid.UUID
    arret_montee_id: uuid.UUID | None = None
    date_debut: date
    date_fin: date


# ------------------------------------------------------------------
#  Logement, restauration, santé, bibliothèque
# ------------------------------------------------------------------


class ResidenceLecture(SchemaBase):
    id: uuid.UUID
    code: str
    nom: str
    etablissement_id: uuid.UUID | None = None
    adresse: str | None = None
    capacite: int
    places_occupees: int
    tarif_mensuel: float
    mixte: bool
    accessible_handicap: bool


class ChambreLecture(SchemaBase):
    id: uuid.UUID
    residence_id: uuid.UUID
    numero: str
    batiment: str | None = None
    etage: int
    nombre_lits: int
    lits_occupes: int
    tarif_mensuel: float
    disponible: bool
    accessible_handicap: bool


class DemandeLogement(SchemaEntree):
    apprenant_id: uuid.UUID
    chambre_id: uuid.UUID
    date_debut: date
    date_fin: date | None = None


class MenuLecture(SchemaBase):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    date_service: date
    service: str
    entree: str | None = None
    plat_principal: str
    accompagnement: str | None = None
    dessert: str | None = None
    boisson: str | None = None
    calories: int | None = None
    vegetarien: bool


class LivreLecture(SchemaBase):
    id: uuid.UUID
    isbn: str | None = None
    titre: str
    auteur: str
    editeur: str | None = None
    annee_publication: int | None = None
    categorie: str | None = None
    langue: str
    nombre_pages: int | None = None
    resume: str | None = None
    format_accessible: bool
    audio_disponible: bool
    braille_disponible: bool


class LivreEcriture(SchemaEntree):
    isbn: str | None = None
    titre: str = Field(min_length=1, max_length=500)
    auteur: str = Field(min_length=1, max_length=255)
    editeur: str | None = None
    annee_publication: int | None = Field(default=None, ge=1400, le=2100)
    categorie: str | None = None
    langue: str = "Français"
    nombre_pages: int | None = Field(default=None, ge=1)
    resume: str | None = None
    format_accessible: bool = False
    audio_disponible: bool = False
    braille_disponible: bool = False


class PretLecture(SchemaBase):
    id: uuid.UUID
    exemplaire_id: uuid.UUID
    apprenant_id: uuid.UUID | None = None
    date_pret: date
    date_retour_prevue: date
    date_retour_effective: date | None = None
    jours_retard: int
    penalite: float
    rendu: bool


class PretCreation(SchemaEntree):
    exemplaire_id: uuid.UUID
    apprenant_id: uuid.UUID | None = None
    enseignant_id: uuid.UUID | None = None
    duree_jours: int = Field(default=14, ge=1, le=90)


# ------------------------------------------------------------------
#  Apprentissage
# ------------------------------------------------------------------


class CoursLecture(SchemaBase):
    id: uuid.UUID
    code: str
    titre: str
    description: str | None = None
    matiere_id: uuid.UUID | None = None
    niveau_id: uuid.UUID | None = None
    enseignant_id: uuid.UUID | None = None
    langue: Langue
    duree_heures: int
    statut: StatutPublication
    disponible_hors_ligne: bool
    transcription_disponible: bool
    sous_titres_disponibles: bool
    version_audio: bool
    nombre_inscrits: int
    note_moyenne: float | None = None


class CoursEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    titre: str = Field(min_length=1, max_length=255)
    description: str | None = None
    matiere_id: uuid.UUID | None = None
    niveau_id: uuid.UUID | None = None
    enseignant_id: uuid.UUID | None = None
    langue: Langue = Langue.FR
    duree_heures: int = Field(default=0, ge=0)
    disponible_hors_ligne: bool = True
    transcription_disponible: bool = False
    sous_titres_disponibles: bool = False
    version_audio: bool = False


class RessourceLecture(SchemaBase):
    id: uuid.UUID
    code: str
    titre: str
    description: str | None = None
    type_ressource: TypeRessource
    matiere_id: uuid.UUID | None = None
    niveau_id: uuid.UUID | None = None
    fichier_url: str | None = None
    taille_ko: int
    langue: Langue
    statut: StatutPublication
    licence: str | None = None
    mots_cles: str | None = None
    nombre_vues: int
    nombre_telechargements: int
    poids_leger: bool


class ProgressionLecture(SchemaBase):
    apprenant_id: uuid.UUID
    cours_id: uuid.UUID
    lecons_terminees: int
    lecons_totales: int
    pourcentage: float
    temps_passe_minutes: int
    termine: bool
    note_finale: float | None = None
    certificat_delivre: bool


# ------------------------------------------------------------------
#  Projets, stages et emploi
# ------------------------------------------------------------------


class ProjetLecture(SchemaBase):
    id: uuid.UUID
    code: str
    titre: str
    resume: str | None = None
    domaine: str | None = None
    etablissement_id: uuid.UUID | None = None
    statut: StatutProjet
    date_debut: date | None = None
    date_fin_prevue: date | None = None
    budget_prevu: float
    budget_obtenu: float
    competences_recherchees: str | None = None
    places_disponibles: int
    avancement_pourcentage: float
    ouvert_candidatures: bool


class ProjetEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    titre: str = Field(min_length=1, max_length=255)
    resume: str | None = None
    description: str | None = None
    domaine: str | None = None
    objectifs: str | None = None
    impact_attendu: str | None = None
    etablissement_id: uuid.UUID | None = None
    structure_id: uuid.UUID | None = None
    date_debut: date | None = None
    date_fin_prevue: date | None = None
    budget_prevu: float = Field(default=0.0, ge=0)
    competences_recherchees: str | None = None
    places_disponibles: int = Field(default=0, ge=0)
    ouvert_candidatures: bool = True


class AdhesionProjet(SchemaEntree):
    apprenant_id: uuid.UUID | None = None
    enseignant_id: uuid.UUID | None = None
    nom_complet: str = Field(min_length=1, max_length=180)
    role: RoleMembreProjet = RoleMembreProjet.MEMBRE
    competences: str | None = None


class EntrepriseLecture(SchemaBase):
    id: uuid.UUID
    code: str
    raison_sociale: str
    sigle: str | None = None
    secteur_activite: str | None = None
    commune_id: uuid.UUID | None = None
    adresse: str | None = None
    telephone: str | None = None
    email: str | None = None
    effectif: int | None = None
    partenaire_officiel: bool
    accueille_handicap: bool
    actif: bool


class EntrepriseEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    raison_sociale: str = Field(min_length=1, max_length=255)
    sigle: str | None = None
    secteur_activite: str | None = None
    ifu: str | None = None
    commune_id: uuid.UUID | None = None
    adresse: str | None = None
    telephone: str | None = None
    email: str | None = None
    site_web: str | None = None
    effectif: int | None = Field(default=None, ge=0)
    contact_nom: str | None = None
    partenaire_officiel: bool = False
    accueille_handicap: bool = False


class OffreLecture(SchemaBase):
    id: uuid.UUID
    reference: str
    intitule: str
    entreprise_id: uuid.UUID
    type_contrat: TypeContrat
    description: str | None = None
    competences_requises: str | None = None
    niveau_requis: str | None = None
    domaine: str | None = None
    lieu: str | None = None
    duree_mois: int | None = None
    gratification: float
    places: int
    places_pourvues: int
    date_publication: date
    date_limite: date | None = None
    accessible_handicap: bool
    ouverte: bool


class OffreEcriture(SchemaEntree):
    reference: str | None = None
    intitule: str = Field(min_length=1, max_length=255)
    entreprise_id: uuid.UUID
    type_contrat: TypeContrat = TypeContrat.STAGE
    description: str | None = None
    missions: str | None = None
    competences_requises: str | None = None
    niveau_requis: str | None = None
    domaine: str | None = None
    lieu: str | None = None
    commune_id: uuid.UUID | None = None
    duree_mois: int | None = Field(default=None, ge=1, le=60)
    gratification: float = Field(default=0.0, ge=0)
    places: int = Field(default=1, ge=1)
    date_limite: date | None = None
    date_prise_poste: date | None = None
    accessible_handicap: bool = False


class CandidatureOffreCreation(SchemaEntree):
    offre_id: uuid.UUID
    apprenant_id: uuid.UUID
    lettre_motivation: str | None = None
    cv_url: str | None = None


class CandidatureOffreLecture(SchemaBase):
    id: uuid.UUID
    offre_id: uuid.UUID
    apprenant_id: uuid.UUID
    statut: StatutCandidature
    date_candidature: date | None = None
    date_entretien: date | None = None
    date_reponse: date | None = None
    commentaire_recruteur: str | None = None


class StageLecture(SchemaBase):
    id: uuid.UUID
    reference: str
    apprenant_id: uuid.UUID
    entreprise_id: uuid.UUID
    sujet: str
    tuteur_entreprise: str | None = None
    date_debut: date
    date_fin: date
    gratification: float
    convention_signee: bool
    note_finale: float | None = None
    appreciation: str | None = None
    valide: bool


# ------------------------------------------------------------------
#  Santé scolaire
# ------------------------------------------------------------------


class CentreSanteLecture(SchemaBase):
    id: uuid.UUID
    code: str
    nom: str
    etablissement_id: uuid.UUID | None = None
    commune_id: uuid.UUID | None = None
    services: str | None = None
    telephone: str | None = None
    nombre_agents: int
    actif: bool


class CentreSanteEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=32)
    nom: str = Field(min_length=1, max_length=255)
    etablissement_id: uuid.UUID | None = None
    commune_id: uuid.UUID | None = None
    services: str | None = Field(default=None, max_length=500)
    telephone: str | None = None
    nombre_agents: int = Field(default=0, ge=0)
    actif: bool = True


class CampagneSanteLecture(SchemaBase):
    id: uuid.UUID
    code: str
    intitule: str
    theme: str | None = None
    date_debut: date
    date_fin: date
    beneficiaires_cibles: int
    beneficiaires_atteints: int


class RendezVousLecture(SchemaBase):
    id: uuid.UUID
    centre_sante_id: uuid.UUID
    apprenant_id: uuid.UUID
    motif: str
    date_rdv: datetime
    statut: str
    orientation: str | None = None


# ------------------------------------------------------------------
#  Alphabétisation
# ------------------------------------------------------------------


class CentreAlphabetisationLecture(SchemaBase):
    id: uuid.UUID
    code: str
    nom: str
    commune_id: uuid.UUID | None = None
    langue_enseignement: Langue
    responsable: str | None = None
    telephone: str | None = None
    nombre_formateurs: int
    nombre_apprenants: int
    actif: bool


class ParcoursAlphabetisationLecture(SchemaBase):
    id: uuid.UUID
    centre_id: uuid.UUID
    nom_complet: str
    age: int | None = None
    langue: Langue
    niveau_initial: str
    niveau_atteint: str | None = None
    progression_pourcentage: float
    certifie: bool


# ------------------------------------------------------------------
#  Recherche scientifique
# ------------------------------------------------------------------


class LaboratoireLecture(SchemaBase):
    id: uuid.UUID
    code: str
    nom: str
    etablissement_id: uuid.UUID | None = None
    domaines: str | None = None
    directeur_nom: str | None = None
    annee_creation: int | None = None
    nombre_chercheurs: int
    actif: bool


class ChercheurLecture(SchemaBase):
    id: uuid.UUID
    laboratoire_id: uuid.UUID | None = None
    nom_complet: str
    grade: str | None = None
    specialite: str | None = None
    orcid: str | None = None
    indice_h: int
    nombre_publications: int


class PublicationLecture(SchemaBase):
    id: uuid.UUID
    titre: str
    type_publication: str
    auteur_principal_id: uuid.UUID | None = None
    revue: str | None = None
    editeur: str | None = None
    annee: int
    doi: str | None = None
    mots_cles: str | None = None
    acces_libre: bool
    nombre_citations: int


class ProjetRechercheLecture(SchemaBase):
    id: uuid.UUID
    code: str
    titre: str
    laboratoire_id: uuid.UUID | None = None
    domaine: str | None = None
    resume: str | None = None
    date_debut: date | None = None
    date_fin: date | None = None
    financement: float
    bailleur: str | None = None
    statut: StatutProjet
