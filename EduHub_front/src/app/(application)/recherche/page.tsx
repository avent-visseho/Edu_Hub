'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { Download, MessageSquare, Plus, Search, Sparkles, Trash2, Wand2 } from 'lucide-react';
import { useMemo, useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Pagination, Tableau } from '@/components/ui/donnees';
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
import { api } from '@/lib/api';
import { formaterNombre } from '@/lib/utils';
import type { EntiteRecherche, ReponseNaturelle, ResultatRecherche } from '@/types/api';

/** Libellés français des opérateurs exposés par l'API. */
const OPERATEURS: Record<string, string> = {
  eq: 'est égal à',
  ne: 'est différent de',
  gt: 'est supérieur à',
  gte: 'est supérieur ou égal à',
  lt: 'est inférieur à',
  lte: 'est inférieur ou égal à',
  contains: 'contient',
  startswith: 'commence par',
  endswith: 'finit par',
  in: 'fait partie de',
  not_in: 'ne fait pas partie de',
  between: 'est compris entre',
  is_null: "n'est pas renseigné",
  not_null: 'est renseigné',
};

interface CritereSaisi {
  id: string;
  champ: string;
  operateur: string;
  valeur: string;
}

export default function PageRecherche() {
  const [onglet, setOnglet] = useState<'constructeur' | 'naturel'>('constructeur');

  return (
    <>
      <EntetePage
        titre="Recherche avancée"
        description="Interrogez l'ensemble des données du système, par filtres visuels ou en posant votre question en français."
      />

      <div
        role="tablist"
        aria-label="Mode de recherche"
        className="mb-4 inline-flex rounded-lg border p-1"
      >
        {(
          [
            { cle: 'constructeur', libelle: 'Constructeur de requêtes', icone: Wand2 },
            { cle: 'naturel', libelle: 'Question en français', icone: MessageSquare },
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
              className={`inline-flex h-10 items-center gap-2 rounded px-4 text-sm font-medium transition ${
                actif
                  ? 'bg-[rgb(var(--accent))] text-[rgb(var(--accent-contraste))]'
                  : 'hover:bg-[rgb(var(--fond-doux))]'
              }`}
            >
              <Icone size={16} aria-hidden />
              {element.libelle}
            </button>
          );
        })}
      </div>

      {onglet === 'constructeur' ? <Constructeur /> : <RechercheNaturelle />}
    </>
  );
}

// ------------------------------------------------------------------
//  Constructeur visuel
// ------------------------------------------------------------------

