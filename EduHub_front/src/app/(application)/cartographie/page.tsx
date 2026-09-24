'use client';

import { useQuery } from '@tanstack/react-query';
import { MapPin } from 'lucide-react';
import { useMemo, useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import {
  Badge,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  MessageErreur,
  Selection,
} from '@/components/ui/primitives';
import { api } from '@/lib/api';
import { formaterNombre } from '@/lib/utils';

interface PointCarte {
  id: string;
  libelle: string;
  latitude: number;
  longitude: number;
  effectif: number;
  accessibilite: string | null;
  type: string | null;
  statut: string | null;
  commune: string | null;
  departement: string | null;
}

/** Bornes géographiques du Bénin, pour projeter les points sans fond de carte. */
const BORNES = { latMin: 6.0, latMax: 12.5, lonMin: 0.7, lonMax: 3.9 };

const COULEURS: Record<string, string> = {
  EPP: '#284f8b',
  EPRIV: '#5d86c1',
  EM: '#0891b2',
  CEG: '#16a153',
  LYCEE: '#15803d',
  CS: '#65a30d',
  LT: '#d77706',
  CFP: '#b45309',
  UNIV: '#7c3aed',
  IUT: '#a855f7',
  CAL: '#be123c',
};

export default function PageCartographie() {
  const [type, setType] = useState('');

  const points = useQuery({
    queryKey: ['carte-points'],
    queryFn: () => api.get<PointCarte[]>('/etablissements-carte/points', { limite: 2000 }),
  });

  const filtres = useMemo(() => {
    const liste = points.data ?? [];
    return type ? liste.filter((point) => point.type === type) : liste;
  }, [points.data, type]);

  const types = useMemo(() => {
    const ensemble = new Set((points.data ?? []).map((point) => point.type).filter(Boolean));
    return Array.from(ensemble) as string[];
  }, [points.data]);

  const parDepartement = useMemo(() => {
    const compteur = new Map<string, number>();
    for (const point of filtres) {
      const cle = point.departement ?? '—';
      compteur.set(cle, (compteur.get(cle) ?? 0) + 1);
    }
    return Array.from(compteur.entries()).sort((a, b) => b[1] - a[1]);
  }, [filtres]);

  if (points.isLoading) return <Chargement libelle="Chargement de la carte nationale…" />;
  if (points.isError) return <MessageErreur erreur={points.error} />;

  /** Projette une coordonnée géographique dans le repère du dessin. */
  function projeter(point: PointCarte) {
    const x = ((point.longitude - BORNES.lonMin) / (BORNES.lonMax - BORNES.lonMin)) * 100;
    const y = ((BORNES.latMax - point.latitude) / (BORNES.latMax - BORNES.latMin)) * 100;
    return { x: Math.min(98, Math.max(2, x)), y: Math.min(98, Math.max(2, y)) };
  }

  return (
    <>
      <EntetePage
        titre="Cartographie du réseau éducatif"
        description="Implantation des établissements sur le territoire national, colorée par type."
        actions={
          <Selection
            etiquette="Type d'établissement"
            etiquetteMasquee
            value={type}
            onChange={(evenement) => setType(evenement.target.value)}
            options={[
              { valeur: '', libelle: 'Tous les types' },
              ...types.map((valeur) => ({ valeur, libelle: valeur })),
            ]}
            className="h-11"
          />
        }
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_20rem]">
        <Carte>
          <EnteteCarte
            titre={`${formaterNombre(filtres.length)} établissement(s) localisé(s)`}
            description="Chaque point représente un établissement ; sa taille reflète l'effectif accueilli."
          />
          <CorpsCarte>
            <figure>
              <figcaption className="sr-only">
                Carte des établissements du Bénin, projetée en coordonnées géographiques.
              </figcaption>
              <svg
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                role="img"
                aria-label={`Carte de ${filtres.length} établissements`}
                className="h-[26rem] w-full rounded-lg border surface-douce"
              >
                {/* Repères de latitude et de longitude */}
                {[20, 40, 60, 80].map((position) => (
                  <g key={position} stroke="rgb(var(--bordure))" strokeWidth="0.15">
                    <line x1={position} y1="0" x2={position} y2="100" />
                    <line x1="0" y1={position} x2="100" y2={position} />
                  </g>
                ))}

                {filtres.map((point) => {
                  const { x, y } = projeter(point);
                  const rayon = Math.min(1.8, 0.5 + Math.sqrt(point.effectif) / 22);
                  return (
                    <circle
                      key={point.id}
                      cx={x}
                      cy={y}
                      r={rayon}
                      fill={COULEURS[point.type ?? ''] ?? '#4b5563'}
                      fillOpacity={0.78}
                      stroke="white"
                      strokeWidth="0.12"
                    >
                      <title>
                        {point.libelle} — {point.commune ?? ''} ({point.effectif} élèves)
                      </title>
                    </circle>
                  );
                })}
              </svg>
            </figure>

            <ul className="mt-4 flex flex-wrap gap-3 text-sm">
              {types.map((valeur) => (
                <li key={valeur} className="inline-flex items-center gap-1.5">
                  <span
                    aria-hidden
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: COULEURS[valeur] ?? '#4b5563' }}
                  />
                  {valeur}
                </li>
              ))}
            </ul>
          </CorpsCarte>
        </Carte>

        <Carte className="h-fit">
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <MapPin size={19} aria-hidden /> Par département
              </span>
            }
          />
          <ul className="divide-y">
            {parDepartement.map(([departement, effectif]) => (
              <li
                key={departement}
                className="flex items-center justify-between gap-2 px-5 py-2.5 text-sm"
              >
                <span>{departement}</span>
                <Badge ton="neutre">{formaterNombre(effectif)}</Badge>
              </li>
            ))}
          </ul>
        </Carte>
      </div>
    </>
  );
}
