'use client';

import { useQuery } from '@tanstack/react-query';
import { Accessibility, DoorOpen, Download, MapPin, Users } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur, Jauge, ListeDescriptive, Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
  Selection,
} from '@/components/ui/primitives';
import { api, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterDate, formaterNombre, humaniser } from '@/lib/utils';

interface Centre {
  id: string;
  session_id: string;
  code: string;
  nom: string;
  adresse: string | null;
  latitude: number | null;
  longitude: number | null;
  capacite: number;
  nombre_candidats: number;
  nombre_salles: number;
  chef_centre_nom: string | null;
  chef_centre_telephone: string | null;
  accessible_handicap: boolean;
  actif: boolean;
}

interface SalleComposition {
  id: string;
  code: string;
  nom: string;
  batiment: string | null;
  capacite: number;
  nombre_candidats: number;
  place_debut: number | null;
  place_fin: number | null;
  accessible_handicap: boolean;
  salle_amenagee: boolean;
}

interface CandidatAffecte {
  id: string;
  numero_candidat: string;
  numero_table: string | null;
  nom_complet: string;
  sexe: string;
  date_naissance: string;
  numero_place: number | null;
  salle_composition_id: string | null;
  tiers_temps: boolean;
  type_handicap: string;
}

export default function PageCentre() {
  const parametres = useParams<{ id: string }>();
  const router = useRouter();
  const { peut } = useSession();
  const [salleId, setSalleId] = useState('');

  const centre = useQuery({
    queryKey: ['centre', parametres.id],
    queryFn: () => api.get<Centre>(`/centres/${parametres.id}`),
  });

  const salles = useQuery({
    queryKey: ['salles-centre', parametres.id],
    queryFn: () => api.get<SalleComposition[]>(`/centres/${parametres.id}/salles`),
  });

  // Un centre compte au plus quelques centaines de candidats : une seule page
  // suffit, et le filtrage par salle se fait alors sans nouvel aller-retour.
  const candidats = useQuery({
    queryKey: ['candidats-centre', parametres.id],
    queryFn: () =>
      api.get<Page<CandidatAffecte>>('/candidats', {
        centre_id: parametres.id,
        size: 200,
        sort_by: 'numero_place',
      }),
  });

  if (centre.isLoading) return <Chargement libelle="Ouverture du centre de composition…" />;
  if (centre.isError) return <MessageErreur erreur={centre.error} />;

  const donnees = centre.data!;
  const listeSalles = salles.data ?? [];
  const parSalle = new Map(listeSalles.map((salle) => [salle.id, salle]));
  // Les numéros de place repartent de 1 dans chaque salle : on trie donc par
  // salle puis par place, comme le fait l'export CSV d'émargement.
  const affectes = (candidats.data?.items ?? [])
    .filter((candidat) => !salleId || candidat.salle_composition_id === salleId)
    .sort((a, b) => {
      const salleA = parSalle.get(a.salle_composition_id ?? '')?.code ?? '';
      const salleB = parSalle.get(b.salle_composition_id ?? '')?.code ?? '';
      if (salleA !== salleB) return salleA.localeCompare(salleB);
      return (a.numero_place ?? 0) - (b.numero_place ?? 0);
    });
  const amenagements = affectes.filter((candidat) => candidat.tiers_temps).length;

  return (
    <>
      <EntetePage
        fil={[
          { libelle: 'Centres de composition', href: '/centres' },
          { libelle: donnees.nom },
        ]}
        titre={donnees.nom}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs">{donnees.code}</span>
            {donnees.accessible_handicap ? (
              <Badge ton="succes">
                <Accessibility size={13} aria-hidden /> Accessible
              </Badge>
            ) : (
              <Badge ton="neutre">Non accessible</Badge>
            )}
            <Badge ton={donnees.actif ? 'info' : 'neutre'}>
              {donnees.actif ? 'Centre actif' : 'Centre fermé'}
            </Badge>
          </span>
        }
        actions={
          peut('candidats', 'EXPORT') ? (
            <Bouton
              variante="secondaire"
              icone={<Download size={17} aria-hidden />}
              onClick={() =>
                api.telecharger(
                  `/centres/${parametres.id}/liste-emargement`,
                  `liste-emargement-${donnees.code}.csv`,
                  salleId ? { salle_id: salleId } : undefined,
                )
              }
            >
              Liste d&apos;émargement
            </Bouton>
          ) : null
        }
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Indicateur
          libelle="Candidats affectés"
          valeur={donnees.nombre_candidats}
          icone={<Users size={19} aria-hidden />}
          pictogramme="👥"
        />
        <Indicateur
          libelle="Capacité totale"
          valeur={donnees.capacite}
          icone={<DoorOpen size={19} aria-hidden />}
          pictogramme="🚪"
        />
        <Indicateur libelle="Salles ouvertes" valeur={donnees.nombre_salles} pictogramme="🏫" />
        <Indicateur
          libelle="Aménagements d'épreuve"
          valeur={amenagements}
          unite="tiers temps"
          icone={<Accessibility size={19} aria-hidden />}
          pictogramme="♿"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <MapPin size={19} aria-hidden /> Identité du centre
              </span>
            }
          />
          <CorpsCarte className="space-y-4">
            <ListeDescriptive
              colonnes={1}
              entrees={[
                { terme: 'Code', valeur: <span className="font-mono text-sm">{donnees.code}</span> },
                { terme: 'Adresse', valeur: donnees.adresse ?? '—' },
                { terme: 'Chef de centre', valeur: donnees.chef_centre_nom ?? 'Non désigné' },
                { terme: 'Téléphone', valeur: donnees.chef_centre_telephone ?? '—' },
                {
                  terme: 'Coordonnées',
                  valeur:
                    donnees.latitude != null && donnees.longitude != null
                      ? `${donnees.latitude.toFixed(4)} ; ${donnees.longitude.toFixed(4)}`
                      : '—',
                },
              ]}
            />
            <Jauge
              valeur={donnees.nombre_candidats}
              maximum={donnees.capacite || 1}
              etiquette="Taux d'occupation du centre"
              ton={donnees.nombre_candidats > donnees.capacite ? 'danger' : 'succes'}
            />
          </CorpsCarte>
        </Carte>

        <Carte className="xl:col-span-2">
          <EnteteCarte
            titre="Salles de composition"
            description="Plage de places attribuée à chaque salle lors de la répartition."
          />
          {salles.isLoading ? (
            <CorpsCarte>
              <Chargement libelle="Chargement des salles…" />
            </CorpsCarte>
          ) : (
            <Tableau
              legende="Salles de composition du centre"
              lignes={listeSalles}
              cleLigne={(salle) => salle.id}
              onLigneClic={(salle) => setSalleId(salle.id === salleId ? '' : salle.id)}
              vide={<EtatVide titre="Aucune salle déclarée" />}
              colonnes={[
                {
                  cle: 'nom',
                  entete: 'Salle',
                  rendu: (salle) => (
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{salle.nom}</span>
                      <span className="block text-xs texte-doux">
                        {salle.batiment ?? salle.code}
                      </span>
                    </span>
                  ),
                },
                {
                  cle: 'places',
                  entete: 'Places',
                  secondaire: true,
                  rendu: (salle) =>
                    salle.place_debut != null && salle.place_fin != null
                      ? `${salle.place_debut} – ${salle.place_fin}`
                      : '—',
                },
                {
                  cle: 'occupation',
                  entete: 'Candidats',
                  alignement: 'droite',
                  rendu: (salle) =>
                    `${formaterNombre(salle.nombre_candidats)} / ${formaterNombre(salle.capacite)}`,
                },
                {
                  cle: 'amenagement',
                  entete: 'Aménagement',
                  rendu: (salle) => (
                    <span className="flex flex-wrap gap-1.5">
                      {salle.salle_amenagee ? <Badge ton="info">Salle aménagée</Badge> : null}
                      {salle.accessible_handicap ? (
                        <Badge ton="succes">
                          <Accessibility size={13} aria-hidden /> Accessible
                        </Badge>
                      ) : null}
                      {!salle.salle_amenagee && !salle.accessible_handicap ? (
                        <span className="texte-doux">—</span>
                      ) : null}
                    </span>
                  ),
                },
              ]}
            />
          )}
        </Carte>
      </div>

      <Carte className="mt-4">
        <EnteteCarte
          titre="Liste d'émargement"
          description={
            salleId
              ? `Candidats de la salle « ${parSalle.get(salleId)?.nom ?? salleId} », par numéro de place.`
              : 'Tous les candidats du centre, par numéro de place. Cliquez sur une salle pour filtrer.'
          }
          action={
            <Selection
              etiquette="Salle"
              etiquetteMasquee
              value={salleId}
              onChange={(evenement) => setSalleId(evenement.target.value)}
              options={[
                { valeur: '', libelle: 'Toutes les salles' },
                ...listeSalles.map((salle) => ({ valeur: salle.id, libelle: salle.nom })),
              ]}
            />
          }
        />
        {candidats.isLoading ? (
          <CorpsCarte>
            <Chargement libelle="Chargement des candidats affectés…" />
          </CorpsCarte>
        ) : (
          <Tableau
            legende="Candidats affectés au centre de composition"
            lignes={affectes}
            cleLigne={(candidat) => candidat.id}
            onLigneClic={(candidat) => router.push(`/candidats/${candidat.id}`)}
            vide={
              <EtatVide
                titre="Aucun candidat affecté"
                description="La répartition des candidats n'a pas encore été lancée pour cette session."
              />
            }
            colonnes={[
              {
                cle: 'place',
                entete: 'Place',
                alignement: 'droite',
                largeur: '7%',
                rendu: (candidat) => candidat.numero_place ?? '—',
              },
              {
                cle: 'candidat',
                entete: 'Candidat',
                rendu: (candidat) => (
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{candidat.nom_complet}</span>
                    <span className="block font-mono text-xs texte-doux">
                      {candidat.numero_candidat}
                    </span>
                  </span>
                ),
              },
              {
                cle: 'table',
                entete: 'Numéro de table',
                secondaire: true,
                rendu: (candidat) => (
                  <span className="font-mono text-xs">{candidat.numero_table ?? '—'}</span>
                ),
              },
              {
                cle: 'salle',
                entete: 'Salle',
                secondaire: true,
                rendu: (candidat) =>
                  candidat.salle_composition_id
                    ? (parSalle.get(candidat.salle_composition_id)?.nom ?? '—')
                    : '—',
              },
              {
                cle: 'naissance',
                entete: 'Né(e) le',
                secondaire: true,
                rendu: (candidat) => formaterDate(candidat.date_naissance),
              },
              {
                cle: 'amenagement',
                entete: 'Aménagement',
                rendu: (candidat) =>
                  candidat.tiers_temps ? (
                    <Badge ton="info">
                      <Accessibility size={13} aria-hidden />{' '}
                      {candidat.type_handicap === 'AUCUN'
                        ? 'Tiers temps'
                        : humaniser(candidat.type_handicap)}
                    </Badge>
                  ) : (
                    <span className="texte-doux">—</span>
                  ),
              },
            ]}
          />
        )}
      </Carte>
    </>
  );
}
