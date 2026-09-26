'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Save, Send } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Chargement,
  EnteteCarte,
  MessageErreur,
  tonDuStatut,
} from '@/components/ui/primitives';
import { api } from '@/lib/api';
import { useSession } from '@/lib/session';
import { cn, formaterDate, formaterNote, humaniser } from '@/lib/utils';

interface Evaluation {
  id: string;
  code: string;
  intitule: string;
  classe_id: string;
  classe_libelle: string | null;
  matiere_id: string;
  matiere_libelle: string | null;
  periode_id: string;
  periode_libelle: string | null;
  type_evaluation: string;
  date_evaluation: string;
  bareme: number;
  coefficient: number;
  statut: string;
  moyenne: number | null;
  note_min: number | null;
  note_max: number | null;
  ecart_type: number | null;
  nombre_notes: number;
}

interface ApprenantClasse {
  id: string;
  identifiant_educatif: string;
  nom_complet: string;
  tiers_temps: boolean;
}

interface Note {
  id: string;
  apprenant_id: string;
  valeur: number | null;
  statut: string;
  appreciation: string | null;
  rang: number | null;
}

/** Statuts de note autres que la saisie d'une valeur chiffrée. */
const STATUTS_SANS_NOTE = [
  { valeur: 'ABSENT', libelle: 'Absent' },
  { valeur: 'ABSENT_JUSTIFIE', libelle: 'Absent justifié' },
  { valeur: 'NON_RENDU', libelle: 'Non rendu' },
  { valeur: 'DISPENSE', libelle: 'Dispensé' },
  { valeur: 'FRAUDE', libelle: 'Fraude' },
];

