'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { UsersRound } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeRessource } from '@/components/ui/liste';
import {
  Badge,
  Bouton,
  Carte,
  CorpsCarte,
  EnteteCarte,
  Selection,
  tonDuStatut,
} from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, ErreurApi, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
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

interface ClasseSimple {
  id: string;
  code: string;
  libelle: string;
  effectif: number;
}

export default function PageCandidats() {
  const router = useRouter();
  const fileAttente = useQueryClient();
  const { peut } = useSession();
  const [classeId, setClasseId] = useState('');
  const [journal, setJournal] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState('');
  const [statut, setStatut] = useState('');

  const sessions = useQuery({
    queryKey: ['sessions-liste'],
    queryFn: () => api.get<Page<SessionExamen>>('/sessions', { size: 50 }),
  });

  // Les deux filtres sont appliqués par l'API : le total et la pagination
  // restent donc cohérents avec la sélection.
  const classes = useQuery({
    queryKey: ['classes-inscription'],
    queryFn: () => api.get<Page<ClasseSimple>>('/classes', { size: 200, sort_by: 'libelle' }),
  });

  const inscrireClasse = useMutation({
    mutationFn: () =>
      api.post<{ message: string }>('/candidats/inscription-classe', {
        session_id: sessionId,
        classe_id: classeId,
      }),
    onSuccess: (reponse) => {
      setJournal(reponse.message);
      setClasseId('');
      void fileAttente.invalidateQueries({ queryKey: ['/candidats'] });
    },
    onError: (erreurBrute: unknown) => {
      setJournal(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "L'inscription collective n'a pas pu être enregistrée.",
      );
    },
  });

  const liste = useListe<Candidat>('/candidats', {
    tri: 'nom',
    filtres: {
      session_id: sessionId || undefined,
      statut_dossier: statut || undefined,
    },
  });

  return (
    <>
      <EntetePage
        titre="Candidats"
        description="Dossiers de candidature aux examens et concours, de la soumission à la décision finale."
      />

      {peut('candidats', 'CREATE') ? (
        <Carte className="mb-4">
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <UsersRound size={19} aria-hidden /> Inscrire une classe entière
              </span>
            }
            description="Présente d'un seul geste tous les élèves d'une classe à la session choisie. Les élèves déjà inscrits sont ignorés."
          />
          <CorpsCarte>
            <div className="grid gap-3 sm:grid-cols-2">
              <Selection
                etiquette="Session d'examen"
                aide="Reprend la session sélectionnée dans les filtres de la liste."
                value={sessionId}
                onChange={(evenement) => setSessionId(evenement.target.value)}
                options={[
                  { valeur: '', libelle: 'Choisir une session…' },
                  ...(sessions.data?.items ?? []).map((session) => ({
                    valeur: session.id,
                    libelle: session.libelle,
                  })),
                ]}
              />
              <Selection
                etiquette="Classe"
                value={classeId}
                onChange={(evenement) => setClasseId(evenement.target.value)}
                options={[
                  { valeur: '', libelle: 'Choisir une classe…' },
                  ...(classes.data?.items ?? []).map((classe) => ({
                    valeur: classe.id,
                    libelle: `${classe.libelle} (${classe.effectif} élèves)`,
                  })),
                ]}
              />
            </div>
            <Bouton
              className="mt-3"
              disabled={!sessionId || !classeId}
              chargement={inscrireClasse.isPending}
              onClick={() => inscrireClasse.mutate()}
            >
              Inscrire la classe
            </Bouton>
            {journal ? (
              <p role="status" className="mt-2 text-sm texte-doux">
                {journal}
              </p>
            ) : null}
          </CorpsCarte>
        </Carte>
      ) : null}

      <ListeRessource
        legende="Liste des candidats"
        placeholderRecherche="Rechercher par nom, numéro de candidat ou numéro de table…"
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
        cleLigne={(candidat) => candidat.id}
        onLigneClic={(candidat) => router.push(`/candidats/${candidat.id}`)}
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
                  <p className="font-mono text-xs texte-doux">Table {candidat.numero_table}</p>
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
