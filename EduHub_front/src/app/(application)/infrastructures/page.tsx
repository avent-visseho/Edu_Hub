'use client';

import { useQuery } from '@tanstack/react-query';
import { Accessibility, Armchair, Building, DoorOpen, Wrench } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Selection, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterDate, formaterMontant, formaterNombre, humaniser } from '@/lib/utils';
import type { Etablissement } from '@/types/api';

type Onglet = 'batiments' | 'salles' | 'equipements';

interface Batiment {
  id: string;
  code: string;
  nom: string;
  nombre_etages: number;
  annee_construction: number | null;
  etat: string;
  accessibilite: string;
}

interface Salle {
  id: string;
  code: string;
  nom: string;
  etage: number;
  capacite: number;
  capacite_examen: number;
  superficie_m2: number | null;
  disponible: boolean;
  accessibilite: string;
  equipement_resume: string | null;
}

interface Equipement {
  id: string;
  reference: string;
  designation: string;
  type_equipement: string;
  quantite: number;
  etat: string;
  date_acquisition: string | null;
  valeur_acquisition: number | null;
  adapte_handicap: boolean;
}

const ONGLETS: Array<{ cle: Onglet; libelle: string; icone: typeof Building }> = [
  { cle: 'batiments', libelle: 'Bâtiments', icone: Building },
  { cle: 'salles', libelle: 'Salles', icone: DoorOpen },
  { cle: 'equipements', libelle: 'Équipements', icone: Armchair },
];

/** Traduit le niveau d'accessibilité déclaré en ton de badge. */
function tonAccessibilite(niveau: string): 'succes' | 'alerte' | 'danger' | 'neutre' {
  if (niveau === 'TOTALE') return 'succes';
  if (niveau === 'PARTIELLE') return 'alerte';
  if (niveau === 'AUCUNE') return 'danger';
  return 'neutre';
}