function Constructeur() {
  const entites = useQuery({
    queryKey: ['entites-recherche'],
    queryFn: () => api.get<EntiteRecherche[]>('/recherche/entites'),
  });

  const [entiteCle, setEntiteCle] = useState('apprenants');
  const [criteres, setCriteres] = useState<CritereSaisi[]>([]);
  const [conjonction, setConjonction] = useState<'AND' | 'OR'>('AND');
  const [page, setPage] = useState(1);

  const entite = useMemo(
    () => entites.data?.find((element) => element.cle === entiteCle),
    [entites.data, entiteCle],
  );

  const recherche = useMutation({
    mutationFn: (numeroPage: number) =>
      api.post<ResultatRecherche>('/recherche/avancee', {
        entite: entiteCle,
        conjonction,
        criteres: criteres
          .filter((critere) => critere.champ && critere.operateur)
          .map((critere) => ({
            champ: critere.champ,
            operateur: critere.operateur,
            valeur: normaliserValeur(critere.valeur, critere.operateur),
          })),
        page: numeroPage,
        taille: 25,
      }),
  });

  function ajouterCritere() {
    const premier = entite?.champs[0];
    setCriteres((precedents) => [
      ...precedents,
      {
        id: crypto.randomUUID(),
        champ: premier?.cle ?? '',
        operateur: premier?.operateurs[0] ?? 'eq',
        valeur: '',
      },
    ]);
  }

  function modifierCritere(id: string, modifications: Partial<CritereSaisi>) {
    setCriteres((precedents) =>
      precedents.map((critere) => (critere.id === id ? { ...critere, ...modifications } : critere)),
    );
  }

  function executer(numeroPage = 1) {
    setPage(numeroPage);
    recherche.mutate(numeroPage);
  }

  if (entites.isLoading) return <Chargement libelle="Chargement des variables interrogeables…" />;
  if (entites.isError) return <MessageErreur erreur={entites.error} />;

  const resultat = recherche.data;

  return (
    <div className="space-y-4">
      <Carte>
        <EnteteCarte
          titre="Construire la requête"
          description="Choisissez ce que vous cherchez, puis empilez les conditions."
          action={
            <Bouton onClick={() => executer(1)} chargement={recherche.isPending}>
              <Search size={17} aria-hidden /> Exécuter
            </Bouton>
          }
        />
        <CorpsCarte className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Selection
              etiquette="Je cherche"
              value={entiteCle}
              onChange={(evenement) => {
                setEntiteCle(evenement.target.value);
                setCriteres([]);
              }}
              options={(entites.data ?? []).map((element) => ({
                valeur: element.cle,
                libelle: element.libelle,
              }))}
            />
            <Selection
              etiquette="Combinaison des conditions"
              value={conjonction}
              onChange={(evenement) => setConjonction(evenement.target.value as 'AND' | 'OR')}
              options={[
                { valeur: 'AND', libelle: 'Toutes les conditions (ET)' },
                { valeur: 'OR', libelle: "Au moins une condition (OU)" },
              ]}
            />
          </div>

          <div className="space-y-2">
            {criteres.map((critere, index) => {
              const champ = entite?.champs.find((element) => element.cle === critere.champ);
              const sansValeur = ['is_null', 'not_null'].includes(critere.operateur);
              return (
                <div
                  key={critere.id}
                  className="grid gap-2 rounded-lg border p-3 sm:grid-cols-[auto_1fr_1fr_1fr_auto] sm:items-end"
                >
                  <span className="pb-2.5 text-sm font-semibold texte-doux">
                    {index === 0 ? 'SI' : conjonction === 'AND' ? 'ET' : 'OU'}
                  </span>

                  <Selection
                    etiquette="Variable"
                    etiquetteMasquee
                    value={critere.champ}
                    onChange={(evenement) => {
                      const nouveau = entite?.champs.find(
                        (element) => element.cle === evenement.target.value,
                      );
                      modifierCritere(critere.id, {
                        champ: evenement.target.value,
                        operateur: nouveau?.operateurs[0] ?? 'eq',
                        valeur: '',
                      });
                    }}
                    options={(entite?.champs ?? []).map((element) => ({
                      valeur: element.cle,
                      libelle: element.calcule ? `${element.libelle} (calculé)` : element.libelle,
                    }))}
                  />

                  <Selection
                    etiquette="Opérateur"
                    etiquetteMasquee
                    value={critere.operateur}
                    onChange={(evenement) =>
                      modifierCritere(critere.id, { operateur: evenement.target.value })
                    }
                    options={(champ?.operateurs ?? ['eq']).map((operateur) => ({
                      valeur: operateur,
                      libelle: OPERATEURS[operateur] ?? operateur,
                    }))}
                  />

                  {sansValeur ? (
                    <span className="pb-2.5 text-sm texte-doux">—</span>
                  ) : champ?.choix && champ.choix.length > 0 ? (
                    <Selection
                      etiquette="Valeur"
                      etiquetteMasquee
                      value={critere.valeur}
                      onChange={(evenement) =>
                        modifierCritere(critere.id, { valeur: evenement.target.value })
                      }
                      options={[
                        { valeur: '', libelle: 'Choisir…' },
                        ...champ.choix.map((choix) => ({ valeur: choix, libelle: choix })),
                      ]}
                    />
                  ) : (
                    <Champ
                      etiquette="Valeur"
                      etiquetteMasquee
                      type={champ?.type === 'nombre' ? 'number' : champ?.type === 'date' ? 'date' : 'text'}
                      value={critere.valeur}
                      onChange={(evenement) =>
                        modifierCritere(critere.id, { valeur: evenement.target.value })
                      }
                      placeholder={
                        critere.operateur === 'between' ? 'Deux valeurs séparées par une virgule' : 'Valeur'
                      }
                    />
                  )}

                  <Bouton
                    variante="fantome"
                    taille="sm"
                    aria-label="Retirer cette condition"
                    onClick={() =>
                      setCriteres((precedents) =>
                        precedents.filter((element) => element.id !== critere.id),
                      )
                    }
                  >
                    <Trash2 size={17} aria-hidden />
                  </Bouton>
                </div>
              );
            })}

            <Bouton variante="secondaire" onClick={ajouterCritere} icone={<Plus size={17} aria-hidden />}>
              Ajouter une condition
            </Bouton>
          </div>
        </CorpsCarte>
      </Carte>

      {recherche.isError ? <MessageErreur erreur={recherche.error} /> : null}

      {resultat ? (
        <Carte>
          <EnteteCarte
            titre={`${formaterNombre(resultat.total)} résultat(s)`}
            description={`Entité interrogée : ${entite?.libelle ?? resultat.entite}.`}
            action={
              <Bouton
                variante="secondaire"
                onClick={() =>
                  void api
                    .telecharger(`/recherche/avancee/export?format_export=csv`, `${resultat.entite}.csv`)
                    .catch(() => undefined)
                }
                icone={<Download size={17} aria-hidden />}
              >
                Exporter
              </Bouton>
            }
          />
          <ResultatTable resultat={resultat} onPage={executer} page={page} />
        </Carte>
      ) : null}
    </div>
  );
}

// ------------------------------------------------------------------
//  Recherche en langage naturel
// ------------------------------------------------------------------

