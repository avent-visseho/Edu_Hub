'use client';

import { useQuery } from '@tanstack/react-query';
import { BookUser, Briefcase, Phone, Users } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Selection, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterDate, humaniser } from '@/lib/utils';
import type { Etablissement } from '@/types/api';

type Onglet = 'parents' | 'personnels';

interface EnfantRattache {
  id: string;
  nom_complet: string | null;
  identifiant_educatif: string | null;
  lien: string;
  contact_principal: boolean;
}

interface Parent {
  id: string;
  nom_complet: string;
  sexe: string | null;
  profession: string | null;
  telephone: string | null;
  email: string | null;
  adresse: string | null;
  niveau_alphabetisation: string | null;
  nombre_enfants: number;
  enfants_scolarises: EnfantRattache[];
}

interface Personnel {
  id: string;
  matricule: string;
  nom_complet: string;
  sexe: string;
  categorie: string;
  fonction: string;
  statut_agent: string;
  situation: string;
  etablissement_id: string | null;
  telephone: string | null;
  email: string | null;
  date_prise_service: string | null;
  peut_saisir_notes: boolean;
}

const CATEGORIES = [
  'ADMINISTRATIF',
  'TECHNIQUE',
  'SANTE',
  'SECURITE',
  'ENTRETIEN',
  'RESTAURATION',
  'BIBLIOTHEQUE',
  'INFORMATIQUE',
];

