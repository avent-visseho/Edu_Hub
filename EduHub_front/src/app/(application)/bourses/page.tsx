'use client';

import { useQuery } from '@tanstack/react-query';

import { EntetePage } from '@/components/layout/entete-page';
import { Jauge, Tableau } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import {
  Badge,
  Carte,
  CorpsCarte,
  Chargement,
  EnteteCarte,
  EtatVide,
  tonDuStatut,
} from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterDate, formaterMontant, formaterNote, humaniser } from '@/lib/utils';

interface AideSociale {
  id: string;
  numero: string;
  type_aide: string;
  libelle: string;
  montant: number;
  en_nature: boolean;
  date_demande: string;
  date_attribution: string | null;
  statut: string;
  beneficiaire_nom: string | null;
  identifiant_educatif: string | null;
}

interface Programme {
  id: string;
  code: string;
  intitule: string;
  montant_mensuel: number;
  duree_mois: number;
  places: number;
  places_attribuees: number;
  moyenne_minimale: number | null;
  date_cloture: string;
  ouvert: boolean;
  reserve_handicap: boolean;
}

interface Candidature {
  id: string;
  numero: string;
  statut: string;
  moyenne_reference: number | null;
  score_evaluation: number | null;
  montant_attribue: number;
  date_soumission: string | null;
}

export default function PageBourses() {
  const programmes = useQuery({
    queryKey: ['programmes-bourse'],
    queryFn: () => api.get<Page<Programme>>('/programmes-bourse', { size: 50 }),
  });

  const liste = useListe<Candidature>('/candidatures-bourse', { tri: 'numero' });

  const aides = useQuery({
    queryKey: ['aides-sociales'],
    queryFn: () => api.get<Page<AideSociale>>('/aides-sociales', { size: 100, sort_by: 'numero' }),
  });

  return (
    <>
      <EntetePage
        titre="Bourses et aides sociales"
        description="Programmes ouverts, candidatures et attributions — y compris les dispositifs réservés à l'inclusion."
        personnel={{
          titre: 'Mes bourses',
          description: "Vos demandes de bourse et d'aide sociale, et leur suivi.",
        }}
      />

      <section className="mb-6" aria-labelledby="programmes">
        <h2 id="programmes" className="mb-3 text-lg font-semibold">
          Programmes de bourses
        </h2>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(programmes.data?.items ?? []).map((programme) => (
            <Carte key={programme.id}>
              <EnteteCarte
                titre={<span className="text-base">{programme.intitule}</span>}
                description={`${formaterMontant(programme.montant_mensuel)} par mois sur ${programme.duree_mois} mois.`}
                action={programme.reserve_handicap ? <Badge ton="info">Inclusion</Badge> : null}
              />
              <CorpsCarte className="space-y-3 p-4">
                <Jauge
                  valeur={programme.places_attribuees}
                  maximum={programme.places || 1}
                  etiquette={`${programme.places_attribuees} / ${programme.places} places attribuées`}
                  ton={programme.places_attribuees >= programme.places ? 'alerte' : 'succes'}
                />
                <dl className="flex flex-wrap gap-x-4 gap-y-1 text-sm texte-doux">
                  <div className="flex gap-1.5">
                    <dt>Moyenne minimale</dt>
                    <dd className="font-medium">{formaterNote(programme.moyenne_minimale)}</dd>
                  </div>
                  <div className="flex gap-1.5">
                    <dt>Clôture</dt>
                    <dd className="font-medium">{formaterDate(programme.date_cloture)}</dd>
                  </div>
                </dl>
              </CorpsCarte>
            </Carte>
          ))}
        </div>
      </section>

      <h2 className="mb-3 text-lg font-semibold">Candidatures</h2>
      <ListeRessource
        legende="Candidatures aux bourses"
        placeholderRecherche="Rechercher par numéro de candidature…"
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
        cleLigne={(candidature) => candidature.id}
        videTitre="Aucune candidature"
        colonnes={[
          {
            cle: 'numero',
            entete: 'Numéro',
            rendu: (candidature) => <span className="font-mono text-xs">{candidature.numero}</span>,
          },
          {
            cle: 'moyenne',
            entete: 'Moyenne de référence',
            alignement: 'droite',
            rendu: (candidature) => formaterNote(candidature.moyenne_reference),
          },
          {
            cle: 'score',
            entete: 'Score',
            alignement: 'droite',
            secondaire: true,
            rendu: (candidature) => formaterNote(candidature.score_evaluation),
          },
          {
            cle: 'montant',
            entete: 'Montant attribué',
            alignement: 'droite',
            rendu: (candidature) =>
              candidature.montant_attribue > 0
                ? formaterMontant(candidature.montant_attribue)
                : '—',
          },
          {
            cle: 'soumission',
            entete: 'Soumission',
            secondaire: true,
            rendu: (candidature) => formaterDate(candidature.date_soumission),
          },
          {
            cle: 'statut',
            entete: 'Statut',
            rendu: (candidature) => (
              <Badge ton={tonDuStatut(candidature.statut)}>{humaniser(candidature.statut)}</Badge>
            ),
          },
        ]}
      />

      <Carte className="mt-4">
        <EnteteCarte
          titre="Aides sociales ponctuelles"
          description="Dispositifs d'appoint — fournitures, restauration, transport, logement, santé — attribués hors programme de bourse."
        />
        {aides.isLoading ? (
          <CorpsCarte>
            <Chargement libelle="Chargement des aides sociales…" />
          </CorpsCarte>
        ) : (
          <Tableau
            legende="Aides sociales attribuées"
            lignes={aides.data?.items ?? []}
            cleLigne={(aide) => aide.id}
            vide={<EtatVide titre="Aucune aide sociale" />}
            colonnes={[
              {
                cle: 'beneficiaire',
                entete: 'Bénéficiaire',
                rendu: (aide) => (
                  <span className="min-w-0">
                    <span className="block truncate font-medium">
                      {aide.beneficiaire_nom ?? '—'}
                    </span>
                    <span className="block font-mono text-xs texte-doux">
                      {aide.identifiant_educatif ?? aide.numero}
                    </span>
                  </span>
                ),
              },
              {
                cle: 'libelle',
                entete: 'Aide',
                rendu: (aide) => (
                  <span className="min-w-0">
                    <span className="block truncate">{aide.libelle}</span>
                    <span className="block text-xs texte-doux">{humaniser(aide.type_aide)}</span>
                  </span>
                ),
              },
              {
                cle: 'montant',
                entete: 'Montant',
                alignement: 'droite',
                rendu: (aide) =>
                  aide.en_nature ? (
                    <span className="texte-doux">En nature</span>
                  ) : (
                    formaterMontant(aide.montant)
                  ),
              },
              {
                cle: 'dates',
                entete: 'Demande / attribution',
                secondaire: true,
                rendu: (aide) => (
                  <span className="min-w-0">
                    <span className="block">{formaterDate(aide.date_demande)}</span>
                    <span className="block text-xs texte-doux">
                      {aide.date_attribution
                        ? formaterDate(aide.date_attribution)
                        : 'Non attribuée'}
                    </span>
                  </span>
                ),
              },
              {
                cle: 'statut',
                entete: 'Statut',
                rendu: (aide) => (
                  <Badge ton={tonDuStatut(aide.statut)}>{humaniser(aide.statut)}</Badge>
                ),
              },
            ]}
          />
        )}
      </Carte>
    </>
  );
}
