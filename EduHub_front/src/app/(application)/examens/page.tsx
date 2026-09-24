'use client';

import { useRouter } from 'next/navigation';

import { EntetePage } from '@/components/layout/entete-page';
import { Jauge } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { formaterNombre, formaterNote, formaterPourcentage, humaniser } from '@/lib/utils';
import type { SessionExamen } from '@/types/api';

export default function PageExamens() {
  const router = useRouter();
  const liste = useListe<SessionExamen>('/sessions', { tri: 'annee' });

  return (
    <>
      <EntetePage
        titre="Sessions d'examen et de concours"
        description="Pilotage complet : candidatures, centres, surveillance, correction, délibération et résultats."
      />

      <ListeRessource
        legende="Liste des sessions d'examen"
        placeholderRecherche="Rechercher une session…"
        items={liste.items}
        total={liste.total}
        pages={liste.pages}
        page={liste.etat.page}
        taille={liste.etat.taille}
        chargement={liste.isLoading}
        erreur={liste.error}
        recherche={liste.etat.recherche}
        onRecherche={liste.changerRecherche}
        onPage={liste.changerPage}
        cleLigne={(session) => session.id}
        onLigneClic={(session) => router.push(`/examens/${session.id}`)}
        videTitre="Aucune session"
        colonnes={[
          {
            cle: 'libelle',
            entete: 'Session',
            rendu: (session) => (
              <div className="min-w-0">
                <p className="font-medium">{session.libelle}</p>
                <p className="truncate font-mono text-xs texte-doux">{session.code}</p>
              </div>
            ),
          },
          {
            cle: 'statut',
            entete: 'Étape',
            rendu: (session) => (
              <Badge ton={tonDuStatut(session.statut)}>{humaniser(session.statut)}</Badge>
            ),
          },
          {
            cle: 'inscrits',
            entete: 'Inscrits',
            alignement: 'droite',
            rendu: (session) => formaterNombre(session.nombre_inscrits),
          },
          {
            cle: 'admis',
            entete: 'Admis',
            alignement: 'droite',
            secondaire: true,
            rendu: (session) => formaterNombre(session.nombre_admis),
          },
          {
            cle: 'reussite',
            entete: 'Taux de réussite',
            largeur: '14rem',
            rendu: (session) =>
              session.taux_reussite !== null ? (
                <Jauge
                  valeur={session.taux_reussite}
                  etiquette={formaterPourcentage(session.taux_reussite)}
                  ton={
                    session.taux_reussite >= 70
                      ? 'succes'
                      : session.taux_reussite >= 50
                        ? 'alerte'
                        : 'danger'
                  }
                />
              ) : (
                <span className="texte-doux">—</span>
              ),
          },
          {
            cle: 'moyenne',
            entete: 'Moyenne',
            alignement: 'droite',
            secondaire: true,
            rendu: (session) => formaterNote(session.moyenne_generale),
          },
        ]}
      />
    </>
  );
}