export default function PageSaisieNotes() {
  const parametres = useParams<{ id: string }>();
  const { peut } = useSession();
  const client = useQueryClient();

  const [saisies, setSaisies] = useState<Record<string, { valeur: string; statut: string }>>({});
  const [confirmation, setConfirmation] = useState<string | null>(null);

  const evaluation = useQuery({
    queryKey: ['evaluation', parametres.id],
    queryFn: () => api.get<Evaluation>(`/evaluations/${parametres.id}`),
  });

  const apprenants = useQuery({
    queryKey: ['classe-apprenants', evaluation.data?.classe_id],
    enabled: Boolean(evaluation.data?.classe_id),
    queryFn: () => api.get<ApprenantClasse[]>(`/classes/${evaluation.data!.classe_id}/apprenants`),
  });

  const notes = useQuery({
    queryKey: ['evaluation-notes', parametres.id],
    queryFn: () => api.get<Note[]>(`/evaluations/${parametres.id}/notes`),
  });

  // Les notes déjà saisies préremplissent le formulaire.
  useEffect(() => {
    if (!notes.data) return;
    setSaisies(
      Object.fromEntries(
        notes.data.map((note) => [
          note.apprenant_id,
          { valeur: note.valeur !== null ? String(note.valeur) : '', statut: note.statut },
        ]),
      ),
    );
  }, [notes.data]);

  const enregistrement = useMutation({
    mutationFn: () =>
      api.post<{ message: string; details: Record<string, unknown> }>(
        `/evaluations/${parametres.id}/notes`,
        {
          notes: (apprenants.data ?? []).map((apprenant) => {
            const saisie = saisies[apprenant.id] ?? { valeur: '', statut: 'SAISIE' };
            const chiffre = saisie.valeur.replace(',', '.');
            return {
              apprenant_id: apprenant.id,
              valeur: saisie.statut === 'SAISIE' && chiffre !== '' ? Number(chiffre) : null,
              statut: saisie.statut === 'SAISIE' && chiffre === '' ? 'NON_RENDU' : saisie.statut,
            };
          }),
        },
      ),
    onSuccess: (reponse) => {
      setConfirmation(reponse.message);
      void client.invalidateQueries({ queryKey: ['evaluation', parametres.id] });
      void client.invalidateQueries({ queryKey: ['evaluation-notes', parametres.id] });
    },
  });

  const validation = useMutation({
    mutationFn: (niveau: string) =>
      api.post(`/evaluations/${parametres.id}/valider`, undefined, {
        parametres: { niveau },
      }),
    onSuccess: () => {
      setConfirmation('Évaluation validée.');
      void client.invalidateQueries({ queryKey: ['evaluation', parametres.id] });
    },
  });

  const statistiques = useMemo(() => {
    const valeurs = Object.values(saisies)
      .filter((saisie) => saisie.statut === 'SAISIE' && saisie.valeur !== '')
      .map((saisie) => Number(saisie.valeur.replace(',', '.')))
      .filter((valeur) => !Number.isNaN(valeur));
    if (valeurs.length === 0) return null;
    return {
      saisies: valeurs.length,
      moyenne: valeurs.reduce((total, valeur) => total + valeur, 0) / valeurs.length,
      minimum: Math.min(...valeurs),
      maximum: Math.max(...valeurs),
    };
  }, [saisies]);

  if (evaluation.isLoading) return <Chargement libelle="Ouverture de l'évaluation…" />;
  if (evaluation.isError) return <MessageErreur erreur={evaluation.error} />;

  const donnees = evaluation.data!;
  const verrouillee = ['VALIDEE_ETABLISSEMENT', 'PUBLIEE'].includes(donnees.statut);
  const liste = apprenants.data ?? [];

  function modifier(
    apprenantId: string,
    modifications: Partial<{ valeur: string; statut: string }>,
  ) {
    setSaisies((precedentes) => {
      const courante = precedentes[apprenantId] ?? { valeur: '', statut: 'SAISIE' };
      return { ...precedentes, [apprenantId]: { ...courante, ...modifications } };
    });
    setConfirmation(null);
  }

  return (
    <>
      <EntetePage
        fil={[{ libelle: 'Évaluations', href: '/evaluations' }, { libelle: donnees.intitule }]}
        titre={donnees.intitule}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <Badge ton="neutre">{humaniser(donnees.type_evaluation)}</Badge>
            {donnees.matiere_libelle ? <span>{donnees.matiere_libelle}</span> : null}
            {donnees.classe_libelle ? (
              <>
                <span aria-hidden>·</span>
                <span>{donnees.classe_libelle}</span>
              </>
            ) : null}
            <span aria-hidden>·</span>
            <span>{formaterDate(donnees.date_evaluation)}</span>
            <span aria-hidden>·</span>
            <span>
              Barème /{donnees.bareme} — coefficient {donnees.coefficient}
            </span>
            <Badge ton={tonDuStatut(donnees.statut)}>{humaniser(donnees.statut)}</Badge>
          </span>
        }
        actions={
          <>
            {peut('notes', 'CREATE') && !verrouillee ? (
              <Bouton
                onClick={() => enregistrement.mutate()}
                chargement={enregistrement.isPending}
                icone={<Save size={17} aria-hidden />}
              >
                Enregistrer les notes
              </Bouton>
            ) : null}
            {peut('notes', 'VALIDATE') ? (
              <Bouton
                variante="secondaire"
                onClick={() =>
                  validation.mutate(
                    donnees.statut === 'VALIDEE_ENSEIGNANT'
                      ? 'etablissement'
                      : donnees.statut === 'VALIDEE_ETABLISSEMENT'
                        ? 'publication'
                        : 'enseignant',
                  )
                }
                chargement={validation.isPending}
                icone={
                  donnees.statut === 'VALIDEE_ETABLISSEMENT' ? (
                    <Send size={17} aria-hidden />
                  ) : (
                    <CheckCircle2 size={17} aria-hidden />
                  )
                }
              >
                {donnees.statut === 'VALIDEE_ENSEIGNANT'
                  ? 'Valider (établissement)'
                  : donnees.statut === 'VALIDEE_ETABLISSEMENT'
                    ? 'Publier les notes'
                    : 'Valider (enseignant)'}
              </Bouton>
            ) : null}
          </>
        }
      />

      {confirmation ? (
        <div
          role="status"
          className="mb-4 rounded-lg border border-[rgb(var(--succes))]/40 bg-[rgb(var(--succes))]/8 px-4 py-3 text-sm font-medium"
        >
          {confirmation}
        </div>
      ) : null}
      {enregistrement.isError ? <MessageErreur erreur={enregistrement.error} /> : null}
      {validation.isError ? <MessageErreur erreur={validation.error} /> : null}

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicateur
          libelle="Notes saisies"
          valeur={`${statistiques?.saisies ?? donnees.nombre_notes} / ${liste.length}`}
          pictogramme="📝"
        />
        <Indicateur
          libelle="Moyenne"
          valeur={formaterNote(statistiques?.moyenne ?? donnees.moyenne)}
          unite={`/ ${donnees.bareme}`}
          pictogramme="📊"
        />
        <Indicateur
          libelle="Note la plus basse"
          valeur={formaterNote(statistiques?.minimum ?? donnees.note_min)}
          pictogramme="🔻"
        />
        <Indicateur
          libelle="Note la plus haute"
          valeur={formaterNote(statistiques?.maximum ?? donnees.note_max)}
          pictogramme="🔼"
        />
      </div>

      <Carte>
        <EnteteCarte
          titre="Saisie des notes"
          description={
            verrouillee
              ? 'Les notes sont validées : elles ne sont plus modifiables.'
              : `Saisissez une note sur ${donnees.bareme}, ou choisissez un statut particulier.`
          }
        />
        {apprenants.isLoading || notes.isLoading ? (
          <Chargement />
        ) : (
          <div className="defilement-fin overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">
                Saisie des notes de l&apos;évaluation {donnees.intitule}
              </caption>
              <thead>
                <tr className="surface-douce">
                  {['Apprenant', 'Identifiant', `Note / ${donnees.bareme}`, 'Statut'].map(
                    (entete) => (
                      <th
                        key={entete}
                        scope="col"
                        className="border-b px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide texte-doux"
                      >
                        {entete}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {liste.map((apprenant) => {
                  const saisie = saisies[apprenant.id] ?? { valeur: '', statut: 'SAISIE' };
                  const nombre = Number(saisie.valeur.replace(',', '.'));
                  const horsBareme =
                    saisie.valeur !== '' && (!Number.isFinite(nombre) || nombre > donnees.bareme);

                  return (
                    <tr key={apprenant.id} className="border-b last:border-0">
                      <td className="px-4 py-2.5">
                        <span className="flex flex-wrap items-center gap-2 font-medium">
                          {apprenant.nom_complet}
                          {apprenant.tiers_temps ? <Badge ton="info">Tiers temps</Badge> : null}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="font-mono text-xs texte-doux">
                          {apprenant.identifiant_educatif}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <label className="sr-only" htmlFor={`note-${apprenant.id}`}>
                          Note de {apprenant.nom_complet}
                        </label>
                        <input
                          id={`note-${apprenant.id}`}
                          type="text"
                          inputMode="decimal"
                          value={saisie.valeur}
                          disabled={verrouillee || saisie.statut !== 'SAISIE'}
                          onChange={(evenement) =>
                            modifier(apprenant.id, { valeur: evenement.target.value })
                          }
                          aria-invalid={horsBareme || undefined}
                          className={cn(
                            'w-24 rounded-lg border bg-[rgb(var(--fond-carte))] px-3 py-1.5 text-right tabular-nums',
                            horsBareme && 'border-[rgb(var(--danger))]',
                            'disabled:opacity-50',
                          )}
                          placeholder="—"
                        />
                        {horsBareme ? (
                          <span className="ml-2 text-xs font-medium text-[rgb(var(--danger))]">
                            Hors barème
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 py-2.5">
                        <label className="sr-only" htmlFor={`statut-${apprenant.id}`}>
                          Statut de {apprenant.nom_complet}
                        </label>
                        <select
                          id={`statut-${apprenant.id}`}
                          value={saisie.statut}
                          disabled={verrouillee}
                          onChange={(evenement) =>
                            modifier(apprenant.id, {
                              statut: evenement.target.value,
                              valeur: evenement.target.value === 'SAISIE' ? saisie.valeur : '',
                            })
                          }
                          className="rounded-lg border bg-[rgb(var(--fond-carte))] px-2 py-1.5 text-sm disabled:opacity-50"
                        >
                          <option value="SAISIE">Note chiffrée</option>
                          {STATUTS_SANS_NOTE.map((statut) => (
                            <option key={statut.valeur} value={statut.valeur}>
                              {statut.libelle}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Carte>
    </>
  );
}
