'use client';

import { useRouter } from 'next/navigation';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { humaniser } from '@/lib/utils';

interface Enseignant {
  id: string;
  matricule: string;
  nom_complet: string;
  sexe: string;
  grade: string | null;
  specialite: string | null;
  statut_agent: string;
  situation: string;
  heures_hebdomadaires: number;
  anciennete_annees: number;
  peut_corriger: boolean;
  peut_surveiller: boolean;
  peut_presider_jury: boolean;
}

export default function PageEnseignants() {
  const router = useRouter();
  const liste = useListe<Enseignant>('/enseignants', { tri: 'nom' });

  return (
    <>
      <EntetePage
        titre="Enseignants"
        description="Corps enseignant, qualifications, affectations et aptitudes aux examens."
      />

      <ListeRessource
        legende="Liste des enseignants"
        placeholderRecherche="Rechercher par nom, matricule ou spécialité…"
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
        cleLigne={(enseignant) => enseignant.id}
        onLigneClic={(enseignant) => router.push(`/enseignants/${enseignant.id}`)}
        videTitre="Aucun enseignant"
        colonnes={[
          {
            cle: 'matricule',
            entete: 'Matricule',
            rendu: (enseignant) => (
              <span className="font-mono text-xs">{enseignant.matricule}</span>
            ),
          },
          {
            cle: 'nom',
            entete: 'Nom et prénoms',
            rendu: (enseignant) => <span className="font-medium">{enseignant.nom_complet}</span>,
          },
          {
            cle: 'specialite',
            entete: 'Spécialité',
            secondaire: true,
            rendu: (enseignant) => enseignant.specialite ?? '—',
          },
          {
            cle: 'grade',
            entete: 'Grade',
            secondaire: true,
            rendu: (enseignant) => enseignant.grade ?? '—',
          },
          {
            cle: 'anciennete',
            entete: 'Ancienneté',
            alignement: 'droite',
            secondaire: true,
            rendu: (enseignant) => `${enseignant.anciennete_annees} an(s)`,
          },
          {
            cle: 'aptitudes',
            entete: 'Aptitudes examens',
            secondaire: true,
            rendu: (enseignant) => (
              <span className="flex flex-wrap gap-1">
                {enseignant.peut_surveiller ? <Badge ton="neutre">Surveillance</Badge> : null}
                {enseignant.peut_corriger ? <Badge ton="neutre">Correction</Badge> : null}
                {enseignant.peut_presider_jury ? <Badge ton="info">Jury</Badge> : null}
              </span>
            ),
          },
          {
            cle: 'situation',
            entete: 'Situation',
            rendu: (enseignant) => (
              <Badge ton={tonDuStatut(enseignant.situation)}>
                {humaniser(enseignant.situation)}
              </Badge>
            ),
          },
        ]}
      />
    </>
  );
}
