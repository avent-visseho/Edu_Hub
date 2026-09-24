'use client';

import { useRouter } from 'next/navigation';

import { EntetePage } from '@/components/layout/entete-page';
import { Jauge } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import { useListe } from '@/hooks/useListe';
import { formaterNote } from '@/lib/utils';
import type { Classe } from '@/types/api';

export default function PageClasses() {
  const router = useRouter();
  const liste = useListe<Classe>('/classes', { tri: 'code' });

  return (
    <>
      <EntetePage
        titre="Classes"
        description="Divisions ouvertes pour l'année académique en cours, avec leur effectif et leur moyenne."
      />

      <ListeRessource
        legende="Liste des classes"
        placeholderRecherche="Rechercher par code ou libellé…"
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
        cleLigne={(classe) => classe.id}
        onLigneClic={(classe) => router.push(`/classes/${classe.id}`)}
        videTitre="Aucune classe"
        colonnes={[
          {
            cle: 'libelle',
            entete: 'Classe',
            rendu: (classe) => (
              <div className="min-w-0">
                <p className="font-medium">{classe.libelle}</p>
                <p className="truncate font-mono text-xs texte-doux">{classe.code}</p>
              </div>
            ),
          },
          {
            cle: 'effectif',
            entete: 'Effectif',
            largeur: '18rem',
            rendu: (classe) => (
              <Jauge
                valeur={classe.effectif}
                maximum={classe.effectif_max}
                etiquette={`${classe.effectif} / ${classe.effectif_max} élèves`}
                ton={
                  classe.effectif > classe.effectif_max
                    ? 'danger'
                    : classe.effectif > classe.effectif_max * 0.9
                      ? 'alerte'
                      : 'accent'
                }
              />
            ),
          },
          {
            cle: 'moyenne',
            entete: 'Moyenne de classe',
            alignement: 'droite',
            rendu: (classe) => (
              <span className="font-semibold">{formaterNote(classe.moyenne_classe)}</span>
            ),
          },
        ]}
      />
    </>
  );
}
