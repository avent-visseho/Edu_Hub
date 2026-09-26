'use client';

import { useRouter } from 'next/navigation';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { formaterDate, humaniser } from '@/lib/utils';
import type { Apprenant } from '@/types/api';

export default function PageApprenants() {
  const router = useRouter();
  const liste = useListe<Apprenant>('/apprenants', { tri: 'nom' });

  return (
    <>
      <EntetePage
        titre="Apprenants"
        description="Élèves et étudiants inscrits dans le système, identifiés par leur identifiant éducatif national."
        personnel={{
          titre: 'Mon dossier',
          description: 'Votre fiche scolaire : état civil, inscription et parcours.',
        }}
      />

      <ListeRessource
        legende="Liste des apprenants"
        placeholderRecherche="Rechercher par nom, prénoms ou identifiant éducatif…"
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
        cleLigne={(apprenant) => apprenant.id}
        onLigneClic={(apprenant) => router.push(`/apprenants/${apprenant.id}`)}
        videTitre="Aucun apprenant"
        videDescription="Aucun apprenant ne correspond à cette recherche."
        colonnes={[
          {
            cle: 'identifiant',
            entete: 'Identifiant',
            rendu: (apprenant) => (
              <span className="font-mono text-xs">{apprenant.identifiant_educatif}</span>
            ),
          },
          {
            cle: 'nom',
            entete: 'Nom et prénoms',
            rendu: (apprenant) => <span className="font-medium">{apprenant.nom_complet}</span>,
          },
          {
            cle: 'sexe',
            entete: 'Sexe',
            secondaire: true,
            rendu: (apprenant) => (apprenant.sexe === 'FEMININ' ? 'Féminin' : 'Masculin'),
          },
          {
            cle: 'naissance',
            entete: 'Date de naissance',
            secondaire: true,
            rendu: (apprenant) => formaterDate(apprenant.date_naissance),
          },
          {
            cle: 'besoins',
            entete: 'Besoin spécifique',
            secondaire: true,
            rendu: (apprenant) =>
              apprenant.type_handicap === 'AUCUN' ? (
                <span className="texte-doux">—</span>
              ) : (
                <Badge ton="info">{humaniser(apprenant.type_handicap)}</Badge>
              ),
          },
          {
            cle: 'statut',
            entete: 'Statut',
            rendu: (apprenant) => (
              <Badge ton={tonDuStatut(apprenant.statut)}>{humaniser(apprenant.statut)}</Badge>
            ),
          },
        ]}
      />
    </>
  );
}
