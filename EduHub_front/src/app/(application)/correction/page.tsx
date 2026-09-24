'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, FileStack, Percent, UserCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur, Jauge, Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Champ,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  Interrupteur,
  MessageErreur,
  Selection,
  tonDuStatut,
} from '@/components/ui/primitives';
import { api, ErreurApi, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterMontant, formaterNombre, formaterNote, humaniser } from '@/lib/utils';
import type { SessionExamen } from '@/types/api';

interface Epreuve {
  id: string;
  code: string;
  libelle: string;
  date_epreuve: string | null;
  duree_minutes: number;
  bareme: number;
  coefficient: number;
  note_eliminatoire: number | null;
}

interface Correcteur {
  id: string;
  code_correcteur: string;
  nom_complet: string;
  est_chef_correcteur: boolean;
  copies_attribuees: number;
  copies_corrigees: number;
  indemnite: number;
  actif: boolean;
}

interface Copie {
  id: string;
  code_anonymat: string;
  lot: string | null;
  correcteur_id: string | null;
  note_correcteur: number | null;
  note_second_correcteur: number | null;
  note_finale: number | null;
  double_correction: boolean;
  ecart_significatif: boolean;
  corrigee: boolean;
  validee: boolean;
}

interface NoteEpreuve {
  id: string;
  candidat_id: string;
  valeur: number | null;
  valeur_sur_20: number | null;
  coefficient: number;
  points: number | null;
  statut: string;
  validee: boolean;
  numero_candidat: string | null;
  nom_complet: string | null;
}

/** Écart au-delà duquel l'API déclenche une troisième lecture. */
const ECART_CRITIQUE = 3;

