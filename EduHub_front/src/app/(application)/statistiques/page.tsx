'use client';

import { useQuery } from '@tanstack/react-query';
import { FileDown } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { GraphiqueBarres, GraphiqueLignes } from '@/components/graphiques';
import { Tableau } from '@/components/ui/donnees';
import {
  Bouton,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  MessageErreur,
  Selection,
} from '@/components/ui/primitives';
import { api, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterNombre, formaterNote, formaterPourcentage } from '@/lib/utils';
import type { SessionExamen } from '@/types/api';

interface SyntheseTerritoriale extends Record<string, unknown> {
  code: string;
  libelle: string;
  etablissements: number;
  apprenants: number;
  enseignants: number;
  candidats: number;
  admis: number;
  taux_reussite: number | null;
  moyenne: number | null;
}

export default function PageStatistiques() {
  const { peut } = useSession();
  const [sessionId, setSessionId] = useState('');
  const [rapport, setRapport] = useState<string | null>(null);

  const sessions = useQuery({
    queryKey: ['sessions-liste'],
    queryFn: () => api.get<Page<SessionExamen>>('/sessions', { size: 50 }),
  });

  const synthese = useQuery({
    queryKey: ['synthese-territoriale', sessionId],
    queryFn: () =>
      api.get<SyntheseTerritoriale[]>('/tableaux-de-bord/territoires', {
        session_examen_id: sessionId || undefined,
      }),
  });

  const evolution = useQuery({
    queryKey: ['comparaison-sessions'],
    queryFn: async () => {
      const liste = await api.get<Page<SessionExamen>>('/sessions', { size: 50 });
      return liste.items
        .filter((session) => session.taux_reussite !== null)
        .map((session) => ({
          session: session.code,
          annee: session.annee,
          taux_reussite: session.taux_reussite,
          moyenne: session.moyenne_generale,
        }));
    },
  });

  async function genererRapport() {
    const reponse = await api.post<{ id: string; reference: string }>('/rapports', {
      type_rapport: sessionId ? 'examen' : 'annuel',
      session_id: sessionId || undefined,
      format_export: 'PDF',
    });
    setRapport(reponse.id);
    await api.ouvrir(`/rapports/${reponse.id}/pdf`);
  }

  if (synthese.isLoading) return <Chargement libelle="Consolidation des statistiques…" />;
  if (synthese.isError) return <MessageErreur erreur={synthese.error} />;

  const donnees = synthese.data ?? [];

  return (
    <>
      <EntetePage
        titre="Statistiques nationales"
        description="Comparaison territoriale des effectifs, des résultats et des moyennes."
        actions={
          <>
            <Selection
              etiquette="Session d'examen"
              etiquetteMasquee
              value={sessionId}
              onChange={(evenement) => setSessionId(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Vue générale (hors examen)' },
                ...(sessions.data?.items ?? []).map((session) => ({
                  valeur: session.id,
                  libelle: session.libelle,
                })),
              ]}
              className="h-11"
            />
            {peut('rapports', 'CREATE') ? (
              <Bouton onClick={() => void genererRapport()} icone={<FileDown size={17} aria-hidden />}>
                Produire un rapport
              </Bouton>
            ) : null}
          </>
        }
      />

      {rapport ? (
        <div
          role="status"
          className="mb-4 rounded-lg border border-[rgb(var(--succes))]/40 bg-[rgb(var(--succes))]/8 px-4 py-3 text-sm"
        >
          Rapport généré et ouvert dans un nouvel onglet.
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <Carte>
          <EnteteCarte titre="Apprenants par département" />
          <CorpsCarte>
            <GraphiqueBarres
              titre="Apprenants par département"
              donnees={donnees}
              cleAbscisse="libelle"
              series={[{ cle: 'apprenants', libelle: 'Apprenants' }]}
              hauteur={280}
            />
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte titre="Évolution du taux de réussite" />
          <CorpsCarte>
            <GraphiqueLignes
              titre="Évolution du taux de réussite"
              donnees={evolution.data ?? []}
              cleAbscisse="session"
              series={[
                { cle: 'taux_reussite', libelle: 'Taux de réussite' },
                { cle: 'moyenne', libelle: 'Moyenne générale', couleur: '#16a153' },
              ]}
              hauteur={280}
              longueurEtiquette={14}
            />
          </CorpsCarte>
        </Carte>
      </div>

      <Carte className="mt-4">
        <EnteteCarte
          titre="Synthèse territoriale"
          description={
            sessionId
              ? "Résultats de la session sélectionnée, département par département."
              : 'Effectifs par département. Sélectionnez une session pour afficher les résultats.'
          }
        />
        <Tableau
          legende="Synthèse par département"
          lignes={donnees}
          cleLigne={(ligne) => ligne.code}
          colonnes={[
            { cle: 'departement', entete: 'Département', rendu: (ligne) => ligne.libelle },
            {
              cle: 'etablissements',
              entete: 'Établissements',
              alignement: 'droite',
              rendu: (ligne) => formaterNombre(ligne.etablissements),
            },
            {
              cle: 'apprenants',
              entete: 'Apprenants',
              alignement: 'droite',
              rendu: (ligne) => formaterNombre(ligne.apprenants),
            },
            {
              cle: 'candidats',
              entete: 'Candidats',
              alignement: 'droite',
              secondaire: true,
              rendu: (ligne) => formaterNombre(ligne.candidats),
            },
            {
              cle: 'admis',
              entete: 'Admis',
              alignement: 'droite',
              secondaire: true,
              rendu: (ligne) => formaterNombre(ligne.admis),
            },
            {
              cle: 'reussite',
              entete: 'Réussite',
              alignement: 'droite',
              rendu: (ligne) =>
                ligne.taux_reussite !== null ? (
                  <span
                    className={
                      ligne.taux_reussite >= 60
                        ? 'font-semibold text-[rgb(var(--succes))]'
                        : ligne.taux_reussite >= 40
                          ? 'font-semibold text-[rgb(var(--alerte))]'
                          : 'font-semibold text-[rgb(var(--danger))]'
                    }
                  >
                    {formaterPourcentage(ligne.taux_reussite)}
                  </span>
                ) : (
                  <span className="texte-doux">—</span>
                ),
            },
            {
              cle: 'moyenne',
              entete: 'Moyenne',
              alignement: 'droite',
              secondaire: true,
              rendu: (ligne) => formaterNote(ligne.moyenne),
            },
          ]}
        />
      </Carte>
    </>
  );
}
