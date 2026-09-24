'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Accessibility,
  Award,
  CheckCircle2,
  FileText,
  MapPin,
  Printer,
  XCircle,
} from 'lucide-react';
import { useParams } from 'next/navigation';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur, ListeDescriptive, Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
  Selection,
  tonDuStatut,
} from '@/components/ui/primitives';
import { api, ErreurApi } from '@/lib/api';
import {
  formaterDate,
  formaterDateHeure,
  formaterMontant,
  formaterNote,
  humaniser,
} from '@/lib/utils';
import { useSession } from '@/lib/session';

interface Candidat {
  id: string;
  numero_candidat: string;
  numero_table: string | null;
  nom: string;
  prenoms: string;
  nom_complet: string;
  sexe: string;
  date_naissance: string;
  lieu_naissance: string | null;
  telephone: string | null;
  type_candidature: string;
  statut_dossier: string;
  montant_frais: number;
  statut_paiement: string;
  numero_place: number | null;
  type_handicap: string;
  tiers_temps: boolean;
  motif_rejet: string | null;
}

interface Piece {
  id: string;
  nom_fichier: string;
  statut: string;
  motif_rejet: string | null;
  version: number;
}

interface NoteEpreuve {
  epreuve: string;
  matiere: string;
  note: number | null;
  coefficient: number;
  points: number | null;
  statut: string;
}

interface Dossier {
  candidat: Candidat;
  session: string | null;
  affectation: {
    centre: string | null;
    salle: string | null;
    place: number | null;
    numero_table: string | null;
  };
  pieces: Piece[];
  pieces_manquantes: Array<{ id: string; libelle: string }>;
  dossier_complet: boolean;
  notes: NoteEpreuve[];
  resultat: {
    moyenne: number | null;
    mention: string | null;
    decision: string;
    rang_national: number | null;
    publie: boolean;
  } | null;
}

/** Action proposée par la machine à états pour l'état courant du dossier. */
interface ActionPossible {
  action: string;
  libelle: string;
  vers: string;
}

interface EtapeHistorique {
  date: string;
  workflow: string;
  action: string;
  statut_avant: string | null;
  statut_apres: string;
  acteur: string | null;
  commentaire: string | null;
}

const STATUTS_PIECE = [
  { valeur: 'VALIDE', libelle: 'Valider la pièce' },
  { valeur: 'REJETE', libelle: 'Rejeter la pièce' },
];

