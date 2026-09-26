'use client';

import { useQuery } from '@tanstack/react-query';
import { Bus, Clock, CreditCard, MapPin, Truck, Users } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Jauge, Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
  tonDuStatut,
} from '@/components/ui/primitives';
import { ListeRessource } from '@/components/ui/liste';
import { useListe } from '@/hooks/useListe';
import { api, type Page } from '@/lib/api';
import { formaterDate, formaterMontant, humaniser } from '@/lib/utils';

interface Vehicule {
  id: string;
  immatriculation: string;
  code: string;
  type_vehicule: string;
  marque: string | null;
  modele: string | null;
  places: number;
  places_pmr: number;
  statut: string;
  climatise: boolean;
}

interface Abonnement {
  id: string;
  numero_carte: string;
  date_debut: string;
  date_fin: string;
  montant: number;
  statut_paiement: string;
  actif: boolean;
  abonne_nom: string | null;
  ligne_libelle: string | null;
}

interface Ligne {
  id: string;
  code: string;
  libelle: string;
  origine: string;
  destination: string;
  distance_km: number | null;
  duree_minutes: number | null;
  tarif: number;
  tarif_abonnement: number;
  couleur: string | null;
  active: boolean;
}

interface Arret {
  id: string;
  code: string;
  nom: string;
  ordre: number;
  heure_passage_aller: string | null;
  abri: boolean;
  accessible_handicap: boolean;
}

interface Trajet {
  id: string;
  ligne: string;
  ligne_code: string;
  vehicule: string | null;
  conducteur: string | null;
  sens: string;
  statut: string;
  heure_depart_prevue: string;
  prochain_arret: string | null;
  minutes_avant_prochain_arret: number | null;
  places_occupees: number;
  places_disponibles: number | null;
  retard_minutes: number;
}

