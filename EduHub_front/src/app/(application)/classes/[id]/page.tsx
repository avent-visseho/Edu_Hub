'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, Play } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { GraphiqueBarres } from '@/components/graphiques';
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
import { api } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterNote, formaterPourcentage, humaniser } from '@/lib/utils';

interface ApprenantClasse {
  id: string;
  identifiant_educatif: string;
  nom_complet: string;
  sexe: string;
  type_handicap: string;
  tiers_temps: boolean;
  numero_inscription: string;
  statut: string;
  redoublant: boolean;
  moyenne_annuelle: number | null;
}

interface StatistiquesClasse {
  classe_id: string;
  classe_libelle: string;
  periode_libelle: string;
  effectif: number;
  moyenne_classe: number | null;
  moyenne_maximale: number | null;
  moyenne_minimale: number | null;
  nombre_moyennes_superieures_10: number;
  taux_reussite: number;
  distribution: Array<{ tranche: string; effectif: number }>;
  par_matiere: Array<{
    matiere: string;
    moyenne: number | null;
    minimum: number | null;
    maximum: number | null;
    effectif: number;
  }>;
}

interface Periode {
  id: string;
  code: string;
  libelle: string;
  numero: number;
}

export default function PageDetailClasse() {
  const parametres = useParams<{ id: string }>();
  const { peut } = useSession();
  const client = useQueryClient();
  const [periodeId, setPeriodeId] = useState('');

  const annee = useQuery({
    queryKey: ['annee-courante'],
    queryFn: () =>
      api.get<{ id: string; libelle: string; periodes: Periode[] }>(
        '/annees-academiques/courante',
      ),
  });

  const periodeActive = periodeId || annee.data?.periodes[0]?.id || '';

  const apprenants = useQuery({
    queryKey: ['classe-apprenants', parametres.id],
    queryFn: () => api.get<ApprenantClasse[]>(`/classes/${parametres.id}/apprenants`),
  });

  const statistiques = useQuery({
    queryKey: ['classe-statistiques', parametres.id, periodeActive],
    enabled: Boolean(periodeActive),
    retry: false,
    queryFn: () =>
      api.get<StatistiquesClasse>(`/classes/${parametres.id}/statistiques`, {
        periode_id: periodeActive,
      }),
  });

  const generation = useMutation({
    mutationFn: () =>
      api.post<{ bulletins_generes: number; moyenne_classe: number | null }>(
        '/bulletins/generer',
        { classe_id: parametres.id, periode_id: periodeActive, publier: true },
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['classe-statistiques'] });
      void client.invalidateQueries({ queryKey: ['classe-apprenants'] });
    },
  });

  if (apprenants.isLoading) return <Chargement libelle="Ouverture de la classe…" />;
  if (apprenants.isError) return <MessageErreur erreur={apprenants.error} />;

  const stats = statistiques.data;

  return (
    <>
      <EntetePage
        fil={[{ libelle: 'Classes', href: '/classes' }, { libelle: stats?.classe_libelle ?? 'Classe' }]}
        titre={stats?.classe_libelle ?? 'Classe'}
        description={`${apprenants.data?.length ?? 0} apprenant(s) inscrit(s).`}
        actions={
          <>
            <Selection
              etiquette="Période"
              etiquetteMasquee
              value={periodeActive}
              onChange={(evenement) => setPeriodeId(evenement.target.value)}
              options={(annee.data?.periodes ?? []).map((periode) => ({
                valeur: periode.id,
                libelle: periode.libelle,
              }))}
              className="h-11"
            />
            {peut('bulletins', 'CREATE') ? (
              <Bouton
                onClick={() => generation.mutate()}
                chargement={generation.isPending}
                icone={<Play size={17} aria-hidden />}
              >
                Générer les bulletins
              </Bouton>
            ) : null}
          </>
        }
      />

      {generation.isSuccess ? (
        <div
          role="status"
          className="mb-4 rounded-lg border border-[rgb(var(--succes))]/40 bg-[rgb(var(--succes))]/8 px-4 py-3 text-sm"
        >
          <p className="font-medium">
            {generation.data.bulletins_generes} bulletin(s) généré(s) et publié(s) — moyenne de
            classe {formaterNote(generation.data.moyenne_classe)}.
          </p>
        </div>
      ) : null}
      {generation.isError ? <MessageErreur erreur={generation.error} /> : null}

      {stats ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
            <Indicateur libelle="Effectif" valeur={stats.effectif} pictogramme="🧑‍🎓" />
            <Indicateur
              libelle="Moyenne de classe"
              valeur={formaterNote(stats.moyenne_classe)}
              unite="/ 20"
              pictogramme="📊"
            />
            <Indicateur
              libelle="Meilleure moyenne"
              valeur={formaterNote(stats.moyenne_maximale)}
              pictogramme="🥇"
            />
            <Indicateur
              libelle="Moyenne la plus basse"
              valeur={formaterNote(stats.moyenne_minimale)}
              pictogramme="🔻"
            />
            <Indicateur
              libelle="Taux de réussite"
              valeur={formaterPourcentage(stats.taux_reussite)}
              pictogramme="🏆"
            />
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            <Carte>
              <EnteteCarte
                titre="Distribution des moyennes"
                description={`Période : ${stats.periode_libelle}.`}
              />
              <CorpsCarte>
                <GraphiqueBarres
                  titre="Distribution des moyennes de la classe"
                  donnees={stats.distribution}
                  cleAbscisse="tranche"
                  series={[{ cle: 'effectif', libelle: 'Apprenants', couleur: '#284f8b' }]}
                  hauteur={250}
                />
              </CorpsCarte>
            </Carte>

            <Carte>
              <EnteteCarte titre="Moyennes par matière" />
              <CorpsCarte>
                <GraphiqueBarres
                  titre="Moyenne par matière"
                  donnees={stats.par_matiere}
                  cleAbscisse="matiere"
                  series={[{ cle: 'moyenne', libelle: 'Moyenne', couleur: '#16a153' }]}
                  hauteur={250}
                />
              </CorpsCarte>
            </Carte>
          </div>
        </>
      ) : statistiques.isError ? (
        <Carte className="mt-4">
          <CorpsCarte>
            <EtatVide
              titre="Aucune statistique disponible"
              description="Générez les bulletins de la période pour calculer les moyennes et les rangs."
              icone={<FileText size={32} aria-hidden />}
            />
          </CorpsCarte>
        </Carte>
      ) : null}

      <Carte className="mt-4">
        <EnteteCarte titre="Élèves de la classe" />
        <Tableau
          legende="Élèves inscrits dans la classe"
          lignes={apprenants.data ?? []}
          cleLigne={(apprenant) => apprenant.id}
          vide={<EtatVide titre="Aucun élève inscrit" />}
          colonnes={[
            {
              cle: 'identifiant',
              entete: 'Identifiant',
              secondaire: true,
              rendu: (apprenant) => (
                <span className="font-mono text-xs">{apprenant.identifiant_educatif}</span>
              ),
            },
            {
              cle: 'nom',
              entete: 'Nom et prénoms',
              rendu: (apprenant) => (
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{apprenant.nom_complet}</span>
                  {apprenant.redoublant ? <Badge ton="alerte">Redoublant</Badge> : null}
                  {apprenant.tiers_temps ? <Badge ton="info">Tiers temps</Badge> : null}
                </span>
              ),
            },
            {
              cle: 'sexe',
              entete: 'Sexe',
              secondaire: true,
              rendu: (apprenant) => (apprenant.sexe === 'FEMININ' ? 'Féminin' : 'Masculin'),
            },
            {
              cle: 'moyenne',
              entete: 'Moyenne annuelle',
              alignement: 'droite',
              rendu: (apprenant) => formaterNote(apprenant.moyenne_annuelle),
            },
            {
              cle: 'statut',
              entete: 'Statut',
              rendu: (apprenant) => (
                <Badge ton={tonDuStatut(apprenant.statut)}>{humaniser(apprenant.statut)}</Badge>
              ),
            },
          ]}
        />
      </Carte>
    </>
  );
}
