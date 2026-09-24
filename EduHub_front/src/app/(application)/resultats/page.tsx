'use client';

import { useQuery } from '@tanstack/react-query';
import { Download, Printer } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Bouton, Selection, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterNote, humaniser } from '@/lib/utils';
import type { SessionExamen } from '@/types/api';

interface Resultat {
  id: string;
  session_id: string;
  candidat_id: string;
  moyenne: number | null;
  mention: string | null;
  decision: string;
  rang_national: number | null;
  rang_departemental: number | null;
  repeche: boolean;
  publie: boolean;
}

export default function PageResultats() {
  const [sessionId, setSessionId] = useState('');

  const sessions = useQuery({
    queryKey: ['sessions-liste'],
    queryFn: () => api.get<Page<SessionExamen>>('/sessions', { size: 50 }),
  });

  const liste = useListe<Resultat>('/resultats', {
    tri: 'rang_national',
    filtres: { session_id: sessionId || undefined },
  });

  return (
    <>
      <EntetePage
        titre="Résultats d'examen"
        description="Résultats délibérés, avec moyennes, mentions, rangs et repêchages du jury."
        actions={
          sessionId ? (
            <Bouton
              variante="secondaire"
              onClick={() =>
                void api.telecharger(
                  `/resultats/session/${sessionId}/export`,
                  'resultats-session.csv',
                )
              }
              icone={<Download size={17} aria-hidden />}
            >
              Exporter
            </Bouton>
          ) : null
        }
      />

      <ListeRessource
        legende="Liste des résultats"
        placeholderRecherche="Filtrer les résultats…"
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
        cleLigne={(resultat) => resultat.id}
        videTitre="Aucun résultat"
        videDescription="Délibérez une session pour produire ses résultats."
        filtres={
          <Selection
            etiquette="Session"
            value={sessionId}
            onChange={(evenement) => setSessionId(evenement.target.value)}
            options={[
              { valeur: '', libelle: 'Toutes les sessions' },
              ...(sessions.data?.items ?? []).map((session) => ({
                valeur: session.id,
                libelle: session.libelle,
              })),
            ]}
          />
        }
        colonnes={[
          {
            cle: 'rang',
            entete: 'Rang',
            alignement: 'droite',
            rendu: (resultat) => (
              <span className="font-semibold tabular-nums">{resultat.rang_national ?? '—'}</span>
            ),
          },
          {
            cle: 'moyenne',
            entete: 'Moyenne',
            alignement: 'droite',
            rendu: (resultat) => (
              <span className="font-semibold tabular-nums">{formaterNote(resultat.moyenne)}</span>
            ),
          },
          {
            cle: 'mention',
            entete: 'Mention',
            rendu: (resultat) =>
              resultat.mention ? <Badge ton="succes">{resultat.mention}</Badge> : '—',
          },
          {
            cle: 'decision',
            entete: 'Décision',
            rendu: (resultat) => (
              <span className="flex flex-wrap items-center gap-2">
                <Badge ton={tonDuStatut(resultat.decision)}>{humaniser(resultat.decision)}</Badge>
                {resultat.repeche ? <Badge ton="alerte">Repêché</Badge> : null}
              </span>
            ),
          },
          {
            cle: 'rang_dep',
            entete: 'Rang départemental',
            alignement: 'droite',
            secondaire: true,
            rendu: (resultat) => resultat.rang_departemental ?? '—',
          },
          {
            cle: 'actions',
            entete: 'Relevé',
            alignement: 'centre',
            rendu: (resultat) => (
              <Bouton
                variante="fantome"
                taille="sm"
                aria-label="Imprimer le relevé de notes"
                onClick={() => void api.ouvrir(`/resultats/${resultat.id}/releve`)}
              >
                <Printer size={16} aria-hidden />
              </Bouton>
            ),
          },
        ]}
      />
    </>
  );
}
