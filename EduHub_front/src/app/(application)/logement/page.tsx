'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Accessibility, BedDouble, Building } from 'lucide-react';
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
} from '@/components/ui/primitives';
import { SelecteurApprenant, type ApprenantChoisi } from '@/components/ui/selecteur-apprenant';
import { api, ErreurApi, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterMontant, formaterNombre, formaterPourcentage } from '@/lib/utils';

interface Residence {
  id: string;
  code: string;
  nom: string;
  adresse: string | null;
  capacite: number;
  places_occupees: number;
  tarif_mensuel: number;
  mixte: boolean;
  accessible_handicap: boolean;
}

interface Chambre {
  id: string;
  numero: string;
  batiment: string | null;
  etage: number;
  nombre_lits: number;
  lits_occupes: number;
  tarif_mensuel: number;
  disponible: boolean;
  accessible_handicap: boolean;
}

export default function PageLogement() {
  const fileAttente = useQueryClient();
  const { peut } = useSession();
  const [residenceId, setResidenceId] = useState<string | null>(null);
  const [chambre, setChambre] = useState<Chambre | null>(null);
  const [apprenant, setApprenant] = useState<ApprenantChoisi | null>(null);
  const [debut, setDebut] = useState(() => new Date().toISOString().slice(0, 10));
  const [fin, setFin] = useState('');
  const [journal, setJournal] = useState<string | null>(null);
  const [disponiblesSeulement, setDisponiblesSeulement] = useState(false);

  const residences = useQuery({
    queryKey: ['residences'],
    queryFn: () => api.get<Page<Residence>>('/residences', { size: 50 }),
  });

  const active = residenceId ?? residences.data?.items[0]?.id ?? null;

  const attribuer = useMutation({
    mutationFn: () =>
      api.post<{ message: string }>('/residences/attributions', {
        apprenant_id: apprenant!.id,
        chambre_id: chambre!.id,
        date_debut: debut,
        date_fin: fin || null,
      }),
    onSuccess: (reponse) => {
      setJournal(
        `${reponse.message} ${apprenant!.nom_complet} est logé(e) en chambre ${chambre!.numero}.`,
      );
      setApprenant(null);
      setFin('');
      setChambre(null);
      void fileAttente.invalidateQueries({ queryKey: ['chambres'] });
      void fileAttente.invalidateQueries({ queryKey: ['residences'] });
    },
    onError: (erreurBrute: unknown) => {
      setJournal(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "L'attribution n'a pas pu être enregistrée.",
      );
    },
  });

  const chambres = useQuery({
    queryKey: ['chambres', active, disponiblesSeulement],
    enabled: Boolean(active),
    queryFn: () =>
      api.get<Chambre[]>(`/residences/${active}/chambres`, {
        disponibles_seulement: disponiblesSeulement,
      }),
  });

  if (residences.isLoading) return <Chargement libelle="Chargement du parc de logements…" />;
  if (residences.isError) return <MessageErreur erreur={residences.error} />;

  const liste = residences.data?.items ?? [];
  const residence = liste.find((element) => element.id === active);
  const capaciteTotale = liste.reduce((total, element) => total + element.capacite, 0);
  const occupationTotale = liste.reduce((total, element) => total + element.places_occupees, 0);

  return (
    <>
      <EntetePage
        titre="Logement étudiant"
        description="Résidences universitaires et internats : capacité, occupation et accessibilité."
        personnel={{
          titre: 'Mon logement',
          description: 'Votre hébergement et les résidences ouvertes à votre établissement.',
        }}
      />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicateur
          libelle="Résidences"
          valeur={liste.length}
          icone={<Building size={18} />}
          pictogramme="🏢"
        />
        <Indicateur libelle="Capacité totale" valeur={capaciteTotale} pictogramme="🛏️" />
        <Indicateur libelle="Places occupées" valeur={occupationTotale} pictogramme="👥" />
        <Indicateur
          libelle="Taux d'occupation"
          valeur={formaterPourcentage(
            capaciteTotale ? (occupationTotale * 100) / capaciteTotale : 0,
          )}
          pictogramme="📊"
        />
      </div>

      {liste.length === 0 ? (
        <Carte>
          <EtatVide
            titre="Aucune résidence enregistrée"
            description="Les résidences universitaires apparaîtront ici après le chargement des données."
            icone={<BedDouble size={32} aria-hidden />}
          />
        </Carte>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[20rem_1fr]">
          <Carte className="h-fit">
            <EnteteCarte titre="Résidences" />
            <ul className="divide-y">
              {liste.map((element) => (
                <li key={element.id}>
                  <button
                    type="button"
                    onClick={() => setResidenceId(element.id)}
                    aria-current={element.id === active ? 'true' : undefined}
                    className={`w-full px-4 py-3 text-left transition ${
                      element.id === active
                        ? 'bg-[rgb(var(--accent))]/10'
                        : 'hover:bg-[rgb(var(--fond-doux))]'
                    }`}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="min-w-0 truncate text-sm font-medium">{element.nom}</span>
                      {element.accessible_handicap ? (
                        <Accessibility size={15} aria-label="Accessible" className="shrink-0" />
                      ) : null}
                    </span>
                    <span className="mt-1 block">
                      <Jauge
                        valeur={element.places_occupees}
                        maximum={element.capacite || 1}
                        etiquette={`${element.places_occupees} / ${element.capacite} places`}
                        ton={element.places_occupees >= element.capacite ? 'alerte' : 'succes'}
                      />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </Carte>

          <div className="space-y-4">
            {residence ? (
              <Carte>
                <EnteteCarte
                  titre={residence.nom}
                  description={residence.adresse ?? undefined}
                  action={
                    <span className="flex gap-1.5">
                      {residence.mixte ? <Badge ton="neutre">Mixte</Badge> : null}
                      {residence.accessible_handicap ? (
                        <Badge ton="succes">Accessible</Badge>
                      ) : null}
                    </span>
                  }
                />
                <CorpsCarte>
                  <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
                    <div>
                      <dt className="texte-doux">Capacité</dt>
                      <dd className="font-semibold">{formaterNombre(residence.capacite)} places</dd>
                    </div>
                    <div>
                      <dt className="texte-doux">Occupées</dt>
                      <dd className="font-semibold">{formaterNombre(residence.places_occupees)}</dd>
                    </div>
                    <div>
                      <dt className="texte-doux">Tarif mensuel</dt>
                      <dd className="font-semibold">{formaterMontant(residence.tarif_mensuel)}</dd>
                    </div>
                  </dl>
                </CorpsCarte>
              </Carte>
            ) : null}

            <Carte>
              <EnteteCarte
                titre="Chambres"
                description={`${chambres.data?.length ?? 0} chambre(s) affichée(s).`}
                action={
                  <label className="inline-flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={disponiblesSeulement}
                      onChange={(evenement) => setDisponiblesSeulement(evenement.target.checked)}
                      className="h-4 w-4 rounded border"
                    />
                    Disponibles seulement
                  </label>
                }
              />
              <Tableau
                legende="Chambres de la résidence"
                lignes={chambres.data ?? []}
                cleLigne={(chambre) => chambre.id}
                vide={<EtatVide titre="Aucune chambre" />}
                colonnes={[
                  {
                    cle: 'numero',
                    entete: 'Chambre',
                    rendu: (chambre) => (
                      <span className="flex items-center gap-2 font-medium">
                        {chambre.numero}
                        {chambre.accessible_handicap ? <Badge ton="info">Accessible</Badge> : null}
                      </span>
                    ),
                  },
                  {
                    cle: 'batiment',
                    entete: 'Bâtiment',
                    secondaire: true,
                    rendu: (chambre) => `${chambre.batiment ?? '—'} · étage ${chambre.etage}`,
                  },
                  {
                    cle: 'lits',
                    entete: 'Occupation',
                    largeur: '13rem',
                    rendu: (chambre) => (
                      <Jauge
                        valeur={chambre.lits_occupes}
                        maximum={chambre.nombre_lits || 1}
                        etiquette={`${chambre.lits_occupes} / ${chambre.nombre_lits} lits`}
                        ton={chambre.lits_occupes >= chambre.nombre_lits ? 'alerte' : 'succes'}
                      />
                    ),
                  },
                  {
                    cle: 'tarif',
                    entete: 'Tarif',
                    alignement: 'droite',
                    secondaire: true,
                    rendu: (chambre) => formaterMontant(chambre.tarif_mensuel),
                  },
                  {
                    cle: 'attribution',
                    entete: 'Attribuer',
                    alignement: 'droite',
                    rendu: (chambre) =>
                      chambre.lits_occupes >= chambre.nombre_lits ? (
                        <span className="texte-doux">Complète</span>
                      ) : (
                        <Bouton
                          taille="sm"
                          variante="secondaire"
                          disabled={!peut('logement', 'ASSIGN')}
                          onClick={() => {
                            setChambre(chambre);
                            setJournal(null);
                          }}
                        >
                          Attribuer un lit
                        </Bouton>
                      ),
                  },
                  {
                    cle: 'disponible',
                    entete: 'Statut',
                    rendu: (chambre) => (
                      <Badge ton={chambre.disponible ? 'succes' : 'neutre'}>
                        {chambre.disponible ? 'Places libres' : 'Complète'}
                      </Badge>
                    ),
                  },
                ]}
              />
            </Carte>
          </div>
        </div>
      )}

      {journal ? (
        <p role="status" className="surface mt-4 rounded-lg border px-4 py-3 text-sm">
          {journal}
        </p>
      ) : null}

      {chambre ? (
        <Carte className="mt-4">
          <EnteteCarte
            titre={`Attribuer un lit — chambre ${chambre.numero}`}
            description={`${chambre.nombre_lits - chambre.lits_occupes} lit(s) libre(s), ${formaterMontant(chambre.tarif_mensuel)} par mois.`}
            action={
              <Bouton variante="fantome" taille="sm" onClick={() => setChambre(null)}>
                Fermer
              </Bouton>
            }
          />
          <CorpsCarte>
            <div className="grid gap-3 sm:grid-cols-3">
              <SelecteurApprenant
                etiquette="Apprenant logé"
                choisi={apprenant}
                onChoisir={setApprenant}
              />
              <Champ
                etiquette="Début du séjour"
                type="date"
                value={debut}
                onChange={(evenement) => setDebut(evenement.target.value)}
              />
              <Champ
                etiquette="Fin du séjour"
                aide="Laisser vide pour une attribution sans terme fixé."
                type="date"
                value={fin}
                onChange={(evenement) => setFin(evenement.target.value)}
              />
            </div>
            <Bouton
              className="mt-3"
              disabled={!apprenant || !debut}
              chargement={attribuer.isPending}
              onClick={() => attribuer.mutate()}
            >
              Enregistrer l&apos;attribution
            </Bouton>
          </CorpsCarte>
        </Carte>
      ) : null}
    </>
  );
}
