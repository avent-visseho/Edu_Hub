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
export function humaniser(valeur: string | null | undefined): string {
  if (!valeur) return '—';
  const texte = valeur.replace(/_/g, ' ').toLowerCase();
  return texte.charAt(0).toUpperCase() + texte.slice(1);
}

/** Tronque un texte en préservant les mots. */
export function tronquer(texte: string, longueur = 120): string {
  if (texte.length <= longueur) return texte;
  return `${texte.slice(0, longueur).trimEnd()}…`;
}
