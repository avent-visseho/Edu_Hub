'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';

import { libelleEntree, NAVIGATION } from '@/components/layout/navigation';
import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur } from '@/components/ui/donnees';
import { Carte, CorpsCarte, EnteteCarte, Squelette } from '@/components/ui/primitives';
import { api } from '@/lib/api';
import { useSession } from '@/lib/session';
import type { TableauBord } from '@/types/api';

/** Phrase d'accueil propre au rôle, pour situer d'emblée ce qu'on peut faire. */
const INTRODUCTIONS: Record<string, string> = {
  STUDENT: 'Vos classes, vos notes, vos bulletins et votre vie étudiante.',
  PARENT: 'Le suivi scolaire de vos enfants : notes, bulletins, assiduité.',
  TEACHER: 'Vos classes, vos évaluations et la saisie de vos notes.',
  SCHOOL_ADMIN: 'La vie de votre établissement : effectifs, personnels, inscriptions.',
  CANDIDATE: 'Vos candidatures aux examens et concours, et vos résultats.',
  CORRECTOR: 'Vos lots de copies à corriger.',
  RESEARCHER: 'Vos projets de recherche et vos laboratoires.',
};

/**
 * Accueil des comptes qui n'ont pas accès aux indicateurs nationaux.
 *
 * Le tableau de bord national consolide des chiffres réservés au pilotage :
 * un élève, un parent ou un enseignant n'a pas la permission analytics:READ et
 * recevait donc une erreur en guise de page d'accueil. Plutôt que de masquer
 * l'entrée du menu — ce qui les aurait laissés sans point de départ — on leur
 * présente ce à quoi leur rôle donne accès.
 *
 * La liste n'est pas écrite en dur : elle reprend la navigation, filtrée par
 * les permissions réellement accordées. Ajouter une rubrique à l'application la
 * fait apparaître ici pour qui y a droit, sans rien changer à ce fichier.
 */
export function AccueilPersonnel() {
  const { utilisateur, peut } = useSession();

  // Les indicateurs du rôle : la moyenne et l'assiduité d'un élève, le suivi
  // des enfants d'un parent, les classes d'un enseignant. L'API les compose
  // dans le périmètre de l'appelant ; rien n'est à filtrer ici.
  const tableau = useQuery({
    queryKey: ['mon-tableau'],
    queryFn: () => api.get<TableauBord>('/tableaux-de-bord/mon-tableau'),
  });

  const roles = utilisateur?.roles ?? [];
  const introduction =
    roles.map((role) => INTRODUCTIONS[role]).find(Boolean) ??
    'Voici les espaces auxquels votre compte donne accès.';

  const groupes = NAVIGATION.map((groupe) => ({
    ...groupe,
    entrees: groupe.entrees.filter((entree) => {
      // L'accueil lui-même n'a pas à figurer parmi les destinations proposées.
      if (entree.href === '/tableau-de-bord') return false;
      if (!entree.permission) return true;
      const [ressource, action] = entree.permission.split(':');
      return peut(ressource, action);
    }),
  })).filter((groupe) => groupe.entrees.length > 0);

  return (
    <>
      <EntetePage
        titre={`Bonjour ${utilisateur?.prenoms ?? ''}`.trim()}
        description={introduction}
      />

      {tableau.isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {[0, 1, 2, 3, 4].map((rang) => (
            <Squelette key={rang} className="h-24" />
          ))}
        </div>
      )}

      {tableau.data && tableau.data.indicateurs.length > 0 && (
        <div className="mb-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {tableau.data.indicateurs.map((indicateur) => (
            <Indicateur
              key={indicateur.code}
              libelle={indicateur.libelle}
              valeur={indicateur.valeur}
              unite={indicateur.unite}
            />
          ))}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {groupes.map((groupe) => (
          <Carte key={groupe.titre}>
            <EnteteCarte titre={groupe.titre} />
            <CorpsCarte>
              <ul className="space-y-0.5">
                {groupe.entrees.map((entree) => {
                  const Icone = entree.icone;
                  return (
                    <li key={entree.href}>
                      <Link
                        href={entree.href}
                        className="flex items-center gap-2.5 rounded-lg px-2 py-2 text-sm transition hover:bg-[rgb(var(--fond-doux))]"
                      >
                        <Icone size={18} aria-hidden className="shrink-0 texte-doux" />
                        {libelleEntree(entree, utilisateur?.niveau_scope ?? '', roles)}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </CorpsCarte>
          </Carte>
        ))}
      </div>

      {groupes.length === 0 && (
        <Carte>
          <CorpsCarte>
            <p className="text-sm texte-doux">
              Aucun espace n&apos;est ouvert à ce compte. Rapprochez-vous de votre administration
              pour qu&apos;un rôle lui soit attribué.
            </p>
          </CorpsCarte>
        </Carte>
      )}
    </>
  );
}
