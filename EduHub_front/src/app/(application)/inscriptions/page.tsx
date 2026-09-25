'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRightLeft, ClipboardList, GraduationCap, UserCheck, Users } from 'lucide-react';
import { useState } from 'react';

import { GraphiqueBarres } from '@/components/graphiques';
import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur, Jauge } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import {
  Badge,
  Bouton,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  Selection,
  tonDuStatut,
} from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, ErreurApi, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import {
  formaterDate,
  formaterDateHeure,
  formaterMontant,
  formaterNombre,
  formaterPourcentage,
  humaniser,
} from '@/lib/utils';
import type { Etablissement } from '@/types/api';

interface Inscription {
  id: string;
  numero: string;
  apprenant_id: string;
  classe_id: string | null;
  statut: string;
  regime: string;
  redoublant: boolean;
  boursier: boolean;
  date_demande: string;
  date_validation: string | null;
  frais_scolarite: number;
  montant_paye: number;
  decision: string;
  motif_rejet: string | null;
  apprenant_nom: string | null;
  identifiant_educatif: string | null;
  etablissement_nom: string | null;
  classe_libelle: string | null;
  annee_libelle: string | null;
}

interface AnneeAcademique {
  id: string;
  code: string;
  libelle: string;
  courante: boolean;
}

interface ActionPossible {
  action: string;
  libelle: string;
  vers: string;
}

interface EtapeHistorique {
  date: string;
  action: string;
  statut_avant: string | null;
  statut_apres: string;
  acteur: string | null;
  commentaire: string | null;
}

interface StatistiquesScolarite {
  inscriptions: number;
  par_sexe: Record<string, number>;
  taux_filles: number;
  par_statut: Record<string, number>;
}

/** Étapes du workflow d'inscription, dans l'ordre de la chaîne. */
const ETAPES = [
  'DEMANDE',
  'DOSSIER_DEPOSE',
  'EN_VERIFICATION',
  'VALIDEE',
  'INSCRIT',
];

const SORTIES = ['REJETEE', 'TRANSFERE', 'ABANDON', 'EXCLU'];

