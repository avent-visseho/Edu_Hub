'use client';

import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useId, useRef, useState } from 'react';

import { useDebounce } from '@/hooks/useListe';
import { useAccessibilite } from '@/lib/accessibilite';
import { api } from '@/lib/api';
import { cn, humaniser } from '@/lib/utils';

interface Resultat {
  type: string;
  id: string;
  libelle: string;
  description: string | null;
  lien: string;
}

/**
 * Recherche transverse de l'en-tête.
 *
 * Elle interroge apprenants, enseignants, établissements, diplômes et projets
 * d'un seul tenant, et mène directement à la fiche. Le constructeur de requêtes
 * reste accessible en bas de la liste pour les interrogations élaborées.
 */
export function RechercheGlobale() {
  const router = useRouter();
  const { modeSimplifie } = useAccessibilite();
  const [terme, setTerme] = useState('');
  const [ouvert, setOuvert] = useState(false);
  const [surligne, setSurligne] = useState(0);
  const conteneur = useRef<HTMLDivElement>(null);
  const identifiant = useId();

  const differe = useDebounce(terme, 300);

  const resultats = useQuery({
    queryKey: ['recherche-globale', differe],
    queryFn: () => api.get<Resultat[]>('/recherche/globale', { q: differe, limite: 8 }),
    enabled: differe.trim().length >= 2,
  });

  // Un clic en dehors referme la liste : elle recouvre le contenu de la page.
  useEffect(() => {
    function surClic(evenement: MouseEvent) {
      if (!conteneur.current?.contains(evenement.target as Node)) setOuvert(false);
    }
    document.addEventListener('mousedown', surClic);
    return () => document.removeEventListener('mousedown', surClic);
  }, []);

  useEffect(() => setSurligne(0), [differe]);

  const liste = resultats.data ?? [];
  const affiche = ouvert && differe.trim().length >= 2;

  function ouvrir(resultat: Resultat) {
    setOuvert(false);
    setTerme('');
    router.push(resultat.lien);
  }

  function auClavier(evenement: React.KeyboardEvent<HTMLInputElement>) {
    if (evenement.key === 'Escape') {
      setOuvert(false);
      return;
    }
    if (evenement.key === 'Enter') {
      evenement.preventDefault();
      if (liste[surligne]) ouvrir(liste[surligne]);
      else router.push('/recherche');
      return;
    }
    if (evenement.key === 'ArrowDown' || evenement.key === 'ArrowUp') {
      evenement.preventDefault();
      if (liste.length === 0) return;
      const pas = evenement.key === 'ArrowDown' ? 1 : -1;
      setSurligne((precedent) => (precedent + pas + liste.length) % liste.length);
    }
  }

  return (
    <div ref={conteneur} className="relative flex-1">
      <label htmlFor={identifiant} className="sr-only">
        Rechercher dans tout le système
      </label>
      <span className="flex h-11 max-w-md items-center gap-2 rounded-lg border px-3">
        <Search size={18} aria-hidden className="texte-doux" />
        <input
          id={identifiant}
          type="search"
          role="combobox"
          aria-expanded={affiche}
          aria-controls={`${identifiant}-liste`}
          aria-autocomplete="list"
          value={terme}
          onChange={(evenement) => {
            setTerme(evenement.target.value);
            setOuvert(true);
          }}
          onFocus={() => setOuvert(true)}
          onKeyDown={auClavier}
          placeholder={
            modeSimplifie ? 'Chercher' : 'Rechercher un élève, une école, un diplôme…'
          }
          className="w-full bg-transparent text-sm outline-none placeholder:text-[rgb(var(--texte-doux))]"
        />
      </span>

      {affiche ? (
        <div
          id={`${identifiant}-liste`}
          role="listbox"
          aria-label="Résultats de la recherche"
          className="surface absolute left-0 top-12 z-30 w-full max-w-md overflow-hidden rounded-lg border shadow-carte"
        >
          {resultats.isLoading ? (
            <p className="px-4 py-3 text-sm texte-doux">Recherche en cours…</p>
          ) : liste.length === 0 ? (
            <p className="px-4 py-3 text-sm texte-doux">
              Aucun résultat pour « {differe} ».
            </p>
          ) : (
            <ul className="max-h-80 overflow-y-auto">
              {liste.map((resultat, index) => (
                <li key={`${resultat.type}-${resultat.id}`}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={index === surligne}
                    onMouseEnter={() => setSurligne(index)}
                    onClick={() => ouvrir(resultat)}
                    className={cn(
                      'flex w-full items-baseline gap-2 px-4 py-2 text-left text-sm',
                      index === surligne && 'bg-[rgb(var(--fond-doux))]',
                    )}
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{resultat.libelle}</span>
                      {resultat.description ? (
                        <span className="block truncate text-xs texte-doux">
                          {resultat.description}
                        </span>
                      ) : null}
                    </span>
                    <span className="shrink-0 text-xs texte-doux">
                      {humaniser(resultat.type)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button
            type="button"
            onClick={() => {
              setOuvert(false);
              router.push('/recherche');
            }}
            className="w-full border-t px-4 py-2 text-left text-xs texte-doux hover:bg-[rgb(var(--fond-doux))]"
          >
            Ouvrir la recherche avancée pour croiser plusieurs conditions
          </button>
        </div>
      ) : null}
    </div>
  );
}
