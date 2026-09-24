'use client';

import { useRouter } from 'next/navigation';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeRessource } from '@/components/ui/liste';
import { Badge } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { formaterNombre, humaniser } from '@/lib/utils';
import type { Etablissement } from '@/types/api';

export default function PageEtablissements() {
  const router = useRouter();
  const liste = useListe<Etablissement>('/etablissements', { tri: 'nom' });

  return (
    <>
      <EntetePage
        titre="Établissements"
        description="Écoles, collèges, lycées, centres de formation et universités enregistrés."
      />

      <ListeRessource
        legende="Liste des établissements"
        placeholderRecherche="Rechercher par nom, code ou directeur…"
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
        cleLigne={(etablissement) => etablissement.id}
        onLigneClic={(etablissement) => router.push(`/etablissements/${etablissement.id}`)}
        videTitre="Aucun établissement"
        colonnes={[
          {
            cle: 'code',
            entete: 'Code',
            rendu: (etablissement) => (
              <span className="font-mono text-xs">{etablissement.code}</span>
            ),
          },
          {
            cle: 'nom',
            entete: 'Établissement',
            rendu: (etablissement) => (
              <div className="min-w-0">
                <p className="font-medium">{etablissement.nom}</p>
                {etablissement.directeur_nom ? (
                  <p className="truncate text-xs texte-doux">{etablissement.directeur_nom}</p>
                ) : null}
              </div>
            ),
          },
          {
            cle: 'effectif',
            entete: 'Effectif',
            alignement: 'droite',
            rendu: (etablissement) => formaterNombre(etablissement.effectif_actuel),
          },
          {
            cle: 'capacite',
            entete: 'Capacité',
            alignement: 'droite',
            secondaire: true,
            rendu: (etablissement) => formaterNombre(etablissement.capacite_accueil),
          },
          {
            cle: 'services',
            entete: 'Services',
            secondaire: true,
            rendu: (etablissement) => (
              <span className="flex flex-wrap gap-1">
                {etablissement.electricite ? <Badge ton="neutre">Électricité</Badge> : null}
                {etablissement.eau_potable ? <Badge ton="neutre">Eau</Badge> : null}
                {etablissement.connexion_internet ? <Badge ton="neutre">Internet</Badge> : null}
                {etablissement.cantine ? <Badge ton="neutre">Cantine</Badge> : null}
              </span>
            ),
          },
          {
            cle: 'accessibilite',
            entete: 'Accessibilité',
            rendu: (etablissement) => (
              <Badge
                ton={
                  etablissement.accessibilite === 'NON_ACCESSIBLE'
                    ? 'danger'
                    : etablissement.accessibilite === 'PARTIELLEMENT'
                      ? 'alerte'
                      : 'succes'
                }
              >
                {humaniser(etablissement.accessibilite)}
              </Badge>
            ),
          },
          {
            cle: 'centre',
            entete: "Centre d'examen",
            alignement: 'centre',
            secondaire: true,
            rendu: (etablissement) =>
              etablissement.est_centre_examen ? <Badge ton="info">Oui</Badge> : <span className="texte-doux">—</span>,
          },
        ]}
      />
    </>
  );
}
