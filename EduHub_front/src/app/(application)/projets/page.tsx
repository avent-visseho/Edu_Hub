'use client';

import { Lightbulb, Users } from 'lucide-react';

import { EntetePage } from '@/components/layout/entete-page';
import { Jauge } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { formaterDate, formaterMontant, humaniser } from '@/lib/utils';

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
  const liste = useListe<Projet>('/projets', { tri: 'titre' });

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
            rendu: (projet) => (
              <span className="flex flex-wrap items-center gap-2">
                <Badge ton={tonDuStatut(projet.statut)}>{humaniser(projet.statut)}</Badge>
                {projet.ouvert_candidatures && projet.places_disponibles > 0 ? (
                  <Badge ton="info">
                    <Users size={13} aria-hidden /> {projet.places_disponibles} place(s)
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
