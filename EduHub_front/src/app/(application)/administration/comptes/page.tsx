'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, ShieldCheck, Trash2, UserPlus } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Tableau } from '@/components/ui/donnees';
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
} from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, ErreurApi, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterDate, formaterDateHeure, formaterNombre, humaniser } from '@/lib/utils';
import type { Affectation, Etablissement, Utilisateur } from '@/types/api';

interface Role {
  id: string;
  code: string;
  libelle: string;
  niveau_scope: string;
}

interface Structure {
  id: string;
  code: string;
  libelle: string;
  sigle: string | null;
  categorie: string;
}

interface DetailCompte extends Utilisateur {
  affectations: Affectation[];
}

/** Portées demandant qu'une structure ou un établissement soit désigné. */
const PORTEE_STRUCTURE = new Set(['MINISTERE', 'DIRECTION', 'DEPARTEMENT']);
const PORTEE_ETABLISSEMENT = new Set(['ETABLISSEMENT', 'CLASSE']);

interface StatistiquesComptes {
  total: number;
  actifs: number;
  inactifs: number;
  deja_connectes: number;
  par_role: Array<{ code: string; libelle: string; comptes: number }>;
}

export default function PageComptes() {
  const fileAttente = useQueryClient();
  const { peut, utilisateur } = useSession();

  const [compteId, setCompteId] = useState<string | null>(null);
  const [roleCode, setRoleCode] = useState('');
  const [portee, setPortee] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [provisoire, setProvisoire] = useState<string | null>(null);

  const liste = useListe<Utilisateur>('/utilisateurs', { tri: 'nom' });

  const statistiques = useQuery({
    queryKey: ['statistiques-comptes'],
    queryFn: () => api.get<StatistiquesComptes>('/statistiques/comptes'),
  });

  const roles = useQuery({
    queryKey: ['roles'],
    queryFn: () => api.get<Page<Role>>('/roles', { size: 50 }),
    enabled: peut('roles', 'READ'),
  });

  const structures = useQuery({
    queryKey: ['structures-liste'],
    queryFn: () => api.get<Page<Structure>>('/structures', { size: 100 }),
    enabled: peut('structures', 'READ'),
  });

  const etablissements = useQuery({
    queryKey: ['etablissements-liste'],
    queryFn: () => api.get<Page<Etablissement>>('/etablissements', { size: 200, sort_by: 'nom' }),
  });

  const detail = useQuery({
    queryKey: ['compte-detail', compteId],
    queryFn: () => api.get<DetailCompte>(`/utilisateurs/${compteId}/detail`),
    enabled: Boolean(compteId),
  });

  const role = (roles.data?.items ?? []).find((element) => element.code === roleCode) ?? null;
  const demandeStructure = role ? PORTEE_STRUCTURE.has(role.niveau_scope) : false;
  const demandeEtablissement = role ? PORTEE_ETABLISSEMENT.has(role.niveau_scope) : false;

  function signaler(erreurBrute: unknown, defaut: string) {
    setMessage(null);
    setProvisoire(null);
    setErreur(erreurBrute instanceof ErreurApi ? erreurBrute.message : defaut);
  }

  function rafraichir() {
    void fileAttente.invalidateQueries({ queryKey: ['compte-detail', compteId] });
    void fileAttente.invalidateQueries({ queryKey: ['statistiques-comptes'] });
  }

  const attribuer = useMutation({
    mutationFn: () =>
      api.post<{ message: string }>(`/utilisateurs/${compteId}/roles`, {
        role_code: roleCode,
        structure_id: demandeStructure ? portee || null : null,
        etablissement_id: demandeEtablissement ? portee || null : null,
      }),
    onSuccess: (reponse) => {
      setErreur(null);
      setMessage(reponse.message);
      setRoleCode('');
      setPortee('');
      rafraichir();
    },
    onError: (e) => signaler(e, "Le rôle n'a pas pu être attribué."),
  });

  const retirer = useMutation({
    mutationFn: (affectation: Affectation) =>
      api.delete<{ message: string }>(`/utilisateurs/${compteId}/roles/${affectation.id}`),
    onSuccess: () => {
      setErreur(null);
      setMessage('Rôle retiré.');
      rafraichir();
    },
    onError: (e) => signaler(e, "Le rôle n'a pas pu être retiré."),
  });

  const reinitialiser = useMutation({
    mutationFn: () =>
      api.post<{ message: string; mot_de_passe_provisoire: string; changement_requis: boolean }>(
        `/utilisateurs/${compteId}/reinitialiser-mot-de-passe`,
        { forcer_changement: true },
      ),
    onSuccess: (reponse) => {
      setErreur(null);
      setMessage(null);
      // Le mot de passe provisoire n'est renvoyé qu'une fois : il est affiché
      // à part, pour être transmis à la personne avant de quitter l'écran.
      setProvisoire(reponse.mot_de_passe_provisoire);
      rafraichir();
    },
    onError: (e) => signaler(e, "Le mot de passe n'a pas pu être réinitialisé."),
  });

  function nomPortee(affectation: Affectation): string {
    if (affectation.structure_id) {
      const structure = (structures.data?.items ?? []).find(
        (element) => element.id === affectation.structure_id,
      );
      return structure ? (structure.sigle ?? structure.libelle) : 'Structure';
    }
    if (affectation.etablissement_id) {
      const etablissement = (etablissements.data?.items ?? []).find(
        (element) => element.id === affectation.etablissement_id,
      );
      return etablissement?.nom ?? 'Établissement';
    }
    return 'Portée nationale';
  }

  return (
    <>
      <EntetePage
        titre="Comptes et rôles"
        description="Utilisateurs de la plateforme, leurs rôles et leur portée institutionnelle. Un rôle s'exerce toujours dans un périmètre : national, ministériel, départemental ou dans un établissement."
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
      {provisoire ? (
        <div
          role="status"
          className="mb-4 rounded-lg border border-[rgb(var(--alerte))]/40 bg-[rgb(var(--alerte))]/10 px-4 py-3 text-sm"
        >
          <p className="font-medium">
            Mot de passe provisoire — à communiquer maintenant, il ne sera plus affiché.
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-3">
            <code className="rounded bg-[rgb(var(--fond-carte))] px-2 py-1 font-mono text-base">
              {provisoire}
            </code>
            <Bouton variante="fantome" taille="sm" onClick={() => setProvisoire(null)}>
              Masquer
            </Bouton>
          </p>
          <p className="mt-1 texte-doux">La personne devra le changer à sa première connexion.</p>
        </div>
      ) : null}

      {statistiques.data ? (
        <div className="mb-4 grid gap-4 xl:grid-cols-[1fr_22rem]">
          <Carte>
            <EnteteCarte titre="Répartition par rôle" />
            <Tableau
              legende="Comptes par rôle"
              lignes={statistiques.data.par_role.filter((ligne) => ligne.comptes > 0)}
              cleLigne={(ligne) => ligne.code}
              colonnes={[
                { cle: 'libelle', entete: 'Rôle', rendu: (ligne) => ligne.libelle },
                {
                  cle: 'code',
                  entete: 'Code',
                  secondaire: true,
                  rendu: (ligne) => <span className="font-mono text-xs">{ligne.code}</span>,
                },
                {
                  cle: 'comptes',
                  entete: 'Comptes',
                  alignement: 'droite',
                  rendu: (ligne) => formaterNombre(ligne.comptes),
                },
              ]}
            />
          </Carte>

          <Carte className="h-fit">
            <EnteteCarte titre="Vue d'ensemble" />
            <CorpsCarte>
              <dl className="space-y-2.5 text-sm">
                {[
                  { terme: 'Comptes enregistrés', valeur: statistiques.data.total },
                  { terme: 'Comptes actifs', valeur: statistiques.data.actifs },
                  { terme: 'Comptes désactivés', valeur: statistiques.data.inactifs },
                  { terme: 'Déjà connectés', valeur: statistiques.data.deja_connectes },
                ].map((entree) => (
                  <div key={entree.terme} className="flex items-center justify-between gap-2">
                    <dt className="texte-doux">{entree.terme}</dt>
                    <dd className="font-semibold tabular-nums">{formaterNombre(entree.valeur)}</dd>
                  </div>
                ))}
              </dl>
            </CorpsCarte>
          </Carte>
        </div>
      ) : null}

      <ListeRessource
        legende="Liste des comptes"
        placeholderRecherche="Rechercher par adresse, nom ou téléphone…"
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
        cleLigne={(compte) => compte.id}
        onLigneClic={(compte) => {
          setCompteId(compte.id);
          setRoleCode('');
          setPortee('');
          setMessage(null);
          setErreur(null);
          setProvisoire(null);
        }}
        videTitre="Aucun compte"
        colonnes={[
          {
            cle: 'nom',
            entete: 'Utilisateur',
            rendu: (compte) => (
              <div className="min-w-0">
                <p className="font-medium">{compte.nom_complet}</p>
                <p className="truncate text-xs texte-doux">{compte.email}</p>
              </div>
            ),
          },
          {
            cle: 'connexion',
            entete: 'Dernière connexion',
            secondaire: true,
            rendu: (compte) =>
              compte.derniere_connexion ? formaterDateHeure(compte.derniere_connexion) : 'Jamais',
          },
          {
            cle: 'accessibilite',
            entete: 'Accessibilité',
            secondaire: true,
            rendu: (compte) => (
              <span className="flex flex-wrap gap-1.5">
                {compte.mode_simplifie ? <Badge ton="info">Simplifié</Badge> : null}
                {compte.contraste_eleve ? <Badge ton="info">Contraste</Badge> : null}
                {compte.grande_police ? <Badge ton="info">Grande police</Badge> : null}
                {compte.lecture_vocale ? <Badge ton="info">Vocal</Badge> : null}
              </span>
            ),
          },
          {
            cle: 'statut',
            entete: 'Statut',
            rendu: (compte) => (
              <span className="flex flex-wrap items-center gap-2">
                <Badge ton={compte.actif ? 'succes' : 'danger'}>
                  {compte.actif ? 'Actif' : 'Désactivé'}
                </Badge>
                {compte.doit_changer_mot_de_passe ? (
                  <Badge ton="alerte">
                    <KeyRound size={13} aria-hidden /> Mot de passe à changer
                  </Badge>
                ) : null}
              </span>
            ),
          },
        ]}
      />

      {compteId ? (
        <Carte className="mt-4">
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <ShieldCheck size={19} aria-hidden />{' '}
                {detail.data?.nom_complet ?? 'Chargement du compte…'}
              </span>
            }
            description={detail.data?.email}
            action={
              <span className="flex flex-wrap items-center gap-2">
                {peut('utilisateurs', 'UPDATE') ? (
                  <Bouton
                    variante="secondaire"
                    taille="sm"
                    icone={<KeyRound size={16} aria-hidden />}
                    chargement={reinitialiser.isPending}
                    disabled={detail.data?.id === utilisateur?.id}
                    onClick={() => reinitialiser.mutate()}
                  >
                    Réinitialiser le mot de passe
                  </Bouton>
                ) : null}
                <Bouton variante="fantome" taille="sm" onClick={() => setCompteId(null)}>
                  Fermer
                </Bouton>
              </span>
            }
          />

          {detail.isLoading ? (
            <CorpsCarte>
              <Chargement libelle="Chargement du compte…" />
            </CorpsCarte>
          ) : (
            <>
              <Tableau
                legende="Rôles exercés par le compte"
                lignes={detail.data?.affectations ?? []}
                cleLigne={(affectation) => affectation.id}
                vide={<EtatVide titre="Aucun rôle attribué" />}
                colonnes={[
                  {
                    cle: 'role',
                    entete: 'Rôle',
                    rendu: (affectation) => (
                      <span className="min-w-0">
                        <span className="block font-medium">{affectation.role.libelle}</span>
                        <span className="block font-mono text-xs texte-doux">
                          {affectation.role.code}
                        </span>
                      </span>
                    ),
                  },
                  {
                    cle: 'portee',
                    entete: 'Portée',
                    rendu: (affectation) => (
                      <span className="flex flex-wrap items-center gap-2">
                        <Badge ton="neutre">{humaniser(affectation.role.niveau_scope)}</Badge>
                        <span className="texte-doux">{nomPortee(affectation)}</span>
                      </span>
                    ),
                  },
                  {
                    cle: 'actif',
                    entete: 'État',
                    rendu: (affectation) => (
                      <Badge ton={affectation.actif ? 'succes' : 'neutre'}>
                        {affectation.actif ? 'Active' : 'Suspendue'}
                      </Badge>
                    ),
                  },
                  {
                    cle: 'actions',
                    entete: 'Actions',
                    alignement: 'droite',
                    rendu: (affectation) => (
                      <Bouton
                        variante="fantome"
                        taille="sm"
                        icone={<Trash2 size={15} aria-hidden />}
                        disabled={!peut('roles', 'ASSIGN') || retirer.isPending}
                        onClick={() => retirer.mutate(affectation)}
                      >
                        Retirer
                      </Bouton>
                    ),
                  },
                ]}
              />

              {peut('roles', 'ASSIGN') ? (
                <CorpsCarte className="border-t">
                  <h3 className="mb-3 flex items-center gap-2 font-medium">
                    <UserPlus size={17} aria-hidden /> Attribuer un rôle
                  </h3>
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    <Selection
                      etiquette="Rôle"
                      value={roleCode}
                      onChange={(evenement) => {
                        setRoleCode(evenement.target.value);
                        setPortee('');
                      }}
                      options={[
                        { valeur: '', libelle: 'Choisir un rôle…' },
                        ...(roles.data?.items ?? []).map((element) => ({
                          valeur: element.code,
                          libelle: `${element.libelle} (${humaniser(element.niveau_scope)})`,
                        })),
                      ]}
                    />
                    {demandeStructure ? (
                      <Selection
                        etiquette="Structure"
                        aide="Ministère, direction nationale ou direction départementale."
                        value={portee}
                        onChange={(evenement) => setPortee(evenement.target.value)}
                        options={[
                          { valeur: '', libelle: 'Aucune — portée nationale' },
                          ...(structures.data?.items ?? []).map((element) => ({
                            valeur: element.id,
                            libelle: element.sigle ?? element.libelle,
                          })),
                        ]}
                      />
                    ) : null}
                    {demandeEtablissement ? (
                      <Selection
                        etiquette="Établissement"
                        value={portee}
                        onChange={(evenement) => setPortee(evenement.target.value)}
                        options={[
                          { valeur: '', libelle: 'Choisir un établissement…' },
                          ...(etablissements.data?.items ?? []).map((element) => ({
                            valeur: element.id,
                            libelle: element.nom,
                          })),
                        ]}
                      />
                    ) : null}
                  </div>
                  <Bouton
                    className="mt-3"
                    disabled={!roleCode || (demandeEtablissement && !portee)}
                    chargement={attribuer.isPending}
                    onClick={() => attribuer.mutate()}
                  >
                    Attribuer
                  </Bouton>
                  {role ? (
                    <p className="mt-2 text-xs texte-doux">
                      Portée du rôle : {humaniser(role.niveau_scope)}.
                      {demandeStructure || demandeEtablissement
                        ? ' Le périmètre désigné borne tout ce que le compte pourra voir et modifier.'
                        : " Ce rôle s'exerce sans périmètre restreint."}
                    </p>
                  ) : null}
                </CorpsCarte>
              ) : null}

              <CorpsCarte className="border-t">
                <h3 className="mb-2 font-medium">
                  Permissions effectives — {detail.data?.permissions.length ?? 0}
                </h3>
                <p className="mb-3 text-sm texte-doux">
                  Résultat cumulé des rôles ci-dessus, au format ressource:action.
                  {detail.data?.derniere_connexion
                    ? ` Dernière connexion le ${formaterDate(detail.data.derniere_connexion)}.`
                    : ' Ce compte ne s’est jamais connecté.'}
                </p>
                <ul className="flex flex-wrap gap-1.5">
                  {(detail.data?.permissions ?? []).map((permission) => (
                    <li key={permission}>
                      <Badge ton="neutre">
                        <span className="font-mono text-xs">{permission}</span>
                      </Badge>
                    </li>
                  ))}
                </ul>
              </CorpsCarte>
            </>
          )}
        </Carte>
      ) : null}
    </>
  );
}
