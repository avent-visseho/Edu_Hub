'use client';

import { ChevronLeft, ChevronRight, Volume2 } from 'lucide-react';
import type { ReactNode } from 'react';

import { useAccessibilite } from '@/lib/accessibilite';
import { cn, formaterNombre } from '@/lib/utils';

import { Bouton } from './primitives';

// ------------------------------------------------------------------
//  Vignette d'indicateur
// ------------------------------------------------------------------

export function Indicateur({
  libelle,
  valeur,
  unite,
  variation,
  icone,
  pictogramme,
  className,
}: {
  libelle: string;
  valeur: string | number;
  unite?: string | null;
  variation?: number | null;
  icone?: ReactNode;
  /** Émoji affiché en mode simplifié. */
  pictogramme?: string;
  className?: string;
}) {
  const { modeSimplifie, lectureVocale, lire } = useAccessibilite();
  const affichage = typeof valeur === 'number' ? formaterNombre(valeur) : valeur;

  return (
    <div className={cn('surface rounded-xl p-4 shadow-carte', className)}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium texte-doux">{libelle}</p>
        <span aria-hidden className="texte-doux opacity-70">
          {modeSimplifie && pictogramme ? (
            <span className="text-xl">{pictogramme}</span>
          ) : (
            icone
          )}
        </span>
      </div>

      <p className="mt-2 flex items-baseline gap-1.5">
        <span className="text-3xl font-semibold tabular-nums tracking-tight">{affichage}</span>
        {unite ? <span className="text-sm texte-doux">{unite}</span> : null}
      </p>

      {variation !== null && variation !== undefined ? (
        <p
          className={cn(
            'mt-1 text-xs font-medium',
            variation >= 0 ? 'text-[rgb(var(--succes))]' : 'text-[rgb(var(--danger))]',
          )}
        >
          {variation >= 0 ? '▲' : '▼'} {formaterNombre(Math.abs(variation), 1)} % sur un an
        </p>
      ) : null}

      {lectureVocale ? (
        <button
          type="button"
          onClick={() => lire(`${libelle} : ${affichage} ${unite ?? ''}`)}
          className="mt-2 inline-flex items-center gap-1 text-xs texte-doux hover:underline"
        >
          <Volume2 size={14} aria-hidden /> Écouter
        </button>
      ) : null}
    </div>
  );
}

// ------------------------------------------------------------------
//  Tableau
// ------------------------------------------------------------------

export interface ColonneTableau<T> {
  cle: string;
  entete: ReactNode;
  rendu: (ligne: T) => ReactNode;
  /** Alignement du contenu ; les nombres sont alignés à droite. */
  alignement?: 'gauche' | 'centre' | 'droite';
  /** Colonne masquée sur petit écran. */
  secondaire?: boolean;
  largeur?: string;
}