export default function PageInfrastructures() {
  const [onglet, setOnglet] = useState<Onglet>('batiments');
  const [etablissementId, setEtablissementId] = useState('');
  const [etat, setEtat] = useState('');

  const etablissements = useQuery({
    queryKey: ['etablissements-liste'],
    queryFn: () => api.get<Page<Etablissement>>('/etablissements', { size: 200, sort_by: 'nom' }),
  });

  const filtresCommuns = { etablissement_id: etablissementId || undefined };

  // Les trois compteurs restent affichés quel que soit l'onglet ouvert : une
  // page d'un élément suffit, seul le total est lu.
  const comptages = useQuery({
    queryKey: ['comptages-infrastructures', etablissementId],
    queryFn: async () => {
      const [batiments, salles, equipements] = await Promise.all([
        api.get<Page<unknown>>('/batiments', { size: 1, ...filtresCommuns }),
        api.get<Page<unknown>>('/salles', { size: 1, ...filtresCommuns }),
        api.get<Page<unknown>>('/equipements', { size: 1, ...filtresCommuns }),
      ]);
      return {
        batiments: batiments.total,
        salles: salles.total,
        equipements: equipements.total,
      };
    },
  });

  const batiments = useListe<Batiment>('/batiments', {
    tri: 'code',
    active: onglet === 'batiments',
    filtres: { ...filtresCommuns, etat: etat || undefined },
  });

  const salles = useListe<Salle>('/salles', {
    tri: 'code',
    active: onglet === 'salles',
    filtres: { ...filtresCommuns, accessibilite: etat || undefined },
  });

  const equipements = useListe<Equipement>('/equipements', {
    tri: 'reference',
    active: onglet === 'equipements',
    filtres: { ...filtresCommuns, etat: etat || undefined },
  });

  const options =
    onglet === 'salles'
      ? [
          { valeur: '', libelle: 'Toutes les accessibilités' },
          { valeur: 'TOTALE', libelle: 'Accessibilité totale' },
          { valeur: 'PARTIELLE', libelle: 'Accessibilité partielle' },
          { valeur: 'AUCUNE', libelle: 'Aucune accessibilité' },
        ]
      : [
          { valeur: '', libelle: 'Tous les états' },
          { valeur: 'NEUF', libelle: 'Neuf' },
          { valeur: 'BON', libelle: 'Bon' },
          { valeur: 'MOYEN', libelle: 'Moyen' },
          { valeur: 'MAUVAIS', libelle: 'Mauvais' },
          { valeur: 'HORS_SERVICE', libelle: 'Hors service' },
        ];

  const filtres = (
    <div className="grid gap-4 sm:grid-cols-2">
      <Selection
        etiquette="Établissement"
        value={etablissementId}
        onChange={(evenement) => setEtablissementId(evenement.target.value)}
        options={[
          { valeur: '', libelle: 'Tous les établissements' },
          ...(etablissements.data?.items ?? []).map((etablissement) => ({
            valeur: etablissement.id,
            libelle: etablissement.nom,
          })),
        ]}
      />
      <Selection
        etiquette={onglet === 'salles' ? 'Accessibilité' : 'État'}
        value={etat}
        onChange={(evenement) => setEtat(evenement.target.value)}
        options={options}
      />
    </div>
  );

  return (
    <>
      <EntetePage
        titre="Infrastructures"
        description="Patrimoine bâti, salles de cours et équipements des établissements, avec leur état et leur niveau d'accessibilité."
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <Indicateur
          libelle="Bâtiments recensés"
          valeur={comptages.data?.batiments ?? '—'}
          icone={<Building size={19} aria-hidden />}
          pictogramme="🏢"
        />
        <Indicateur
          libelle="Salles recensées"
          valeur={comptages.data?.salles ?? '—'}
          icone={<DoorOpen size={19} aria-hidden />}
          pictogramme="🚪"
        />
        <Indicateur
          libelle="Équipements recensés"
          valeur={comptages.data?.equipements ?? '—'}
          icone={<Wrench size={19} aria-hidden />}
          pictogramme="🔧"
        />
      </div>

      <div
        role="tablist"
        aria-label="Catégorie d'infrastructure"
        className="mb-4 flex flex-wrap gap-2"
      >
        {ONGLETS.map((element) => {
          const Icone = element.icone;
          const actif = onglet === element.cle;
          return (
            <button
              key={element.cle}
              type="button"
              role="tab"
              aria-selected={actif}
              onClick={() => {
                setOnglet(element.cle);
                setEtat('');
              }}
              className={
                actif
                  ? 'inline-flex items-center gap-2 rounded-lg bg-[rgb(var(--accent))] px-4 py-2 text-sm font-medium text-white'
                  : 'surface inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-[rgb(var(--fond-doux))]'
              }
            >
              <Icone size={17} aria-hidden />
              {element.libelle}
            </button>
          );
        })}
      </div>

      {onglet === 'batiments' ? (
        <ListeRessource
          legende="Liste des bâtiments"
          placeholderRecherche="Rechercher un bâtiment par code ou nom…"
          items={batiments.items}
          total={batiments.total}
          pages={batiments.pages}
          page={batiments.etat.page}
          taille={batiments.etat.taille}
          chargement={batiments.isLoading}
          erreur={batiments.error}
          recherche={batiments.etat.recherche}
          onRecherche={batiments.changerRecherche}
          onPage={batiments.changerPage}
          cleLigne={(batiment) => batiment.id}
          videTitre="Aucun bâtiment"
          filtres={filtres}
          colonnes={[
            {
              cle: 'nom',
              entete: 'Bâtiment',
              rendu: (batiment) => (
                <span className="min-w-0">
                  <span className="block truncate font-medium">{batiment.nom}</span>
                  <span className="block font-mono text-xs texte-doux">{batiment.code}</span>
                </span>
              ),
            },
            {
              cle: 'etages',
              entete: 'Niveaux',
              alignement: 'droite',
              rendu: (batiment) => batiment.nombre_etages,
            },
            {
              cle: 'construction',
              entete: 'Construit en',
              alignement: 'droite',
              secondaire: true,
              rendu: (batiment) => batiment.annee_construction ?? '—',
            },
            {
              cle: 'etat',
              entete: 'État',
              rendu: (batiment) => (
                <Badge ton={tonDuStatut(batiment.etat)}>{humaniser(batiment.etat)}</Badge>
              ),
            },
            {
              cle: 'accessibilite',
              entete: 'Accessibilité',
              rendu: (batiment) => (
                <Badge ton={tonAccessibilite(batiment.accessibilite)}>
                  <Accessibility size={13} aria-hidden /> {humaniser(batiment.accessibilite)}
                </Badge>
              ),
            },
          ]}
        />
      ) : null}

      {onglet === 'salles' ? (
        <ListeRessource
          legende="Liste des salles"
          placeholderRecherche="Rechercher une salle par code ou nom…"
          items={salles.items}
          total={salles.total}
          pages={salles.pages}
          page={salles.etat.page}
          taille={salles.etat.taille}
          chargement={salles.isLoading}
          erreur={salles.error}
          recherche={salles.etat.recherche}
          onRecherche={salles.changerRecherche}
          onPage={salles.changerPage}
          cleLigne={(salle) => salle.id}
          videTitre="Aucune salle"
          filtres={filtres}
          colonnes={[
            {
              cle: 'nom',
              entete: 'Salle',
              rendu: (salle) => (
                <span className="min-w-0">
                  <span className="block truncate font-medium">{salle.nom}</span>
                  <span className="block font-mono text-xs texte-doux">
                    {salle.code} · étage {salle.etage}
                  </span>
                </span>
              ),
            },
            {
              cle: 'capacite',
              entete: 'Capacité',
              alignement: 'droite',
              rendu: (salle) => (
                <span className="min-w-0">
                  <span className="block">{formaterNombre(salle.capacite)} en cours</span>
                  <span className="block text-xs texte-doux">
                    {formaterNombre(salle.capacite_examen)} en examen
                  </span>
                </span>
              ),
            },
            {
              cle: 'superficie',
              entete: 'Superficie',
              alignement: 'droite',
              secondaire: true,
              rendu: (salle) =>
                salle.superficie_m2 != null ? `${formaterNombre(salle.superficie_m2)} m²` : '—',
            },
            {
              cle: 'equipement',
              entete: 'Équipement',
              secondaire: true,
              rendu: (salle) => salle.equipement_resume ?? '—',
            },
            {
              cle: 'disponible',
              entete: 'Disponibilité',
              rendu: (salle) => (
                <span className="flex flex-wrap gap-1.5">
                  <Badge ton={salle.disponible ? 'succes' : 'neutre'}>
                    {salle.disponible ? 'Disponible' : 'Indisponible'}
                  </Badge>
                  <Badge ton={tonAccessibilite(salle.accessibilite)}>
                    <Accessibility size={13} aria-hidden /> {humaniser(salle.accessibilite)}
                  </Badge>
                </span>
              ),
            },
          ]}
        />
      ) : null}

      {onglet === 'equipements' ? (
        <ListeRessource
          legende="Liste des équipements"
          placeholderRecherche="Rechercher un équipement par référence ou désignation…"
          items={equipements.items}
          total={equipements.total}
          pages={equipements.pages}
          page={equipements.etat.page}
          taille={equipements.etat.taille}
          chargement={equipements.isLoading}
          erreur={equipements.error}
          recherche={equipements.etat.recherche}
          onRecherche={equipements.changerRecherche}
          onPage={equipements.changerPage}
          cleLigne={(equipement) => equipement.id}
          videTitre="Aucun équipement"
          filtres={filtres}
          colonnes={[
            {
              cle: 'designation',
              entete: 'Équipement',
              rendu: (equipement) => (
                <span className="min-w-0">
                  <span className="block truncate font-medium">{equipement.designation}</span>
                  <span className="block font-mono text-xs texte-doux">{equipement.reference}</span>
                </span>
              ),
            },
            {
              cle: 'type',
              entete: 'Type',
              secondaire: true,
              rendu: (equipement) => humaniser(equipement.type_equipement),
            },
            {
              cle: 'quantite',
              entete: 'Quantité',
              alignement: 'droite',
              rendu: (equipement) => formaterNombre(equipement.quantite),
            },
            {
              cle: 'valeur',
              entete: 'Valeur',
              alignement: 'droite',
              secondaire: true,
              rendu: (equipement) =>
                equipement.valeur_acquisition != null
                  ? formaterMontant(equipement.valeur_acquisition)
                  : '—',
            },
            {
              cle: 'acquisition',
              entete: 'Acquis le',
              alignement: 'droite',
              secondaire: true,
              rendu: (equipement) =>
                equipement.date_acquisition ? formaterDate(equipement.date_acquisition) : '—',
            },
            {
              cle: 'etat',
              entete: 'État',
              rendu: (equipement) => (
                <span className="flex flex-wrap gap-1.5">
                  <Badge ton={tonDuStatut(equipement.etat)}>{humaniser(equipement.etat)}</Badge>
                  {equipement.adapte_handicap ? (
                    <Badge ton="info">
                      <Accessibility size={13} aria-hidden /> Adapté
                    </Badge>
                  ) : null}
                </span>
              ),
            },
          ]}
        />
      ) : null}
    </>
  );
}
