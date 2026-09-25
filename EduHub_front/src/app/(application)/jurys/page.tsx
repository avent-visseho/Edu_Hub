'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Gavel, ShieldCheck, UserPlus, Users } from 'lucide-react';
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
} from '@/components/ui/primitives';
import { api, ErreurApi, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterDate, formaterMontant, formaterNombre, humaniser } from '@/lib/utils';
import type { SessionExamen } from '@/types/api';

interface Jury {
  id: string;
  session_id: string;
  centre_id: string | null;
  code: string;
  libelle: string;
  president_nom: string | null;
  date_deliberation: string | null;
  lieu: string | null;
  nombre_candidats: number;
  nombre_admis: number;
  cloture: boolean;
}

interface MembreJury {
  id: string;
  nom_complet: string;
  qualite: string | null;
  est_president: boolean;
  est_rapporteur: boolean;
  present: boolean;
}

interface Surveillance {
  id: string;
  centre_id: string;
  salle_composition_id: string | null;
  role: string;
  nom_complet: string;
  telephone: string | null;
  indemnite: number;
  present: boolean | null;
}

interface Centre {
  id: string;
  code: string;
  nom: string;
}

/** Tous les centres sont nommés « Centre de composition — X » : le préfixe
 *  n'apporte rien dans une colonne déjà intitulée « Centre ». */
function nomCourtCentre(nom: string | undefined): string {
  if (!nom) return '—';
  return nom.replace(/^Centre de composition\s*[—-]\s*/, '');
}

const ROLES_SURVEILLANCE = [
  'CHEF_CENTRE',
  'CHEF_CENTRE_ADJOINT',
  'SECRETAIRE',
  'SURVEILLANT_GENERAL',
  'SURVEILLANT',
  'OPERATEUR_SAISIE',
  'PERSONNEL_SOUTIEN',
  'SECURITE',
];

