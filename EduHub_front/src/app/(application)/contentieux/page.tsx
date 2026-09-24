'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Gavel } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import {
  Badge,
  Bouton,
  Carte,
  Champ,
  CorpsCarte,
  EnteteCarte,
  MessageErreur,
  Selection,
  tonDuStatut,
} from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterDate, formaterNote, humaniser } from '@/lib/utils';
import { useSession } from '@/lib/session';
import type { SessionExamen } from '@/types/api';

interface Contentieux {
  id: string;
  numero: string;
  session_id: string;
  candidat_id: string;
  type_contentieux: string;
  objet: string;
  expose: string;
  statut: string;
  date_depot: string;
  date_decision: string | null;
  conclusion: string | null;
  note_avant: number | null;
  note_apres: number | null;
  decision_revisee: string | null;
}

const STATUTS = [
  'DEPOSEE',
  'RECEVABLE',
  'IRRECEVABLE',
  'EN_INSTRUCTION',
  'TRANCHEE_FAVORABLE',
  'TRANCHEE_DEFAVORABLE',
  'CLOTUREE',
];

export default function PageContentieux() {
  const { peut } = useSession();
  const client = useQueryClient();
  const [sessionId, setSessionId] = useState('');
  const [enInstruction, setEnInstruction] = useState<Contentieux | null>(null);
  const [statut, setStatut] = useState('TRANCHEE_FAVORABLE');
  const [conclusion, setConclusion] = useState('');
  const [noteApres, setNoteApres] = useState('');

  const sessions = useQuery({
    queryKey: ['sessions-liste'],
    queryFn: () => api.get<Page<SessionExamen>>('/sessions', { size: 50 }),
  });

  const liste = useListe<Contentieux>('/contentieux', {
    tri: 'date_depot',
    filtres: { session_id: sessionId || undefined },
  });

  const instruction = useMutation({
    mutationFn: () =>
      api.post(`/contentieux/${enInstruction!.id}/instruire`, {
        statut,
        conclusion: conclusion || undefined,
        note_apres: noteApres ? Number(noteApres.replace(',', '.')) : undefined,
        decision_revisee: statut === 'TRANCHEE_FAVORABLE' ? 'ADMIS' : undefined,
      }),
    onSuccess: () => {
      setEnInstruction(null);
      setConclusion('');
      setNoteApres('');
      void client.invalidateQueries({ queryKey: ['/contentieux'] });
    },
  });

  const parStatut = liste.items.reduce<Record<string, number>>((compteur, dossier) => {
    compteur[dossier.statut] = (compteur[dossier.statut] ?? 0) + 1;
    return compteur;
  }, {});

  return (
    <>
      <EntetePage
        titre="Contentieux des examens"
        description="Réclamations des candidats, leur instruction et la révision éventuelle des notes et décisions."
      />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicateur
          libelle="Réclamations"
          valeur={liste.total}
          icone={<Gavel size={18} />}
          pictogramme="⚖️"
        />
        <Indicateur
          libelle="En instruction"
          valeur={(parStatut.EN_INSTRUCTION ?? 0) + (parStatut.DEPOSEE ?? 0)}
          pictogramme="🔎"
        />
        <Indicateur
          libelle="Tranchées favorablement"
          valeur={parStatut.TRANCHEE_FAVORABLE ?? 0}
          pictogramme="✅"
        />
        <Indicateur
          libelle="Tranchées défavorablement"
          valeur={parStatut.TRANCHEE_DEFAVORABLE ?? 0}
          pictogramme="❌"
        />
      </div>

      {enInstruction ? (
        <Carte className="mb-4">
          <EnteteCarte
            titre={`Instruire la réclamation ${enInstruction.numero}`}
            description={enInstruction.objet}
            action={
              <button
                type="button"
                onClick={() => setEnInstruction(null)}
                className="text-sm font-medium hover:underline"
              >
                Annuler
              </button>
            }
          />
          <CorpsCarte className="space-y-4">
            <p className="rounded-lg surface-douce px-3 py-2.5 text-sm">
              {enInstruction.expose}
            </p>
            <div className="grid gap-4 sm:grid-cols-3">
              <Selection
                etiquette="Décision"
                value={statut}
                onChange={(evenement) => setStatut(evenement.target.value)}
                options={STATUTS.map((valeur) => ({ valeur, libelle: humaniser(valeur) }))}
              />
              <Champ
                etiquette="Note révisée"
                type="text"
                inputMode="decimal"
                value={noteApres}
                onChange={(evenement) => setNoteApres(evenement.target.value)}
                placeholder="Sur 20"
                aide="À renseigner uniquement en cas de décision favorable."
              />
              <Champ
                etiquette="Conclusion"
                value={conclusion}
                onChange={(evenement) => setConclusion(evenement.target.value)}
                placeholder="Motivation de la décision"
              />
            </div>
            {instruction.isError ? <MessageErreur erreur={instruction.error} /> : null}
            <Bouton onClick={() => instruction.mutate()} chargement={instruction.isPending}>
              Enregistrer la décision
            </Bouton>
          </CorpsCarte>
        </Carte>
      ) : null}

      <ListeRessource
        legende="Réclamations déposées"
        placeholderRecherche="Rechercher par numéro ou objet…"
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
        cleLigne={(dossier) => dossier.id}
        videTitre="Aucune réclamation"
        videDescription="Les candidats peuvent contester leur résultat jusqu'à la date limite de la session."
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
            cle: 'numero',
            entete: 'Réclamation',
            rendu: (dossier) => (
              <div className="min-w-0">
                <p className="font-mono text-xs">{dossier.numero}</p>
                <p className="truncate text-sm font-medium">{dossier.objet}</p>
              </div>
            ),
          },
          {
            cle: 'type',
            entete: 'Motif',
            secondaire: true,
            rendu: (dossier) => (
              <Badge ton="neutre">{humaniser(dossier.type_contentieux)}</Badge>
            ),
          },
          {
            cle: 'depot',
            entete: 'Déposée le',
            secondaire: true,
            rendu: (dossier) => formaterDate(dossier.date_depot),
          },
          {
            cle: 'notes',
            entete: 'Note',
            alignement: 'droite',
            rendu: (dossier) =>
              dossier.note_apres !== null ? (
                <span className="tabular-nums">
                  <span className="texte-doux line-through">
                    {formaterNote(dossier.note_avant)}
                  </span>{' '}
                  <span className="font-semibold text-[rgb(var(--succes))]">
                    {formaterNote(dossier.note_apres)}
                  </span>
                </span>
              ) : (
                formaterNote(dossier.note_avant)
              ),
          },
          {
            cle: 'statut',
            entete: 'Statut',
            rendu: (dossier) => (
              <Badge ton={tonDuStatut(dossier.statut)}>{humaniser(dossier.statut)}</Badge>
            ),
          },
          {
            cle: 'action',
            entete: 'Instruction',
            alignement: 'centre',
            rendu: (dossier) =>
              peut('contentieux', 'VALIDATE') ? (
                <Bouton
                  variante="fantome"
                  taille="sm"
                  onClick={() => {
                    setEnInstruction(dossier);
                    setConclusion(dossier.conclusion ?? '');
                    setNoteApres('');
                  }}
                >
                  Instruire
                </Bouton>
              ) : (
                <span className="texte-doux">—</span>
              ),
          },
        ]}
      />
    </>
  );
}
