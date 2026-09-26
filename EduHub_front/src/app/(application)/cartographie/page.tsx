'use client';

import { useQuery } from '@tanstack/react-query';
import { Layers, MapPin } from 'lucide-react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useMemo, useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import {
  COULEUR_DEFAUT,
  COULEURS_TYPE,
  libelleType,
  type PointCarte,
} from '@/components/carte/carte-leaflet';
import {
  Badge,
  Carte,
  Champ,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  MessageErreur,
  Selection,
} from '@/components/ui/primitives';
import { api } from '@/lib/api';
import { formaterNombre } from '@/lib/utils';

/**
 * Leaflet manipule `window` dès son chargement : rendu côté serveur impossible.
 * L'import dynamique le charge uniquement dans le navigateur, et affiche un
 * cadre d'attente pendant ce temps plutôt qu'un saut de mise en page.
 */
const CarteLeaflet = dynamic(() => import('@/components/carte/carte-leaflet'), {
  ssr: false,
  loading: () => (
    <div
      className="flex h-[30rem] w-full items-center justify-center rounded-lg border surface-douce md:h-[34rem]"
      role="status"
    >
      <span className="text-sm text-[rgb(var(--texte-doux))]">Chargement du fond de carte…</span>
    </div>
  ),
});

export default function PageCartographie() {
  const [type, setType] = useState('');
  const [departement, setDepartement] = useState('');
  const [recherche, setRecherche] = useState('');
  const [survole, setSurvole] = useState<string | null>(null);

  const points = useQuery({
    queryKey: ['carte-points'],
    queryFn: () => api.get<PointCarte[]>('/etablissements-carte/points', { limite: 2000 }),
  });

  const tous = useMemo(() => points.data ?? [], [points.data]);

  const types = useMemo(
    () => Array.from(new Set(tous.map((point) => point.type).filter(Boolean))).sort() as string[],
    [tous],
  );

  const departements = useMemo(
    () =>
      Array.from(
        new Set(tous.map((point) => point.departement).filter(Boolean)),
      ).sort() as string[],
    [tous],
  );

  const filtres = useMemo(() => {
    const terme = recherche.trim().toLowerCase();
    return tous.filter((point) => {
      if (type && point.type !== type) return false;
      if (departement && point.departement !== departement) return false;
      if (terme) {
        const cible = `${point.libelle} ${point.commune ?? ''}`.toLowerCase();
        if (!cible.includes(terme)) return false;
      }
      return true;
    });
  }, [tous, type, departement, recherche]);

  const parDepartement = useMemo(() => {
    const compteur = new Map<string, number>();
    for (const point of filtres) {
      const cle = point.departement ?? '—';
      compteur.set(cle, (compteur.get(cle) ?? 0) + 1);
    }
    return Array.from(compteur.entries()).sort((a, b) => b[1] - a[1]);
  }, [filtres]);

  const effectifTotal = useMemo(
    () => filtres.reduce((somme, point) => somme + (point.effectif ?? 0), 0),
    [filtres],
  );

  if (points.isLoading) return <Chargement libelle="Chargement de la carte nationale…" />;
  if (points.isError) return <MessageErreur erreur={points.error} />;

  return (
    <>
      <EntetePage
        titre="Cartographie du réseau éducatif"
        description="Implantation réelle des établissements sur fond OpenStreetMap. Survolez un point pour l'identifier, cliquez pour ouvrir sa fiche."
        actions={
          <div className="flex flex-wrap gap-2">
            <Champ
              etiquette="Rechercher un établissement"
              etiquetteMasquee
              type="search"
              placeholder="Nom ou commune…"
              value={recherche}
              onChange={(evenement) => setRecherche(evenement.target.value)}
              className="h-11 w-56"
            />
            <Selection
              etiquette="Type d'établissement"
              etiquetteMasquee
              value={type}
              onChange={(evenement) => setType(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Tous les types' },
                ...types.map((valeur) => ({ valeur, libelle: libelleType(valeur) })),
              ]}
              className="h-11"
            />
            <Selection
              etiquette="Département"
              etiquetteMasquee
              value={departement}
              onChange={(evenement) => setDepartement(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Tous les départements' },
                ...departements.map((valeur) => ({ valeur, libelle: valeur })),
              ]}
              className="h-11"
            />
          </div>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_22rem]">
        <Carte>
          <EnteteCarte
            titre={`${formaterNombre(filtres.length)} établissement(s) localisé(s)`}
            description={`${formaterNombre(effectifTotal)} apprenants accueillis — la taille du disque reflète l'effectif.`}
          />
          <CorpsCarte>
            <CarteLeaflet points={filtres} survole={survole} />

            <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-sm">
              {types.map((valeur) => (
                <li key={valeur} className="inline-flex items-center gap-1.5">
                  <span
                    aria-hidden
                    className="h-3 w-3 shrink-0 rounded-full border border-white"
                    style={{ backgroundColor: COULEURS_TYPE[valeur] ?? COULEUR_DEFAUT }}
                  />
                  {libelleType(valeur)}
                </li>
              ))}
            </ul>

            <p className="mt-3 text-xs text-[rgb(var(--texte-doux))]">
              Fond de carte © contributeurs OpenStreetMap. La liste ci-contre reprend les mêmes
              établissements, pour une consultation sans carte.
            </p>
          </CorpsCarte>
        </Carte>

        <div className="space-y-4">
          {/*
            Cette liste n'est pas un simple complément : une carte reste
            inutilisable au clavier et au lecteur d'écran. Elle donne accès aux
            mêmes établissements, dans le même ordre de filtrage, avec un lien
            vers chaque fiche.
          */}
          <Carte>
            <EnteteCarte
              titre={
                <span className="flex items-center gap-2">
                  <Layers size={19} aria-hidden /> Établissements
                </span>
              }
              description="Survolez une ligne pour la situer sur la carte."
            />
            <ul className="max-h-[22rem] divide-y overflow-y-auto">
              {filtres.slice(0, 200).map((point) => (
                <li key={point.id}>
                  <Link
                    href={`/etablissements/${point.id}`}
                    onMouseEnter={() => setSurvole(point.id)}
                    onMouseLeave={() => setSurvole(null)}
                    onFocus={() => setSurvole(point.id)}
                    onBlur={() => setSurvole(null)}
                    className="flex items-start gap-2.5 px-5 py-2.5 text-sm hover:bg-[rgb(var(--fond-doux))] focus-visible:bg-[rgb(var(--fond-doux))] focus-visible:outline-none"
                  >
                    <span
                      aria-hidden
                      className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{
                        backgroundColor: COULEURS_TYPE[point.type ?? ''] ?? COULEUR_DEFAUT,
                      }}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{point.libelle}</span>
                      <span className="block truncate text-xs text-[rgb(var(--texte-doux))]">
                        {[point.commune, point.departement].filter(Boolean).join(' · ')}
                        {point.effectif ? ` — ${formaterNombre(point.effectif)} apprenants` : ''}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
              {filtres.length === 0 && (
                <li className="px-5 py-6 text-center text-sm text-[rgb(var(--texte-doux))]">
                  Aucun établissement ne correspond à ces filtres.
                </li>
              )}
            </ul>
            {filtres.length > 200 && (
              <p className="border-t px-5 py-2.5 text-xs text-[rgb(var(--texte-doux))]">
                200 premiers affichés sur {formaterNombre(filtres.length)}. Affinez les filtres pour
                réduire la liste.
              </p>
            )}
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
              {parDepartement.map(([nom, effectif]) => (
                <li
                  key={nom}
                  className="flex items-center justify-between gap-2 px-5 py-2.5 text-sm"
                >
                  <span>{nom}</span>
                  <Badge ton="neutre">{formaterNombre(effectif)}</Badge>
                </li>
              ))}
            </ul>
          </Carte>
        </div>
      </div>
    </>
  );
}
