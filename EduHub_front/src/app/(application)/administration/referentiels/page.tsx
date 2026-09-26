'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Layers, Plus, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Pagination, Tableau, type ColonneTableau } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Champ,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  Interrupteur,
  MessageErreur,
} from '@/components/ui/primitives';
import { api, ErreurApi, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import { cn, formaterNombre } from '@/lib/utils';

/** Élément de référentiel : tous partagent au minimum un code et un libellé. */
interface Element extends Record<string, unknown> {
  id: string;
  code: string;
  libelle: string;
  actif?: boolean;
}

interface Referentiel {
  cle: string;
  libelle: string;
  chemin: string;
  /** Colonnes propres au référentiel, en plus du code et du libellé. */
  colonnes?: Array<{ cle: string; entete: string; rendu: (element: Element) => string }>;
}

function texte(valeur: unknown): string {
  if (valeur === null || valeur === undefined || valeur === '') return '—';
  if (typeof valeur === 'boolean') return valeur ? 'Oui' : 'Non';
  if (typeof valeur === 'number') return formaterNombre(valeur);
  return String(valeur);
}

/**
 * Référentiels exposés.
 *
 * Le découpage suit celui de l'API : les nomenclatures simples partagent le
 * même contrat code / libellé / ordre, les autres portent quelques attributs
 * propres que l'on affiche en colonnes supplémentaires.
 */
const GROUPES: Array<{ titre: string; referentiels: Referentiel[] }> = [
  {
    titre: 'Territoire',
    referentiels: [
      {
        cle: 'departements',
        libelle: 'Départements',
        chemin: '/departements',
        colonnes: [
          { cle: 'chef_lieu', entete: 'Chef-lieu', rendu: (e) => texte(e.chef_lieu) },
          { cle: 'population', entete: 'Population', rendu: (e) => texte(e.population) },
        ],
      },
      {
        cle: 'communes',
        libelle: 'Communes',
        chemin: '/communes',
        colonnes: [{ cle: 'population', entete: 'Population', rendu: (e) => texte(e.population) }],
      },
    ],
  },
  {
    titre: 'Structure du système éducatif',
    referentiels: [
      {
        cle: 'ordres-enseignement',
        libelle: "Ordres d'enseignement",
        chemin: '/ordres-enseignement',
      },
      { cle: 'cycles', libelle: 'Cycles', chemin: '/cycles' },
      {
        cle: 'niveaux',
        libelle: 'Niveaux',
        chemin: '/niveaux',
        colonnes: [{ cle: 'rang', entete: 'Rang', rendu: (e) => texte(e.rang) }],
      },
      {
        cle: 'series',
        libelle: 'Séries',
        chemin: '/series',
        colonnes: [{ cle: 'technique', entete: 'Technique', rendu: (e) => texte(e.technique) }],
      },
      {
        cle: 'filieres',
        libelle: 'Filières',
        chemin: '/filieres',
        colonnes: [
          { cle: 'duree_annees', entete: 'Durée', rendu: (e) => `${texte(e.duree_annees)} an(s)` },
        ],
      },
      {
        cle: 'matieres',
        libelle: 'Matières',
        chemin: '/matieres',
        colonnes: [
          { cle: 'domaine', entete: 'Domaine', rendu: (e) => texte(e.domaine) },
          { cle: 'coefficient_defaut', entete: 'Coef.', rendu: (e) => texte(e.coefficient_defaut) },
          {
            cle: 'volume_horaire_defaut',
            entete: 'Volume',
            rendu: (e) => `${texte(e.volume_horaire_defaut)} h`,
          },
        ],
      },
    ],
  },
  {
    titre: 'Établissements',
    referentiels: [
      {
        cle: 'types-etablissement',
        libelle: "Types d'établissement",
        chemin: '/types-etablissement',
      },
      {
        cle: 'statuts-etablissement',
        libelle: "Statuts d'établissement",
        chemin: '/statuts-etablissement',
      },
      { cle: 'types-salle', libelle: 'Types de salle', chemin: '/types-salle' },
    ],
  },
  {
    titre: 'Examens et diplômes',
    referentiels: [
      {
        cle: 'types-examen',
        libelle: "Types d'examen",
        chemin: '/types-examen',
        colonnes: [
          { cle: 'est_concours', entete: 'Concours', rendu: (e) => texte(e.est_concours) },
        ],
      },
      {
        cle: 'diplomes-referentiel',
        libelle: 'Diplômes de référence',
        chemin: '/diplomes-referentiel',
        colonnes: [
          {
            cle: 'niveau_qualification',
            entete: 'Qualification',
            rendu: (e) => texte(e.niveau_qualification),
          },
        ],
      },
      {
        cle: 'types-document',
        libelle: 'Types de document',
        chemin: '/types-document',
        colonnes: [
          {
            cle: 'extensions_autorisees',
            entete: 'Extensions',
            rendu: (e) => texte(e.extensions_autorisees),
          },
          {
            cle: 'taille_max_ko',
            entete: 'Taille max.',
            rendu: (e) => `${texte(e.taille_max_ko)} Ko`,
          },
        ],
      },
    ],
  },
  {
    titre: 'Vie étudiante et inclusion',
    referentiels: [
      { cle: 'types-bourse', libelle: 'Types de bourse', chemin: '/types-bourse' },
      { cle: 'types-formation', libelle: 'Types de formation', chemin: '/types-formation' },
      { cle: 'types-handicap', libelle: 'Types de handicap', chemin: '/types-handicap' },
    ],
  },
];

const TOUS = GROUPES.flatMap((groupe) => groupe.referentiels);

interface Arrondissement {
  id: string;
  code: string;
  libelle: string;
  commune_id: string;
  actif: boolean;
}

interface Village {
  id: string;
  code: string;
  libelle: string;
  arrondissement_id: string;
  quartier_ville: boolean;
}

/**
 * Découpage d'une commune.
 *
 * Arrondissements et villages ne sont pas de simples nomenclatures : ils
 * forment un arbre que l'on parcourt de proche en proche, sans jamais charger
 * les 390 villages du pays d'un coup.
 */
function DecoupageCommune({ commune }: { commune: Element }) {
  const [arrondissementId, setArrondissementId] = useState<string | null>(null);

  const arrondissements = useQuery({
    queryKey: ['arrondissements', commune.id],
    queryFn: () => api.get<Arrondissement[]>(`/communes/${commune.id}/arrondissements`),
  });

  const villages = useQuery({
    queryKey: ['villages', arrondissementId],
    queryFn: () =>
      api.get<Page<Village>>('/villages', { arrondissement_id: arrondissementId, size: 100 }),
    enabled: Boolean(arrondissementId),
  });

  return (
    <Carte className="mt-4">
      <EnteteCarte
        titre={`Découpage de ${commune.libelle}`}
        description="Arrondissements de la commune, puis villages et quartiers de l'arrondissement choisi."
      />
      <CorpsCarte className="grid gap-4 xl:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-medium">
            Arrondissements — {(arrondissements.data ?? []).length}
          </h3>
          {arrondissements.isLoading ? (
            <Chargement libelle="Chargement des arrondissements…" />
          ) : (arrondissements.data ?? []).length === 0 ? (
            <p className="text-sm texte-doux">Aucun arrondissement déclaré.</p>
          ) : (
            <ul className="surface-douce max-h-64 overflow-y-auto rounded-lg">
              {(arrondissements.data ?? []).map((arrondissement) => (
                <li key={arrondissement.id}>
                  <button
                    type="button"
                    onClick={() =>
                      setArrondissementId(
                        arrondissement.id === arrondissementId ? null : arrondissement.id,
                      )
                    }
                    aria-current={arrondissement.id === arrondissementId ? 'true' : undefined}
                    className={cn(
                      'flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-[rgb(var(--fond-doux))]',
                      arrondissement.id === arrondissementId &&
                        'bg-[rgb(var(--accent))]/12 font-medium text-[rgb(var(--accent))]',
                    )}
                  >
                    <span className="truncate">{arrondissement.libelle}</span>
                    <span className="shrink-0 font-mono text-xs texte-doux">
                      {arrondissement.code}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h3 className="mb-2 text-sm font-medium">
            Villages et quartiers{villages.data ? ` — ${villages.data.total}` : ''}
          </h3>
          {!arrondissementId ? (
            <p className="text-sm texte-doux">
              Choisissez un arrondissement pour voir son découpage.
            </p>
          ) : villages.isLoading ? (
            <Chargement libelle="Chargement des villages…" />
          ) : (villages.data?.items ?? []).length === 0 ? (
            <p className="text-sm texte-doux">Aucun village déclaré pour cet arrondissement.</p>
          ) : (
            <ul className="surface-douce max-h-64 space-y-0.5 overflow-y-auto rounded-lg p-2">
              {(villages.data?.items ?? []).map((village) => (
                <li
                  key={village.id}
                  className="flex items-center justify-between gap-2 px-1 text-sm"
                >
                  <span className="truncate">{village.libelle}</span>
                  {village.quartier_ville ? <Badge ton="info">Quartier</Badge> : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </CorpsCarte>
    </Carte>
  );
}

export default function PageReferentiels() {
  const fileAttente = useQueryClient();
  const { peut } = useSession();

  const [cle, setCle] = useState(TOUS[0].cle);
  const [page, setPage] = useState(1);
  const [recherche, setRecherche] = useState('');
  const [nouveau, setNouveau] = useState({ code: '', libelle: '', description: '', actif: true });
  const [aConfirmer, setAConfirmer] = useState<string | null>(null);
  const [commune, setCommune] = useState<Element | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const referentiel = useMemo(() => TOUS.find((element) => element.cle === cle) ?? TOUS[0], [cle]);

  const taille = 25;
  const liste = useQuery({
    queryKey: ['referentiel', referentiel.chemin, page, recherche],
    queryFn: () =>
      api.get<Page<Element>>(referentiel.chemin, {
        page,
        size: taille,
        q: recherche || undefined,
      }),
  });

  useEffect(() => {
    setPage(1);
    setMessage(null);
    setErreur(null);
    setAConfirmer(null);
    setCommune(null);
  }, [cle, recherche]);

  // La confirmation retombe d'elle-même : un bouton resté armé finirait par
  // être cliqué par inadvertance.
  useEffect(() => {
    if (!aConfirmer) return;
    const minuteur = setTimeout(() => setAConfirmer(null), 5000);
    return () => clearTimeout(minuteur);
  }, [aConfirmer]);

  function signaler(erreurBrute: unknown, defaut: string) {
    setMessage(null);
    setErreur(erreurBrute instanceof ErreurApi ? erreurBrute.message : defaut);
  }

  function rafraichir() {
    void fileAttente.invalidateQueries({ queryKey: ['referentiel', referentiel.chemin] });
  }

  const creer = useMutation({
    mutationFn: () =>
      api.post<Element>(referentiel.chemin, {
        code: nouveau.code.trim().toUpperCase(),
        libelle: nouveau.libelle.trim(),
        description: nouveau.description.trim() || null,
        actif: nouveau.actif,
      }),
    onSuccess: (element) => {
      setErreur(null);
      setMessage(`« ${element.libelle} » ajouté au référentiel.`);
      setNouveau({ code: '', libelle: '', description: '', actif: true });
      rafraichir();
    },
    onError: (e) => signaler(e, "L'élément n'a pas pu être créé."),
  });

  const basculer = useMutation({
    mutationFn: (element: Element) =>
      api.patch<Element>(`${referentiel.chemin}/${element.id}`, { actif: !element.actif }),
    onSuccess: (element) => {
      setErreur(null);
      setMessage(`« ${element.libelle} » ${element.actif ? 'réactivé' : 'désactivé'}.`);
      rafraichir();
    },
    onError: (e) => signaler(e, "L'état n'a pas pu être modifié."),
  });

  const supprimer = useMutation({
    mutationFn: (element: Element) => api.delete(`${referentiel.chemin}/${element.id}`),
    onSuccess: () => {
      setErreur(null);
      setMessage('Élément retiré du référentiel.');
      setAConfirmer(null);
      rafraichir();
    },
    onError: (e) => {
      setAConfirmer(null);
      signaler(e, "L'élément n'a pas pu être retiré.");
    },
  });

  const elements = liste.data?.items ?? [];
  const peutEcrire = peut('referentiels', 'CREATE');
  // Une nomenclature simple n'a ni contrainte ni dépendance : seul ce cas
  // autorise la création depuis cet écran, les autres ayant des champs propres.
  const creationPossible = peutEcrire && !referentiel.colonnes;

  const colonnes: Array<ColonneTableau<Element>> = [
    {
      cle: 'code',
      entete: 'Code',
      largeur: '10rem',
      rendu: (element) => <span className="font-mono text-xs">{element.code}</span>,
    },
    {
      cle: 'libelle',
      entete: 'Libellé',
      rendu: (element) => (
        <span className="min-w-0">
          <span className="block font-medium">{element.libelle}</span>
          {element.description ? (
            <span className="block truncate text-xs texte-doux">{String(element.description)}</span>
          ) : null}
        </span>
      ),
    },
    ...(referentiel.colonnes ?? []).map((colonne) => ({
      cle: colonne.cle,
      entete: colonne.entete,
      alignement: 'droite' as const,
      secondaire: true,
      rendu: (element: Element) => colonne.rendu(element),
    })),
    {
      cle: 'actif',
      entete: 'État',
      rendu: (element) =>
        element.actif === undefined ? (
          <span className="texte-doux">—</span>
        ) : (
          <Badge ton={element.actif ? 'succes' : 'neutre'}>
            {element.actif ? 'Actif' : 'Inactif'}
          </Badge>
        ),
    },
    {
      cle: 'actions',
      entete: 'Actions',
      alignement: 'droite',
      largeur: '15rem',
      rendu: (element) => (
        <span className="flex items-center justify-end gap-2">
          {element.actif !== undefined ? (
            <Bouton
              taille="sm"
              variante="secondaire"
              disabled={!peut('referentiels', 'UPDATE') || basculer.isPending}
              onClick={() => basculer.mutate(element)}
            >
              {element.actif ? 'Désactiver' : 'Réactiver'}
            </Bouton>
          ) : null}
          <Bouton
            taille="sm"
            variante={aConfirmer === element.id ? 'danger' : 'fantome'}
            aria-label={
              aConfirmer === element.id
                ? `Confirmer le retrait de ${element.libelle}`
                : `Retirer ${element.libelle}`
            }
            disabled={!peut('referentiels', 'DELETE') || supprimer.isPending}
            onClick={() =>
              aConfirmer === element.id ? supprimer.mutate(element) : setAConfirmer(element.id)
            }
            icone={<Trash2 size={15} aria-hidden />}
          >
            {aConfirmer === element.id ? 'Confirmer' : 'Retirer'}
          </Bouton>
        </span>
      ),
    },
  ];

  return (
    <>
      <EntetePage
        fil={[{ libelle: 'Administration' }, { libelle: 'Référentiels' }]}
        titre="Référentiels"
        description="Nomenclatures partagées par tout le système : territoire, structure du système éducatif, établissements, examens et vie étudiante."
      />

      {message ? (
        <p
          role="status"
          className="mb-4 rounded-lg border border-[rgb(var(--succes))]/40 bg-[rgb(var(--succes))]/10 px-4 py-3 text-sm"
        >
          {message}
        </p>
      ) : null}
      {erreur ? (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-[rgb(var(--danger))]/40 bg-[rgb(var(--danger))]/10 px-4 py-3 text-sm"
        >
          {erreur}
        </p>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,15rem)_minmax(0,1fr)]">
        <Carte className="h-fit">
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <Layers size={19} aria-hidden /> Référentiels
              </span>
            }
          />
          <nav aria-label="Choix du référentiel" className="pb-2">
            {GROUPES.map((groupe) => (
              <div key={groupe.titre} className="mb-1">
                <h3 className="px-5 pb-1 pt-3 text-xs font-semibold uppercase tracking-wide texte-doux">
                  {groupe.titre}
                </h3>
                <ul>
                  {groupe.referentiels.map((element) => (
                    <li key={element.cle}>
                      <button
                        type="button"
                        onClick={() => setCle(element.cle)}
                        aria-current={cle === element.cle ? 'true' : undefined}
                        className={cn(
                          'w-full px-5 py-1.5 text-left text-sm hover:bg-[rgb(var(--fond-doux))]',
                          cle === element.cle &&
                            'bg-[rgb(var(--accent))]/12 font-medium text-[rgb(var(--accent))]',
                        )}
                      >
                        {element.libelle}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </Carte>

        <div>
          <Carte>
            <EnteteCarte
              titre={referentiel.libelle}
              description={
                liste.data
                  ? `${formaterNombre(liste.data.total)} élément(s) dans ce référentiel.`
                  : undefined
              }
              action={
                <Champ
                  etiquette={`Rechercher dans ${referentiel.libelle}`}
                  etiquetteMasquee
                  type="search"
                  placeholder="Rechercher…"
                  value={recherche}
                  onChange={(evenement) => setRecherche(evenement.target.value)}
                />
              }
            />
            {liste.isLoading ? (
              <CorpsCarte>
                <Chargement libelle="Chargement du référentiel…" />
              </CorpsCarte>
            ) : liste.isError ? (
              <CorpsCarte>
                <MessageErreur erreur={liste.error} />
              </CorpsCarte>
            ) : (
              <>
                <Tableau
                  legende={`Éléments du référentiel « ${referentiel.libelle} »`}
                  lignes={elements}
                  cleLigne={(element) => element.id}
                  onLigneClic={
                    cle === 'communes'
                      ? (element) => setCommune(element.id === commune?.id ? null : element)
                      : undefined
                  }
                  vide={<EtatVide titre="Aucun élément" />}
                  colonnes={colonnes}
                />
                <div className="px-5 pb-4">
                  <Pagination
                    page={page}
                    pages={liste.data?.pages ?? 0}
                    total={liste.data?.total ?? 0}
                    taille={taille}
                    onChange={setPage}
                  />
                </div>
              </>
            )}
          </Carte>

          {creationPossible ? (
            <Carte className="mt-4">
              <EnteteCarte
                titre={
                  <span className="flex items-center gap-2">
                    <Plus size={19} aria-hidden /> Ajouter à « {referentiel.libelle} »
                  </span>
                }
                description="Le code identifie l'élément dans tout le système : il est mis en majuscules et ne devrait plus changer."
              />
              <CorpsCarte>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  <Champ
                    etiquette="Code"
                    required
                    value={nouveau.code}
                    onChange={(evenement) =>
                      setNouveau((precedent) => ({ ...precedent, code: evenement.target.value }))
                    }
                  />
                  <Champ
                    etiquette="Libellé"
                    required
                    value={nouveau.libelle}
                    onChange={(evenement) =>
                      setNouveau((precedent) => ({ ...precedent, libelle: evenement.target.value }))
                    }
                  />
                  <Champ
                    etiquette="Description"
                    value={nouveau.description}
                    onChange={(evenement) =>
                      setNouveau((precedent) => ({
                        ...precedent,
                        description: evenement.target.value,
                      }))
                    }
                  />
                </div>
                <div className="mt-3 max-w-sm">
                  <Interrupteur
                    etiquette="Actif dès la création"
                    actif={nouveau.actif}
                    onChange={() =>
                      setNouveau((precedent) => ({ ...precedent, actif: !precedent.actif }))
                    }
                  />
                </div>
                <Bouton
                  className="mt-3"
                  disabled={!nouveau.code.trim() || !nouveau.libelle.trim()}
                  chargement={creer.isPending}
                  onClick={() => creer.mutate()}
                >
                  Ajouter
                </Bouton>
              </CorpsCarte>
            </Carte>
          ) : null}

          {cle === 'communes' && commune ? <DecoupageCommune commune={commune} /> : null}

          {creationPossible ? null : peutEcrire ? (
            <p className="mt-3 text-sm texte-doux">
              « {referentiel.libelle} » porte des attributs propres : la création se fait par import
              ou par l&apos;API, cet écran en assure la consultation et l&apos;activation.
            </p>
          ) : null}
        </div>
      </div>
    </>
  );
}
