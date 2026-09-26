'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  BellRing,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Landmark,
  MapPin,
  Play,
  Scale,
} from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur, Tableau } from '@/components/ui/donnees';
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
  tonDuStatut,
} from '@/components/ui/primitives';
import { api, ErreurApi, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import { cn, formaterNombre, humaniser } from '@/lib/utils';

interface Structure {
  id: string;
  code: string;
  libelle: string;
  sigle: string | null;
  categorie: string;
  niveau_scope: string;
  responsable_nom: string | null;
  telephone: string | null;
  email: string | null;
  adresse: string | null;
  missions: string | null;
  actif: boolean;
  enfants: Structure[];
}

interface RegleMetier {
  id: string;
  code: string;
  libelle: string;
  description: string | null;
  domaine: string;
  entite_cible: string;
  conditions: Record<string, unknown>;
  consequences: Record<string, unknown>;
  priorite: number;
  active: boolean;
  nombre_declenchements: number;
}

interface Declenchement {
  regle: string;
  libelle: string;
  domaine?: string;
  applicable: boolean;
  condition?: string;
  occurrences?: number;
  message?: string;
  consequences?: Record<string, unknown>;
}

interface Alerte {
  id: string;
  code: string;
  titre: string;
  message: string;
  niveau: string;
  domaine: string;
  valeur_mesuree: number | null;
  seuil: number | null;
  traitee: boolean;
}

/** Pictogramme associé à chaque échelon de l'organigramme. */
const ICONES_CATEGORIE: Record<string, typeof Landmark> = {
  MINISTERE: Landmark,
  DIRECTION_DEPARTEMENTALE: MapPin,
};

function NoeudStructure({
  structure,
  profondeur,
  ouverts,
  basculer,
}: {
  structure: Structure;
  profondeur: number;
  ouverts: Record<string, boolean>;
  basculer: (id: string, ouvert: boolean) => void;
}) {
  const aDesEnfants = structure.enfants.length > 0;
  // Les deux premiers échelons sont dépliés d'emblée : l'organigramme se lit
  // d'un coup d'œil sans cliquer.
  const ouvert = ouverts[structure.id] ?? profondeur < 1;
  const Icone = ICONES_CATEGORIE[structure.categorie] ?? Building2;

  return (
    <li>
      <div
        className={cn(
          'flex flex-wrap items-center gap-2 rounded-lg px-2 py-2',
          profondeur === 0 && 'font-medium',
        )}
        style={{ marginLeft: `${profondeur * 1.25}rem` }}
      >
        {aDesEnfants ? (
          <button
            type="button"
            onClick={() => basculer(structure.id, ouvert)}
            aria-expanded={ouvert}
            aria-label={`${ouvert ? 'Replier' : 'Déplier'} ${structure.libelle}`}
            className="rounded p-0.5 hover:bg-[rgb(var(--fond-doux))]"
          >
            {ouvert ? (
              <ChevronDown size={16} aria-hidden />
            ) : (
              <ChevronRight size={16} aria-hidden />
            )}
          </button>
        ) : (
          <span className="w-[22px]" aria-hidden />
        )}
        <Icone size={17} aria-hidden className="texte-doux" />
        <span className="min-w-0">
          <span className="block truncate">{structure.libelle}</span>
          <span className="block text-xs texte-doux">
            {structure.sigle ?? structure.code}
            {structure.responsable_nom ? ` · ${structure.responsable_nom}` : ''}
          </span>
        </span>
        <Badge ton="neutre">{humaniser(structure.categorie)}</Badge>
        {!structure.actif ? <Badge ton="danger">Inactive</Badge> : null}
      </div>

      {aDesEnfants && ouvert ? (
        <ul className="border-l" style={{ marginLeft: `${profondeur * 1.25 + 0.9}rem` }}>
          {structure.enfants.map((enfant) => (
            <NoeudStructure
              key={enfant.id}
              structure={enfant}
              profondeur={profondeur + 1}
              ouverts={ouverts}
              basculer={basculer}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export default function PageGouvernance() {
  const fileAttente = useQueryClient();
  const { peut } = useSession();

  const [ouverts, setOuverts] = useState<Record<string, boolean>>({});
  const [domaine, setDomaine] = useState('');
  const [simulation, setSimulation] = useState<Declenchement[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const arbre = useQuery({
    queryKey: ['arbre-institutionnel'],
    queryFn: () => api.get<Structure[]>('/structures/arbre/complet'),
  });

  const regles = useQuery({
    queryKey: ['regles-metier', domaine],
    queryFn: () =>
      api.get<Page<RegleMetier>>('/regles-metier', {
        size: 100,
        domaine: domaine || undefined,
        sort_by: 'priorite',
      }),
  });

  const alertes = useQuery({
    queryKey: ['alertes'],
    queryFn: () => api.get<Page<Alerte>>('/alertes', { size: 50 }),
  });

  const simuler = useMutation({
    mutationFn: () =>
      api.get<Declenchement[]>('/moteur-regles/simuler', {
        domaine: domaine || undefined,
      }),
    onSuccess: (resultat) => {
      setErreur(null);
      setSimulation(resultat);
    },
    onError: (erreurBrute: unknown) => {
      setSimulation(null);
      setErreur(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "La simulation n'a pas pu être exécutée.",
      );
    },
  });

  const traiter = useMutation({
    mutationFn: (id: string) => api.post<Alerte>(`/alertes/${id}/traiter`),
    onSuccess: () => {
      void fileAttente.invalidateQueries({ queryKey: ['alertes'] });
    },
  });

  function basculer(id: string, ouvert: boolean) {
    setOuverts((precedent) => ({ ...precedent, [id]: !ouvert }));
  }

  const listeRegles = regles.data?.items ?? [];
  const listeAlertes = alertes.data?.items ?? [];
  const domaines = [...new Set(listeRegles.map((regle) => regle.domaine))].sort();
  const aTraiter = listeAlertes.filter((alerte) => !alerte.traitee).length;

  function compter(noeuds: Structure[]): number {
    return noeuds.reduce((somme, noeud) => somme + 1 + compter(noeud.enfants), 0);
  }

  return (
    <>
      <EntetePage
        titre="Gouvernance"
        description="Organisation institutionnelle, règles métier appliquées aux données et alertes qu'elles produisent."
      />

      {erreur ? (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-[rgb(var(--danger))]/40 bg-[rgb(var(--danger))]/10 px-4 py-3 text-sm"
        >
          {erreur}
        </p>
      ) : null}

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Indicateur
          libelle="Structures recensées"
          valeur={arbre.data ? compter(arbre.data) : '—'}
          icone={<Landmark size={19} aria-hidden />}
          pictogramme="🏛️"
        />
        <Indicateur
          libelle="Règles métier"
          valeur={regles.data?.total ?? '—'}
          unite={`${listeRegles.filter((regle) => regle.active).length} active(s)`}
          icone={<Scale size={19} aria-hidden />}
          pictogramme="⚖️"
        />
        <Indicateur
          libelle="Alertes ouvertes"
          valeur={aTraiter}
          icone={<BellRing size={19} aria-hidden />}
          pictogramme="🔔"
        />
        <Indicateur
          libelle="Déclenchements cumulés"
          valeur={listeRegles.reduce((somme, regle) => somme + regle.nombre_declenchements, 0)}
          pictogramme="📊"
        />
      </div>

      <Carte className="mb-4">
        <EnteteCarte
          titre="Organigramme institutionnel"
          description="Ministère → direction nationale → direction départementale. Chaque rôle est porté par une structure et un périmètre."
        />
        <CorpsCarte>
          {arbre.isLoading ? (
            <Chargement libelle="Chargement de l'organigramme…" />
          ) : arbre.isError ? (
            <MessageErreur erreur={arbre.error} />
          ) : (
            <ul className="text-sm">
              {(arbre.data ?? []).map((structure) => (
                <NoeudStructure
                  key={structure.id}
                  structure={structure}
                  profondeur={0}
                  ouverts={ouverts}
                  basculer={basculer}
                />
              ))}
            </ul>
          )}
        </CorpsCarte>
      </Carte>

      <Carte className="mb-4">
        <EnteteCarte
          titre="Règles métier"
          description="Chaque règle s'exprime sur un champ déclaré d'une entité interrogeable : la simulation la confronte aux données réelles sans rien modifier."
          action={
            <div className="flex flex-wrap items-end gap-2">
              <Selection
                etiquette="Domaine"
                etiquetteMasquee
                value={domaine}
                onChange={(evenement) => {
                  setDomaine(evenement.target.value);
                  setSimulation(null);
                }}
                options={[
                  { valeur: '', libelle: 'Tous les domaines' },
                  ...domaines.map((valeur) => ({ valeur, libelle: humaniser(valeur) })),
                ]}
                className="h-11"
              />
              <Bouton
                disabled={!peut('parametres', 'READ')}
                chargement={simuler.isPending}
                icone={<Play size={17} aria-hidden />}
                onClick={() => simuler.mutate()}
              >
                Simuler
              </Bouton>
            </div>
          }
        />
        {regles.isLoading ? (
          <CorpsCarte>
            <Chargement libelle="Chargement des règles…" />
          </CorpsCarte>
        ) : (
          <Tableau
            legende="Règles métier du moteur de gouvernance"
            lignes={listeRegles}
            cleLigne={(regle) => regle.id}
            vide={<EtatVide titre="Aucune règle métier" />}
            colonnes={[
              {
                cle: 'libelle',
                entete: 'Règle',
                rendu: (regle) => (
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{regle.libelle}</span>
                    <span className="block font-mono text-xs texte-doux">{regle.code}</span>
                  </span>
                ),
              },
              {
                cle: 'condition',
                entete: 'Condition',
                rendu: (regle) => (
                  <span className="min-w-0">
                    <span className="block font-mono text-xs">
                      {String(regle.conditions.champ ?? '—')}{' '}
                      {String(regle.conditions.operateur ?? '')}{' '}
                      {String(regle.conditions.valeur ?? '')}
                    </span>
                    <span className="block text-xs texte-doux">
                      sur {humaniser(regle.entite_cible)}
                    </span>
                  </span>
                ),
              },
              {
                cle: 'domaine',
                entete: 'Domaine',
                secondaire: true,
                rendu: (regle) => humaniser(regle.domaine),
              },
              {
                cle: 'priorite',
                entete: 'Priorité',
                alignement: 'droite',
                secondaire: true,
                rendu: (regle) => regle.priorite,
              },
              {
                cle: 'declenchements',
                entete: 'Déclenchements',
                alignement: 'droite',
                rendu: (regle) => formaterNombre(regle.nombre_declenchements),
              },
              {
                cle: 'etat',
                entete: 'État',
                rendu: (regle) => (
                  <Badge ton={regle.active ? 'succes' : 'neutre'}>
                    {regle.active ? 'Active' : 'Inactive'}
                  </Badge>
                ),
              },
            ]}
          />
        )}

        {simulation ? (
          <CorpsCarte className="border-t">
            <h3 className="mb-3 font-medium">
              Résultat de la simulation — {simulation.length} règle(s) évaluée(s)
            </h3>
            <ul className="space-y-3">
              {simulation.map((declenchement) => (
                <li key={declenchement.regle} className="surface-douce rounded-lg p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{declenchement.libelle}</span>
                    <span className="font-mono text-xs texte-doux">{declenchement.regle}</span>
                    {declenchement.applicable ? (
                      <Badge ton={(declenchement.occurrences ?? 0) > 0 ? 'alerte' : 'succes'}>
                        {formaterNombre(declenchement.occurrences ?? 0)} occurrence(s)
                      </Badge>
                    ) : (
                      <Badge ton="danger">Non applicable</Badge>
                    )}
                  </div>
                  <p className="mt-1 texte-doux">
                    {declenchement.applicable
                      ? `Condition évaluée : ${declenchement.condition}.`
                      : declenchement.message}
                  </p>
                </li>
              ))}
            </ul>
          </CorpsCarte>
        ) : null}
      </Carte>

      <Carte>
        <EnteteCarte
          titre="Alertes"
          description="Situations détectées par le moteur de règles et remontées au pilotage."
          action={<Badge ton={aTraiter > 0 ? 'alerte' : 'succes'}>{aTraiter} à traiter</Badge>}
        />
        {alertes.isLoading ? (
          <CorpsCarte>
            <Chargement libelle="Chargement des alertes…" />
          </CorpsCarte>
        ) : (
          <Tableau
            legende="Alertes de gouvernance"
            lignes={listeAlertes}
            cleLigne={(alerte) => alerte.id}
            vide={<EtatVide titre="Aucune alerte" description="Aucun seuil n'est franchi." />}
            colonnes={[
              {
                cle: 'titre',
                entete: 'Alerte',
                rendu: (alerte) => (
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{alerte.titre}</span>
                    <span className="block truncate text-xs texte-doux">{alerte.message}</span>
                  </span>
                ),
              },
              {
                cle: 'niveau',
                entete: 'Niveau',
                rendu: (alerte) => (
                  <Badge ton={tonDuStatut(alerte.niveau)}>{humaniser(alerte.niveau)}</Badge>
                ),
              },
              {
                cle: 'domaine',
                entete: 'Domaine',
                secondaire: true,
                rendu: (alerte) => humaniser(alerte.domaine),
              },
              {
                cle: 'mesure',
                entete: 'Mesure / seuil',
                alignement: 'droite',
                secondaire: true,
                rendu: (alerte) =>
                  alerte.valeur_mesuree != null
                    ? `${formaterNombre(alerte.valeur_mesuree, 2)} / ${formaterNombre(alerte.seuil ?? 0, 2)}`
                    : '—',
              },
              {
                cle: 'action',
                entete: 'Traitement',
                alignement: 'droite',
                rendu: (alerte) =>
                  alerte.traitee ? (
                    <Badge ton="succes">
                      <CheckCircle2 size={13} aria-hidden /> Traitée
                    </Badge>
                  ) : (
                    <Bouton
                      taille="sm"
                      variante="secondaire"
                      disabled={!peut('analytics', 'UPDATE')}
                      chargement={traiter.isPending && traiter.variables === alerte.id}
                      onClick={() => traiter.mutate(alerte.id)}
                    >
                      Marquer traitée
                    </Bouton>
                  ),
              },
            ]}
          />
        )}
      </Carte>
    </>
  );
}
