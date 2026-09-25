'use client';

import { useQuery } from '@tanstack/react-query';
import { useId, useState } from 'react';

import { useDebounce } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { cn } from '@/lib/utils';

export interface ApprenantChoisi {
  id: string;
  nom_complet: string;
  identifiant_educatif: string;
}

/**
 * Choix d'un apprenant par recherche.
 *
 * Une liste déroulante de 2 500 élèves serait inutilisable : on interroge
 * l'API au fil de la frappe et l'on ne propose que les correspondances.
 */
export function SelecteurApprenant({
  etiquette,
  aide,
  choisi,
  onChoisir,
}: {
  etiquette: string;
  aide?: string;
  choisi: ApprenantChoisi | null;
  onChoisir: (apprenant: ApprenantChoisi | null) => void;
}) {
  const identifiant = useId();
  const [terme, setTerme] = useState('');
  const differe = useDebounce(terme, 300);

  const resultats = useQuery({
    queryKey: ['apprenants-selecteur', differe],
    queryFn: () =>
      api.get<Page<ApprenantChoisi>>('/apprenants', { q: differe, size: 8, sort_by: 'nom' }),
    enabled: differe.trim().length >= 2 && !choisi,
  });

  if (choisi) {
    return (
      <div className="space-y-1.5">
        <span className="block text-sm font-medium">{etiquette}</span>
        <p className="surface-douce flex flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2.5 text-sm">
          <span className="min-w-0">
            <span className="block truncate font-medium">{choisi.nom_complet}</span>
            <span className="block font-mono text-xs texte-doux">
              {choisi.identifiant_educatif}
            </span>
          </span>
          <button
            type="button"
            onClick={() => {
              onChoisir(null);
              setTerme('');
            }}
            className="shrink-0 text-xs texte-doux hover:underline"
          >
            Changer
          </button>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <label htmlFor={identifiant} className="block text-sm font-medium">
        {etiquette}
      </label>
      <input
        id={identifiant}
        type="search"
        value={terme}
        onChange={(evenement) => setTerme(evenement.target.value)}
        placeholder="Nom, prénoms ou identifiant éducatif…"
        className="w-full rounded-lg border bg-[rgb(var(--fond-carte))] px-3 py-2.5 placeholder:text-[rgb(var(--texte-doux))]/70"
      />
      {aide ? <p className="text-xs texte-doux">{aide}</p> : null}

      {differe.trim().length >= 2 ? (
        <ul className="surface max-h-56 overflow-y-auto rounded-lg border">
          {resultats.isLoading ? (
            <li className="px-3 py-2 text-sm texte-doux">Recherche…</li>
          ) : (resultats.data?.items ?? []).length === 0 ? (
            <li className="px-3 py-2 text-sm texte-doux">Aucun apprenant trouvé.</li>
          ) : (
            (resultats.data?.items ?? []).map((apprenant) => (
              <li key={apprenant.id}>
                <button
                  type="button"
                  onClick={() => onChoisir(apprenant)}
                  className={cn(
                    'w-full px-3 py-2 text-left text-sm hover:bg-[rgb(var(--fond-doux))]',
                  )}
                >
                  <span className="block truncate font-medium">{apprenant.nom_complet}</span>
                  <span className="block font-mono text-xs texte-doux">
                    {apprenant.identifiant_educatif}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}
