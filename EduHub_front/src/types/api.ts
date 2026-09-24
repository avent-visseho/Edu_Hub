/** Types partagés avec l'API EduHub. */

export type Sexe = 'MASCULIN' | 'FEMININ';

export type NiveauScope =
  | 'NATIONAL'
  | 'MINISTERE'
  | 'DIRECTION'
  | 'DEPARTEMENT'
  | 'ETABLISSEMENT'
  | 'PERSONNEL';

export interface Jetons {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Affectation {
  id: string;
  role: { id: string; code: string; libelle: string; niveau_scope: NiveauScope };
  structure_id: string | null;
  etablissement_id: string | null;
  actif: boolean;
}

export interface Utilisateur {
  id: string;
  email: string;
  nom: string;
  prenoms: string;
  nom_complet: string;
  sexe: Sexe | null;
  telephone: string | null;
  photo_url: string | null;
  actif: boolean;
  doit_changer_mot_de_passe: boolean;
  derniere_connexion: string | null;
  langue: string;
  type_handicap: string;
  mode_simplifie: boolean;
  contraste_eleve: boolean;
  grande_police: boolean;
  lecture_vocale: boolean;
  affectations?: Affectation[];
  roles: string[];
  permissions: string[];
  niveau_scope: NiveauScope;
}

export interface Indicateur {
  code: string;
  libelle: string;
  valeur: number;
  unite: string | null;
  variation: number | null;
  detail: Record<string, unknown> | null;
}

export interface TableauBord {
  perimetre: string;
  perimetre_libelle: string;
  indicateurs: Indicateur[];
  graphiques: Record<string, Array<Record<string, unknown>>>;
  alertes: Array<{
    id: string;
    titre: string;
    niveau: string;
    domaine: string;
    message: string;
  }>;
}

export interface ColonneRecherche {
  cle: string;
  libelle: string;
}

export interface ResultatRecherche {
  entite: string;
  total: number;
  page: number;
  taille: number;
  pages: number;
  colonnes: ColonneRecherche[];
  lignes: Array<Record<string, unknown>>;
}

export interface ChampRecherche {
  cle: string;
  libelle: string;
  type: string;
  choix: string[];
  operateurs: string[];
  calcule?: boolean;
}

export interface EntiteRecherche {
  cle: string;
  libelle: string;
  colonnes: ColonneRecherche[];
  champs: ChampRecherche[];
}

export interface ReponseNaturelle {
  question: string;
  entite: string;
  confiance: number;
  explications: string[];
  filtres: Array<{ champ: string; operateur: string; valeur: unknown }>;
  resultat: ResultatRecherche | null;
}

export interface Apprenant {
  id: string;
  identifiant_educatif: string;
  matricule: string | null;
  nom: string;
  prenoms: string;
  nom_complet: string;
  sexe: Sexe;
  date_naissance: string;
  lieu_naissance: string | null;
  etablissement_actuel_id: string | null;
  statut: string;
  type_handicap: string;
  tiers_temps: boolean;
  besoins_specifiques: string | null;
  orphelin: boolean;
  situation_vulnerable: boolean;
}

export interface Etablissement {
  id: string;
  code: string;
  nom: string;
  sigle: string | null;
  commune_id: string | null;
  adresse: string | null;
  latitude: number | null;
  longitude: number | null;
  directeur_nom: string | null;
  telephone: string | null;
  email: string | null;
  capacite_accueil: number;
  effectif_actuel: number;
  est_centre_examen: boolean;
  internat: boolean;
  cantine: boolean;
  electricite: boolean;
  eau_potable: boolean;
  connexion_internet: boolean;
  accessibilite: string;
  zone_rurale: boolean;
  actif: boolean;
}

export interface Classe {
  id: string;
  code: string;
  libelle: string;
  etablissement_id: string;
  annee_id: string;
  niveau_id: string;
  serie_id: string | null;
  effectif: number;
  effectif_max: number;
  moyenne_classe: number | null;
}

export interface Bulletin {
  id: string;
  numero: string;
  apprenant_id: string;
  classe_id: string;
  periode_id: string;
  etablissement_id: string;
  moyenne_generale: number | null;
  total_points: number | null;
  total_coefficients: number | null;
  rang: number | null;
  effectif_classe: number | null;
  moyenne_classe: number | null;
  moyenne_premier: number | null;
  moyenne_dernier: number | null;
  absences_heures: number;
  absences_justifiees: number;
  retards: number;
  appreciation_generale: string | null;
  decision: string | null;
  mention: string | null;
  publie: boolean;
  code_verification: string | null;
}

export interface LigneBulletin {
  matiere_id: string;
  matiere_libelle: string | null;
  moyenne: number | null;
  coefficient: number;
  points: number | null;
  rang: number | null;
  moyenne_classe: number | null;
  note_min: number | null;
  note_max: number | null;
  appreciation: string | null;
}

export interface BulletinDetail extends Bulletin {
  apprenant_nom: string | null;
  apprenant_identifiant: string | null;
  classe_libelle: string | null;
  etablissement_nom: string | null;
  periode_libelle: string | null;
  annee_libelle: string | null;
  lignes: LigneBulletin[];
}

export interface SessionExamen {
  id: string;
  examen_id: string;
  code: string;
  libelle: string;
  type_session: string;
  annee: number;
  statut: string;
  date_debut: string | null;
  date_fin: string | null;
  nombre_inscrits: number;
  nombre_presents: number;
  nombre_absents: number;
  nombre_admis: number;
  taux_reussite: number | null;
  moyenne_generale: number | null;
}

export interface TableauBordSession {
  session: SessionExamen;
  dossiers: Record<string, number>;
  centres: number;
  salles: number;
  surveillants: number;
  correcteurs: number;
  copies_corrigees: number;
  copies_totales: number;
  jurys: number;
  contentieux: Record<string, number>;
  budget: Record<string, number>;
  resultats_par_departement: Array<{
    code: string;
    departement: string;
    candidats: number;
    admis: number;
    non_admis: number;
    taux_reussite: number;
    moyenne: number | null;
  }>;
}

export interface ResultatPublic {
  numero_candidat: string;
  numero_table: string | null;
  nom_complet: string;
  examen: string;
  session: string;
  serie: string | null;
  centre: string | null;
  moyenne: number | null;
  mention: string | null;
  decision: string;
  rang_national: number | null;
  code_verification: string | null;
}

export interface VerificationDocument {
  valide: boolean;
  message: string;
  type_document: string | null;
  numero: string | null;
  titulaire: string | null;
  intitule: string | null;
  session: string | null;
  annee: number | null;
  mention: string | null;
  date_delivrance: string | null;
}