export default function PageTransport() {
  const [ligneId, setLigneId] = useState<string | null>(null);

  const lignes = useQuery({
    queryKey: ['lignes-transport'],
    queryFn: () => api.get<Page<Ligne>>('/transport/lignes', { size: 50 }),
  });

  const ligneActive = ligneId ?? lignes.data?.items[0]?.id ?? null;

  const arrets = useQuery({
    queryKey: ['arrets', ligneActive],
    enabled: Boolean(ligneActive),
    queryFn: () => api.get<Arret[]>(`/transport/lignes/${ligneActive}/arrets`),
  });

  const vehicules = useQuery({
    queryKey: ['vehicules'],
    queryFn: () => api.get<Page<Vehicule>>('/transport/vehicules', { size: 50, sort_by: 'code' }),
  });

  const abonnements = useListe<Abonnement>('/transport/abonnements', { tri: 'numero_carte' });

  const trajets = useQuery({
    queryKey: ['trajets', ligneActive],
    enabled: Boolean(ligneActive),
    // Le suivi se rafraîchit régulièrement : c'est l'information la plus périssable.
    refetchInterval: 30_000,
    queryFn: () => api.get<Trajet[]>(`/transport/lignes/${ligneActive}/temps-reel`),
  });

  if (lignes.isLoading) return <Chargement libelle="Chargement du réseau de transport…" />;
  if (lignes.isError) return <MessageErreur erreur={lignes.error} />;

  const ligne = lignes.data?.items.find((element) => element.id === ligneActive);

  return (
    <>
      <EntetePage
        titre="Transport scolaire et universitaire"
        description="Lignes, arrêts, véhicules et suivi des trajets en temps réel."
        personnel={{
          titre: 'Mon transport',
          description: 'Votre abonnement et les lignes desservant votre établissement.',
          parRole: {
            PARENT: {
              titre: 'Transport de mes enfants',
              description: 'Leur abonnement et les lignes desservant leur établissement.',
            },
          },
        }}
      />

      <div className="grid gap-4 xl:grid-cols-[20rem_1fr]">
        {/* Lignes */}
        <Carte className="h-fit">
          <EnteteCarte titre="Lignes" description={`${lignes.data?.total ?? 0} ligne(s).`} />
          <ul className="divide-y">
            {(lignes.data?.items ?? []).map((element) => (
              <li key={element.id}>
                <button
                  type="button"
                  onClick={() => setLigneId(element.id)}
                  aria-current={element.id === ligneActive ? 'true' : undefined}
                  className={`flex w-full items-center gap-3 px-4 py-3 text-left transition ${
                    element.id === ligneActive
                      ? 'bg-[rgb(var(--accent))]/10'
                      : 'hover:bg-[rgb(var(--fond-doux))]'
                  }`}
                >
                  <span
                    aria-hidden
                    className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-xs font-bold text-white"
                    style={{ backgroundColor: element.couleur ?? '#284f8b' }}
                  >
                    {element.code}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">{element.libelle}</span>
                    <span className="block truncate text-xs texte-doux">
                      {element.origine} → {element.destination}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Carte>

        <div className="space-y-4">
          {ligne ? (
            <Carte>
              <EnteteCarte
                titre={ligne.libelle}
                description={`${ligne.distance_km ?? '—'} km · environ ${ligne.duree_minutes ?? '—'} minutes`}
                action={
                  <Badge ton={ligne.active ? 'succes' : 'neutre'}>
                    {ligne.active ? 'En service' : 'Suspendue'}
                  </Badge>
                }
              />
              <CorpsCarte>
                <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
                  <div>
                    <dt className="texte-doux">Tarif au trajet</dt>
                    <dd className="font-semibold">{formaterMontant(ligne.tarif)}</dd>
                  </div>
                  <div>
                    <dt className="texte-doux">Abonnement mensuel</dt>
                    <dd className="font-semibold">{formaterMontant(ligne.tarif_abonnement)}</dd>
                  </div>
                </dl>
              </CorpsCarte>
            </Carte>
          ) : null}

          {/* Suivi en temps réel */}
          <Carte>
            <EnteteCarte
              titre={
                <span className="flex items-center gap-2">
                  <Bus size={19} aria-hidden /> Trajets en cours
                </span>
              }
              description="Position simulée, prochain arrêt et places disponibles."
            />
            {(trajets.data ?? []).length > 0 ? (
              <ul className="divide-y">
                {(trajets.data ?? []).map((trajet) => (
                  <li key={trajet.id} className="px-5 py-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="flex flex-wrap items-center gap-2 font-medium">
                          Bus {trajet.vehicule ?? '—'}
                          <Badge ton={tonDuStatut(trajet.statut)}>{humaniser(trajet.statut)}</Badge>
                          {trajet.retard_minutes > 0 ? (
                            <Badge ton="alerte">+{trajet.retard_minutes} min</Badge>
                          ) : null}
                        </p>
                        <p className="mt-1 flex flex-wrap items-center gap-3 text-sm texte-doux">
                          <span className="inline-flex items-center gap-1.5">
                            <Clock size={15} aria-hidden /> Départ{' '}
                            {trajet.heure_depart_prevue?.slice(0, 5)}
                          </span>
                          {trajet.prochain_arret ? (
                            <span className="inline-flex items-center gap-1.5">
                              <MapPin size={15} aria-hidden /> {trajet.prochain_arret}
                              {trajet.minutes_avant_prochain_arret !== null
                                ? ` dans ${trajet.minutes_avant_prochain_arret} min`
                                : ''}
                            </span>
                          ) : null}
                          {trajet.conducteur ? <span>{trajet.conducteur}</span> : null}
                        </p>
                      </div>
                      {trajet.places_disponibles !== null ? (
                        <div className="w-40 shrink-0">
                          <Jauge
                            valeur={trajet.places_occupees}
                            maximum={trajet.places_occupees + trajet.places_disponibles}
                            etiquette={`${trajet.places_disponibles} places libres`}
                            ton={trajet.places_disponibles > 5 ? 'succes' : 'alerte'}
                          />
                        </div>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <EtatVide
                titre="Aucun trajet en cours"
                description="Les trajets du jour apparaîtront ici dès leur programmation."
                icone={<Bus size={32} aria-hidden />}
              />
            )}
          </Carte>

          {/* Arrêts */}
          <Carte>
            <EnteteCarte
              titre={
                <span className="flex items-center gap-2">
                  <MapPin size={19} aria-hidden /> Arrêts desservis
                </span>
              }
            />
            {(arrets.data ?? []).length > 0 ? (
              <ol className="divide-y">
                {(arrets.data ?? []).map((arret) => (
                  <li key={arret.id} className="flex items-center gap-3 px-5 py-3">
                    <span
                      aria-hidden
                      className="grid h-7 w-7 shrink-0 place-items-center rounded-full surface-douce text-xs font-semibold"
                    >
                      {arret.ordre}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{arret.nom}</span>
                      {arret.heure_passage_aller ? (
                        <span className="block text-xs texte-doux">
                          Passage vers {arret.heure_passage_aller.slice(0, 5)}
                        </span>
                      ) : null}
                    </span>
                    <span className="flex shrink-0 gap-1.5">
                      {arret.abri ? <Badge ton="neutre">Abri</Badge> : null}
                      {arret.accessible_handicap ? <Badge ton="info">Accessible</Badge> : null}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <EtatVide titre="Aucun arrêt déclaré" icone={<Users size={32} aria-hidden />} />
            )}
          </Carte>

          {/* Parc de véhicules */}
          <Carte>
            <EnteteCarte
              titre={
                <span className="flex items-center gap-2">
                  <Truck size={19} aria-hidden /> Parc de véhicules
                </span>
              }
              description={`${vehicules.data?.total ?? 0} véhicule(s), dont les places réservées aux personnes à mobilité réduite.`}
            />
            <Tableau
              legende="Véhicules affectés au transport scolaire"
              lignes={vehicules.data?.items ?? []}
              cleLigne={(vehicule) => vehicule.id}
              vide={<EtatVide titre="Aucun véhicule déclaré" />}
              colonnes={[
                {
                  cle: 'immatriculation',
                  entete: 'Véhicule',
                  rendu: (vehicule) => (
                    <span className="min-w-0">
                      <span className="block font-medium">{vehicule.immatriculation}</span>
                      <span className="block text-xs texte-doux">
                        {[vehicule.marque, vehicule.modele].filter(Boolean).join(' ') ||
                          vehicule.code}
                      </span>
                    </span>
                  ),
                },
                {
                  cle: 'type',
                  entete: 'Type',
                  secondaire: true,
                  rendu: (vehicule) => humaniser(vehicule.type_vehicule),
                },
                {
                  cle: 'places',
                  entete: 'Places',
                  alignement: 'droite',
                  rendu: (vehicule) => (
                    <span className="min-w-0">
                      <span className="block">{vehicule.places}</span>
                      <span className="block text-xs texte-doux">
                        dont {vehicule.places_pmr} PMR
                      </span>
                    </span>
                  ),
                },
                {
                  cle: 'statut',
                  entete: 'État',
                  rendu: (vehicule) => (
                    <span className="flex flex-wrap gap-1.5">
                      <Badge ton={tonDuStatut(vehicule.statut)}>{humaniser(vehicule.statut)}</Badge>
                      {vehicule.climatise ? <Badge ton="neutre">Climatisé</Badge> : null}
                    </span>
                  ),
                },
              ]}
            />
          </Carte>
        </div>
      </div>

      {/* Abonnements */}
      <Carte className="mt-4">
        <EnteteCarte
          titre={
            <span className="flex items-center gap-2">
              <CreditCard size={19} aria-hidden /> Abonnements
            </span>
          }
          description="Cartes de transport des apprenants, par ligne desservie."
        />
        <ListeRessource
          legende="Abonnements au transport scolaire"
          placeholderRecherche="Rechercher par numéro de carte…"
          items={abonnements.items}
          total={abonnements.total}
          pages={abonnements.pages}
          page={abonnements.etat.page}
          taille={abonnements.etat.taille}
          chargement={abonnements.isLoading}
          erreur={abonnements.error}
          recherche={abonnements.etat.recherche}
          onRecherche={abonnements.changerRecherche}
          onPage={abonnements.changerPage}
          cleLigne={(abonnement) => abonnement.id}
          videTitre="Aucun abonnement"
          colonnes={[
            {
              cle: 'abonne',
              entete: 'Abonné',
              rendu: (abonnement) => (
                <span className="min-w-0">
                  <span className="block truncate font-medium">{abonnement.abonne_nom ?? '—'}</span>
                  <span className="block font-mono text-xs texte-doux">
                    {abonnement.numero_carte}
                  </span>
                </span>
              ),
            },
            {
              cle: 'ligne',
              entete: 'Ligne',
              rendu: (abonnement) => (
                <span className="block max-w-[22rem] truncate">
                  {abonnement.ligne_libelle ?? '—'}
                </span>
              ),
            },
            {
              cle: 'validite',
              entete: 'Validité',
              secondaire: true,
              rendu: (abonnement) =>
                `${formaterDate(abonnement.date_debut)} → ${formaterDate(abonnement.date_fin)}`,
            },
            {
              cle: 'montant',
              entete: 'Montant',
              alignement: 'droite',
              rendu: (abonnement) => formaterMontant(abonnement.montant),
            },
            {
              cle: 'statut',
              entete: 'État',
              rendu: (abonnement) => (
                <span className="flex flex-wrap gap-1.5">
                  <Badge ton={tonDuStatut(abonnement.statut_paiement)}>
                    {humaniser(abonnement.statut_paiement)}
                  </Badge>
                  <Badge ton={abonnement.actif ? 'succes' : 'neutre'}>
                    {abonnement.actif ? 'Actif' : 'Expiré'}
                  </Badge>
                </span>
              ),
            },
          ]}
        />
      </Carte>
    </>
  );
}
