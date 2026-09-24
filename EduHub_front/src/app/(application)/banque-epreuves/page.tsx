'use client';

import { Download } from 'lucide-react';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Bouton } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { formaterNombre, humaniser } from '@/lib/utils';

interface EpreuveArchivee {
  id: string;
  reference: string;
  titre: string;
  nature: string;
  annee: number;
  duree_minutes: number | null;
  coefficient: number | null;
  sujet_url: string | null;
  corrige_url: string | null;
  mots_cles: string | null;
  nombre_telechargements: number;
  public: boolean;
}

export default function PageBanqueEpreuves() {
  const liste = useListe<EpreuveArchivee>('/banque-epreuves', { tri: 'annee' });

  return (
    <>
      <EntetePage
        titre="Banque d'épreuves"
        description="Sujets archivés des examens, concours et examens blancs — classés par filière, niveau, matière et session."
      />

      <ListeRessource
        legende="Banque d'épreuves archivées"
        placeholderRecherche="Rechercher par titre, référence ou mot-clé…"
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
        cleLigne={(epreuve) => epreuve.id}
        videTitre="Aucune épreuve archivée"
        colonnes={[
          {
            cle: 'titre',
            entete: 'Épreuve',
            rendu: (epreuve) => (
              <div className="min-w-0">
                <p className="font-medium">{epreuve.titre}</p>
                <p className="truncate font-mono text-xs texte-doux">{epreuve.reference}</p>
              </div>
            ),
          },
          {
            cle: 'nature',
            entete: 'Nature',
            secondaire: true,
            rendu: (epreuve) => <Badge ton="neutre">{humaniser(epreuve.nature)}</Badge>,
          },
          {
            cle: 'annee',
            entete: 'Année',
            alignement: 'droite',
            rendu: (epreuve) => epreuve.annee,
          },
          {
            cle: 'duree',
            entete: 'Durée',
            alignement: 'droite',
            secondaire: true,
            rendu: (epreuve) => (epreuve.duree_minutes ? `${epreuve.duree_minutes} min` : '—'),
          },
          {
            cle: 'coefficient',
            entete: 'Coef.',
            alignement: 'centre',
            secondaire: true,
            rendu: (epreuve) => epreuve.coefficient ?? '—',
          },
          {
            cle: 'telechargements',
            entete: 'Téléchargements',
            alignement: 'droite',
            secondaire: true,
            rendu: (epreuve) => formaterNombre(epreuve.nombre_telechargements),
          },
          {
            cle: 'actions',
            entete: 'Sujet',
            alignement: 'centre',
            rendu: () => (
              <Bouton variante="fantome" taille="sm" aria-label="Télécharger le sujet" disabled>
                <Download size={16} aria-hidden />
              </Bouton>
            ),
          },
        ]}
      />
    </>
  );
}
