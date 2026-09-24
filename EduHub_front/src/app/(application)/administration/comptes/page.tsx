'use client';

import { useQuery } from '@tanstack/react-query';
import { KeyRound } from 'lucide-react';

import { EntetePage } from '@/components/layout/entete-page';
import { Tableau } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Carte, CorpsCarte, EnteteCarte } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api } from '@/lib/api';
import { formaterDateHeure, formaterNombre } from '@/lib/utils';
import type { Utilisateur } from '@/types/api';

interface StatistiquesComptes {
  total: number;
  actifs: number;
  inactifs: number;
  deja_connectes: number;
  par_role: Array<{ code: string; libelle: string; comptes: number }>;
}

export default function PageComptes() {
  const liste = useListe<Utilisateur>('/utilisateurs', { tri: 'nom' });

  const statistiques = useQuery({
    queryKey: ['statistiques-comptes'],
    queryFn: () => api.get<StatistiquesComptes>('/statistiques/comptes'),
  });

  return (
    <>
      <EntetePage
        titre="Comptes et rôles"
        description="Utilisateurs de la plateforme, leurs rôles et leur portée institutionnelle."
      />

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
                    <dd className="font-semibold tabular-nums">
                      {formaterNombre(entree.valeur)}
                    </dd>
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
        cleLigne={(utilisateur) => utilisateur.id}
        videTitre="Aucun compte"
        colonnes={[
          {
            cle: 'nom',
            entete: 'Utilisateur',
            rendu: (utilisateur) => (
              <div className="min-w-0">
                <p className="font-medium">{utilisateur.nom_complet}</p>
                <p className="truncate text-xs texte-doux">{utilisateur.email}</p>
              </div>
            ),
          },
          {
            cle: 'connexion',
            entete: 'Dernière connexion',
            secondaire: true,
            rendu: (utilisateur) =>
              utilisateur.derniere_connexion
                ? formaterDateHeure(utilisateur.derniere_connexion)
                : 'Jamais',
          },
          {
            cle: 'accessibilite',
            entete: 'Accessibilité',
            secondaire: true,
            rendu: (utilisateur) => (
              <span className="flex flex-wrap gap-1.5">
                {utilisateur.mode_simplifie ? <Badge ton="info">Simplifié</Badge> : null}
                {utilisateur.contraste_eleve ? <Badge ton="info">Contraste</Badge> : null}
                {utilisateur.grande_police ? <Badge ton="info">Grande police</Badge> : null}
                {utilisateur.lecture_vocale ? <Badge ton="info">Vocal</Badge> : null}
              </span>
            ),
          },
          {
            cle: 'statut',
            entete: 'Statut',
            rendu: (utilisateur) => (
              <span className="flex flex-wrap items-center gap-2">
                <Badge ton={utilisateur.actif ? 'succes' : 'danger'}>
                  {utilisateur.actif ? 'Actif' : 'Désactivé'}
                </Badge>
                {utilisateur.doit_changer_mot_de_passe ? (
                  <Badge ton="alerte">
                    <KeyRound size={13} aria-hidden /> Mot de passe à changer
                  </Badge>
                ) : null}
              </span>
            ),
          },
        ]}
      />
    </>
  );
}