export default function PageAnnuaire() {
  const router = useRouter();
  const [onglet, setOnglet] = useState<Onglet>('parents');
  const [categorie, setCategorie] = useState('');
  const [etablissementId, setEtablissementId] = useState('');

  const etablissements = useQuery({
    queryKey: ['etablissements-liste'],
    queryFn: () => api.get<Page<Etablissement>>('/etablissements', { size: 200, sort_by: 'nom' }),
  });

  const parents = useListe<Parent>('/parents', {
    tri: 'nom',
    active: onglet === 'parents',
  });

  const personnels = useListe<Personnel>('/personnels', {
    tri: 'nom',
    active: onglet === 'personnels',
    filtres: {
      categorie: categorie || undefined,
      etablissement_id: etablissementId || undefined,
    },
  });

  const parEtablissement = new Map(
    (etablissements.data?.items ?? []).map((element) => [element.id, element.nom]),
  );

  return (
    <>
      <EntetePage
        titre="Annuaire"
        description="Parents et tuteurs rattachés aux apprenants, et personnels non enseignants des établissements."
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <Indicateur
          libelle="Parents et tuteurs"
          valeur={parents.total || '—'}
          icone={<BookUser size={19} aria-hidden />}
          pictogramme="👨‍👩‍👧"
        />
        <Indicateur
          libelle="Personnels non enseignants"
          valeur={personnels.total || '—'}
          icone={<Briefcase size={19} aria-hidden />}
          pictogramme="🧰"
        />
        {/* Le décompte porte sur la page affichée : il n'a de sens que l'onglet
            des personnels ouvert, sans quoi la liste n'est pas chargée. */}
        <Indicateur
          libelle="Habilités à saisir des notes"
          valeur={
            onglet === 'personnels'
              ? personnels.items.filter((agent) => agent.peut_saisir_notes).length
              : '—'
          }
          unite={onglet === 'personnels' ? 'sur la page affichée' : undefined}
          pictogramme="✍️"
        />
      </div>

      <div role="tablist" aria-label="Catégorie d'annuaire" className="mb-4 flex flex-wrap gap-2">
        {(
          [
            { cle: 'parents', libelle: 'Parents et tuteurs', icone: Users },
            { cle: 'personnels', libelle: 'Personnels', icone: Briefcase },
          ] as const
        ).map((element) => {
          const Icone = element.icone;
          const actif = onglet === element.cle;
          return (
            <button
              key={element.cle}
              type="button"
              role="tab"
              aria-selected={actif}
              onClick={() => setOnglet(element.cle)}
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

      {onglet === 'parents' ? (
        <ListeRessource
          legende="Liste des parents et tuteurs"
          placeholderRecherche="Rechercher par nom, prénoms ou téléphone…"
          items={parents.items}
          total={parents.total}
          pages={parents.pages}
          page={parents.etat.page}
          taille={parents.etat.taille}
          chargement={parents.isLoading}
          erreur={parents.error}
          recherche={parents.etat.recherche}
          onRecherche={parents.changerRecherche}
          onPage={parents.changerPage}
          cleLigne={(parent) => parent.id}
          videTitre="Aucun parent enregistré"
          colonnes={[
            {
              cle: 'nom',
              entete: 'Parent ou tuteur',
              rendu: (parent) => (
                <span className="min-w-0">
                  <span className="block truncate font-medium">{parent.nom_complet}</span>
                  <span className="block truncate text-xs texte-doux">
                    {parent.profession ?? 'Profession non renseignée'}
                  </span>
                </span>
              ),
            },
            {
              cle: 'contact',
              entete: 'Contact',
              rendu: (parent) => (
                <span className="min-w-0">
                  <span className="flex items-center gap-1.5">
                    <Phone size={14} aria-hidden className="texte-doux" />
                    {parent.telephone ?? '—'}
                  </span>
                  {parent.email ? (
                    <span className="block truncate text-xs texte-doux">{parent.email}</span>
                  ) : null}
                </span>
              ),
            },
            {
              cle: 'enfants',
              entete: 'Enfants scolarisés',
              rendu: (parent) =>
                parent.enfants_scolarises.length === 0 ? (
                  <span className="texte-doux">Aucun</span>
                ) : (
                  <ul className="space-y-0.5">
                    {parent.enfants_scolarises.map((enfant) => (
                      <li key={enfant.id}>
                        <button
                          type="button"
                          onClick={(evenement) => {
                            evenement.stopPropagation();
                            router.push(`/apprenants/${enfant.id}`);
                          }}
                          className="flex flex-wrap items-center gap-1.5 text-left hover:underline"
                        >
                          <span>{enfant.nom_complet ?? '—'}</span>
                          <span className="text-xs texte-doux">{humaniser(enfant.lien)}</span>
                          {enfant.contact_principal ? (
                            <Badge ton="info">Contact principal</Badge>
                          ) : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                ),
            },
            {
              cle: 'alphabetisation',
              entete: 'Alphabétisation',
              secondaire: true,
              rendu: (parent) => parent.niveau_alphabetisation ?? '—',
            },
          ]}
        />
      ) : (
        <ListeRessource
          legende="Liste des personnels non enseignants"
          placeholderRecherche="Rechercher par nom, matricule ou fonction…"
          items={personnels.items}
          total={personnels.total}
          pages={personnels.pages}
          page={personnels.etat.page}
          taille={personnels.etat.taille}
          chargement={personnels.isLoading}
          erreur={personnels.error}
          recherche={personnels.etat.recherche}
          onRecherche={personnels.changerRecherche}
          onPage={personnels.changerPage}
          cleLigne={(agent) => agent.id}
          videTitre="Aucun personnel"
          filtres={
            <div className="grid gap-4 sm:grid-cols-2">
              <Selection
                etiquette="Catégorie"
                value={categorie}
                onChange={(evenement) => setCategorie(evenement.target.value)}
                options={[
                  { valeur: '', libelle: 'Toutes les catégories' },
                  ...CATEGORIES.map((valeur) => ({ valeur, libelle: humaniser(valeur) })),
                ]}
              />
              <Selection
                etiquette="Établissement"
                value={etablissementId}
                onChange={(evenement) => setEtablissementId(evenement.target.value)}
                options={[
                  { valeur: '', libelle: 'Tous les établissements' },
                  ...(etablissements.data?.items ?? []).map((element) => ({
                    valeur: element.id,
                    libelle: element.nom,
                  })),
                ]}
              />
            </div>
          }
          colonnes={[
            {
              cle: 'nom',
              entete: 'Agent',
              rendu: (agent) => (
                <span className="min-w-0">
                  <span className="block truncate font-medium">{agent.nom_complet}</span>
                  <span className="block font-mono text-xs texte-doux">{agent.matricule}</span>
                </span>
              ),
            },
            {
              cle: 'fonction',
              entete: 'Fonction',
              rendu: (agent) => (
                <span className="min-w-0">
                  <span className="block truncate">{agent.fonction}</span>
                  <span className="block text-xs texte-doux">{humaniser(agent.categorie)}</span>
                </span>
              ),
            },
            {
              cle: 'etablissement',
              entete: 'Affectation',
              secondaire: true,
              rendu: (agent) => (
                <span className="block max-w-[18rem] truncate">
                  {agent.etablissement_id
                    ? (parEtablissement.get(agent.etablissement_id) ?? '—')
                    : 'Structure centrale'}
                </span>
              ),
            },
            {
              cle: 'service',
              entete: 'En poste depuis',
              alignement: 'droite',
              secondaire: true,
              rendu: (agent) =>
                agent.date_prise_service ? formaterDate(agent.date_prise_service) : '—',
            },
            {
              cle: 'statut',
              entete: 'Statut',
              rendu: (agent) => (
                <span className="flex flex-wrap gap-1.5">
                  <Badge ton="neutre">{humaniser(agent.statut_agent)}</Badge>
                  <Badge ton={tonDuStatut(agent.situation)}>{humaniser(agent.situation)}</Badge>
                  {agent.peut_saisir_notes ? <Badge ton="info">Saisie des notes</Badge> : null}
                </span>
              ),
            },
          ]}
        />
      )}
    </>
  );
}
