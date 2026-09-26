'use client';

import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  Award,
  BookOpen,
  Building2,
  DoorOpen,
  GraduationCap,
  Percent,
  UserSquare2,
  Users,
} from 'lucide-react';
import Link from 'next/link';

import { AccueilPersonnel } from '@/components/layout/accueil-personnel';
import { EntetePage } from '@/components/layout/entete-page';
import { GraphiqueBarres, GraphiqueSecteurs } from '@/components/graphiques';
import { Indicateur } from '@/components/ui/donnees';
import {
  Badge,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  MessageErreur,
  tonDuStatut,
} from '@/components/ui/primitives';
import { api } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterNombre, humaniser } from '@/lib/utils';
import type { TableauBord } from '@/types/api';

/** Icône et pictogramme associés à chaque indicateur national. */
const HABILLAGE: Record<string, { icone: React.ReactNode; pictogramme: string }> = {
  apprenants: { icone: <Users size={18} />, pictogramme: '🧑‍🎓' },
  enseignants: { icone: <UserSquare2 size={18} />, pictogramme: '👩‍🏫' },
  etablissements: { icone: <Building2 size={18} />, pictogramme: '🏫' },
  classes: { icone: <BookOpen size={18} />, pictogramme: '📚' },
  salles: { icone: <DoorOpen size={18} />, pictogramme: '🚪' },
  sessions_examen: { icone: <GraduationCap size={18} />, pictogramme: '🎓' },
  candidats: { icone: <Award size={18} />, pictogramme: '🧾' },
  taux_filles: { icone: <Percent size={18} />, pictogramme: '👧' },
  taux_reussite: { icone: <Percent size={18} />, pictogramme: '🏆' },
  ratio_eleves_enseignant: { icone: <Users size={18} />, pictogramme: '⚖️' },
};

