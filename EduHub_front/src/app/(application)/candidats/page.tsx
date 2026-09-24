'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Selection, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterDate, humaniser } from '@/lib/utils';
import type { SessionExamen } from '@/types/api';

interface Candidat {
  id: string;
  numero_candidat: string;
  numero_table: string | null;
  nom_complet: string;
  sexe: string;
  date_naissance: string;
  type_candidature: string;
  statut_dossier: string;
  type_handicap: string;
  tiers_temps: boolean;
  statut_paiement: string;
}

export default function PageCandidats() {
  const [sessionId, setSessionId] = useState('');
  const [statut, setStatut] = useState('');

  const sessions = useQuery({
    queryKey: ['sessions-liste'],
    queryFn: () => api.get<Page<SessionExamen>>('/sessions', { size: 50 }),
  });

  const liste = useListe<Candidat>('/candidats', {
    tri: 'nom',
    filtres: { session_id: sessionId || undefined },
  });

  const items = statut
    ? liste.items.filter((candidat) => candidat.statut_dossier === statut)
    : liste.items;

  return (
    <>
      <EntetePage
        titre="Candidats"
        description="Dossiers de candidature aux examens et concours, de la soumission à la décision finale."
      />

      <ListeRessource
        legende="Liste des candidats"
        placeholderRecherche="Rechercher par nom, numéro de candidat ou numéro de table…"
        items={items}
        total={liste.total}
        pages={liste.pages}
        page={liste.etat.page}
        taille={liste.etat.taille}
        chargement={liste.isLoading}
        erreur={liste.error}
        recherche={liste.etat.recherche}
        onRecherche={liste.changerRecherche}
        onPage={liste.changerPage}
        cleLigne={(candidat) => candidat.id}
        videTitre="Aucun candidat"
        filtres={
          <div className="grid gap-4 sm:grid-cols-2">
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
            <Selection
              etiquette="Statut du dossier"
              value={statut}
              onChange={(evenement) => setStatut(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Tous les statuts' },
                ...[
                  'BROUILLON',
                  'SOUMIS',
                  'EN_ETUDE',
                  'INCOMPLET',
                  'REJETE',
                  'VALIDE',
                  'CONVOQUE',
                  'CORRIGE',
                  'ADMIS',
                  'NON_ADMIS',
                ].map((valeur) => ({ valeur, libelle: humaniser(valeur) })),
              ]}
            />
          </div>
        }
        colonnes={[
          {
            cle: 'numero',
            entete: 'Numéro',
            rendu: (candidat) => (
              <div className="min-w-0">
                <p className="font-mono text-xs">{candidat.numero_candidat}</p>
                {candidat.numero_table ? (
                  <p className="font-mono text-xs texte-doux">
                    Table {candidat.numero_table}
                  </p>
                ) : null}
              </div>
            ),
          },
          {
            cle: 'nom',
            entete: 'Nom et prénoms',
            rendu: (candidat) => (
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{candidat.nom_complet}</span>
                {candidat.tiers_temps ? <Badge ton="info">Tiers temps</Badge> : null}
              </span>
            ),
          },
          {
            cle: 'naissance',
            entete: 'Naissance',
            secondaire: true,
            rendu: (candidat) => formaterDate(candidat.date_naissance),
          },
          {
            cle: 'type',
            entete: 'Type',
            secondaire: true,
            rendu: (candidat) => (
              <Badge ton={candidat.type_candidature === 'LIBRE' ? 'alerte' : 'neutre'}>
                {humaniser(candidat.type_candidature)}
              </Badge>
            ),
          },
          {
            cle: 'statut',
            entete: 'Dossier',
            rendu: (candidat) => (
              <Badge ton={tonDuStatut(candidat.statut_dossier)}>
                {humaniser(candidat.statut_dossier)}
              </Badge>
            ),
          },
        ]}
      />
    </>
  );
}
