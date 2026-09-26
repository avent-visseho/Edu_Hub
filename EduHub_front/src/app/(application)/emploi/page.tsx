'use client';

import { useQuery } from '@tanstack/react-query';
import { Accessibility, Briefcase, Building2 } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Selection, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterDate, formaterMontant, formaterNote, humaniser } from '@/lib/utils';

interface Entreprise {
  id: string;
  code: string;
  raison_sociale: string;
  secteur_activite: string | null;
  adresse: string | null;
  telephone: string | null;
  effectif: number | null;
  partenaire_officiel: boolean;
  accueille_handicap: boolean;
}

interface Offre {
  id: string;
  reference: string;
  intitule: string;
  entreprise_id: string;
  type_contrat: string;
  competences_requises: string | null;
  niveau_requis: string | null;
  domaine: string | null;
  lieu: string | null;
  duree_mois: number | null;
  gratification: number;
  places: number;
  places_pourvues: number;
  date_publication: string;
  date_limite: string | null;
  accessible_handicap: boolean;
  ouverte: boolean;
}

interface Stage {
  id: string;
  reference: string;
  sujet: string;
  tuteur_entreprise: string | null;
  date_debut: string;
  date_fin: string;
  gratification: number;
  convention_signee: boolean;
  note_finale: number | null;
  valide: boolean;
}

interface Candidature {
  id: string;
  statut: string;
  date_candidature: string | null;
  date_entretien: string | null;
  date_reponse: string | null;
  commentaire_recruteur: string | null;
  candidat_nom: string | null;
  offre_intitule: string | null;
}

type Onglet = 'offres' | 'entreprises' | 'stages' | 'candidatures';

