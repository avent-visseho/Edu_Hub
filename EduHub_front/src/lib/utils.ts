import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Compose des classes Tailwind en résolvant les conflits. */
export function cn(...entrees: ClassValue[]): string {
  return twMerge(clsx(entrees));
}

/** Formate un nombre à la française : 12 345,67. */
export function formaterNombre(valeur: number | null | undefined, decimales = 0): string {
  if (valeur === null || valeur === undefined || Number.isNaN(valeur)) return '—';
  return new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(valeur);
}

/** Formate une note sur 20 : 16,85. */
export function formaterNote(valeur: number | null | undefined): string {
  if (valeur === null || valeur === undefined) return '—';
  return formaterNombre(valeur, 2);
}

/** Formate un pourcentage : 62,4 %. */
export function formaterPourcentage(valeur: number | null | undefined, decimales = 1): string {
  if (valeur === null || valeur === undefined) return '—';
  return `${formaterNombre(valeur, decimales)} %`;
}

/** Formate un montant en francs CFA. */
export function formaterMontant(valeur: number | null | undefined): string {
  if (valeur === null || valeur === undefined) return '—';
  return `${formaterNombre(valeur)} F CFA`;
}

/** Formate une date ISO au format 12/03/2027. */
export function formaterDate(valeur: string | Date | null | undefined): string {
  if (!valeur) return '—';
  const date = typeof valeur === 'string' ? new Date(valeur) : valeur;
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short' }).format(date);
}

/** Formate une date et une heure : 12/03/2027 à 14:05. */
export function formaterDateHeure(valeur: string | Date | null | undefined): string {
  if (!valeur) return '—';
  const date = typeof valeur === 'string' ? new Date(valeur) : valeur;
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date);
}

/** Initiales d'un nom complet, pour les pastilles d'avatar. */
export function initiales(nom: string | null | undefined): string {
  if (!nom) return '—';
  return nom
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((mot) => mot[0]?.toUpperCase() ?? '')
    .join('');
}

/** Rend lisible un libellé technique : STATUT_EN_COURS → Statut en cours. */
/**
 * Accentuation des codes d'énumération.
 *
 * Les valeurs stockées sont en ASCII — c'est le bon choix pour un identifiant —
 * mais les afficher telles quelles donnerait « Publiee » ou « Ministere » au
 * milieu d'une interface entièrement française. La table ne couvre que les mots
 * réellement produits par les énumérations du domaine.
 */
const ACCENTS: Record<string, string> = {
  abandonne: 'abandonné',
  accepte: 'accepté',
  acceptee: 'acceptée',
  accessibilite: 'accessibilité',
  adapte: 'adapté',
  ajourne: 'ajourné',
  annule: 'annulé',
  annulee: 'annulée',
  anticipee: 'anticipée',
  archive: 'archivé',
  archivee: 'archivée',
  assiduite: 'assiduité',
  attribuee: 'attribuée',
  benevole: 'bénévole',
  bibliotheque: 'bibliothèque',
  cloturee: 'clôturée',
  competence: 'compétence',
  competences: 'compétences',
  conge: 'congé',
  contestee: 'contestée',
  controle: 'contrôle',
  convoque: 'convoqué',
  corrige: 'corrigé',
  corrigee: 'corrigée',
  cree: 'créé',
  creee: 'créée',
  creneau: 'créneau',
  creneaux: 'créneaux',
  defavorable: 'défavorable',
  delegue: 'délégué',
  deleguee: 'déléguée',
  deliberation: 'délibération',
  depart: 'départ',
  departement: 'département',
  departementale: 'départementale',
  departements: 'départements',
  depose: 'déposé',
  deposee: 'déposée',
  desiste: 'désisté',
  detachement: 'détachement',
  diplome: 'diplôme',
  diplomes: 'diplômes',
  echoue: 'échoué',
  eleve: 'élève',
  eleves: 'élèves',
  eliminatoire: 'éliminatoire',
  emis: 'émis',
  emises: 'émises',
  envoyee: 'envoyée',
  etablissement: 'établissement',
  etablissements: 'établissements',
  etat: 'état',
  etude: 'étude',
  evaluation: 'évaluation',
  evaluations: 'évaluations',
  expire: 'expiré',
  felicitations: 'félicitations',
  feminin: 'féminin',
  frere: 'frère',
  general: 'général',
  idee: 'idée',
  identite: 'identité',
  incomplete: 'incomplète',
  injustifiee: 'injustifiée',
  interet: 'intérêt',
  interim: 'intérim',
  justifie: 'justifié',
  justifiee: 'justifiée',
  materiel: 'matériel',
  mere: 'mère',
  ministere: 'ministère',
  numerique: 'numérique',
  operateur: 'opérateur',
  paye: 'payé',
  pere: 'père',
  periode: 'période',
  periodes: 'périodes',
  planifie: 'planifié',
  planifiee: 'planifiée',
  preparation: 'préparation',
  preselectionnee: 'présélectionnée',
  present: 'présent',
  presentation: 'présentation',
  pret: 'prêt',
  prets: 'prêts',
  publie: 'publié',
  publiee: 'publiée',
  publies: 'publiés',
  rattachee: 'rattachée',
  recu: 'reçu',
  recus: 'reçus',
  reference: 'référence',
  references: 'références',
  refuse: 'refusé',
  refusee: 'refusée',
  regle: 'règle',
  reglement: 'règlement',
  regles: 'règles',
  rejete: 'rejeté',
  rejetee: 'rejetée',
  releve: 'relevé',
  rembourse: 'remboursé',
  remplacee: 'remplacée',
  repartition: 'répartition',
  reportee: 'reportée',
  reseau: 'réseau',
  reserve: 'réservé',
  resultat: 'résultat',
  resultats: 'résultats',
  retarde: 'retardé',
  retire: 'retiré',
  retiree: 'retirée',
  reussite: 'réussite',
  sante: 'santé',
  scolarite: 'scolarité',
  seance: 'séance',
  seances: 'séances',
  secretaire: 'secrétaire',
  securite: 'sécurité',
  serie: 'série',
  series: 'séries',
  soeur: 'sœur',
  speciale: 'spéciale',
  specialite: 'spécialité',
  specialites: 'spécialités',
  synthese: 'synthèse',
  syntheses: 'synthèses',
  systeme: 'système',
  termine: 'terminé',
  terminee: 'terminée',
  tranchee: 'tranchée',
  transfere: 'transféré',
  valide: 'validé',
  validee: 'validée',
  verification: 'vérification',
  video: 'vidéo',
  videoprojecteur: 'vidéoprojecteur',
};

/** Rend lisible un code d'énumération : `ABSENCE_JUSTIFIEE` → `Absence justifiée`. */
export function humaniser(valeur: string | null | undefined): string {
  if (!valeur) return '—';
  const texte = valeur
    .replace(/_/g, ' ')
    .toLowerCase()
    .split(' ')
    .map((mot) => ACCENTS[mot] ?? mot)
    .join(' ');
  return texte.charAt(0).toUpperCase() + texte.slice(1);
}

/** Tronque un texte en préservant les mots. */
export function tronquer(texte: string, longueur = 120): string {
  if (texte.length <= longueur) return texte;
  return `${texte.slice(0, longueur).trimEnd()}…`;
}