export default function PageDossierCandidat() {
  const parametres = useParams<{ id: string }>();
  const fileAttente = useQueryClient();
  const { peut } = useSession();

  const [action, setAction] = useState('');
  const [commentaire, setCommentaire] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const dossier = useQuery({
    queryKey: ['dossier-candidat', parametres.id],
    queryFn: () => api.get<Dossier>(`/candidats/${parametres.id}/dossier`),
  });

  const actions = useQuery({
    queryKey: ['actions-candidat', parametres.id],
    queryFn: () => api.get<ActionPossible[]>(`/candidats/${parametres.id}/transitions`),
  });

  const historique = useQuery({
    queryKey: ['historique-candidat', parametres.id],
    queryFn: () => api.get<EtapeHistorique[]>(`/workflows/candidats/${parametres.id}/historique`),
    // Réservé aux profils habilités à consulter la piste d'audit.
    enabled: peut('audit', 'READ'),
  });

  function rafraichir() {
    setAction('');
    void fileAttente.invalidateQueries({ queryKey: ['dossier-candidat', parametres.id] });
    void fileAttente.invalidateQueries({ queryKey: ['actions-candidat', parametres.id] });
    void fileAttente.invalidateQueries({ queryKey: ['historique-candidat', parametres.id] });
  }

  function signaler(erreurBrute: unknown) {
    setMessage(null);
    setErreur(
      erreurBrute instanceof ErreurApi ? erreurBrute.message : "L'action n'a pas pu être appliquée.",
    );
  }

  const appliquerTransition = useMutation({
    mutationFn: () =>
      api.post<Candidat>(`/candidats/${parametres.id}/transition`, {
        action,
        commentaire: commentaire || null,
        motif: commentaire || null,
      }),
    onSuccess: (candidatMaj) => {
      setErreur(null);
      setMessage(`Dossier passé à l'état « ${humaniser(candidatMaj.statut_dossier)} ».`);
      setCommentaire('');
      rafraichir();
    },
    onError: signaler,
  });

  const validerPiece = useMutation({
    mutationFn: (variables: { piece: string; statut: string }) =>
      api.post<{ message: string }>(
        `/candidats/${parametres.id}/pieces/${variables.piece}/validation`,
        { statut: variables.statut },
      ),
    onSuccess: (reponse) => {
      setErreur(null);
      setMessage(reponse.message);
      rafraichir();
    },
    onError: signaler,
  });

  if (dossier.isLoading) return <Chargement libelle="Ouverture du dossier de candidature…" />;
  if (dossier.isError) return <MessageErreur erreur={dossier.error} />;

  const donnees = dossier.data!;
  const candidat = donnees.candidat;
  const total = donnees.notes.reduce((somme, note) => somme + (note.points ?? 0), 0);
  const coefficients = donnees.notes.reduce((somme, note) => somme + note.coefficient, 0);

  return (
    <>
      <EntetePage
        fil={[{ libelle: 'Candidats', href: '/candidats' }, { libelle: candidat.nom_complet }]}
        titre={candidat.nom_complet}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs">{candidat.numero_candidat}</span>
            <Badge ton={tonDuStatut(candidat.statut_dossier)}>
              {humaniser(candidat.statut_dossier)}
            </Badge>
            <Badge ton="neutre">{humaniser(candidat.type_candidature)}</Badge>
            {candidat.tiers_temps ? (
              <Badge ton="info">
                <Accessibility size={13} aria-hidden /> Tiers temps
              </Badge>
            ) : null}
            {donnees.session ? <span>{donnees.session}</span> : null}
          </span>
        }
        actions={
          peut('candidats', 'PRINT') ? (
            <Bouton
              variante="secondaire"
              icone={<Printer size={17} aria-hidden />}
              onClick={() => api.ouvrir(`/candidats/${parametres.id}/convocation`)}
            >
              Convocation
            </Bouton>
          ) : null
        }
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
          libelle="Pièces fournies"
          valeur={`${donnees.pieces.length} / ${donnees.pieces.length + donnees.pieces_manquantes.length}`}
          icone={<FileText size={19} aria-hidden />}
          pictogramme="📄"
        />
        <Indicateur
          libelle="Frais d'inscription"
          valeur={formaterMontant(candidat.montant_frais)}
          unite={humaniser(candidat.statut_paiement)}
          pictogramme="💳"
        />
        <Indicateur
          libelle="Notes saisies"
          valeur={`${donnees.notes.filter((note) => note.note !== null).length} / ${donnees.notes.length}`}
          pictogramme="✍️"
        />
        <Indicateur
          libelle="Moyenne"
          valeur={donnees.resultat?.moyenne != null ? formaterNote(donnees.resultat.moyenne) : '—'}
          unite="/ 20"
          icone={<Award size={19} aria-hidden />}
          pictogramme="🎓"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Carte>
          <EnteteCarte titre="État civil" />
          <CorpsCarte>
            <ListeDescriptive
              colonnes={1}
              entrees={[
                { terme: 'Nom', valeur: candidat.nom },
                { terme: 'Prénoms', valeur: candidat.prenoms },
                { terme: 'Sexe', valeur: humaniser(candidat.sexe) },
                { terme: 'Date de naissance', valeur: formaterDate(candidat.date_naissance) },
                { terme: 'Lieu de naissance', valeur: candidat.lieu_naissance ?? '—' },
                { terme: 'Téléphone', valeur: candidat.telephone ?? '—' },
                {
                  terme: 'Besoin spécifique',
                  valeur:
                    candidat.type_handicap === 'AUCUN' ? 'Aucun' : humaniser(candidat.type_handicap),
                },
              ]}
            />
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <MapPin size={19} aria-hidden /> Affectation de composition
              </span>
            }
            description="Centre, salle et place attribués lors de la répartition."
          />
          <CorpsCarte>
            {donnees.affectation.centre ? (
              <ListeDescriptive
                colonnes={1}
                entrees={[
                  { terme: 'Centre', valeur: donnees.affectation.centre },
                  { terme: 'Salle', valeur: donnees.affectation.salle ?? '—' },
                  { terme: 'Place', valeur: donnees.affectation.place ?? '—' },
                  {
                    terme: 'Numéro de table',
                    valeur: (
                      <span className="font-mono text-sm">
                        {donnees.affectation.numero_table ?? '—'}
                      </span>
                    ),
                  },
                ]}
              />
            ) : (
              <EtatVide
                titre="Candidat non encore réparti"
                description="La répartition des candidats dans les centres n'a pas été lancée pour cette session."
              />
            )}
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte
            titre="Instruction du dossier"
            description="Chaque changement d'état est historisé."
          />
          <CorpsCarte className="space-y-3">
            <Selection
              etiquette="Action à appliquer"
              aide="Seules les actions autorisées depuis l'état courant sont proposées."
              options={[
                { valeur: '', libelle: 'Choisir une action…' },
                ...(actions.data ?? []).map((possible) => ({
                  valeur: possible.action,
                  libelle: `${possible.libelle} → ${humaniser(possible.vers)}`,
                })),
              ]}
              value={action}
              onChange={(evenement) => setAction(evenement.target.value)}
            />
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Commentaire</span>
              <textarea
                rows={3}
                value={commentaire}
                onChange={(evenement) => setCommentaire(evenement.target.value)}
                placeholder="Motif ou observation transmise au candidat…"
                className="w-full rounded-lg border bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-[rgb(var(--accent))]"
              />
            </label>
            <Bouton
              disabled={!action || !peut('candidats', 'VALIDATE')}
              chargement={appliquerTransition.isPending}
              onClick={() => appliquerTransition.mutate()}
            >
              Appliquer
            </Bouton>
            {!peut('candidats', 'VALIDATE') ? (
              <p className="text-xs texte-doux">
                Votre profil ne permet pas d&apos;instruire les dossiers de candidature.
              </p>
            ) : actions.data?.length === 0 ? (
              <p className="text-xs texte-doux">
                Aucune action n&apos;est possible depuis l&apos;état «{' '}
                {humaniser(candidat.statut_dossier)} ».
              </p>
            ) : null}
            {candidat.motif_rejet ? (
              <p className="text-sm text-[rgb(var(--danger))]">
                Motif de rejet enregistré : {candidat.motif_rejet}
              </p>
            ) : null}
          </CorpsCarte>
        </Carte>
      </div>

      <Carte className="mt-4">
        <EnteteCarte
          titre="Pièces du dossier"
          description={
            donnees.dossier_complet
              ? 'Toutes les pièces obligatoires ont été fournies.'
              : `Pièces obligatoires manquantes : ${donnees.pieces_manquantes
                  .map((piece) => piece.libelle)
                  .join(', ')}.`
          }
          action={
            <Badge ton={donnees.dossier_complet ? 'succes' : 'alerte'}>
              {donnees.dossier_complet ? (
                <>
                  <CheckCircle2 size={13} aria-hidden /> Dossier complet
                </>
              ) : (
                <>
                  <XCircle size={13} aria-hidden /> Dossier incomplet
                </>
              )}
            </Badge>
          }
        />
        <Tableau
          legende="Pièces jointes au dossier de candidature"
          lignes={donnees.pieces}
          cleLigne={(piece) => piece.id}
          vide={<EtatVide titre="Aucune pièce déposée" />}
          colonnes={[
            {
              cle: 'nom_fichier',
              entete: 'Fichier',
              rendu: (piece) => <span className="font-medium">{piece.nom_fichier}</span>,
            },
            {
              cle: 'version',
              entete: 'Version',
              alignement: 'droite',
              secondaire: true,
              rendu: (piece) => piece.version,
            },
            {
              cle: 'statut',
              entete: 'Statut',
              rendu: (piece) => (
                <span className="flex flex-wrap items-center gap-1.5">
                  <Badge ton={tonDuStatut(piece.statut)}>{humaniser(piece.statut)}</Badge>
                  {piece.motif_rejet ? (
                    <span className="text-xs texte-doux">{humaniser(piece.motif_rejet)}</span>
                  ) : null}
                </span>
              ),
            },
            {
              cle: 'actions',
              entete: 'Vérification',
              alignement: 'droite',
              rendu: (piece) => (
                <Selection
                  etiquette={`Vérification de ${piece.nom_fichier}`}
                  etiquetteMasquee
                  disabled={!peut('documents', 'VALIDATE') || validerPiece.isPending}
                  value=""
                  options={[{ valeur: '', libelle: 'Choisir…' }, ...STATUTS_PIECE]}
                  onChange={(evenement) => {
                    if (!evenement.target.value) return;
                    validerPiece.mutate({ piece: piece.id, statut: evenement.target.value });
                  }}
                />
              ),
            },
          ]}
        />
      </Carte>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Carte>
          <EnteteCarte
            titre="Notes aux épreuves"
            description={
              coefficients > 0
                ? `${formaterNote(total)} points pour ${coefficients} coefficient(s).`
                : 'Aucune épreuve notée.'
            }
          />
          <Tableau
            legende="Notes obtenues par épreuve"
            lignes={donnees.notes}
            cleLigne={(note, index) => `${note.epreuve}-${index}`}
            vide={<EtatVide titre="Aucune note saisie" />}
            colonnes={[
              {
                cle: 'epreuve',
                entete: 'Épreuve',
                rendu: (note) => (
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{note.matiere}</span>
                    <span className="block truncate text-xs texte-doux">{note.epreuve}</span>
                  </span>
                ),
              },
              {
                cle: 'note',
                entete: 'Note',
                alignement: 'droite',
                rendu: (note) => (note.note != null ? formaterNote(note.note) : '—'),
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
                rendu: (note) => (note.points != null ? formaterNote(note.points) : '—'),
              },
              {
                cle: 'statut',
                entete: 'Statut',
                secondaire: true,
                rendu: (note) => <Badge ton={tonDuStatut(note.statut)}>{humaniser(note.statut)}</Badge>,
              },
            ]}
          />
          {donnees.resultat ? (
            <CorpsCarte className="border-t">
              <ListeDescriptive
                colonnes={2}
                entrees={[
                  {
                    terme: 'Décision',
                    valeur: (
                      <Badge ton={tonDuStatut(donnees.resultat.decision)}>
                        {humaniser(donnees.resultat.decision)}
                      </Badge>
                    ),
                  },
                  { terme: 'Mention', valeur: donnees.resultat.mention ?? '—' },
                  {
                    terme: 'Moyenne',
                    valeur:
                      donnees.resultat.moyenne != null
                        ? `${formaterNote(donnees.resultat.moyenne)} / 20`
                        : '—',
                  },
                  {
                    terme: 'Rang national',
                    valeur: donnees.resultat.rang_national ?? '—',
                  },
                  {
                    terme: 'Publication',
                    valeur: donnees.resultat.publie ? 'Résultat publié' : 'Non publié',
                  },
                ]}
              />
            </CorpsCarte>
          ) : null}
        </Carte>

        <Carte>
          <EnteteCarte
            titre="Historique du dossier"
            description="Traçabilité complète des transitions de workflow."
          />
          {!peut('audit', 'READ') ? (
            <CorpsCarte>
              <EtatVide
                titre="Historique non accessible"
                description="La consultation de la piste d'audit demande l'habilitation correspondante."
              />
            </CorpsCarte>
          ) : historique.isLoading ? (
            <CorpsCarte>
              <Chargement libelle="Chargement de l'historique…" />
            </CorpsCarte>
          ) : (
            <Tableau
              legende="Transitions du dossier de candidature"
              lignes={[...(historique.data ?? [])].reverse()}
              cleLigne={(etape, index) => `${etape.date}-${index}`}
              vide={<EtatVide titre="Aucune transition enregistrée" />}
              colonnes={[
                {
                  cle: 'action',
                  entete: 'Action',
                  rendu: (etape) => (
                    <span className="min-w-0">
                      <span className="block font-medium">{humaniser(etape.action)}</span>
                      <span className="block text-xs texte-doux">
                        {humaniser(etape.statut_avant ?? 'initial')} →{' '}
                        {humaniser(etape.statut_apres)}
                      </span>
                      {etape.commentaire ? (
                        <span className="block text-xs texte-doux">{etape.commentaire}</span>
                      ) : null}
                    </span>
                  ),
                },
                {
                  cle: 'auteur',
                  entete: 'Auteur',
                  secondaire: true,
                  rendu: (etape) => etape.acteur ?? 'Automatique',
                },
                {
                  cle: 'date',
                  entete: 'Date',
                  alignement: 'droite',
                  rendu: (etape) => formaterDateHeure(etape.date),
                },
              ]}
            />
          )}
        </Carte>
      </div>
    </>
  );
}