export default function PageJurys() {
  const fileAttente = useQueryClient();
  const { peut } = useSession();

  const [sessionId, setSessionId] = useState('');
  const [juryId, setJuryId] = useState('');
  const [role, setRole] = useState('');
  const [nouveau, setNouveau] = useState({
    nom_complet: '',
    qualite: '',
    est_president: false,
    est_rapporteur: false,
  });
  const [message, setMessage] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const sessions = useQuery({
    queryKey: ['sessions-liste'],
    queryFn: () => api.get<Page<SessionExamen>>('/sessions', { size: 50 }),
  });

  const jurys = useQuery({
    queryKey: ['jurys', sessionId],
    queryFn: () => api.get<Page<Jury>>('/jurys', { session_id: sessionId || undefined, size: 100 }),
    enabled: Boolean(sessionId),
  });

  const centres = useQuery({
    queryKey: ['centres-session', sessionId],
    queryFn: () => api.get<Page<Centre>>('/centres', { session_id: sessionId, size: 200 }),
    enabled: Boolean(sessionId),
  });

  const membres = useQuery({
    queryKey: ['membres-jury', juryId],
    queryFn: () => api.get<MembreJury[]>(`/jurys/${juryId}/membres`),
    enabled: Boolean(juryId),
  });

  const surveillance = useQuery({
    queryKey: ['surveillance', sessionId, role],
    queryFn: () =>
      api.get<Page<Surveillance>>('/surveillance', {
        session_id: sessionId,
        role: role || undefined,
        size: 200,
      }),
    enabled: Boolean(sessionId),
  });

  useEffect(() => {
    if (!sessionId && sessions.data?.items.length) setSessionId(sessions.data.items[0].id);
  }, [sessions.data, sessionId]);

  useEffect(() => {
    if (jurys.data?.items.length) setJuryId((precedent) => precedent || jurys.data.items[0].id);
  }, [jurys.data]);

  const parCentre = useMemo(
    () => new Map((centres.data?.items ?? []).map((centre) => [centre.id, centre])),
    [centres.data],
  );

  const ajouter = useMutation({
    mutationFn: () =>
      api.post<{ message: string }>(`/jurys/${juryId}/membres`, {
        nom_complet: nouveau.nom_complet,
        qualite: nouveau.qualite || null,
        est_president: nouveau.est_president,
        est_rapporteur: nouveau.est_rapporteur,
      }),
    onSuccess: (reponse) => {
      setErreur(null);
      setMessage(reponse.message);
      setNouveau({ nom_complet: '', qualite: '', est_president: false, est_rapporteur: false });
      void fileAttente.invalidateQueries({ queryKey: ['membres-jury', juryId] });
    },
    onError: (erreurBrute: unknown) => {
      setMessage(null);
      setErreur(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "Le membre n'a pas pu être ajouté.",
      );
    },
  });

  const listeJurys = jurys.data?.items ?? [];
  const jury = listeJurys.find((element) => element.id === juryId) ?? null;
  const listeSurveillance = surveillance.data?.items ?? [];
  const candidats = listeJurys.reduce((somme, element) => somme + element.nombre_candidats, 0);
  const admis = listeJurys.reduce((somme, element) => somme + element.nombre_admis, 0);
  const clotures = listeJurys.filter((element) => element.cloture).length;

  return (
    <>
      <EntetePage
        titre="Jurys et surveillance"
        description="Composition des jurys de délibération et affectation des agents dans les centres de composition."
        actions={
          <Selection
            etiquette="Session"
            etiquetteMasquee
            value={sessionId}
            onChange={(evenement) => {
              setSessionId(evenement.target.value);
              setJuryId('');
            }}
            options={(sessions.data?.items ?? []).map((session) => ({
              valeur: session.id,
              libelle: session.libelle,
            }))}
            className="h-11"
          />
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
          libelle="Jurys constitués"
          valeur={listeJurys.length}
          unite={`${clotures} clôturé(s)`}
          icone={<Gavel size={19} aria-hidden />}
          pictogramme="⚖️"
        />
        <Indicateur
          libelle="Candidats délibérés"
          valeur={candidats}
          icone={<Users size={19} aria-hidden />}
          pictogramme="👥"
        />
        <Indicateur
          libelle="Admis"
          valeur={admis}
          unite={candidats > 0 ? `${formaterNombre((admis / candidats) * 100, 1)} %` : undefined}
          pictogramme="🎓"
        />
        <Indicateur
          libelle="Agents affectés"
          valeur={listeSurveillance.length}
          icone={<ShieldCheck size={19} aria-hidden />}
          pictogramme="🛡️"
        />
      </div>

      <Carte className="mb-4">
        <EnteteCarte
          titre="Jurys de délibération"
          description="Cliquez sur un jury pour afficher sa composition."
        />
        {jurys.isLoading ? (
          <CorpsCarte>
            <Chargement libelle="Chargement des jurys…" />
          </CorpsCarte>
        ) : jurys.isError ? (
          <CorpsCarte>
            <MessageErreur erreur={jurys.error} />
          </CorpsCarte>
        ) : (
          <Tableau
            legende="Jurys de délibération de la session"
            lignes={listeJurys}
            cleLigne={(element) => element.id}
            onLigneClic={(element) => setJuryId(element.id)}
            vide={
              <EtatVide
                titre="Aucun jury constitué"
                description="Les jurys sont créés au moment de la délibération de la session."
              />
            }
            colonnes={[
              {
                cle: 'libelle',
                entete: 'Jury',
                largeur: '32%',
                rendu: (element) => (
                  <span className="block max-w-[26rem]">
                    <span className="block truncate font-medium">
                      {element.centre_id
                        ? nomCourtCentre(parCentre.get(element.centre_id)?.nom)
                        : element.libelle}
                    </span>
                    <span className="block font-mono text-xs texte-doux">{element.code}</span>
                  </span>
                ),
              },
              {
                cle: 'president',
                entete: 'Président',
                rendu: (element) => element.president_nom ?? 'Non désigné',
              },
              {
                cle: 'deliberation',
                entete: 'Délibération',
                secondaire: true,
                rendu: (element) =>
                  element.date_deliberation ? formaterDate(element.date_deliberation) : '—',
              },
              {
                cle: 'resultats',
                entete: 'Admis',
                largeur: '14rem',
                rendu: (element) => (
                  <Jauge
                    valeur={element.nombre_admis}
                    maximum={element.nombre_candidats || 1}
                    etiquette={`${formaterNombre(element.nombre_admis)} / ${formaterNombre(element.nombre_candidats)}`}
                    ton="succes"
                  />
                ),
              },
              {
                cle: 'etat',
                entete: 'État',
                rendu: (element) => (
                  <Badge ton={element.cloture ? 'succes' : 'alerte'}>
                    {element.cloture ? 'Clôturé' : 'En cours'}
                  </Badge>
                ),
              },
            ]}
          />
        )}
      </Carte>

      <div className="grid gap-4">
        <Carte>
          <EnteteCarte
            titre={
              jury
                ? `Composition — ${nomCourtCentre(parCentre.get(jury.centre_id ?? '')?.nom) || jury.libelle}`
                : 'Composition du jury'
            }
            description={
              jury?.lieu
                ? `Délibération tenue à ${nomCourtCentre(jury.lieu)}.`
                : 'Membres siégeant au jury.'
            }
          />
          {!juryId ? (
            <CorpsCarte>
              <EtatVide titre="Choisissez un jury" />
            </CorpsCarte>
          ) : membres.isLoading ? (
            <CorpsCarte>
              <Chargement libelle="Chargement de la composition…" />
            </CorpsCarte>
          ) : (
            <Tableau
              legende="Membres du jury de délibération"
              lignes={membres.data ?? []}
              cleLigne={(membre) => membre.id}
              vide={<EtatVide titre="Aucun membre enregistré" />}
              colonnes={[
                {
                  cle: 'nom',
                  entete: 'Membre',
                  rendu: (membre) => (
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{membre.nom_complet}</span>
                      <span className="block text-xs texte-doux">{membre.qualite ?? '—'}</span>
                    </span>
                  ),
                },
                {
                  cle: 'role',
                  entete: 'Rôle',
                  rendu: (membre) => (
                    <span className="flex flex-wrap gap-1.5">
                      {membre.est_president ? <Badge ton="info">Président</Badge> : null}
                      {membre.est_rapporteur ? <Badge ton="neutre">Rapporteur</Badge> : null}
                      {!membre.est_president && !membre.est_rapporteur ? (
                        <span className="texte-doux">Membre</span>
                      ) : null}
                    </span>
                  ),
                },
                {
                  cle: 'presence',
                  entete: 'Présence',
                  alignement: 'droite',
                  rendu: (membre) => (
                    <Badge ton={membre.present ? 'succes' : 'danger'}>
                      {membre.present ? 'Présent' : 'Absent'}
                    </Badge>
                  ),
                },
              ]}
            />
          )}

          {juryId && peut('jurys', 'UPDATE') ? (
            <CorpsCarte className="border-t">
              <h3 className="mb-3 flex items-center gap-2 font-medium">
                <UserPlus size={17} aria-hidden /> Ajouter un membre
              </h3>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Champ
                  etiquette="Nom complet"
                  required
                  value={nouveau.nom_complet}
                  onChange={(evenement) =>
                    setNouveau((precedent) => ({
                      ...precedent,
                      nom_complet: evenement.target.value,
                    }))
                  }
                />
                <Champ
                  etiquette="Qualité"
                  placeholder="Inspecteur, chef d'établissement…"
                  value={nouveau.qualite}
                  onChange={(evenement) =>
                    setNouveau((precedent) => ({ ...precedent, qualite: evenement.target.value }))
                  }
                />
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:max-w-2xl">
                <Interrupteur
                  etiquette="Président du jury"
                  actif={nouveau.est_president}
                  onChange={() =>
                    setNouveau((precedent) => ({
                      ...precedent,
                      est_president: !precedent.est_president,
                    }))
                  }
                />
                <Interrupteur
                  etiquette="Rapporteur"
                  actif={nouveau.est_rapporteur}
                  onChange={() =>
                    setNouveau((precedent) => ({
                      ...precedent,
                      est_rapporteur: !precedent.est_rapporteur,
                    }))
                  }
                />
              </div>
              <Bouton
                className="mt-3"
                disabled={nouveau.nom_complet.trim().length === 0}
                chargement={ajouter.isPending}
                onClick={() => ajouter.mutate()}
              >
                Ajouter au jury
              </Bouton>
            </CorpsCarte>
          ) : null}
        </Carte>

        <Carte>
          <EnteteCarte
            titre="Surveillance des épreuves"
            description="Agents affectés aux centres de composition, par rôle."
            action={
              <Selection
                etiquette="Rôle"
                etiquetteMasquee
                value={role}
                onChange={(evenement) => setRole(evenement.target.value)}
                options={[
                  { valeur: '', libelle: 'Tous les rôles' },
                  ...ROLES_SURVEILLANCE.map((valeur) => ({ valeur, libelle: humaniser(valeur) })),
                ]}
              />
            }
          />
          {surveillance.isLoading ? (
            <CorpsCarte>
              <Chargement libelle="Chargement des affectations…" />
            </CorpsCarte>
          ) : (
            <Tableau
              legende="Affectations de surveillance de la session"
              lignes={listeSurveillance}
              cleLigne={(agent) => agent.id}
              vide={
                <EtatVide
                  titre="Aucune affectation de surveillance"
                  description="Les agents sont affectés lors de la préparation logistique de la session."
                />
              }
              colonnes={[
                {
                  cle: 'nom',
                  entete: 'Agent',
                  rendu: (agent) => (
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{agent.nom_complet}</span>
                      <span className="block text-xs texte-doux">{agent.telephone ?? '—'}</span>
                    </span>
                  ),
                },
                {
                  cle: 'role',
                  entete: 'Rôle',
                  rendu: (agent) => <Badge ton="neutre">{humaniser(agent.role)}</Badge>,
                },
                {
                  cle: 'centre',
                  entete: 'Centre',
                  rendu: (agent) => (
                    <span className="block max-w-[18rem] truncate">
                      {nomCourtCentre(parCentre.get(agent.centre_id)?.nom)}
                    </span>
                  ),
                },
                {
                  cle: 'indemnite',
                  entete: 'Indemnité',
                  alignement: 'droite',
                  secondaire: true,
                  rendu: (agent) => formaterMontant(agent.indemnite),
                },
                {
                  cle: 'presence',
                  entete: 'Présence',
                  alignement: 'droite',
                  rendu: (agent) =>
                    agent.present === null ? (
                      <span className="texte-doux">Non pointée</span>
                    ) : (
                      <Badge ton={agent.present ? 'succes' : 'danger'}>
                        {agent.present ? 'Présent' : 'Absent'}
                      </Badge>
                    ),
                },
              ]}
            />
          )}
        </Carte>
      </div>
    </>
  );
}
