'use client';

import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import Link from 'next/link';
import { useEffect, useMemo, useRef } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet';

import { formaterNombre, humaniser } from '@/lib/utils';

export interface PointCarte {
  id: string;
  libelle: string;
  latitude: number;
  longitude: number;
  effectif: number | null;
  accessibilite: string | null;
  type: string | null;
  statut: string | null;
  commune: string | null;
  departement: string | null;
}

/**
 * Couleur par type d'établissement. Les familles partagent une teinte — bleus
 * pour le primaire, verts pour le secondaire général, orangés pour le
 * technique — afin que la carte se lise sans consulter la légende à chaque
 * point.
 */
export const COULEURS_TYPE: Record<string, string> = {
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

export const COULEUR_DEFAUT = '#4b5563';

/** Le Bénin, comme cadrage de repli quand aucun point n'est affiché. */
const BENIN: L.LatLngBoundsExpression = [
  [6.2, 0.77],
  [12.4, 3.85],
];

/**
 * Rayon du disque, proportionnel à la racine de l'effectif : c'est la surface
 * du disque, et non son rayon, qui doit croître avec l'effectif, sans quoi un
 * grand lycée écraserait visuellement tout un canton d'écoles primaires.
 */
function rayon(effectif: number | null): number {
  const valeur = effectif ?? 0;
  if (valeur <= 0) return 4;
  return Math.min(18, 4 + Math.sqrt(valeur) / 7);
}

/**
 * Recadre la vue sur les points affichés. Sans cela, filtrer sur un type
 * laisserait la carte sur le cadrage précédent, avec trois points perdus dans
 * un coin.
 */
function Recadrage({ points }: { points: PointCarte[] }) {
  const carte = useMap();
  const signature = points.map((point) => point.id).join(',');
  const precedente = useRef<string>('');

  useEffect(() => {
    if (signature === precedente.current) return;
    precedente.current = signature;

    if (points.length === 0) {
      carte.fitBounds(BENIN, { padding: [20, 20] });
      return;
    }
    const limites = L.latLngBounds(points.map((point) => [point.latitude, point.longitude]));
    carte.fitBounds(limites, { padding: [36, 36], maxZoom: 12 });
  }, [carte, points, signature]);

  return null;
}

interface Proprietes {
  points: PointCarte[];
  /** Point mis en avant depuis la liste latérale. */
  survole?: string | null;
}

export default function CarteLeaflet({ points, survole }: Proprietes) {
  // Les grands établissements se dessinent en premier pour que les petits, plus
  // nombreux, restent cliquables par-dessus.
  const ordonnes = useMemo(
    () => [...points].sort((a, b) => (b.effectif ?? 0) - (a.effectif ?? 0)),
    [points],
  );

  return (
    <MapContainer
      bounds={BENIN}
      scrollWheelZoom
      className="h-[30rem] w-full rounded-lg border md:h-[34rem]"
      // Le conteneur porte son propre rôle : Leaflet n'en ajoute pas, et un
      // lecteur d'écran annoncerait sinon une division vide.
      aria-label="Carte interactive des établissements scolaires du Bénin"
    >
      <TileLayer
        // OpenStreetMap : libre, sans clé d'accès, et l'attribution ci-dessous
        // est une obligation de sa licence, pas une politesse.
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">Contributeurs OpenStreetMap</a>'
        maxZoom={19}
      />

      <Recadrage points={ordonnes} />

      {ordonnes.map((point) => {
        const couleur = COULEURS_TYPE[point.type ?? ''] ?? COULEUR_DEFAUT;
        const enAvant = survole === point.id;
        return (
          <CircleMarker
            key={point.id}
            center={[point.latitude, point.longitude]}
            radius={enAvant ? rayon(point.effectif) + 5 : rayon(point.effectif)}
            pathOptions={{
              color: enAvant ? '#111827' : '#ffffff',
              weight: enAvant ? 2.5 : 1,
              fillColor: couleur,
              fillOpacity: 0.78,
            }}
          >
            <Tooltip direction="top" offset={[0, -6]} opacity={1}>
              <div className="space-y-0.5">
                <p className="font-semibold">{point.libelle}</p>
                <p className="text-[0.8em] opacity-80">
                  {[point.commune, point.departement].filter(Boolean).join(' · ')}
                </p>
                <p className="text-[0.8em]">
                  {humaniser(point.type ?? '')}
                  {point.effectif ? ` — ${formaterNombre(point.effectif)} apprenants` : ''}
                </p>
              </div>
            </Tooltip>

            <Popup>
              <div className="space-y-1.5">
                <p className="font-semibold">{point.libelle}</p>
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[0.85em]">
                  <dt className="opacity-70">Type</dt>
                  <dd>{humaniser(point.type ?? '—')}</dd>
                  <dt className="opacity-70">Statut</dt>
                  <dd>{point.statut ?? '—'}</dd>
                  <dt className="opacity-70">Commune</dt>
                  <dd>{point.commune ?? '—'}</dd>
                  <dt className="opacity-70">Département</dt>
                  <dd>{point.departement ?? '—'}</dd>
                  <dt className="opacity-70">Effectif</dt>
                  <dd>{formaterNombre(point.effectif ?? 0)}</dd>
                  <dt className="opacity-70">Accessibilité</dt>
                  <dd>{humaniser(point.accessibilite ?? 'NON_RENSEIGNE')}</dd>
                </dl>
                <Link
                  href={`/etablissements/${point.id}`}
                  className="inline-block pt-1 font-medium underline"
                >
                  Ouvrir la fiche
                </Link>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
