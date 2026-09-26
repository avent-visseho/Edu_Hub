'use client';

import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import Link from 'next/link';
import { useEffect, useMemo, useRef } from 'react';
import {
  CircleMarker,
  MapContainer,
  Polygon,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from 'react-leaflet';

import { COULEURS } from '@/components/graphiques';
import { EMPRISE_BENIN, FRONTIERE_BENIN } from '@/data/frontiere-benin';
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
 * point. Chaque famille part d'une couleur de la marque et se décline ensuite
 * en nuances : la carte ne peut pas se contenter des huit couleurs de la
 * palette, il lui en faut onze, toutes distinctes.
 */
export const COULEURS_TYPE: Record<string, string> = {
  EPP: COULEURS.bleu,
  EPRIV: COULEURS.bleuVif,
  EM: COULEURS.cyan,
  CEG: COULEURS.vert,
  LYCEE: '#15803d',
  CS: '#65a30d',
  LT: COULEURS.or,
  CFP: '#b45309',
  UNIV: COULEURS.violet,
  IUT: '#a855f7',
  CAL: COULEURS.rouge,
};

export const COULEUR_DEFAUT = '#4b5563';

/**
 * Libellés des types d'établissement. Les codes sont des sigles : les passer
 * par humaniser() produirait « Epp » ou « Ceg », ce qui est pire que le sigle
 * brut. On les nomme donc en toutes lettres, ce qui rend la légende lisible
 * pour qui ne connaît pas la nomenclature.
 */
export const LIBELLES_TYPE: Record<string, string> = {
  EM: 'École maternelle',
  EPP: 'École primaire publique',
  EPRIV: 'École primaire privée',
  CEG: "Collège d'enseignement général",
  LYCEE: "Lycée d'enseignement général",
  CS: 'Complexe scolaire privé',
  LT: 'Lycée technique',
  CFP: 'Centre de formation professionnelle',
  UNIV: 'Université',
  ENS: 'École normale supérieure',
  IUT: 'Institut universitaire de technologie',
  CAL: "Centre d'alphabétisation",
};

/** Libellé d'un type, ou le sigle lui-même s'il est inconnu. */
export function libelleType(code: string | null): string {
  if (!code) return '—';
  return LIBELLES_TYPE[code] ?? code;
}

/** Emprise du pays, cadrage de repli quand aucun point n'est affiché. */
const BENIN: L.LatLngBoundsExpression = [
  [EMPRISE_BENIN.latMin, EMPRISE_BENIN.lonMin],
  [EMPRISE_BENIN.latMax, EMPRISE_BENIN.lonMax],
];

/**
 * Limite de déplacement : l'emprise du pays, élargie d'un demi-degré pour que
 * les bords restent atteignables sans buter contre la limite.
 */
const LIMITES: L.LatLngBoundsExpression = [
  [EMPRISE_BENIN.latMin - 0.5, EMPRISE_BENIN.lonMin - 0.5],
  [EMPRISE_BENIN.latMax + 0.5, EMPRISE_BENIN.lonMax + 0.5],
];

/** La frontière, en (latitude, longitude) : l'ordre inverse du GeoJSON. */
const CONTOUR: L.LatLngExpression[] = FRONTIERE_BENIN.map(([lon, lat]) => [lat, lon]);

/**
 * Cadre englobant le monde entier, qui sert d'anneau extérieur au masque. Le
 * pays en forme la découpe : Leaflet interprète le second anneau d'un polygone
 * comme un trou, si bien que tout le voisinage se retrouve couvert et que seul
 * le Bénin laisse voir le fond de carte.
 */
const MONDE: L.LatLngExpression[] = [
  [-90, -200],
  [-90, 200],
  [90, 200],
  [90, -200],
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
      maxBounds={LIMITES}
      // Sans viscosité, on peut tirer la carte hors des limites puis la laisser
      // revenir en arrière ; la valeur maximale la retient franchement.
      maxBoundsViscosity={1}
      minZoom={6}
      maxZoom={17}
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

      {/*
        Masque du voisinage : un polygone couvrant le monde, percé à la forme du
        pays. Les États limitrophes et le golfe de Guinée disparaissent sous un
        aplat, sans que le fond de carte ait besoin d'être découpé — ce qu'on ne
        saurait pas faire avec des tuiles matricielles.
      */}
      {/*
        « interactive » se passe en propriété directe et non dans pathOptions :
        react-leaflet applique ce dernier par setStyle(), qui ne connaît que les
        options de tracé. Placé au mauvais endroit, il est ignoré en silence et
        le masque continue d'intercepter survol et clic sur toute la surface.
      */}
      <Polygon
        positions={[MONDE, CONTOUR]}
        interactive={false}
        pathOptions={{
          fillColor: '#f2f4f7',
          fillOpacity: 0.96,
          stroke: false,
        }}
      />

      {/* Le tracé de la frontière, par-dessus le masque. */}
      <Polygon
        positions={CONTOUR}
        interactive={false}
        pathOptions={{
          color: '#1f2937',
          weight: 1.4,
          opacity: 0.75,
          fill: false,
        }}
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
                  {libelleType(point.type)}
                  {point.effectif ? ` — ${formaterNombre(point.effectif)} apprenants` : ''}
                </p>
              </div>
            </Tooltip>

            <Popup>
              <div className="space-y-1.5">
                <p className="font-semibold">{point.libelle}</p>
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[0.85em]">
                  <dt className="opacity-70">Type</dt>
                  <dd>{libelleType(point.type)}</dd>
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
