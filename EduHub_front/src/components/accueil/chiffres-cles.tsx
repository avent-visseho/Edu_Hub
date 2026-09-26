'use client';

import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import { formaterNombre } from '@/lib/utils';

interface Chiffres {
  apprenants: number;
  enseignants: number;
  etablissements: number;
  communes_couvertes: number;
  departements: number;
  communes: number;
  sessions_publiees: number;
}

/**
 * Chiffres affichés sur l'accueil. Le libellé est au singulier ou au pluriel
 * selon la valeur, et l'ordre va du plus parlant au plus administratif.
 */
const LIGNES: Array<{
  cle: keyof Chiffres;
  libelle: (valeur: number) => string;
}> = [
  { cle: 'apprenants', libelle: (n) => (n > 1 ? 'apprenants suivis' : 'apprenant suivi') },
  { cle: 'enseignants', libelle: (n) => (n > 1 ? 'enseignants' : 'enseignant') },
  { cle: 'etablissements', libelle: (n) => (n > 1 ? 'établissements' : 'établissement') },
  {
    cle: 'communes_couvertes',
    libelle: (n) => (n > 1 ? 'communes couvertes' : 'commune couverte'),
  },
  {
    cle: 'sessions_publiees',
    libelle: (n) => (n > 1 ? "sessions d'examen publiées" : "session d'examen publiée"),
  },
];

export function ChiffresCles() {
  const chiffres = useQuery({
    queryKey: ['chiffres-publics'],
    queryFn: () => api.get<Chiffres>('/public/chiffres', undefined, { publique: true }),
    staleTime: 5 * 60 * 1000,
  });

  // L'accueil doit rester lisible même API éteinte : plutôt que de masquer la
  // bande ou d'afficher une erreur au visiteur, on garde la structure et on
  // remplace les valeurs par un tiret.
  const valeur = (cle: keyof Chiffres) =>
    chiffres.data ? formaterNombre(chiffres.data[cle]) : '—';

  return (
    <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-[rgb(var(--bordure))] sm:grid-cols-3 lg:grid-cols-5">
      {LIGNES.map(({ cle, libelle }) => (
        <div key={cle} className="bg-[rgb(var(--fond-carte))] px-5 py-6">
          <dt className="sr-only">{libelle(2)}</dt>
          <dd>
            <span
              className={`block text-3xl font-semibold tabular-nums tracking-tight text-[rgb(var(--marque-bleu))] ${
                chiffres.isPending ? 'animate-pulse' : ''
              }`}
            >
              {valeur(cle)}
            </span>
            <span className="mt-1 block text-sm texte-doux">
              {libelle(chiffres.data?.[cle] ?? 2)}
            </span>
          </dd>
        </div>
      ))}
    </dl>
  );
}