export default function PageTableauDeBord() {
  const { utilisateur, peut } = useSession();

  // Le tableau national consolide les chiffres du pays : il répond à la
  // question d'un ministère ou d'une direction. Un chef d'établissement veut
  // voir son école, un enseignant ses classes, un élève sa scolarité — d'où
  // l'aiguillage sur la portée du compte plutôt que sur la seule permission.
  const pilotage =
    peut('analytics', 'READ') &&
    utilisateur?.niveau_scope !== 'PERSONNEL' &&
    utilisateur?.niveau_scope !== 'ETABLISSEMENT';

  const tableau = useQuery({
    queryKey: ['tableau-bord-national'],
    queryFn: () => api.get<TableauBord>('/tableaux-de-bord/national'),
    enabled: pilotage,
  });

  if (!pilotage) return <AccueilPersonnel />;
  if (tableau.isLoading) return <Chargement libelle="Consolidation des indicateurs…" />;
  if (tableau.isError) return <MessageErreur erreur={tableau.error} />;

  const donnees = tableau.data!;
  const territoires = (donnees.graphiques.effectifs_par_departement ?? []) as Array<
    Record<string, unknown>
  >;
  const distribution = (donnees.graphiques.distribution_moyennes ?? []) as Array<
    Record<string, unknown>
  >;
  const reussite = (donnees.graphiques.taux_reussite_sessions ?? []) as Array<
    Record<string, unknown>
  >;
  const parite = (donnees.graphiques.parite ?? []) as Array<Record<string, unknown>>;
  const inclusion = (donnees.graphiques.inclusion ?? []) as Array<Record<string, unknown>>;

  return (
    <>
      <EntetePage
        titre={`Bonjour ${utilisateur?.prenoms ?? ''}`.trim()}
        description={
          <>
            Vue nationale du système éducatif — {donnees.perimetre_libelle}. Les données de ce
            prototype sont fictives et générées automatiquement.
          </>
        }
      />

      {/* Indicateurs */}
      <section aria-labelledby="indicateurs-cles">
        <h2 id="indicateurs-cles" className="sr-only">
          Indicateurs clés
        </h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
          {donnees.indicateurs.map((indicateur) => (
            <Indicateur
              key={indicateur.code}
              libelle={indicateur.libelle}
              valeur={indicateur.valeur}
              unite={indicateur.unite}
              variation={indicateur.variation}
              icone={HABILLAGE[indicateur.code]?.icone}
              pictogramme={HABILLAGE[indicateur.code]?.pictogramme}
            />
          ))}
        </div>
      </section>

      {/* Graphiques */}
      <section className="mt-6 grid gap-4 xl:grid-cols-3" aria-labelledby="analyses">
        <h2 id="analyses" className="sr-only">
          Analyses
        </h2>

        <Carte className="xl:col-span-2">
          <EnteteCarte
            titre="Effectifs par département"
            description="Établissements et apprenants inscrits, sur l'ensemble du territoire."
          />
          <CorpsCarte>
            <GraphiqueBarres
              titre="Effectifs par département"
              donnees={territoires}
              cleAbscisse="departement"
              series={[
                { cle: 'apprenants', libelle: 'Apprenants' },
                { cle: 'etablissements', libelle: 'Établissements' },
              ]}
              hauteur={300}
            />
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte titre="Parité" description="Répartition filles / garçons." />
          <CorpsCarte>
            <GraphiqueSecteurs
              titre="Répartition par sexe"
              donnees={parite}
              cleLibelle="categorie"
              cleValeur="effectif"
            />
          </CorpsCarte>
        </Carte>

        <Carte className="xl:col-span-2">
          <EnteteCarte
            titre="Distribution des moyennes générales"
            description="Répartition des bulletins par tranche de moyenne."
          />
          <CorpsCarte>
            <GraphiqueBarres
              titre="Distribution des moyennes"
              donnees={distribution}
              cleAbscisse="tranche"
              series={[{ cle: 'effectif', libelle: 'Apprenants', couleur: '#16a153' }]}
              hauteur={260}
            />
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte titre="Inclusion" description="Apprenants déclarant un besoin spécifique." />
          <CorpsCarte>
            {inclusion.length > 0 ? (
              <GraphiqueSecteurs
                titre="Répartition des besoins spécifiques"
                donnees={inclusion}
                cleLibelle="categorie"
                cleValeur="effectif"
              />
            ) : (
              <p className="py-8 text-center text-sm texte-doux">
                Aucun besoin spécifique déclaré dans le jeu de données courant.
              </p>
            )}
          </CorpsCarte>
        </Carte>

        <Carte className="xl:col-span-3">
          <EnteteCarte
            titre="Taux de réussite par session d'examen"
            description="Comparaison des sessions les plus récentes."
            action={
              <Link href="/examens" className="text-sm font-medium hover:underline">
                Voir les sessions
              </Link>
            }
          />
          <CorpsCarte>
            <GraphiqueBarres
              titre="Taux de réussite par session"
              donnees={reussite}
              cleAbscisse="session"
              series={[{ cle: 'taux_reussite', libelle: 'Taux de réussite', couleur: '#284f8b' }]}
              hauteur={300}
              unite="%"
              longueurEtiquette={26}
            />
          </CorpsCarte>
        </Carte>
      </section>

      {/* Alertes */}
      {donnees.alertes.length > 0 ? (
        <section className="mt-6" aria-labelledby="alertes">
          <Carte>
            <EnteteCarte
              titre={
                <span className="flex items-center gap-2">
                  <AlertTriangle size={19} aria-hidden className="text-[rgb(var(--alerte))]" />
                  Alertes à traiter
                </span>
              }
              description={`${formaterNombre(donnees.alertes.length)} signalement(s) produit(s) par le moteur de règles.`}
            />
            <ul className="divide-y">
              {donnees.alertes.map((alerte) => (
                <li key={alerte.id} className="flex flex-wrap items-start gap-3 px-5 py-3.5">
                  <Badge ton={tonDuStatut(alerte.niveau)}>{humaniser(alerte.niveau)}</Badge>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{alerte.titre}</p>
                    <p className="text-sm texte-doux">{alerte.message}</p>
                  </div>
                  <span className="text-xs texte-doux">{humaniser(alerte.domaine)}</span>
                </li>
              ))}
            </ul>
          </Carte>
        </section>
      ) : null}
    </>
  );
}
