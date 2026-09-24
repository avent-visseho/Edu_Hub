'use client';

import { useQuery } from '@tanstack/react-query';
import { HeartPulse, Syringe, Users } from 'lucide-react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur, Jauge, Tableau } from '@/components/ui/donnees';
import {
  Carte,
  Chargement,
  EnteteCarte,
  EtatVide,
  MessageErreur,
} from '@/components/ui/primitives';
import { ListeRessource } from '@/components/ui/liste';
import { useListe } from '@/hooks/useListe';
import { api } from '@/lib/api';
import { formaterDate, formaterNombre } from '@/lib/utils';

interface CentreSante {
  id: string;
  code: string;
  nom: string;
  services: string | null;
  telephone: string | null;
  nombre_agents: number;
  actif: boolean;
}

interface CampagneSante {
  id: string;
  code: string;
  intitule: string;
  theme: string | null;
  date_debut: string;
  date_fin: string;
  beneficiaires_cibles: number;
  beneficiaires_atteints: number;
}

export default function PageSante() {
  const centres = useListe<CentreSante>('/sante/centres', { tri: 'nom' });

  const campagnes = useQuery({
    queryKey: ['campagnes-sante'],
    queryFn: () => api.get<CampagneSante[]>('/sante/campagnes'),
  });

  if (centres.isLoading && campagnes.isLoading) {
    return <Chargement libelle="Chargement de la santé scolaire…" />;
  }
  if (campagnes.isError) return <MessageErreur erreur={campagnes.error} />;

  const listeCampagnes = campagnes.data ?? [];
  const cibles = listeCampagnes.reduce((total, c) => total + c.beneficiaires_cibles, 0);
  const atteints = listeCampagnes.reduce((total, c) => total + c.beneficiaires_atteints, 0);
  const agents = centres.items.reduce((total, c) => total + c.nombre_agents, 0);

  return (
    <>
      <EntetePage
        titre="Santé scolaire"
        description="Infirmeries, centres de santé et campagnes de prévention. Les données médicales individuelles restent hors du système."
      />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicateur
          libelle="Centres de santé"
          valeur={centres.total}
          icone={<HeartPulse size={18} />}
          pictogramme="🩺"
        />
        <Indicateur
          libelle="Agents de santé"
          valeur={agents}
          icone={<Users size={18} />}
          pictogramme="👩‍⚕️"
        />
        <Indicateur
          libelle="Campagnes"
          valeur={listeCampagnes.length}
          icone={<Syringe size={18} />}
          pictogramme="💉"
        />
        <Indicateur
          libelle="Bénéficiaires atteints"
          valeur={formaterNombre(atteints)}
          pictogramme="🎯"
        />
      </div>

      <Carte className="mb-4">
        <EnteteCarte
          titre="Campagnes de prévention"
          description={`${formaterNombre(atteints)} bénéficiaires atteints sur ${formaterNombre(cibles)} ciblés.`}
        />
        <Tableau
          legende="Campagnes de santé scolaire"
          lignes={listeCampagnes}
          cleLigne={(campagne) => campagne.id}
          vide={<EtatVide titre="Aucune campagne en cours" />}
          colonnes={[
            {
              cle: 'intitule',
              entete: 'Campagne',
              rendu: (campagne) => (
                <div className="min-w-0">
                  <p className="font-medium">{campagne.intitule}</p>
                  {campagne.theme ? (
                    <p className="truncate text-xs texte-doux">{campagne.theme}</p>
                  ) : null}
                </div>
              ),
            },
            {
              cle: 'periode',
              entete: 'Période',
              secondaire: true,
              rendu: (campagne) =>
                `${formaterDate(campagne.date_debut)} → ${formaterDate(campagne.date_fin)}`,
            },
            {
              cle: 'couverture',
              entete: 'Couverture',
              largeur: '16rem',
              rendu: (campagne) => (
                <Jauge
                  valeur={campagne.beneficiaires_atteints}
                  maximum={campagne.beneficiaires_cibles || 1}
                  etiquette={`${formaterNombre(campagne.beneficiaires_atteints)} / ${formaterNombre(campagne.beneficiaires_cibles)}`}
                  ton={
                    campagne.beneficiaires_atteints >= campagne.beneficiaires_cibles * 0.8
                      ? 'succes'
                      : campagne.beneficiaires_atteints >= campagne.beneficiaires_cibles * 0.5
                        ? 'alerte'
                        : 'danger'
                  }
                />
              ),
            },
          ]}
        />
      </Carte>

      <h2 className="mb-3 text-lg font-semibold">Centres de santé</h2>
      <ListeRessource
        legende="Centres de santé scolaire"
        placeholderRecherche="Rechercher un centre ou un service…"
        items={centres.items}
        total={centres.total}
        pages={centres.pages}
        page={centres.etat.page}
        taille={centres.etat.taille}
        chargement={centres.isLoading}
        erreur={centres.error}
        recherche={centres.etat.recherche}
        onRecherche={centres.changerRecherche}
        onPage={centres.changerPage}
        cleLigne={(centre) => centre.id}
        videTitre="Aucun centre de santé"
        colonnes={[
          {
            cle: 'nom',
            entete: 'Centre',
            rendu: (centre) => (
              <div className="min-w-0">
                <p className="font-medium">{centre.nom}</p>
                <p className="truncate font-mono text-xs texte-doux">{centre.code}</p>
              </div>
            ),
          },
          {
            cle: 'services',
            entete: 'Services',
            secondaire: true,
            rendu: (centre) => centre.services ?? '—',
          },
          {
            cle: 'agents',
            entete: 'Agents',
            alignement: 'droite',
            rendu: (centre) => centre.nombre_agents,
          },
          {
            cle: 'telephone',
            entete: 'Téléphone',
            secondaire: true,
            rendu: (centre) => centre.telephone ?? '—',
          },
        ]}
      />
    </>
  );
}
