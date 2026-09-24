'use client';

import { useQuery } from '@tanstack/react-query';
import { Accessibility } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Jauge } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Selection } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterNombre } from '@/lib/utils';
import type { SessionExamen } from '@/types/api';

interface Centre {
  id: string;
  code: string;
  nom: string;
  adresse: string | null;
  capacite: number;
  nombre_candidats: number;
  nombre_salles: number;
  chef_centre_nom: string | null;
  chef_centre_telephone: string | null;
  accessible_handicap: boolean;
  actif: boolean;
}

export default function PageCentres() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState('');
  const [accessibles, setAccessibles] = useState('');

  const sessions = useQuery({
    queryKey: ['sessions-liste'],
    queryFn: () => api.get<Page<SessionExamen>>('/sessions', { size: 50 }),
  });

  const liste = useListe<Centre>('/centres', {
    tri: 'code',
    filtres: {
      session_id: sessionId || undefined,
      accessible_handicap: accessibles || undefined,
    },
  });

  return (
    <>
      <EntetePage
        titre="Centres de composition"
        description="Sites où se déroulent les épreuves : capacité, salles, chef de centre et accessibilité."
      />

      <ListeRessource
        legende="Liste des centres de composition"
        placeholderRecherche="Rechercher par code, nom ou chef de centre…"
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
        cleLigne={(centre) => centre.id}
        onLigneClic={(centre) => router.push(`/centres/${centre.id}`)}
        videTitre="Aucun centre de composition"
        videDescription="Lancez la répartition des candidats d'une session pour créer les centres."
        filtres={
          <div className="grid gap-4 sm:grid-cols-2">
            <Selection
              etiquette="Session"
              value={sessionId}
              onChange={(evenement) => setSessionId(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Toutes les sessions' },
                ...(sessions.data?.items ?? []).map((session) => ({
                  valeur: session.id,
                  libelle: session.libelle,
                })),
              ]}
            />
            <Selection
              etiquette="Accessibilité"
              value={accessibles}
              onChange={(evenement) => setAccessibles(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Tous les centres' },
                { valeur: 'true', libelle: 'Accessibles aux personnes handicapées' },
                { valeur: 'false', libelle: 'Non accessibles' },
              ]}
            />
          </div>
        }
        colonnes={[
          {
            cle: 'nom',
            entete: 'Centre',
            rendu: (centre) => (
              <span className="min-w-0">
                <span className="block truncate font-medium">{centre.nom}</span>
                <span className="block font-mono text-xs texte-doux">{centre.code}</span>
              </span>
            ),
          },
          {
            cle: 'chef',
            entete: 'Chef de centre',
            secondaire: true,
            rendu: (centre) => (
              <span className="min-w-0">
                <span className="block truncate">{centre.chef_centre_nom ?? '—'}</span>
                <span className="block text-xs texte-doux">
                  {centre.chef_centre_telephone ?? ''}
                </span>
              </span>
            ),
          },
          {
            cle: 'salles',
            entete: 'Salles',
            alignement: 'droite',
            rendu: (centre) => formaterNombre(centre.nombre_salles),
          },
          {
            cle: 'occupation',
            entete: 'Occupation',
            largeur: '18%',
            rendu: (centre) => (
              <Jauge
                valeur={centre.nombre_candidats}
                maximum={centre.capacite || 1}
                etiquette={`${formaterNombre(centre.nombre_candidats)} / ${formaterNombre(centre.capacite)}`}
                ton={
                  centre.nombre_candidats > centre.capacite
                    ? 'danger'
                    : centre.nombre_candidats / (centre.capacite || 1) > 0.9
                      ? 'alerte'
                      : 'succes'
                }
              />
            ),
          },
          {
            cle: 'accessibilite',
            entete: 'Accessibilité',
            rendu: (centre) =>
              centre.accessible_handicap ? (
                <Badge ton="succes">
                  <Accessibility size={13} aria-hidden /> Accessible
                </Badge>
              ) : (
                <Badge ton="neutre">Non accessible</Badge>
              ),
          },
        ]}
      />
    </>
  );
}
