'use client';

import { useMemo } from 'react';

import { cn } from '@/lib/utils';

export interface Creneau {
  id: string;
  matiere_id: string;
  enseignant_id: string | null;
  salle_id: string | null;
  jour: string;
  heure_debut: string;
  heure_fin: string;
}

const JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI'] as const;

const LIBELLES_JOURS: Record<string, string> = {
  LUNDI: 'Lundi',
  MARDI: 'Mardi',
  MERCREDI: 'Mercredi',
  JEUDI: 'Jeudi',
  VENDREDI: 'Vendredi',
  SAMEDI: 'Samedi',
};

/** Couleur stable dérivée d'un identifiant, pour distinguer les matières. */
const COULEURS = [
  '#284f8b',
  '#16a153',
  '#d77706',
  '#7c3aed',
  '#b91c1c',
  '#0891b2',
  '#a16207',
  '#be123c',
];

function couleurDe(cle: string): string {
  let somme = 0;
  for (const caractere of cle) somme += caractere.charCodeAt(0);
  return COULEURS[somme % COULEURS.length];
}

/**
 * Grille hebdomadaire de l'emploi du temps.
 *
 * Elle reste lisible sur téléphone : en dessous du point de rupture, les
 * créneaux sont simplement regroupés par jour, sous forme de liste.
 */
export function EmploiDuTemps({
  creneaux,
  libelleMatiere,
  libelleEnseignant,
}: {
  creneaux: Creneau[];
  libelleMatiere: (id: string) => string;
  libelleEnseignant: (id: string | null) => string | null;
}) {
  const parJour = useMemo(() => {
    const groupes = new Map<string, Creneau[]>();
    for (const jour of JOURS) groupes.set(jour, []);
    for (const creneau of creneaux) {
      const liste = groupes.get(creneau.jour);
      if (liste) liste.push(creneau);
    }
    for (const liste of groupes.values()) {
      liste.sort((a, b) => a.heure_debut.localeCompare(b.heure_debut));
    }
    return groupes;
  }, [creneaux]);

  const joursUtilises = JOURS.filter((jour) => (parJour.get(jour) ?? []).length > 0);

  if (joursUtilises.length === 0) {
    return (
      <p className="px-5 py-8 text-center text-sm texte-doux">
        Aucun créneau n&apos;est encore défini pour cette classe.
      </p>
    );
  }

  return (
    <div className="p-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {joursUtilises.map((jour) => (
          <section key={jour} aria-labelledby={`jour-${jour}`}>
            <h3
              id={`jour-${jour}`}
              className="mb-2 text-xs font-semibold uppercase tracking-wide texte-doux"
            >
              {LIBELLES_JOURS[jour]}
            </h3>
            <ul className="space-y-2">
              {(parJour.get(jour) ?? []).map((creneau) => {
                const matiere = libelleMatiere(creneau.matiere_id);
                const enseignant = libelleEnseignant(creneau.enseignant_id);
                return (
                  <li
                    key={creneau.id}
                    className={cn('rounded-lg border-l-4 surface-douce px-3 py-2')}
                    style={{ borderLeftColor: couleurDe(creneau.matiere_id) }}
                  >
                    <p className="text-sm font-medium">{matiere}</p>
                    <p className="text-xs tabular-nums texte-doux">
                      {creneau.heure_debut.slice(0, 5)} – {creneau.heure_fin.slice(0, 5)}
                    </p>
                    {enseignant ? (
                      <p className="truncate text-xs texte-doux">{enseignant}</p>
                    ) : (
                      <p className="text-xs italic text-[rgb(var(--alerte))]">
                        Enseignant non affecté
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
