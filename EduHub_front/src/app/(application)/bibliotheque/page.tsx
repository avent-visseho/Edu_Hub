'use client';

import { BookOpen, Headphones, Hand } from 'lucide-react';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeRessource } from '@/components/ui/liste';
import { Badge } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import type { LivreLecture } from '@/types/bibliotheque';

export default function PageBibliotheque() {
  const liste = useListe<LivreLecture>('/bibliotheque/livres', { tri: 'titre' });

  return (
    <>
      <EntetePage
        titre="Bibliothèque"
        description="Catalogue des ouvrages, avec leurs formats accessibles : version audio, braille et gros caractères."
      />

      <ListeRessource
        legende="Catalogue de la bibliothèque"
        placeholderRecherche="Rechercher par titre, auteur ou ISBN…"
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
        cleLigne={(livre) => livre.id}
        videTitre="Aucun ouvrage"
        colonnes={[
          {
            cle: 'titre',
            entete: 'Ouvrage',
            rendu: (livre) => (
              <div className="min-w-0">
                <p className="font-medium">{livre.titre}</p>
                <p className="truncate text-xs texte-doux">{livre.auteur}</p>
              </div>
            ),
          },
          {
            cle: 'categorie',
            entete: 'Catégorie',
            secondaire: true,
            rendu: (livre) => livre.categorie ?? '—',
          },
          {
            cle: 'editeur',
            entete: 'Éditeur',
            secondaire: true,
            rendu: (livre) => livre.editeur ?? '—',
          },
          {
            cle: 'annee',
            entete: 'Année',
            alignement: 'droite',
            secondaire: true,
            rendu: (livre) => livre.annee_publication ?? '—',
          },
          {
            cle: 'accessibilite',
            entete: 'Formats accessibles',
            rendu: (livre) => (
              <span className="flex flex-wrap gap-1.5">
                {livre.format_accessible ? (
                  <Badge ton="info">
                    <BookOpen size={13} aria-hidden /> Gros caractères
                  </Badge>
                ) : null}
                {livre.audio_disponible ? (
                  <Badge ton="succes">
                    <Headphones size={13} aria-hidden /> Audio
                  </Badge>
                ) : null}
                {livre.braille_disponible ? (
                  <Badge ton="succes">
                    <Hand size={13} aria-hidden /> Braille
                  </Badge>
                ) : null}
                {!livre.format_accessible && !livre.audio_disponible && !livre.braille_disponible ? (
                  <span className="texte-doux">—</span>
                ) : null}
              </span>
            ),
          },
        ]}
      />
    </>
  );
}
