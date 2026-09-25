'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Compass, FilePlus2, GraduationCap, Play, Trash2 } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur, Jauge, Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Champ,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
  Selection,
} from '@/components/ui/primitives';
import { ListeRessource } from '@/components/ui/liste';
import { useListe } from '@/hooks/useListe';
import {
  SelecteurApprenant,
  type ApprenantChoisi,
} from '@/components/ui/selecteur-apprenant';
import { api, ErreurApi } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterDate, formaterMontant, formaterNote, formaterPourcentage } from '@/lib/utils';

interface Campagne {
  id: string;
  code: string;
  libelle: string;
  date_ouverture: string;
  date_fermeture: string;
  nombre_voeux_max: number;
  ouverte: boolean;
}

interface Formation {
  id: string;
  code: string;
  intitule: string;
  niveau_entree: string | null;
  duree_annees: number;
  places_offertes: number;
  places_pourvues: number;
  moyenne_minimale: number | null;
  series_admises: string | null;
  debouches: string | null;
  frais_annuels: number;
  ouverte: boolean;
}

export default function PageOrientation() {
  const { peut } = useSession();
  const client = useQueryClient();
  const [dossier, setDossier] = useState<{
    campagne_id: string;
    moyenne: string;
    voeux: string[];
  }>({ campagne_id: '', moyenne: '', voeux: [] });
  const [candidat, setCandidat] = useState<ApprenantChoisi | null>(null);
  const [journalDossier, setJournalDossier] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const campagnes = useQuery({
    queryKey: ['campagnes-orientation'],
    queryFn: () => api.get<Campagne[]>('/orientation/campagnes'),
  });

  const formations = useListe<Formation>('/formations', { tri: 'intitule' });

  const campagneChoisie = (campagnes.data ?? []).find(
    (campagne) => campagne.id === dossier.campagne_id,
  );

  const deposerDossier = useMutation({
    mutationFn: () =>
      api.post<{ id: string }>('/orientation/dossiers', {
        campagne_id: dossier.campagne_id,
        apprenant_id: candidat!.id,
        moyenne_bac: dossier.moyenne ? Number(dossier.moyenne) : null,
        voeux: dossier.voeux
          .filter(Boolean)
          .map((formation_id, index) => ({ formation_id, rang: index + 1 })),
      }),
    onSuccess: () => {
      setJournalDossier(
        `Dossier déposé pour ${candidat!.nom_complet} avec ${dossier.voeux.filter(Boolean).length} vœu(x).`,
      );
      setCandidat(null);
      setDossier((precedent) => ({ ...precedent, moyenne: '', voeux: [] }));
      void client.invalidateQueries({ queryKey: ['campagnes-orientation'] });
    },
    onError: (erreurBrute: unknown) => {
      setJournalDossier(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "Le dossier n'a pas pu être déposé.",
      );
    },
  });

  const affectation = useMutation({
    mutationFn: (campagneId: string) =>
      api.post<{ message: string; details: Record<string, number> }>(
        `/orientation/campagnes/${campagneId}/affecter`,
      ),
    onSuccess: (reponse) => {
      setMessage(
        `${reponse.details.affectes} candidat(s) affecté(s), ` +
          `${reponse.details.liste_attente} en liste d'attente sur ` +
          `${reponse.details.dossiers} dossier(s).`,
      );
      void client.invalidateQueries({ queryKey: ['/formations'] });
    },
  });

  if (campagnes.isLoading) return <Chargement libelle="Chargement des campagnes d'orientation…" />;
  if (campagnes.isError) return <MessageErreur erreur={campagnes.error} />;

  const listeFormations = formations.items;
  const placesOffertes = listeFormations.reduce((total, f) => total + f.places_offertes, 0);
  const placesPourvues = listeFormations.reduce((total, f) => total + f.places_pourvues, 0);

  return (
    <>
      <EntetePage
        titre="Orientation post-baccalauréat"
        description="Campagnes de vœux, offre de formation et affectation des bacheliers par ordre de mérite."
      />

      {message ? (
        <div
          role="status"
          className="mb-4 rounded-lg border border-[rgb(var(--succes))]/40 bg-[rgb(var(--succes))]/8 px-4 py-3 text-sm font-medium"
        >
          {message}
        </div>
      ) : null}
      {affectation.isError ? <MessageErreur erreur={affectation.error} /> : null}

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicateur
          libelle="Formations ouvertes"
          valeur={listeFormations.filter((f) => f.ouverte).length}
          icone={<GraduationCap size={18} />}
          pictogramme="🎓"
        />
        <Indicateur libelle="Places offertes" valeur={placesOffertes} pictogramme="🪑" />
        <Indicateur libelle="Places pourvues" valeur={placesPourvues} pictogramme="✅" />
        <Indicateur
          libelle="Taux de remplissage"
          valeur={formaterPourcentage(
            placesOffertes ? (placesPourvues * 100) / placesOffertes : 0,
          )}
          pictogramme="📊"
        />
      </div>

      <Carte className="mb-4">
        <EnteteCarte
          titre={
            <span className="flex items-center gap-2">
              <Compass size={19} aria-hidden /> Campagnes d&apos;orientation
            </span>
          }
          description="Une campagne fixe la période de dépôt des vœux et leur nombre maximal."
        />
        {campagnes.data && campagnes.data.length > 0 ? (
          <Tableau
            legende="Campagnes d'orientation"
            lignes={campagnes.data}
            cleLigne={(campagne) => campagne.id}
            colonnes={[
              {
                cle: 'libelle',
                entete: 'Campagne',
                rendu: (campagne) => (
                  <div className="min-w-0">
                    <p className="font-medium">{campagne.libelle}</p>
                    <p className="truncate font-mono text-xs texte-doux">{campagne.code}</p>
                  </div>
                ),
              },
              {
                cle: 'periode',
                entete: 'Période de dépôt',
                rendu: (campagne) =>
                  `${formaterDate(campagne.date_ouverture)} → ${formaterDate(campagne.date_fermeture)}`,
              },
              {
                cle: 'voeux',
                entete: 'Vœux maximum',
                alignement: 'centre',
                secondaire: true,
                rendu: (campagne) => campagne.nombre_voeux_max,
              },
              {
                cle: 'statut',
                entete: 'Statut',
                rendu: (campagne) => (
                  <Badge ton={campagne.ouverte ? 'succes' : 'neutre'}>
                    {campagne.ouverte ? 'Ouverte' : 'Close'}
                  </Badge>
                ),
              },
              {
                cle: 'action',
                entete: 'Affectation',
                alignement: 'centre',
                rendu: (campagne) =>
                  peut('orientation', 'ASSIGN') ? (
                    <Bouton
                      variante="secondaire"
                      taille="sm"
                      chargement={affectation.isPending}
                      onClick={() => affectation.mutate(campagne.id)}
                      icone={<Play size={15} aria-hidden />}
                    >
                      Affecter
                    </Bouton>
                  ) : (
                    <span className="texte-doux">—</span>
                  ),
              },
            ]}
          />
        ) : (
          <EtatVide
            titre="Aucune campagne"
            description="Les campagnes d'orientation apparaîtront ici dès leur ouverture."
          />
        )}
      </Carte>

      <h2 className="mb-3 text-lg font-semibold">Offre de formation</h2>
      <ListeRessource
        legende="Catalogue des formations"
        placeholderRecherche="Rechercher une formation, un débouché…"
        items={listeFormations}
        total={formations.total}
        pages={formations.pages}
        page={formations.etat.page}
        taille={formations.etat.taille}
        chargement={formations.isLoading}
        erreur={formations.error}
        recherche={formations.etat.recherche}
        onRecherche={formations.changerRecherche}
        onPage={formations.changerPage}
        cleLigne={(formation) => formation.id}
        videTitre="Aucune formation"
        colonnes={[
          {
            cle: 'intitule',
            entete: 'Formation',
            rendu: (formation) => (
              <div className="min-w-0">
                <p className="font-medium">{formation.intitule}</p>
                {formation.debouches ? (
                  <p className="truncate text-xs texte-doux">{formation.debouches}</p>
                ) : null}
              </div>
            ),
          },
          {
            cle: 'duree',
            entete: 'Durée',
            alignement: 'centre',
            secondaire: true,
            rendu: (formation) => `${formation.duree_annees} an(s)`,
          },
          {
            cle: 'series',
            entete: 'Séries admises',
            secondaire: true,
            rendu: (formation) =>
              formation.series_admises ? (
                <span className="flex flex-wrap gap-1">
                  {formation.series_admises.split(',').map((serie) => (
                    <Badge key={serie} ton="neutre">
                      {serie}
                    </Badge>
                  ))}
                </span>
              ) : (
                '—'
              ),
          },
          {
            cle: 'moyenne',
            entete: 'Moyenne minimale',
            alignement: 'droite',
            rendu: (formation) => formaterNote(formation.moyenne_minimale),
          },
          {
            cle: 'places',
            entete: 'Places',
            largeur: '13rem',
            rendu: (formation) => (
              <Jauge
                valeur={formation.places_pourvues}
                maximum={formation.places_offertes || 1}
                etiquette={`${formation.places_pourvues} / ${formation.places_offertes}`}
                ton={
                  formation.places_pourvues >= formation.places_offertes ? 'alerte' : 'succes'
                }
              />
            ),
          },
          {
            cle: 'frais',
            entete: 'Frais annuels',
            alignement: 'droite',
            secondaire: true,
            rendu: (formation) => formaterMontant(formation.frais_annuels),
          },
        ]}
      />

      {peut('orientation', 'CREATE') ? (
        <Carte className="mt-4">
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <FilePlus2 size={19} aria-hidden /> Déposer un dossier d&apos;orientation
              </span>
            }
            description={
              campagneChoisie
                ? `${campagneChoisie.nombre_voeux_max} vœu(x) au plus pour cette campagne, classés par ordre de préférence.`
                : "Choisissez une campagne : elle fixe le nombre de vœux autorisés."
            }
          />
          <CorpsCarte>
            <div className="grid gap-3 sm:grid-cols-3">
              <Selection
                etiquette="Campagne"
                value={dossier.campagne_id}
                onChange={(evenement) =>
                  setDossier((precedent) => ({
                    ...precedent,
                    campagne_id: evenement.target.value,
                    voeux: [],
                  }))
                }
                options={[
                  { valeur: '', libelle: 'Choisir une campagne…' },
                  ...(campagnes.data ?? []).map((campagne) => ({
                    valeur: campagne.id,
                    libelle: campagne.libelle,
                  })),
                ]}
              />
              <SelecteurApprenant
                etiquette="Candidat"
                choisi={candidat}
                onChoisir={setCandidat}
              />
              <Champ
                etiquette="Moyenne du baccalauréat"
                type="number"
                min={0}
                max={20}
                step="0.01"
                value={dossier.moyenne}
                onChange={(evenement) =>
                  setDossier((precedent) => ({ ...precedent, moyenne: evenement.target.value }))
                }
              />
            </div>

            {campagneChoisie ? (
              <div className="mt-4">
                <h3 className="mb-2 font-medium">Vœux, par ordre de préférence</h3>
                <ul className="space-y-2">
                  {dossier.voeux.map((voeu, index) => (
                    <li key={`${voeu}-${index}`} className="flex items-end gap-2">
                      <span
                        aria-hidden
                        className="grid h-11 w-9 shrink-0 place-items-center rounded-lg surface-douce text-sm font-semibold"
                      >
                        {index + 1}
                      </span>
                      <span className="min-w-0 flex-1">
                        <Selection
                          etiquette={`Vœu numéro ${index + 1}`}
                          etiquetteMasquee
                          value={voeu}
                          onChange={(evenement) =>
                            setDossier((precedent) => ({
                              ...precedent,
                              voeux: precedent.voeux.map((autre, rang) =>
                                rang === index ? evenement.target.value : autre,
                              ),
                            }))
                          }
                          options={[
                            { valeur: '', libelle: 'Choisir une formation…' },
                            ...formations.items.map((formation) => ({
                              valeur: formation.id,
                              libelle: formation.intitule,
                            })),
                          ]}
                        />
                      </span>
                      <Bouton
                        variante="fantome"
                        aria-label={`Retirer le vœu numéro ${index + 1}`}
                        onClick={() =>
                          setDossier((precedent) => ({
                            ...precedent,
                            voeux: precedent.voeux.filter((_, rang) => rang !== index),
                          }))
                        }
                        icone={<Trash2 size={17} aria-hidden />}
                      />
                    </li>
                  ))}
                </ul>
                <Bouton
                  className="mt-2"
                  variante="secondaire"
                  disabled={dossier.voeux.length >= campagneChoisie.nombre_voeux_max}
                  onClick={() =>
                    setDossier((precedent) => ({ ...precedent, voeux: [...precedent.voeux, ''] }))
                  }
                >
                  Ajouter un vœu
                </Bouton>
              </div>
            ) : null}

            <Bouton
              className="mt-3"
              disabled={
                !dossier.campagne_id || !candidat || dossier.voeux.filter(Boolean).length === 0
              }
              chargement={deposerDossier.isPending}
              onClick={() => deposerDossier.mutate()}
            >
              Déposer le dossier
            </Bouton>
            {journalDossier ? (
              <p role="status" className="mt-2 text-sm texte-doux">
                {journalDossier}
              </p>
            ) : null}
          </CorpsCarte>
        </Carte>
      ) : null}
    </>
  );
}