function RechercheNaturelle() {
  const [question, setQuestion] = useState('');

  const suggestions = useQuery({
    queryKey: ['suggestions-recherche'],
    queryFn: () => api.get<string[]>('/recherche/suggestions'),
  });

  const interrogation = useMutation({
    mutationFn: (texte: string) =>
      api.post<ReponseNaturelle>('/recherche/langage-naturel', {
        question: texte,
        executer: true,
        taille: 25,
      }),
  });

  const reponse = interrogation.data;

  return (
    <div className="space-y-4">
      <Carte>
        <EnteteCarte
          titre="Posez votre question"
          description="La plateforme traduit votre phrase en filtres structurés, puis exécute la requête."
        />
        <CorpsCarte>
          <form
            onSubmit={(evenement) => {
              evenement.preventDefault();
              if (question.trim().length > 3) interrogation.mutate(question.trim());
            }}
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
          >
            <div className="flex-1">
              <Champ
                etiquette="Votre question"
                value={question}
                onChange={(evenement) => setQuestion(evenement.target.value)}
                placeholder="Montre-moi les élèves des CEG ayant au moins 17 de moyenne en mathématiques"
              />
            </div>
            <Bouton type="submit" taille="lg" chargement={interrogation.isPending}>
              <Sparkles size={18} aria-hidden /> Interroger
            </Bouton>
          </form>

          <div className="mt-4">
            <p className="mb-2 text-sm font-medium texte-doux">Exemples</p>
            <ul className="flex flex-wrap gap-2">
              {(suggestions.data ?? []).map((exemple) => (
                <li key={exemple}>
                  <button
                    type="button"
                    onClick={() => {
                      setQuestion(exemple);
                      interrogation.mutate(exemple);
                    }}
                    className="rounded-full border px-3 py-1.5 text-left text-sm transition hover:bg-[rgb(var(--fond-doux))]"
                  >
                    {exemple}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </CorpsCarte>
      </Carte>

      {interrogation.isError ? <MessageErreur erreur={interrogation.error} /> : null}

      {reponse ? (
        <>
          <Carte>
            <EnteteCarte
              titre="Interprétation"
              description={`Entité : ${reponse.entite} — indice de confiance ${Math.round(reponse.confiance * 100)} %.`}
            />
            <CorpsCarte className="space-y-3">
              {reponse.filtres.length > 0 ? (
                <ul className="flex flex-wrap gap-2">
                  {reponse.filtres.map((filtre, index) => (
                    <li key={index}>
                      <Badge ton="info">
                        {filtre.champ} {OPERATEURS[filtre.operateur] ?? filtre.operateur}{' '}
                        {String(filtre.valeur)}
                      </Badge>
                    </li>
                  ))}
                </ul>
              ) : null}
              <ul className="space-y-1 text-sm texte-doux">
                {reponse.explications.map((explication, index) => (
                  <li key={index}>— {explication}</li>
                ))}
              </ul>
            </CorpsCarte>
          </Carte>

          {reponse.resultat ? (
            <Carte>
              <EnteteCarte titre={`${formaterNombre(reponse.resultat.total)} résultat(s)`} />
              <ResultatTable resultat={reponse.resultat} />
            </Carte>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

// ------------------------------------------------------------------
//  Restitution commune
// ------------------------------------------------------------------

function ResultatTable({
  resultat,
  onPage,
  page,
}: {
  resultat: ResultatRecherche;
  onPage?: (page: number) => void;
  page?: number;
}) {
  if (resultat.lignes.length === 0) {
    return (
      <EtatVide
        titre="Aucun résultat"
        description="Aucune donnée ne satisfait l'ensemble des conditions posées."
      />
    );
  }

  return (
    <>
      <Tableau
        legende="Résultats de la recherche"
        lignes={resultat.lignes}
        cleLigne={(ligne, index) => String(ligne.id ?? index)}
        colonnes={resultat.colonnes
          .filter((colonne) => colonne.cle !== 'id')
          .map((colonne, index) => ({
            cle: colonne.cle,
            entete: colonne.libelle,
            secondaire: index > 3,
            rendu: (ligne: Record<string, unknown>) => {
              const valeur = ligne[colonne.cle];
              if (valeur === null || valeur === undefined || valeur === '') {
                return <span className="texte-doux">—</span>;
              }
              if (typeof valeur === 'number') {
                return <span className="tabular-nums">{formaterNombre(valeur, 2)}</span>;
              }
              return String(valeur);
            },
          }))}
      />
      {onPage && page ? (
        <Pagination
          page={page}
          pages={resultat.pages}
          total={resultat.total}
          taille={resultat.taille}
          onChange={onPage}
        />
      ) : null}
    </>
  );
}

/** Convertit la saisie texte en valeur exploitable par l'API. */
function normaliserValeur(valeur: string, operateur: string): unknown {
  if (['is_null', 'not_null'].includes(operateur)) return null;
  if (operateur === 'between' || operateur === 'in' || operateur === 'not_in') {
    const morceaux = valeur.split(',').map((element) => element.trim());
    return morceaux.map((element) => (Number.isNaN(Number(element)) ? element : Number(element)));
  }
  if (valeur === 'true') return true;
  if (valeur === 'false') return false;
  const nombre = Number(valeur);
  return valeur !== '' && !Number.isNaN(nombre) ? nombre : valeur;
}
