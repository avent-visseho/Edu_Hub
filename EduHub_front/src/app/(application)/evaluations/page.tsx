'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Selection, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterDate, formaterNote, humaniser } from '@/lib/utils';
import type { Classe } from '@/types/api';

interface Evaluation {
  id: string;
  code: string;
  intitule: string;
  classe_id: string;
  classe_libelle: string | null;
  matiere_id: string;
  matiere_libelle: string | null;
  type_evaluation: string;
  date_evaluation: string;
  bareme: number;
  coefficient: number;
  statut: string;
  moyenne: number | null;
  note_min: number | null;
  note_max: number | null;
  nombre_notes: number;
}

export default function PageEvaluations() {
  const router = useRouter();
  const [classeId, setClasseId] = useState('');

  const classes = useQuery({
    queryKey: ['classes-resume'],
    queryFn: () => api.get<Page<Classe>>('/classes', { size: 200 }),
  });

  const liste = useListe<Evaluation>('/evaluations', {
    tri: 'date_evaluation',
    filtres: { classe_id: classeId || undefined },
  });

  return (
    <>
      <EntetePage
        titre="Évaluations"
        description="Devoirs, interrogations et contrôles continus, de la planification à la publication des notes."
      />

      <ListeRessource
        legende="Liste des évaluations"
        placeholderRecherche="Rechercher une évaluation…"
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
        cleLigne={(evaluation) => evaluation.id}
        onLigneClic={(evaluation) => router.push(`/evaluations/${evaluation.id}`)}
        videTitre="Aucune évaluation"
        videDescription="Les évaluations planifiées par les enseignants apparaîtront ici."
        filtres={
          <Selection
            etiquette="Classe"
            value={classeId}
            onChange={(evenement) => setClasseId(evenement.target.value)}
            options={[
              { valeur: '', libelle: 'Toutes les classes' },
              ...(classes.data?.items ?? []).map((classe) => ({
                valeur: classe.id,
                libelle: classe.libelle,
              })),
            ]}
          />
        }
        colonnes={[
          {
            cle: 'intitule',
            entete: 'Évaluation',
            rendu: (evaluation) => (
              <div className="min-w-0">
                <p className="font-medium">{evaluation.intitule}</p>
                <p className="truncate text-xs texte-doux">
                  {[evaluation.matiere_libelle, evaluation.classe_libelle]
                    .filter(Boolean)
                    .join(' · ') || evaluation.code}
                </p>
              </div>
            ),
          },
          {
            cle: 'type',
            entete: 'Type',
            secondaire: true,
            rendu: (evaluation) => (
              <Badge ton="neutre">{humaniser(evaluation.type_evaluation)}</Badge>
            ),
          },
          {
            cle: 'date',
            entete: 'Date',
            rendu: (evaluation) => formaterDate(evaluation.date_evaluation),
          },
          {
            cle: 'bareme',
            entete: 'Barème · coef.',
            alignement: 'centre',
            secondaire: true,
            rendu: (evaluation) => `/${evaluation.bareme} · coef. ${evaluation.coefficient}`,
          },
          {
            cle: 'moyenne',
            entete: 'Moyenne',
            alignement: 'droite',
            rendu: (evaluation) => (
              <span className="font-semibold">{formaterNote(evaluation.moyenne)}</span>
            ),
          },
          {
            cle: 'notes',
            entete: 'Notes saisies',
            alignement: 'droite',
            secondaire: true,
            rendu: (evaluation) => evaluation.nombre_notes,
          },
          {
            cle: 'statut',
            entete: 'Statut',
            rendu: (evaluation) => (
              <Badge ton={tonDuStatut(evaluation.statut)}>{humaniser(evaluation.statut)}</Badge>
            ),
          },
        ]}
      />
    </>
  );
}
