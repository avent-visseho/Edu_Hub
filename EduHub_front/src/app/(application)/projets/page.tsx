'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Lightbulb, UserPlus, Users } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Jauge } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import {
  Badge,
  Bouton,
  Carte,
  Champ,
  CorpsCarte,
  EnteteCarte,
  Selection,
  tonDuStatut,
} from '@/components/ui/primitives';
import {
  SelecteurApprenant,
  type ApprenantChoisi,
} from '@/components/ui/selecteur-apprenant';
import { useListe } from '@/hooks/useListe';
import { api, ErreurApi } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterDate, formaterMontant, humaniser } from '@/lib/utils';

/** Rôles qu'un membre peut tenir dans l'équipe d'un projet. */
const ROLES_MEMBRE = ['MEMBRE', 'PORTEUR', 'ENCADREUR', 'MENTOR', 'PARTENAIRE'];

interface Projet {
  id: string;
  code: string;
  titre: string;
  resume: string | null;
  domaine: string | null;
  statut: string;
  date_debut: string | null;
  date_fin_prevue: string | null;
  budget_prevu: number;
  budget_obtenu: number;
  places_disponibles: number;
  avancement_pourcentage: number;
  ouvert_candidatures: boolean;
}

export default function PageProjets() {
  const fileAttente = useQueryClient();
  const { peut } = useSession();
  const liste = useListe<Projet>('/projets', { tri: 'titre' });

  const [projet, setProjet] = useState<Projet | null>(null);
  const [apprenant, setApprenant] = useState<ApprenantChoisi | null>(null);
  const [role, setRole] = useState('MEMBRE');
  const [competences, setCompetences] = useState('');
  const [journal, setJournal] = useState<string | null>(null);

  const rejoindre = useMutation({
    mutationFn: () =>
      api.post<{ message: string }>(`/projets/${projet!.id}/rejoindre`, {
        apprenant_id: apprenant!.id,
        nom_complet: apprenant!.nom_complet,
        role,
        competences: competences || null,
      }),
    onSuccess: (reponse) => {
      setJournal(`${reponse.message} ${apprenant!.nom_complet} rejoint « ${projet!.titre} ».`);
      setApprenant(null);
      setCompetences('');
      setProjet(null);
      void fileAttente.invalidateQueries({ queryKey: ['/projets'] });
    },
    onError: (erreurBrute: unknown) => {
      setJournal(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "L'adhésion n'a pas pu être enregistrée.",
      );
    },
  });

  return (
    <>
      <EntetePage
        titre="Projets collaboratifs"
        description="Initiatives portées par les apprenants, les enseignants et les partenaires, avec leur état d'avancement."
      />

      <ListeRessource
        legende="Liste des projets"
        placeholderRecherche="Rechercher par titre, code ou domaine…"
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
        cleLigne={(projet) => projet.id}
        videTitre="Aucun projet"
        colonnes={[
          {
            cle: 'titre',
            entete: 'Projet',
            rendu: (projet) => (
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 font-medium">
                  <Lightbulb size={15} aria-hidden className="shrink-0 texte-doux" />
                  {projet.titre}
                </p>
                {projet.resume ? (
                  <p className="truncate text-xs texte-doux">{projet.resume}</p>
                ) : null}
              </div>
            ),
          },
          {
            cle: 'domaine',
            entete: 'Domaine',
            secondaire: true,
            rendu: (projet) => (projet.domaine ? <Badge ton="neutre">{projet.domaine}</Badge> : '—'),
          },
          {
            cle: 'avancement',
            entete: 'Avancement',
            largeur: '14rem',
            rendu: (projet) => (
              <Jauge
                valeur={projet.avancement_pourcentage}
                etiquette=""
                ton={
                  projet.avancement_pourcentage >= 75
                    ? 'succes'
                    : projet.avancement_pourcentage >= 30
                      ? 'accent'
                      : 'alerte'
                }
              />
            ),
          },
          {
            cle: 'budget',
            entete: 'Budget obtenu',
            alignement: 'droite',
            secondaire: true,
            rendu: (projet) => formaterMontant(projet.budget_obtenu),
          },
          {
            cle: 'echeance',
            entete: 'Échéance',
            secondaire: true,
            rendu: (projet) => formaterDate(projet.date_fin_prevue),
          },
          {
            cle: 'statut',
            entete: 'Statut',
            rendu: (element) => (
              <span className="flex flex-wrap items-center gap-2">
                <Badge ton={tonDuStatut(element.statut)}>{humaniser(element.statut)}</Badge>
                {element.ouvert_candidatures && element.places_disponibles > 0 ? (
                  <Badge ton="info">
                    <Users size={13} aria-hidden /> {element.places_disponibles} place(s)
                  </Badge>
                ) : null}
              </span>
            ),
          },
          {
            cle: 'adhesion',
            entete: 'Équipe',
            alignement: 'droite',
            rendu: (element) =>
              element.ouvert_candidatures && element.places_disponibles > 0 ? (
                <Bouton
                  taille="sm"
                  variante="secondaire"
                  disabled={!peut('projets', 'CREATE')}
                  onClick={() => {
                    setProjet(element);
                    setJournal(null);
                  }}
                >
                  Rejoindre
                </Bouton>
              ) : (
                <span className="texte-doux">Équipe close</span>
              ),
          },
        ]}
      />

      {journal ? (
        <p role="status" className="surface mt-4 rounded-lg border px-4 py-3 text-sm">
          {journal}
        </p>
      ) : null}

      {projet ? (
        <Carte className="mt-4">
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <UserPlus size={19} aria-hidden /> Rejoindre « {projet.titre} »
              </span>
            }
            description={`${projet.places_disponibles} place(s) encore disponible(s) dans l'équipe.`}
            action={
              <Bouton variante="fantome" taille="sm" onClick={() => setProjet(null)}>
                Fermer
              </Bouton>
            }
          />
          <CorpsCarte>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <SelecteurApprenant
                etiquette="Apprenant"
                choisi={apprenant}
                onChoisir={setApprenant}
              />
              <Selection
                etiquette="Rôle dans l'équipe"
                value={role}
                onChange={(evenement) => setRole(evenement.target.value)}
                options={ROLES_MEMBRE.map((valeur) => ({ valeur, libelle: humaniser(valeur) }))}
              />
              <Champ
                etiquette="Compétences apportées"
                placeholder="Programmation, dessin, médiation…"
                value={competences}
                onChange={(evenement) => setCompetences(evenement.target.value)}
              />
            </div>
            <Bouton
              className="mt-3"
              disabled={!apprenant}
              chargement={rejoindre.isPending}
              onClick={() => rejoindre.mutate()}
            >
              Enregistrer l&apos;adhésion
            </Bouton>
          </CorpsCarte>
        </Carte>
      ) : null}
    </>
  );
}
