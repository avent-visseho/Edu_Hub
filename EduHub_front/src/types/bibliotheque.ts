/** Types du domaine bibliothèque. */

export interface LivreLecture {
  id: string;
  isbn: string | null;
  titre: string;
  auteur: string;
  editeur: string | null;
  annee_publication: number | null;
  categorie: string | null;
  langue: string;
  nombre_pages: number | null;
  resume: string | null;
  format_accessible: boolean;
  audio_disponible: boolean;
  braille_disponible: boolean;
}

export interface PretLecture {
  id: string;
  exemplaire_id: string;
  apprenant_id: string | null;
  date_pret: string;
  date_retour_prevue: string;
  date_retour_effective: string | null;
  jours_retard: number;
  penalite: number;
  rendu: boolean;
}