export default function PageCorrection() {
  const fileAttente = useQueryClient();
  const { peut } = useSession();

  const [sessionId, setSessionId] = useState('');
  const [epreuveId, setEpreuveId] = useState('');
  const [correcteurId, setCorrecteurId] = useState('');
  const [restantes, setRestantes] = useState(true);
  const [secondeLecture, setSecondeLecture] = useState(false);
  const [saisies, setSaisies] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const sessions = useQuery({
    queryKey: ['sessions-liste'],
    queryFn: () => api.get<Page<SessionExamen>>('/sessions', { size: 50 }),
  });

  const epreuves = useQuery({
    queryKey: ['epreuves-session', sessionId],
    queryFn: () => api.get<Epreuve[]>(`/sessions/${sessionId}/epreuves`),
    enabled: Boolean(sessionId),
  });

  const correcteurs = useQuery({
    queryKey: ['correcteurs-epreuve', epreuveId],
    queryFn: () =>
      api.get<Page<Correcteur>>('/correcteurs', { epreuve_id: epreuveId, size: 100 }),
    enabled: Boolean(epreuveId),
  });

  const copies = useQuery({
    queryKey: ['copies-epreuve', epreuveId, correcteurId, restantes],
    queryFn: () =>
      api.get<Page<Copie>>('/copies', {
        epreuve_id: epreuveId,
        correcteur_id: correcteurId || undefined,
        corrigee: restantes ? 'false' : undefined,
        size: 100,
        sort_by: 'code_anonymat',
      }),
    enabled: Boolean(epreuveId),
  });

  const notes = useQuery({
    queryKey: ['notes-epreuve', epreuveId],
    queryFn: () => api.get<NoteEpreuve[]>(`/epreuves/${epreuveId}/notes`),
    enabled: Boolean(epreuveId),
  });

  // Première session et première épreuve pré-sélectionnées : l'écran est
  // utilisable sans aucun réglage préalable.
  useEffect(() => {
    if (!sessionId && sessions.data?.items.length) setSessionId(sessions.data.items[0].id);
  }, [sessions.data, sessionId]);

  useEffect(() => {
    if (epreuves.data?.length) setEpreuveId((precedent) => precedent || epreuves.data[0].id);
  }, [epreuves.data]);

  const epreuve = useMemo(
    () => epreuves.data?.find((element) => element.id === epreuveId) ?? null,
    [epreuves.data, epreuveId],
  );

  const parCorrecteur = useMemo(
    () => new Map((correcteurs.data?.items ?? []).map((element) => [element.id, element])),
    [correcteurs.data],
  );

  function signaler(erreurBrute: unknown) {
    setMessage(null);
    setErreur(
      erreurBrute instanceof ErreurApi
        ? erreurBrute.message
        : "La correction n'a pas pu être enregistrée.",
    );
  }

  const corriger = useMutation({
    mutationFn: (variables: { copie: string; note: number }) =>
      api.post<Copie>(
        `/copies/${variables.copie}/corriger`,
        undefined,
        {
          parametres: {
            note: variables.note,
            second_correcteur: secondeLecture ? 'true' : 'false',
          },
        },
      ),
    onSuccess: (copie) => {
      setErreur(null);
      setMessage(
        copie.ecart_significatif
          ? `Copie ${copie.code_anonymat} : écart de plus de ${ECART_CRITIQUE} points entre les deux lectures, une troisième correction est requise.`
          : `Copie ${copie.code_anonymat} corrigée — note finale ${formaterNote(copie.note_finale)}.`,
      );
      setSaisies((precedent) => {
        const suivant = { ...precedent };
        delete suivant[copie.id];
        return suivant;
      });
      void fileAttente.invalidateQueries({ queryKey: ['copies-epreuve'] });
      void fileAttente.invalidateQueries({ queryKey: ['correcteurs-epreuve', epreuveId] });
    },
    onError: signaler,
  });

  const listeCopies = copies.data?.items ?? [];
  const listeCorrecteurs = correcteurs.data?.items ?? [];
  const attribuees = listeCorrecteurs.reduce((somme, c) => somme + c.copies_attribuees, 0);
  const corrigees = listeCorrecteurs.reduce((somme, c) => somme + c.copies_corrigees, 0);
  const ecarts = listeCopies.filter((copie) => copie.ecart_significatif).length;
  const autorise = peut('copies', 'UPDATE');

  return (
    <>
      <EntetePage
        titre="Correction des copies"
        description="Copies anonymées, double correction et notes définitives. L'identité du candidat n'apparaît qu'une fois la correction terminée."
      />

      {message ? (
        <p
          role="status"
          className="mb-4 rounded-lg border border-[rgb(var(--succes))]/40 bg-[rgb(var(--succes))]/10 px-4 py-3 text-sm"
        >
          {message}
        </p>
      ) : null}
      {erreur ? (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-[rgb(var(--danger))]/40 bg-[rgb(var(--danger))]/10 px-4 py-3 text-sm"
        >
          {erreur}
        </p>
      ) : null}

      <Carte className="mb-4">
        <EnteteCarte titre="Épreuve à corriger" />
        <CorpsCarte className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Selection
            etiquette="Session"
            value={sessionId}
            onChange={(evenement) => {
              setSessionId(evenement.target.value);
              setEpreuveId('');
              setCorrecteurId('');
            }}
            options={(sessions.data?.items ?? []).map((session) => ({
              valeur: session.id,
              libelle: session.libelle,
            }))}
          />
          <Selection
            etiquette="Épreuve"
            value={epreuveId}
            onChange={(evenement) => {
              setEpreuveId(evenement.target.value);
              setCorrecteurId('');
            }}
            options={
              epreuves.data?.length
                ? epreuves.data.map((element) => ({
                    valeur: element.id,
                    libelle: `${element.libelle} — barème /${element.bareme}`,
                  }))
                : [{ valeur: '', libelle: 'Aucune épreuve programmée' }]
            }
          />
          <Selection
            etiquette="Correcteur"
            value={correcteurId}
            onChange={(evenement) => setCorrecteurId(evenement.target.value)}
            options={[
              { valeur: '', libelle: 'Tous les correcteurs' },
              ...listeCorrecteurs.map((element) => ({
                valeur: element.id,
                libelle: `${element.nom_complet} (${element.code_correcteur})`,
              })),
            ]}
          />
          <div className="flex flex-col justify-center gap-2">
            <Interrupteur
              etiquette="Copies restant à corriger"
              actif={restantes}
              onChange={() => setRestantes((precedent) => !precedent)}
            />
            <Interrupteur
              etiquette="Seconde lecture"
              description="La note saisie est celle du second correcteur."
              actif={secondeLecture}
              onChange={() => setSecondeLecture((precedent) => !precedent)}
            />
          </div>
        </CorpsCarte>
      </Carte>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Indicateur
          libelle="Copies attribuées"
          valeur={attribuees}
          icone={<FileStack size={19} aria-hidden />}
          pictogramme="📚"
        />
        <Indicateur
          libelle="Copies corrigées"
          valeur={corrigees}
          icone={<CheckCircle2 size={19} aria-hidden />}
          pictogramme="✅"
        />
        <Indicateur
          libelle="Avancement"
          valeur={attribuees > 0 ? `${formaterNombre((corrigees / attribuees) * 100, 1)} %` : '—'}
          icone={<Percent size={19} aria-hidden />}
          pictogramme="📈"
        />
        <Indicateur
          libelle="Écarts significatifs"
          valeur={ecarts}
          unite={`≥ ${ECART_CRITIQUE} points`}
          icone={<AlertTriangle size={19} aria-hidden />}
          pictogramme="⚠️"
        />
      </div>

      <div className="grid gap-4">
        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <UserCheck size={19} aria-hidden /> Correcteurs de l&apos;épreuve
              </span>
            }
            description="Cliquez sur un correcteur pour ne voir que ses copies."
          />
          {correcteurs.isLoading ? (
            <CorpsCarte>
              <Chargement libelle="Chargement des correcteurs…" />
            </CorpsCarte>
          ) : (
            <Tableau
              legende="Correcteurs affectés à l'épreuve"
              lignes={listeCorrecteurs}
              cleLigne={(element) => element.id}
              onLigneClic={(element) =>
                setCorrecteurId(element.id === correcteurId ? '' : element.id)
              }
              vide={<EtatVide titre="Aucun correcteur affecté à cette épreuve" />}
              colonnes={[
                {
                  cle: 'nom',
                  entete: 'Correcteur',
                  rendu: (element) => (
                    <span className="min-w-0">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="truncate font-medium">{element.nom_complet}</span>
                        {element.est_chef_correcteur ? (
                          <Badge ton="info">Chef correcteur</Badge>
                        ) : null}
                      </span>
                      <span className="block font-mono text-xs texte-doux">
                        {element.code_correcteur}
                      </span>
                    </span>
                  ),
                },
                {
                  cle: 'avancement',
                  entete: 'Avancement',
                  largeur: '40%',
                  rendu: (element) => (
                    <Jauge
                      valeur={element.copies_corrigees}
                      maximum={element.copies_attribuees || 1}
                      etiquette={`${formaterNombre(element.copies_corrigees)} sur ${formaterNombre(element.copies_attribuees)}`}
                      ton={
                        element.copies_corrigees >= element.copies_attribuees ? 'succes' : 'accent'
                      }
                    />
                  ),
                },
                {
                  cle: 'indemnite',
                  entete: 'Indemnité',
                  alignement: 'droite',
                  secondaire: true,
                  rendu: (element) => formaterMontant(element.indemnite),
                },
              ]}
            />
          )}
        </Carte>

        <Carte>
          <EnteteCarte
            titre="Copies anonymées"
            description={
              epreuve
                ? `Barème /${epreuve.bareme}, coefficient ${epreuve.coefficient}${
                    epreuve.note_eliminatoire != null
                      ? `, note éliminatoire en dessous de ${formaterNote(epreuve.note_eliminatoire)}/20`
                      : ''
                  }.`
                : 'Choisissez une épreuve.'
            }
            action={
              copies.data ? (
                <Badge ton="neutre">{formaterNombre(copies.data.total)} copie(s)</Badge>
              ) : null
            }
          />
          {copies.isLoading ? (
            <CorpsCarte>
              <Chargement libelle="Chargement des copies…" />
            </CorpsCarte>
          ) : copies.isError ? (
            <CorpsCarte>
              <MessageErreur erreur={copies.error} />
            </CorpsCarte>
          ) : (
            <Tableau
              legende="Copies anonymées de l'épreuve"
              lignes={listeCopies}
              cleLigne={(copie) => copie.id}
              vide={
                <EtatVide
                  titre={restantes ? 'Toutes les copies sont corrigées' : 'Aucune copie'}
                  description={
                    restantes
                      ? 'Décochez « Copies restant à corriger » pour revoir les copies déjà notées.'
                      : undefined
                  }
                />
              }
              colonnes={[
                {
                  cle: 'anonymat',
                  entete: 'Anonymat',
                  rendu: (copie) => (
                    <span className="min-w-0">
                      <span className="block font-mono font-medium">{copie.code_anonymat}</span>
                      <span className="block text-xs texte-doux">
                        {copie.lot ? `Lot ${copie.lot}` : '—'}
                        {copie.correcteur_id
                          ? ` · ${parCorrecteur.get(copie.correcteur_id)?.code_correcteur ?? ''}`
                          : ''}
                      </span>
                    </span>
                  ),
                },
                {
                  cle: 'lectures',
                  entete: 'Lectures',
                  alignement: 'droite',
                  secondaire: true,
                  rendu: (copie) => (
                    <span className="min-w-0">
                      <span className="block">
                        {copie.note_correcteur != null ? formaterNote(copie.note_correcteur) : '—'}
                      </span>
                      <span className="block text-xs texte-doux">
                        {copie.note_second_correcteur != null
                          ? `2ᵉ : ${formaterNote(copie.note_second_correcteur)}`
                          : '2ᵉ : —'}
                      </span>
                    </span>
                  ),
                },
                {
                  cle: 'finale',
                  entete: 'Note finale',
                  alignement: 'droite',
                  rendu: (copie) => (
                    <span className="font-medium">
                      {copie.note_finale != null ? formaterNote(copie.note_finale) : '—'}
                    </span>
                  ),
                },
                {
                  cle: 'saisie',
                  entete: secondeLecture ? 'Seconde lecture' : 'Première lecture',
                  largeur: '16rem',
                  rendu: (copie) => (
                    <div className="flex items-center gap-2">
                      <Champ
                        etiquette={`Note de la copie ${copie.code_anonymat}`}
                        etiquetteMasquee
                        type="number"
                        min={0}
                        max={epreuve?.bareme ?? 20}
                        step="0.25"
                        disabled={!autorise}
                        value={saisies[copie.id] ?? ''}
                        placeholder={`/${epreuve?.bareme ?? 20}`}
                        onChange={(evenement) =>
                          setSaisies((precedent) => ({
                            ...precedent,
                            [copie.id]: evenement.target.value,
                          }))
                        }
                        className="text-right"
                      />
                      <Bouton
                        taille="sm"
                        variante="secondaire"
                        disabled={!autorise || saisies[copie.id] === undefined || saisies[copie.id] === ''}
                        chargement={corriger.isPending && corriger.variables?.copie === copie.id}
                        onClick={() =>
                          corriger.mutate({ copie: copie.id, note: Number(saisies[copie.id]) })
                        }
                      >
                        Noter
                      </Bouton>
                    </div>
                  ),
                },
                {
                  cle: 'etat',
                  entete: 'État',
                  rendu: (copie) => (
                    <span className="flex flex-wrap gap-1.5">
                      <Badge ton={copie.corrigee ? 'succes' : 'neutre'}>
                        {copie.corrigee ? 'Corrigée' : 'À corriger'}
                      </Badge>
                      {copie.double_correction ? <Badge ton="info">Double correction</Badge> : null}
                      {copie.ecart_significatif ? (
                        <Badge ton="danger">
                          <AlertTriangle size={13} aria-hidden /> Écart
                        </Badge>
                      ) : null}
                    </span>
                  ),
                },
              ]}
            />
          )}
        </Carte>
      </div>

      <Carte className="mt-4">
        <EnteteCarte
          titre="Notes définitives de l'épreuve"
          description="Après correction, la note est rattachée au candidat et ramenée sur 20 pour le calcul de la moyenne."
          action={
            notes.data ? (
              <Badge ton="neutre">{formaterNombre(notes.data.length)} note(s)</Badge>
            ) : null
          }
        />
        {notes.isLoading ? (
          <CorpsCarte>
            <Chargement libelle="Chargement des notes…" />
          </CorpsCarte>
        ) : (
          <Tableau
            legende="Notes définitives des candidats à l'épreuve"
            lignes={(notes.data ?? []).slice(0, 100)}
            cleLigne={(note) => note.id}
            vide={<EtatVide titre="Aucune note enregistrée pour cette épreuve" />}
            colonnes={[
              {
                cle: 'candidat',
                entete: 'Candidat',
                rendu: (note) => (
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{note.nom_complet ?? '—'}</span>
                    <span className="block font-mono text-xs texte-doux">
                      {note.numero_candidat ?? ''}
                    </span>
                  </span>
                ),
              },
              {
                cle: 'valeur',
                entete: `Note /${epreuve?.bareme ?? 20}`,
                alignement: 'droite',
                rendu: (note) => (note.valeur != null ? formaterNote(note.valeur) : '—'),
              },
              {
                cle: 'sur20',
                entete: 'Sur 20',
                alignement: 'droite',
                rendu: (note) =>
                  note.valeur_sur_20 != null ? formaterNote(note.valeur_sur_20) : '—',
              },
              {
                cle: 'coefficient',
                entete: 'Coef.',
                alignement: 'droite',
                secondaire: true,
                rendu: (note) => note.coefficient,
              },
              {
                cle: 'points',
                entete: 'Points',
                alignement: 'droite',
                secondaire: true,
                rendu: (note) => (note.points != null ? formaterNote(note.points) : '—'),
              },
              {
                cle: 'statut',
                entete: 'Statut',
                rendu: (note) => (
                  <span className="flex flex-wrap gap-1.5">
                    <Badge ton={tonDuStatut(note.statut)}>{humaniser(note.statut)}</Badge>
                    {note.validee ? <Badge ton="succes">Validée</Badge> : null}
                  </span>
                ),
              },
            ]}
          />
        )}
        {notes.data && notes.data.length > 100 ? (
          <CorpsCarte className="border-t">
            <p className="text-sm texte-doux">
              Les 100 premières notes sont affichées sur {formaterNombre(notes.data.length)}. Le
              relevé complet s&apos;exporte depuis la session d&apos;examen.
            </p>
          </CorpsCarte>
        ) : null}
      </Carte>
    </>
  );
}
