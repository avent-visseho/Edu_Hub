'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { api, type Page } from '@/lib/api';

export interface EtatListe {
  page: number;
  taille: number;
  recherche: string;
  tri: string | null;
  sens: 'asc' | 'desc';
}

/**
 * Pilote une liste paginée de l'API : pagination, recherche et tri.
 *
 * `keepPreviousData` évite le clignotement de la table lors d'un changement de
 * page — un confort qui compte davantage encore sur une connexion lente.
 */
export function useListe<T>(
  chemin: string,
  options: {
    taille?: number;
    tri?: string;
    filtres?: Record<string, string | number | boolean | null | undefined>;
    active?: boolean;
  } = {},
) {
  const [etat, setEtat] = useState<EtatListe>({
    page: 1,
    taille: options.taille ?? 25,
    recherche: '',
    tri: options.tri ?? null,
    sens: 'asc',
  });

  const filtres = options.filtres ?? {};
  const cleFiltres = JSON.stringify(filtres);

  const requete = useQuery({
    queryKey: [chemin, etat, cleFiltres],
    enabled: options.active !== false,
    placeholderData: keepPreviousData,
    queryFn: () =>
      api.get<Page<T>>(chemin, {
        page: etat.page,
        size: etat.taille,
        q: etat.recherche || undefined,
        sort_by: etat.tri ?? undefined,
        sort_dir: etat.sens,
        ...filtres,
      }),
  });

  const changerPage = useCallback((page: number) => {
    setEtat((precedent) => ({ ...precedent, page: Math.max(1, page) }));
  }, []);

  const changerRecherche = useCallback((recherche: string) => {
    setEtat((precedent) => ({ ...precedent, recherche, page: 1 }));
  }, []);

  const trier = useCallback((champ: string) => {
    setEtat((precedent) => ({
      ...precedent,
      tri: champ,
      sens: precedent.tri === champ && precedent.sens === 'asc' ? 'desc' : 'asc',
      page: 1,
    }));
  }, []);

  return useMemo(
    () => ({
      ...requete,
      etat,
      items: requete.data?.items ?? [],
      total: requete.data?.total ?? 0,
      pages: requete.data?.pages ?? 0,
      changerPage,
      changerRecherche,
      trier,
    }),
    [requete, etat, changerPage, changerRecherche, trier],
  );
}

/** Déclenche une valeur avec un délai, pour ne pas interroger l'API à chaque frappe. */
export function useDebounce<T>(valeur: T, delai = 350): T {
  const [differee, setDifferee] = useState(valeur);

  useMemo(() => {
    const minuteur = setTimeout(() => setDifferee(valeur), delai);
    return () => clearTimeout(minuteur);
  }, [valeur, delai]);

  return differee;
}
