'use client';

import { Search, SlidersHorizontal } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';

import { Pagination, Tableau, type ColonneTableau } from './donnees';
import { Carte, Chargement, EtatVide, MessageErreur } from './primitives';

/**
 * Cadre commun des pages de liste : barre de recherche, filtres, tableau
 * paginé et états de chargement, d'erreur et de vide.
 */
export function ListeRessource<T>({
  colonnes,
  items,
  total,
  pages,
  page,
  taille,
  chargement,
  erreur,
  recherche,
  onRecherche,
  onPage,
  cleLigne,
  onLigneClic,
  legende,
  placeholderRecherche = 'Rechercher…',
  filtres,
  actions,
  videTitre = 'Aucun résultat',
  videDescription = 'Ajustez votre recherche ou vos filtres.',
}: {
  colonnes: Array<ColonneTableau<T>>;
  items: T[];
  total: number;
  pages: number;
  page: number;
  taille: number;
  chargement: boolean;
  erreur: unknown;
  recherche: string;
  onRecherche: (valeur: string) => void;
  onPage: (page: number) => void;
  cleLigne: (ligne: T, index: number) => string;
  onLigneClic?: (ligne: T) => void;
  legende: string;
  placeholderRecherche?: string;
  filtres?: ReactNode;
  actions?: ReactNode;
  videTitre?: string;
  videDescription?: string;
}) {
  const [saisie, setSaisie] = useState(recherche);
  const [filtresVisibles, setFiltresVisibles] = useState(false);

  // La recherche n'est envoyée qu'après une courte pause de frappe.
  useEffect(() => {
    const minuteur = setTimeout(() => {
      if (saisie !== recherche) onRecherche(saisie);
    }, 350);
    return () => clearTimeout(minuteur);
  }, [saisie, recherche, onRecherche]);

  return (
    <Carte>
      <div className="flex flex-wrap items-center gap-2 border-b p-3">
        <div className="relative min-w-0 flex-1">
          <label htmlFor="recherche-liste" className="sr-only">
            {placeholderRecherche}
          </label>
          <Search
            size={17}
            aria-hidden
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 texte-doux"
          />
          <input
            id="recherche-liste"
            type="search"
            value={saisie}
            onChange={(evenement) => setSaisie(evenement.target.value)}
            placeholder={placeholderRecherche}
            className="h-11 w-full rounded-lg border bg-[rgb(var(--fond-carte))] pl-10 pr-3"
          />
        </div>

        {filtres ? (
          <button
            type="button"
            onClick={() => setFiltresVisibles((valeur) => !valeur)}
            aria-expanded={filtresVisibles}
            className="inline-flex h-11 items-center gap-2 rounded-lg border px-3 font-medium hover:bg-[rgb(var(--fond-doux))]"
          >
            <SlidersHorizontal size={17} aria-hidden />
            <span className="hidden sm:inline">Filtres</span>
          </button>
        ) : null}

        {actions}
      </div>

      {filtres && filtresVisibles ? (
        <div className="border-b surface-douce p-4">{filtres}</div>
      ) : null}

      {erreur ? (
        <div className="p-4">
          <MessageErreur erreur={erreur} />
        </div>
      ) : chargement && items.length === 0 ? (
        <Chargement />
      ) : (
        <>
          <Tableau
            colonnes={colonnes}
            lignes={items}
            cleLigne={cleLigne}
            onLigneClic={onLigneClic}
            legende={legende}
            vide={<EtatVide titre={videTitre} description={videDescription} />}
          />
          <Pagination
            page={page}
            pages={pages}
            total={total}
            taille={taille}
            onChange={onPage}
          />
        </>
      )}
    </Carte>
  );
}