export default function PageEmploi() {
  const [onglet, setOnglet] = useState<Onglet>('offres');
  const [typeContrat, setTypeContrat] = useState('');

  const entreprises = useQuery({
    queryKey: ['entreprises-resume'],
    queryFn: () => api.get<Page<Entreprise>>('/entreprises', { size: 200 }),
  });

  const nomsEntreprises = new Map(
    (entreprises.data?.items ?? []).map((entreprise) => [entreprise.id, entreprise.raison_sociale]),
  );

  const offres = useListe<Offre>('/offres', {
    tri: 'date_publication',
    filtres: { type_contrat: typeContrat || undefined },
    active: onglet === 'offres',
  });
  const listeEntreprises = useListe<Entreprise>('/entreprises', {
    tri: 'raison_sociale',
    active: onglet === 'entreprises',
  });
  const stages = useListe<Stage>('/stages', { tri: 'date_debut', active: onglet === 'stages' });
  const candidatures = useListe<Candidature>('/candidatures-offre', {
    tri: 'date_candidature',
    sens: 'desc',
    active: onglet === 'candidatures',
  });

  const total = entreprises.data?.items ?? [];
  const partenaires = total.filter((entreprise) => entreprise.partenaire_officiel).length;
  const inclusifs = total.filter((entreprise) => entreprise.accueille_handicap).length;

  return (
    <>
      <EntetePage
        titre="Stages et emploi"
        description="Entreprises partenaires, offres de stage et d'emploi, et suivi des stages conventionnés."
        personnel={{
          titre: 'Mes candidatures',
          description: "Vos candidatures aux offres de stage et d'emploi.",
          parRole: {
            PARENT: {
              titre: 'Candidatures de mes enfants',
              description: "Leurs candidatures aux offres de stage et d'emploi.",
            },
          },
        }}
      />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicateur
          libelle="Entreprises"
          valeur={total.length}
          icone={<Building2 size={18} />}
          pictogramme="🏢"
        />
        <Indicateur libelle="Partenaires officiels" valeur={partenaires} pictogramme="🤝" />
        <Indicateur
          libelle="Accueillent le handicap"
          valeur={inclusifs}
          icone={<Accessibility size={18} />}
          pictogramme="♿"
        />
        <Indicateur
          libelle="Offres ouvertes"
          valeur={offres.total}
          icone={<Briefcase size={18} />}
          pictogramme="💼"
        />
      </div>

      <div role="tablist" aria-label="Section" className="mb-4 inline-flex rounded-lg border p-1">
        {(
          [
            { cle: 'offres', libelle: 'Offres' },
            { cle: 'entreprises', libelle: 'Entreprises' },
            { cle: 'stages', libelle: 'Stages' },
            { cle: 'candidatures', libelle: 'Candidatures' },
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

      {onglet === 'offres' ? (
        <ListeRessource
          legende="Offres de stage et d'emploi"
          placeholderRecherche="Rechercher une offre, un domaine…"
          items={offres.items}
          total={offres.total}
          pages={offres.pages}
          page={offres.etat.page}
          taille={offres.etat.taille}
          chargement={offres.isLoading}
          erreur={offres.error}
          recherche={offres.etat.recherche}
          onRecherche={offres.changerRecherche}
          onPage={offres.changerPage}
          cleLigne={(offre) => offre.id}
          videTitre="Aucune offre"
          filtres={
            <Selection
              etiquette="Type de contrat"
              value={typeContrat}
              onChange={(evenement) => setTypeContrat(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Tous les contrats' },
                ...['STAGE', 'CDD', 'CDI', 'APPRENTISSAGE', 'INTERIM', 'FREELANCE'].map(
                  (valeur) => ({ valeur, libelle: humaniser(valeur) }),
                ),
              ]}
            />
          }
          colonnes={[
            {
              cle: 'intitule',
              entete: 'Offre',
              rendu: (offre) => (
                <div className="min-w-0">
                  <p className="flex flex-wrap items-center gap-2 font-medium">
                    {offre.intitule}
                    {offre.accessible_handicap ? (
                      <Badge ton="info">
                        <Accessibility size={13} aria-hidden /> Accessible
                      </Badge>
                    ) : null}
                  </p>
                  <p className="truncate text-xs texte-doux">
                    {nomsEntreprises.get(offre.entreprise_id) ?? offre.reference}
                    {offre.lieu ? ` · ${offre.lieu}` : ''}
                  </p>
                </div>
              ),
            },
            {
              cle: 'contrat',
              entete: 'Contrat',
              rendu: (offre) => <Badge ton="neutre">{humaniser(offre.type_contrat)}</Badge>,
            },
            {
              cle: 'duree',
              entete: 'Durée',
              alignement: 'centre',
              secondaire: true,
              rendu: (offre) => (offre.duree_mois ? `${offre.duree_mois} mois` : '—'),
            },
            {
              cle: 'gratification',
              entete: 'Gratification',
              alignement: 'droite',
              secondaire: true,
              rendu: (offre) =>
                offre.gratification > 0 ? formaterMontant(offre.gratification) : '—',
            },
            {
              cle: 'places',
              entete: 'Places',
              alignement: 'centre',
              rendu: (offre) => `${offre.places_pourvues} / ${offre.places}`,
            },
            {
              cle: 'limite',
              entete: 'Date limite',
              secondaire: true,
              rendu: (offre) => formaterDate(offre.date_limite),
            },
            {
              cle: 'statut',
              entete: 'Statut',
              rendu: (offre) => (
                <Badge ton={offre.ouverte ? 'succes' : 'neutre'}>
                  {offre.ouverte ? 'Ouverte' : 'Close'}
                </Badge>
              ),
            },
          ]}
        />
      ) : onglet === 'entreprises' ? (
        <ListeRessource
          legende="Entreprises partenaires"
          placeholderRecherche="Rechercher une entreprise, un secteur…"
          items={listeEntreprises.items}
          total={listeEntreprises.total}
          pages={listeEntreprises.pages}
          page={listeEntreprises.etat.page}
          taille={listeEntreprises.etat.taille}
          chargement={listeEntreprises.isLoading}
          erreur={listeEntreprises.error}
          recherche={listeEntreprises.etat.recherche}
          onRecherche={listeEntreprises.changerRecherche}
          onPage={listeEntreprises.changerPage}
          cleLigne={(entreprise) => entreprise.id}
          videTitre="Aucune entreprise"
          colonnes={[
            {
              cle: 'raison',
              entete: 'Entreprise',
              rendu: (entreprise) => (
                <div className="min-w-0">
                  <p className="font-medium">{entreprise.raison_sociale}</p>
                  <p className="truncate text-xs texte-doux">{entreprise.adresse ?? '—'}</p>
                </div>
              ),
            },
            {
              cle: 'secteur',
              entete: 'Secteur',
              rendu: (entreprise) =>
                entreprise.secteur_activite ? (
                  <Badge ton="neutre">{entreprise.secteur_activite}</Badge>
                ) : (
                  '—'
                ),
            },
            {
              cle: 'effectif',
              entete: 'Effectif',
              alignement: 'droite',
              secondaire: true,
              rendu: (entreprise) => entreprise.effectif ?? '—',
            },
            {
              cle: 'telephone',
              entete: 'Téléphone',
              secondaire: true,
              rendu: (entreprise) => entreprise.telephone ?? '—',
            },
            {
              cle: 'engagements',
              entete: 'Engagements',
              rendu: (entreprise) => (
                <span className="flex flex-wrap gap-1.5">
                  {entreprise.partenaire_officiel ? <Badge ton="succes">Partenaire</Badge> : null}
                  {entreprise.accueille_handicap ? <Badge ton="info">Inclusive</Badge> : null}
                </span>
              ),
            },
          ]}
        />
      ) : (
        <ListeRessource
          legende="Stages conventionnés"
          placeholderRecherche="Rechercher un stage, un sujet…"
          items={stages.items}
          total={stages.total}
          pages={stages.pages}
          page={stages.etat.page}
          taille={stages.etat.taille}
          chargement={stages.isLoading}
          erreur={stages.error}
          recherche={stages.etat.recherche}
          onRecherche={stages.changerRecherche}
          onPage={stages.changerPage}
          cleLigne={(stage) => stage.id}
          videTitre="Aucun stage"
          colonnes={[
            {
              cle: 'sujet',
              entete: 'Stage',
              rendu: (stage) => (
                <div className="min-w-0">
                  <p className="font-medium">{stage.sujet}</p>
                  <p className="truncate font-mono text-xs texte-doux">{stage.reference}</p>
                </div>
              ),
            },
            {
              cle: 'periode',
              entete: 'Période',
              secondaire: true,
              rendu: (stage) =>
                `${formaterDate(stage.date_debut)} → ${formaterDate(stage.date_fin)}`,
            },
            {
              cle: 'tuteur',
              entete: 'Tuteur',
              secondaire: true,
              rendu: (stage) => stage.tuteur_entreprise ?? '—',
            },
            {
              cle: 'note',
              entete: 'Note finale',
              alignement: 'droite',
              rendu: (stage) => (
                <span className="font-semibold">{formaterNote(stage.note_finale)}</span>
              ),
            },
            {
              cle: 'statut',
              entete: 'Statut',
              rendu: (stage) => (
                <span className="flex flex-wrap gap-1.5">
                  {stage.convention_signee ? <Badge ton="neutre">Convention signée</Badge> : null}
                  <Badge ton={stage.valide ? 'succes' : 'alerte'}>
                    {stage.valide ? 'Validé' : 'En cours'}
                  </Badge>
                </span>
              ),
            },
          ]}
        />
      )}

      {onglet === 'candidatures' ? (
        <ListeRessource
          legende="Candidatures déposées sur les offres"
          placeholderRecherche="Rechercher une candidature…"
          items={candidatures.items}
          total={candidatures.total}
          pages={candidatures.pages}
          page={candidatures.etat.page}
          taille={candidatures.etat.taille}
          chargement={candidatures.isLoading}
          erreur={candidatures.error}
          recherche={candidatures.etat.recherche}
          onRecherche={candidatures.changerRecherche}
          onPage={candidatures.changerPage}
          cleLigne={(candidature) => candidature.id}
          videTitre="Aucune candidature"
          colonnes={[
            {
              cle: 'candidat',
              entete: 'Candidat',
              rendu: (candidature) => (
                <span className="block truncate font-medium">
                  {candidature.candidat_nom ?? '—'}
                </span>
              ),
            },
            {
              cle: 'offre',
              entete: 'Offre',
              rendu: (candidature) => (
                <span className="block max-w-[22rem] truncate">
                  {candidature.offre_intitule ?? '—'}
                </span>
              ),
            },
            {
              cle: 'depot',
              entete: 'Déposée le',
              alignement: 'droite',
              secondaire: true,
              rendu: (candidature) =>
                candidature.date_candidature ? formaterDate(candidature.date_candidature) : '—',
            },
            {
              cle: 'entretien',
              entete: 'Entretien',
              alignement: 'droite',
              secondaire: true,
              rendu: (candidature) =>
                candidature.date_entretien ? formaterDate(candidature.date_entretien) : '—',
            },
            {
              cle: 'statut',
              entete: 'Suite donnée',
              rendu: (candidature) => (
                <span className="min-w-0">
                  <Badge ton={tonDuStatut(candidature.statut)}>
                    {humaniser(candidature.statut)}
                  </Badge>
                  {candidature.commentaire_recruteur ? (
                    <span className="mt-1 block truncate text-xs texte-doux">
                      {candidature.commentaire_recruteur}
                    </span>
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