export function Tableau<T>({
  colonnes,
  lignes,
  cleLigne,
  onLigneClic,
  legende,
  vide,
}: {
  colonnes: Array<ColonneTableau<T>>;
  lignes: T[];
  cleLigne: (ligne: T, index: number) => string;
  onLigneClic?: (ligne: T) => void;
  /** Description du tableau, lue par les lecteurs d'écran. */
  legende: string;
  vide?: ReactNode;
}) {
  if (lignes.length === 0 && vide) return <>{vide}</>;

  const alignements = {
    gauche: 'text-left',
    centre: 'text-center',
    droite: 'text-right tabular-nums',
  } as const;

  return (
    <div className="defilement-fin overflow-x-auto">
      <table className="w-full min-w-full text-sm">
        <caption className="sr-only">{legende}</caption>
        <thead>
          <tr className="surface-douce">
            {colonnes.map((colonne) => (
              <th
                key={colonne.cle}
                scope="col"
                style={colonne.largeur ? { width: colonne.largeur } : undefined}
                className={cn(
                  'border-b px-4 py-3 text-xs font-semibold uppercase tracking-wide texte-doux',
                  alignements[colonne.alignement ?? 'gauche'],
                  colonne.secondaire && 'hidden md:table-cell',
                )}
              >
                {colonne.entete}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lignes.map((ligne, index) => (
            <tr
              key={cleLigne(ligne, index)}
              onClick={onLigneClic ? () => onLigneClic(ligne) : undefined}
              tabIndex={onLigneClic ? 0 : undefined}
              onKeyDown={
                onLigneClic
                  ? (evenement) => {
                      if (evenement.key === 'Enter' || evenement.key === ' ') {
                        evenement.preventDefault();
                        onLigneClic(ligne);
                      }
                    }
                  : undefined
              }
              className={cn(
                'border-b last:border-0',
                onLigneClic && 'cursor-pointer hover:bg-[rgb(var(--fond-doux))]',
              )}
            >
              {colonnes.map((colonne) => (
                <td
                  key={colonne.cle}
                  className={cn(
                    'px-4 py-3',
                    alignements[colonne.alignement ?? 'gauche'],
                    colonne.secondaire && 'hidden md:table-cell',
                  )}
                >
                  {colonne.rendu(ligne)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ------------------------------------------------------------------
//  Pagination
// ------------------------------------------------------------------

export function Pagination({
  page,
  pages,
  total,
  taille,
  onChange,
}: {
  page: number;
  pages: number;
  total: number;
  taille: number;
  onChange: (page: number) => void;
}) {
  if (total === 0) return null;
  const premier = (page - 1) * taille + 1;
  const dernier = Math.min(page * taille, total);

  return (
    <nav
      aria-label="Pagination"
      className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3 text-sm"
    >
      <p className="texte-doux" aria-live="polite">
        {formaterNombre(premier)} – {formaterNombre(dernier)} sur {formaterNombre(total)}
      </p>
      <div className="flex items-center gap-2">
        <Bouton
          variante="secondaire"
          taille="sm"
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          icone={<ChevronLeft size={16} aria-hidden />}
        >
          Précédent
        </Bouton>
        <span className="px-2 tabular-nums texte-doux">
          Page {page} / {Math.max(pages, 1)}
        </span>
        <Bouton
          variante="secondaire"
          taille="sm"
          onClick={() => onChange(page + 1)}
          disabled={page >= pages}
        >
          Suivant
          <ChevronRight size={16} aria-hidden />
        </Bouton>
      </div>
    </nav>
  );
}

// ------------------------------------------------------------------
//  Barre de progression
// ------------------------------------------------------------------

export function Jauge({
  valeur,
  maximum = 100,
  etiquette,
  ton = 'accent',
}: {
  valeur: number;
  maximum?: number;
  /**
   * Texte affiché à gauche du pourcentage. Une chaîne vide masque toute la
   * ligne ; l'omettre ne laisse que le pourcentage, ce qui convient dans une
   * colonne de tableau dont l'en-tête porte déjà l'intitulé.
   */
  etiquette?: string;
  ton?: 'accent' | 'succes' | 'alerte' | 'danger';
}) {
  const pourcentage = Math.min(100, Math.max(0, (valeur / (maximum || 1)) * 100));
  const couleurs = {
    accent: 'bg-[rgb(var(--accent))]',
    succes: 'bg-[rgb(var(--succes))]',
    alerte: 'bg-[rgb(var(--alerte))]',
    danger: 'bg-[rgb(var(--danger))]',
  } as const;

  return (
    <div className="space-y-1">
      {etiquette !== '' ? (
        <div className="flex justify-between gap-2 text-xs">
          {etiquette ? <span className="texte-doux">{etiquette}</span> : null}
          <span className="ml-auto font-medium tabular-nums">
            {formaterNombre(pourcentage, 1)} %
          </span>
        </div>
      ) : null}
      <div
        role="progressbar"
        aria-valuenow={Math.round(pourcentage)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={etiquette ?? 'Progression'}
        className="h-2 overflow-hidden rounded-full surface-douce"
      >
        <div
          className={cn('h-full rounded-full transition-all', couleurs[ton])}
          style={{ width: `${pourcentage}%` }}
        />
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
//  Liste descriptive
// ------------------------------------------------------------------

export function ListeDescriptive({
  entrees,
  colonnes = 2,
}: {
  entrees: Array<{ terme: string; valeur: ReactNode }>;
  colonnes?: 1 | 2 | 3;
}) {
  const grilles = {
    1: 'sm:grid-cols-1',
    2: 'sm:grid-cols-2',
    3: 'sm:grid-cols-2 lg:grid-cols-3',
  } as const;

  return (
    <dl className={cn('grid grid-cols-1 gap-x-6 gap-y-4', grilles[colonnes])}>
      {entrees.map((entree) => (
        <div key={entree.terme} className="min-w-0">
          <dt className="text-xs font-medium uppercase tracking-wide texte-doux">
            {entree.terme}
          </dt>
          <dd className="mt-0.5 break-words font-medium">{entree.valeur}</dd>
        </div>
      ))}
    </dl>
  );
}