export default function PageInscriptions() {
  const fileAttente = useQueryClient();
  const { peut } = useSession();

  const [anneeId, setAnneeId] = useState('');
  const [etablissementId, setEtablissementId] = useState('');
  const [statut, setStatut] = useState('');
  const [selection, setSelection] = useState<Inscription | null>(null);
  const [commentaire, setCommentaire] = useState('');
  const [action, setAction] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const annees = useQuery({
    queryKey: ['annees'],
    queryFn: () => api.get<Page<AnneeAcademique>>('/annees', { size: 20 }),
  });

  const etablissements = useQuery({
    queryKey: ['etablissements-liste'],
    queryFn: () => api.get<Page<Etablissement>>('/etablissements', { size: 200, sort_by: 'nom' }),
  });

  const statistiques = useQuery({
    queryKey: ['statistiques-scolarite', anneeId],
    queryFn: () =>
      api.get<StatistiquesScolarite>('/statistiques/scolarite', {
        annee_id: anneeId || undefined,
      }),
  });

  const liste = useListe<Inscription>('/inscriptions', {
    tri: 'numero',
    filtres: {
      annee_id: anneeId || undefined,
      etablissement_id: etablissementId || undefined,
      statut: statut || undefined,
    },
  });

  const actions = useQuery({
    queryKey: ['actions-inscription', selection?.id],
    queryFn: () => api.get<ActionPossible[]>(`/inscriptions/${selection!.id}/transitions`),
    enabled: Boolean(selection),
  });

  const historique = useQuery({
    queryKey: ['historique-inscription', selection?.id],
    queryFn: () =>
      api.get<EtapeHistorique[]>(`/workflows/inscriptions/${selection!.id}/historique`),
    // La piste d'audit demande son habilitation propre.
    enabled: Boolean(selection) && peut('audit', 'READ'),
  });

  const appliquer = useMutation({
    mutationFn: () =>
      api.post<Inscription>(`/inscriptions/${selection!.id}/transition`, {
        action,
        commentaire: commentaire || null,
        motif: commentaire || null,
      }),
    onSuccess: (inscription) => {
      setErreur(null);
      setMessage(
        `Inscription ${inscription.numero} : ${humaniser(inscription.statut).toLowerCase()}.`,
      );
      setAction('');
      setCommentaire('');
      setSelection(inscription);
      void fileAttente.invalidateQueries({ queryKey: ['/inscriptions'] });
      void fileAttente.invalidateQueries({ queryKey: ['actions-inscription', inscription.id] });
      void fileAttente.invalidateQueries({ queryKey: ['historique-inscription', inscription.id] });
      void fileAttente.invalidateQueries({ queryKey: ['statistiques-scolarite'] });
    },
    onError: (erreurBrute: unknown) => {
      setMessage(null);
      setErreur(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "La transition n'a pas pu être appliquée.",
      );
    },
  });

  const parStatut = statistiques.data?.par_statut ?? {};
  const repartition = [...ETAPES, ...SORTIES]
    .filter((etape) => parStatut[etape])
    .map((etape) => ({ nom: humaniser(etape), valeur: parStatut[etape] }));
  const inscrits = parStatut.INSCRIT ?? 0;
  const enCours = ETAPES.slice(0, 4).reduce((somme, etape) => somme + (parStatut[etape] ?? 0), 0);
  const sorties = SORTIES.reduce((somme, etape) => somme + (parStatut[etape] ?? 0), 0);

  return (
    <>
      <EntetePage
        titre="Inscriptions"
        description="Demandes d'inscription scolaire, de leur dépôt à l'affectation en classe. Chaque changement d'état est historisé."
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

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Indicateur
          libelle="Inscriptions"
          valeur={statistiques.data?.inscriptions ?? '—'}
          icone={<ClipboardList size={19} aria-hidden />}
          pictogramme="📋"
        />
        <Indicateur
          libelle="Élèves inscrits"
          valeur={inscrits}
          icone={<GraduationCap size={19} aria-hidden />}
          pictogramme="🎓"
        />
        <Indicateur
          libelle="Dossiers en cours"
          valeur={enCours}
          unite="avant affectation"
          icone={<UserCheck size={19} aria-hidden />}
          pictogramme="⏳"
        />
        <Indicateur
          libelle="Part des filles"
          valeur={formaterPourcentage(statistiques.data?.taux_filles ?? 0)}
          icone={<Users size={19} aria-hidden />}
          pictogramme="👧"
        />
      </div>

      <div className="mb-4 grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Carte>
          <EnteteCarte
            titre="Répartition par étape"
            description="Où en sont les dossiers dans la chaîne d'inscription."
          />
          <CorpsCarte>
            {statistiques.isLoading ? (
              <Chargement libelle="Chargement des statistiques…" />
            ) : repartition.length > 0 ? (
              <GraphiqueBarres
                titre="Dossiers par étape du workflow"
                donnees={repartition}
                cleAbscisse="nom"
                series={[{ cle: 'valeur', libelle: 'Dossiers' }]}
                hauteur={220}
              />
            ) : (
              <EtatVide titre="Aucune inscription pour ce périmètre" />
            )}
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte titre="Sorties de parcours" description="Rejets, transferts, abandons et exclusions." />
          <CorpsCarte className="space-y-3">
            {SORTIES.map((sortie) => (
              <Jauge
                key={sortie}
                valeur={parStatut[sortie] ?? 0}
                maximum={statistiques.data?.inscriptions || 1}
                etiquette={`${humaniser(sortie)} — ${formaterNombre(parStatut[sortie] ?? 0)}`}
                ton={sortie === 'TRANSFERE' ? 'accent' : 'alerte'}
              />
            ))}
            <p className="text-sm texte-doux">
              {sorties === 0
                ? 'Aucun dossier sorti du parcours sur ce périmètre.'
                : `${formaterNombre(sorties)} dossier(s) sortis du parcours.`}
            </p>
          </CorpsCarte>
        </Carte>
      </div>

      <ListeRessource
        legende="Liste des inscriptions scolaires"
        placeholderRecherche="Rechercher par numéro d'inscription…"
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
        cleLigne={(inscription) => inscription.id}
        onLigneClic={(inscription) => {
          setSelection(inscription);
          setAction('');
          setMessage(null);
          setErreur(null);
        }}
        videTitre="Aucune inscription"
        filtres={
          <div className="grid gap-4 sm:grid-cols-3">
            <Selection
              etiquette="Année académique"
              value={anneeId}
              onChange={(evenement) => setAnneeId(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Toutes les années' },
                ...(annees.data?.items ?? []).map((annee) => ({
                  valeur: annee.id,
                  libelle: annee.libelle,
                })),
              ]}
            />
            <Selection
              etiquette="Établissement"
              value={etablissementId}
              onChange={(evenement) => setEtablissementId(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Tous les établissements' },
                ...(etablissements.data?.items ?? []).map((etablissement) => ({
                  valeur: etablissement.id,
                  libelle: etablissement.nom,
                })),
              ]}
            />
            <Selection
              etiquette="Étape"
              value={statut}
              onChange={(evenement) => setStatut(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Toutes les étapes' },
                ...[...ETAPES, ...SORTIES].map((valeur) => ({
                  valeur,
                  libelle: humaniser(valeur),
                })),
              ]}
            />
          </div>
        }
        colonnes={[
          {
            cle: 'apprenant',
            entete: 'Apprenant',
            rendu: (inscription) => (
              <span className="min-w-0">
                <span className="block truncate font-medium">
                  {inscription.apprenant_nom ?? '—'}
                </span>
                <span className="block font-mono text-xs texte-doux">
                  {inscription.identifiant_educatif ?? inscription.numero}
                </span>
              </span>
            ),
          },
          {
            cle: 'scolarisation',
            entete: 'Scolarisation',
            secondaire: true,
            rendu: (inscription) => (
              <span className="min-w-0">
                <span className="block truncate">{inscription.classe_libelle ?? 'Sans classe'}</span>
                <span className="block truncate text-xs texte-doux">
                  {inscription.etablissement_nom ?? '—'}
                </span>
              </span>
            ),
          },
          {
            cle: 'regime',
            entete: 'Régime',
            secondaire: true,
            rendu: (inscription) => (
              <span className="flex flex-wrap gap-1.5">
                <Badge ton="neutre">{humaniser(inscription.regime)}</Badge>
                {inscription.redoublant ? <Badge ton="alerte">Redoublant</Badge> : null}
                {inscription.boursier ? <Badge ton="info">Boursier</Badge> : null}
              </span>
            ),
          },
          {
            cle: 'demande',
            entete: 'Demandée le',
            alignement: 'droite',
            secondaire: true,
            rendu: (inscription) => formaterDate(inscription.date_demande),
          },
          {
            cle: 'statut',
            entete: 'Étape',
            rendu: (inscription) => (
              <Badge ton={tonDuStatut(inscription.statut)}>{humaniser(inscription.statut)}</Badge>
            ),
          },
        ]}
      />

      {selection ? (
        <Carte className="mt-4">
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <ArrowRightLeft size={19} aria-hidden /> Instruire —{' '}
                {selection.apprenant_nom ?? selection.numero}
              </span>
            }
            description={`${selection.numero} · ${selection.annee_libelle ?? ''}`}
            action={
              <Bouton variante="fantome" taille="sm" onClick={() => setSelection(null)}>
                Fermer
              </Bouton>
            }
          />
          <CorpsCarte className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              {[
                { terme: 'Étape', valeur: humaniser(selection.statut) },
                { terme: 'Classe', valeur: selection.classe_libelle ?? 'Non affectée' },
                { terme: 'Établissement', valeur: selection.etablissement_nom ?? '—' },
                { terme: 'Régime', valeur: humaniser(selection.regime) },
                {
                  terme: 'Frais de scolarité',
                  valeur: `${formaterMontant(selection.montant_paye)} / ${formaterMontant(selection.frais_scolarite)}`,
                },
                {
                  terme: 'Validée le',
                  valeur: selection.date_validation
                    ? formaterDate(selection.date_validation)
                    : 'Non validée',
                },
                { terme: 'Décision de fin d’année', valeur: humaniser(selection.decision) },
                { terme: 'Motif de rejet', valeur: selection.motif_rejet ?? '—' },
              ].map((entree) => (
                <div key={entree.terme} className="min-w-0">
                  <dt className="text-xs font-medium uppercase tracking-wide texte-doux">
                    {entree.terme}
                  </dt>
                  <dd className="mt-0.5 break-words font-medium">{entree.valeur}</dd>
                </div>
              ))}
            </dl>

            <div className="space-y-3">
              <Selection
                etiquette="Action à appliquer"
                aide="Seules les actions autorisées depuis l'étape courante sont proposées."
                value={action}
                onChange={(evenement) => setAction(evenement.target.value)}
                options={[
                  { valeur: '', libelle: 'Choisir une action…' },
                  ...(actions.data ?? []).map((possible) => ({
                    valeur: possible.action,
                    libelle: `${possible.libelle} → ${humaniser(possible.vers)}`,
                  })),
                ]}
              />
              <label className="block text-sm">
                <span className="mb-1 block font-medium">Commentaire ou motif</span>
                <textarea
                  rows={3}
                  value={commentaire}
                  onChange={(evenement) => setCommentaire(evenement.target.value)}
                  placeholder="Observation transmise à la famille…"
                  className="w-full rounded-lg border bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-[rgb(var(--accent))]"
                />
              </label>
              <Bouton
                disabled={!action || !peut('inscriptions', 'VALIDATE')}
                chargement={appliquer.isPending}
                onClick={() => appliquer.mutate()}
              >
                Appliquer
              </Bouton>
              {!peut('inscriptions', 'VALIDATE') ? (
                <p className="text-xs texte-doux">
                  Votre profil ne permet pas d&apos;instruire les inscriptions.
                </p>
              ) : actions.data?.length === 0 ? (
                <p className="text-xs texte-doux">
                  Aucune action n&apos;est possible depuis l&apos;étape «{' '}
                  {humaniser(selection.statut)} ».
                </p>
              ) : null}
            </div>
          </CorpsCarte>

          {peut('audit', 'READ') ? (
            <CorpsCarte className="border-t">
              <h3 className="mb-3 font-medium">Historique du dossier</h3>
              {historique.isLoading ? (
                <Chargement libelle="Chargement de l'historique…" />
              ) : (historique.data ?? []).length === 0 ? (
                <p className="text-sm texte-doux">
                  Aucune transition enregistrée : ce dossier a été constitué avec son état initial.
                </p>
              ) : (
                <ol className="space-y-2 text-sm">
                  {[...(historique.data ?? [])].reverse().map((etape, index) => (
                    <li key={`${etape.date}-${index}`} className="surface-douce rounded-lg p-3">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{humaniser(etape.action)}</span>
                        <span className="texte-doux">
                          {humaniser(etape.statut_avant ?? 'initial')} →{' '}
                          {humaniser(etape.statut_apres)}
                        </span>
                        <span className="text-xs texte-doux">
                          {formaterDateHeure(etape.date)} · {etape.acteur ?? 'Automatique'}
                        </span>
                      </span>
                      {etape.commentaire ? (
                        <span className="mt-1 block texte-doux">{etape.commentaire}</span>
                      ) : null}
                    </li>
                  ))}
                </ol>
              )}
            </CorpsCarte>
          ) : null}
        </Carte>
      ) : null}
    </>
  );
}
