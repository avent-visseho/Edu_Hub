'use client';

import { useQuery } from '@tanstack/react-query';
import { BookMarked, FlaskConical, Microscope, Users } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur, Tableau } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import {
  Badge,
  Carte,
  EnteteCarte,
  EtatVide,
  tonDuStatut,
} from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterMontant, formaterNombre, humaniser } from '@/lib/utils';

interface Laboratoire {
  id: string;
  code: string;
  nom: string;
  domaines: string | null;
  directeur_nom: string | null;
  annee_creation: number | null;
  nombre_chercheurs: number;
  actif: boolean;
}

interface Chercheur {
  id: string;
  laboratoire_id: string | null;
  nom_complet: string;
  grade: string | null;
  specialite: string | null;
  indice_h: number;
  nombre_publications: number;
}

interface Publication {
  id: string;
  titre: string;
  type_publication: string;
  revue: string | null;
  annee: number;
  doi: string | null;
  acces_libre: boolean;
  nombre_citations: number;
}

interface ProjetRecherche {
  id: string;
  code: string;
  titre: string;
  domaine: string | null;
  financement: number;
  bailleur: string | null;
  statut: string;
}

type Onglet = 'laboratoires' | 'publications' | 'projets';

export default function PageRechercheScientifique() {
  const [onglet, setOnglet] = useState<Onglet>('laboratoires');
  const [laboratoireId, setLaboratoireId] = useState<string | null>(null);

  const laboratoires = useQuery({
    queryKey: ['laboratoires'],
    queryFn: () =>
      api.get<Page<Laboratoire>>('/recherche-scientifique/laboratoires', { size: 100 }),
  });

  const actif = laboratoireId ?? laboratoires.data?.items[0]?.id ?? null;

  const equipe = useQuery({
    queryKey: ['equipe-laboratoire', actif],
    enabled: Boolean(actif) && onglet === 'laboratoires',
    queryFn: () =>
      api.get<Chercheur[]>(`/recherche-scientifique/laboratoires/${actif}/equipe`),
  });

  const publications = useListe<Publication>('/recherche-scientifique/publications', {
    tri: 'annee',
    active: onglet === 'publications',
  });

  const projets = useListe<ProjetRecherche>('/recherche-scientifique/projets', {
    tri: 'titre',
    active: onglet === 'projets',
  });

  const liste = laboratoires.data?.items ?? [];
  const chercheurs = liste.reduce((total, labo) => total + labo.nombre_chercheurs, 0);
  const laboratoire = liste.find((element) => element.id === actif);

  return (
    <>
      <EntetePage
        titre="Recherche scientifique"
        description="Laboratoires, chercheurs, projets financés et production scientifique."
      />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicateur
          libelle="Laboratoires"
          valeur={liste.length}
          icone={<FlaskConical size={18} />}
          pictogramme="🔬"
        />
        <Indicateur
          libelle="Chercheurs"
          valeur={chercheurs}
          icone={<Users size={18} />}
          pictogramme="👨‍🔬"
        />
        <Indicateur
          libelle="Publications"
          valeur={publications.total}
          icone={<BookMarked size={18} />}
          pictogramme="📄"
        />
        <Indicateur
          libelle="Projets de recherche"
          valeur={projets.total}
          icone={<Microscope size={18} />}
          pictogramme="🧪"
        />
      </div>

      <div role="tablist" aria-label="Section" className="mb-4 inline-flex rounded-lg border p-1">
        {(
          [
            { cle: 'laboratoires', libelle: 'Laboratoires' },
            { cle: 'publications', libelle: 'Publications' },
            { cle: 'projets', libelle: 'Projets financés' },
          ] as const
        ).map((element) => (
          <button
            key={element.cle}
            type="button"
            role="tab"
            aria-selected={onglet === element.cle}
            onClick={() => setOnglet(element.cle)}
            className={`h-10 rounded px-4 text-sm font-medium transition ${
              onglet === element.cle
                ? 'bg-[rgb(var(--accent))] text-[rgb(var(--accent-contraste))]'
                : 'hover:bg-[rgb(var(--fond-doux))]'
            }`}
          >
            {element.libelle}
          </button>
        ))}
      </div>

      {onglet === 'laboratoires' ? (
        liste.length === 0 ? (
          <Carte>
            <EtatVide titre="Aucun laboratoire enregistré" />
          </Carte>
        ) : (
          <div className="grid gap-4 xl:grid-cols-[22rem_1fr]">
            <Carte className="h-fit">
              <EnteteCarte titre="Laboratoires" />
              <ul className="defilement-fin max-h-[32rem] divide-y overflow-y-auto">
                {liste.map((element) => (
                  <li key={element.id}>
                    <button
                      type="button"
                      onClick={() => setLaboratoireId(element.id)}
                      aria-current={element.id === actif ? 'true' : undefined}
                      className={`w-full px-4 py-3 text-left transition ${
                        element.id === actif
                          ? 'bg-[rgb(var(--accent))]/10'
                          : 'hover:bg-[rgb(var(--fond-doux))]'
                      }`}
                    >
                      <span className="block truncate text-sm font-medium">{element.nom}</span>
                      <span className="block truncate text-xs texte-doux">
                        {element.domaines ?? '—'} · {element.nombre_chercheurs} chercheur(s)
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </Carte>

            <Carte>
              <EnteteCarte
                titre={laboratoire ? laboratoire.nom : 'Équipe'}
                description={
                  laboratoire
                    ? [
                        laboratoire.domaines,
                        laboratoire.directeur_nom
                          ? `dirigé par ${laboratoire.directeur_nom}`
                          : null,
                        laboratoire.annee_creation ? `créé en ${laboratoire.annee_creation}` : null,
                      ]
                        .filter(Boolean)
                        .join(' · ')
                    : undefined
                }
              />
              <Tableau
                legende="Chercheurs du laboratoire"
                lignes={equipe.data ?? []}
                cleLigne={(chercheur) => chercheur.id}
                vide={<EtatVide titre="Aucun chercheur rattaché" />}
                colonnes={[
                  {
                    cle: 'nom',
                    entete: 'Chercheur',
                    rendu: (chercheur) => (
                      <span className="font-medium">{chercheur.nom_complet}</span>
                    ),
                  },
                  {
                    cle: 'grade',
                    entete: 'Grade',
                    rendu: (chercheur) =>
                      chercheur.grade ? <Badge ton="neutre">{chercheur.grade}</Badge> : '—',
                  },
                  {
                    cle: 'specialite',
                    entete: 'Spécialité',
                    secondaire: true,
                    rendu: (chercheur) => chercheur.specialite ?? '—',
                  },
                  {
                    cle: 'publications',
                    entete: 'Publications',
                    alignement: 'droite',
                    rendu: (chercheur) => formaterNombre(chercheur.nombre_publications),
                  },
                  {
                    cle: 'indice',
                    entete: 'Indice h',
                    alignement: 'droite',
                    rendu: (chercheur) => (
                      <span className="font-semibold">{chercheur.indice_h}</span>
                    ),
                  },
                ]}
              />
            </Carte>
          </div>
        )
      ) : onglet === 'publications' ? (
        <ListeRessource
          legende="Publications scientifiques"
          placeholderRecherche="Rechercher par titre, revue, DOI ou mot-clé…"
          items={publications.items}
          total={publications.total}
          pages={publications.pages}
          page={publications.etat.page}
          taille={publications.etat.taille}
          chargement={publications.isLoading}
          erreur={publications.error}
          recherche={publications.etat.recherche}
          onRecherche={publications.changerRecherche}
          onPage={publications.changerPage}
          cleLigne={(publication) => publication.id}
          videTitre="Aucune publication"
          colonnes={[
            {
              cle: 'titre',
              entete: 'Publication',
              rendu: (publication) => (
                <div className="min-w-0">
                  <p className="font-medium">{publication.titre}</p>
                  {publication.revue ? (
                    <p className="truncate text-xs texte-doux">{publication.revue}</p>
                  ) : null}
                </div>
              ),
            },
            {
              cle: 'type',
              entete: 'Type',
              rendu: (publication) => (
                <Badge ton="neutre">{humaniser(publication.type_publication)}</Badge>
              ),
            },
            {
              cle: 'annee',
              entete: 'Année',
              alignement: 'droite',
              rendu: (publication) => publication.annee,
            },
            {
              cle: 'citations',
              entete: 'Citations',
              alignement: 'droite',
              secondaire: true,
              rendu: (publication) => formaterNombre(publication.nombre_citations),
            },
            {
              cle: 'doi',
              entete: 'DOI',
              secondaire: true,
              rendu: (publication) =>
                publication.doi ? (
                  <span className="font-mono text-xs">{publication.doi}</span>
                ) : (
                  '—'
                ),
            },
            {
              cle: 'acces',
              entete: 'Accès',
              alignement: 'centre',
              rendu: (publication) => (
                <Badge ton={publication.acces_libre ? 'succes' : 'neutre'}>
                  {publication.acces_libre ? 'Libre' : 'Restreint'}
                </Badge>
              ),
            },
          ]}
        />
      ) : (
        <ListeRessource
          legende="Projets de recherche"
          placeholderRecherche="Rechercher un projet, un domaine, un bailleur…"
          items={projets.items}
          total={projets.total}
          pages={projets.pages}
          page={projets.etat.page}
          taille={projets.etat.taille}
          chargement={projets.isLoading}
          erreur={projets.error}
          recherche={projets.etat.recherche}
          onRecherche={projets.changerRecherche}
          onPage={projets.changerPage}
          cleLigne={(projet) => projet.id}
          videTitre="Aucun projet de recherche"
          colonnes={[
            {
              cle: 'titre',
              entete: 'Projet',
              rendu: (projet) => (
                <div className="min-w-0">
                  <p className="font-medium">{projet.titre}</p>
                  <p className="truncate font-mono text-xs texte-doux">{projet.code}</p>
                </div>
              ),
            },
            {
              cle: 'domaine',
              entete: 'Domaine',
              rendu: (projet) =>
                projet.domaine ? <Badge ton="neutre">{projet.domaine}</Badge> : '—',
            },
            {
              cle: 'financement',
              entete: 'Financement',
              alignement: 'droite',
              rendu: (projet) => formaterMontant(projet.financement),
            },
            {
              cle: 'bailleur',
              entete: 'Bailleur',
              secondaire: true,
              rendu: (projet) => projet.bailleur ?? '—',
            },
            {
              cle: 'statut',
              entete: 'Statut',
              rendu: (projet) => (
                <Badge ton={tonDuStatut(projet.statut)}>{humaniser(projet.statut)}</Badge>
              ),
            },
          ]}
        />
      )}
    </>
  );
}
