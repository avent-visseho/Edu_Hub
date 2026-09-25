'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Award,
  Building,
  ClipboardList,
  Download,
  FileSignature,
  Gavel,
  MapPin,
  Scale,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { useParams } from 'next/navigation';

import { EntetePage } from '@/components/layout/entete-page';
import { GraphiqueBarres } from '@/components/graphiques';
import { Indicateur, Jauge, Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  MessageErreur,
  tonDuStatut,
} from '@/components/ui/primitives';
import { api, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import {
  formaterMontant,
  formaterNombre,
  formaterNote,
  formaterPourcentage,
  humaniser,
} from '@/lib/utils';
import type { TableauBordSession } from '@/types/api';

interface BudgetSession {
  id: string;
  code: string;
  libelle: string;
  devise: string;
  valide: boolean;
  exercice: number | null;
}

export default function PagePilotageSession() {
  const parametres = useParams<{ id: string }>();
  const { peut } = useSession();
  const client = useQueryClient();

  const budget = useQuery({
    queryKey: ['budget-session', parametres.id],
    queryFn: () => api.get<Page<BudgetSession>>('/budgets-examen', { session_id: parametres.id }),
  });

  const tableau = useQuery({
    queryKey: ['session-tableau', parametres.id],
    queryFn: () => api.get<TableauBordSession>(`/sessions/${parametres.id}/tableau-de-bord`),
  });

  function actionSession(chemin: string, corps?: unknown) {
    return async () => {
      await api.post(`/sessions/${parametres.id}/${chemin}`, corps);
      await client.invalidateQueries({ queryKey: ['session-tableau', parametres.id] });
    };
  }

  const repartition = useMutation({
    mutationFn: actionSession('repartir-candidats', {
      par_departement: true,
      prioriser_amenagements: true,
      melanger_etablissements: true,
    }),
  });
  const convocations = useMutation({ mutationFn: actionSession('convocations') });
  const copies = useMutation({ mutationFn: actionSession('copies') });
  const deliberation = useMutation({
    mutationFn: actionSession('deliberer', {
      repechage_maximum: 0.5,
      appliquer_note_eliminatoire: true,
      publier: true,
    }),
  });
  const diplomes = useMutation({ mutationFn: actionSession('diplomes') });

  if (tableau.isLoading) return <Chargement libelle="Ouverture du pilotage de session…" />;
  if (tableau.isError) return <MessageErreur erreur={tableau.error} />;

  const donnees = tableau.data!;
  const session = donnees.session;
  const dossiers = Object.entries(donnees.dossiers).map(([statut, effectif]) => ({
    statut: humaniser(statut),
    effectif,
  }));
  const enCours = [repartition, convocations, copies, deliberation, diplomes].some(
    (mutation) => mutation.isPending,
  );
  const erreur = [repartition, convocations, copies, deliberation, diplomes].find(
    (mutation) => mutation.isError,
  );

  return (
    <>
      <EntetePage
        fil={[{ libelle: 'Examens', href: '/examens' }, { libelle: session.libelle }]}
        titre={session.libelle}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs">{session.code}</span>
            <Badge ton={tonDuStatut(session.statut)}>{humaniser(session.statut)}</Badge>
            <span>Session {session.annee}</span>
          </span>
        }
        actions={
          <Bouton
            variante="secondaire"
            onClick={() =>
              void api.telecharger(
                `/resultats/session/${parametres.id}/export`,
                `resultats-${session.code}.csv`,
              )
            }
            icone={<Download size={17} aria-hidden />}
          >
            Exporter les résultats
          </Bouton>
        }
      />

      {erreur ? <MessageErreur erreur={erreur.error} /> : null}

      {/* Chaîne opératoire */}
      <Carte className="mb-4">
        <EnteteCarte
          titre="Chaîne de traitement"
          description="Chaque étape s'appuie sur la précédente : répartition, convocations, copies, délibération, diplômes."
        />
        <CorpsCarte>
          <div className="flex flex-wrap gap-2">
            <Bouton
              variante="secondaire"
              disabled={enCours || !peut('centres', 'ASSIGN')}
              chargement={repartition.isPending}
              onClick={() => repartition.mutate()}
              icone={<MapPin size={17} aria-hidden />}
            >
              1. Répartir les candidats
            </Bouton>
            <Bouton
              variante="secondaire"
              disabled={enCours || !peut('candidats', 'PUBLISH')}
              chargement={convocations.isPending}
              onClick={() => convocations.mutate()}
              icone={<FileSignature size={17} aria-hidden />}
            >
              2. Émettre les convocations
            </Bouton>
            <Bouton
              variante="secondaire"
              disabled={enCours || !peut('copies', 'CREATE')}
              chargement={copies.isPending}
              onClick={() => copies.mutate()}
              icone={<ClipboardList size={17} aria-hidden />}
            >
              3. Générer les copies
            </Bouton>
            <Bouton
              variante="secondaire"
              disabled={enCours || !peut('resultats', 'VALIDATE')}
              chargement={deliberation.isPending}
              onClick={() => deliberation.mutate()}
              icone={<Gavel size={17} aria-hidden />}
            >
              4. Délibérer et publier
            </Bouton>
            <Bouton
              variante="secondaire"
              disabled={enCours || !peut('diplomes', 'CREATE')}
              chargement={diplomes.isPending}
              onClick={() => diplomes.mutate()}
              icone={<Award size={17} aria-hidden />}
            >
              5. Délivrer les diplômes
            </Bouton>
          </div>
        </CorpsCarte>
      </Carte>

      {/* Indicateurs */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Indicateur libelle="Inscrits" valeur={session.nombre_inscrits} icone={<Users size={18} />} pictogramme="🧾" />
        <Indicateur libelle="Présents" valeur={session.nombre_presents} pictogramme="✅" />
        <Indicateur libelle="Absents" valeur={session.nombre_absents} pictogramme="🚫" />
        <Indicateur libelle="Admis" valeur={session.nombre_admis} pictogramme="🏆" />
        <Indicateur
          libelle="Taux de réussite"
          valeur={formaterPourcentage(session.taux_reussite)}
          pictogramme="📈"
        />
        <Indicateur
          libelle="Moyenne générale"
          valeur={formaterNote(session.moyenne_generale)}
          unite="/ 20"
          pictogramme="📊"
        />
      </div>

      {/* Logistique */}
      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <Building size={19} aria-hidden /> Logistique
              </span>
            }
          />
          <CorpsCarte>
            <dl className="space-y-2.5 text-sm">
              {[
                { terme: 'Centres de composition', valeur: donnees.centres },
                { terme: 'Salles', valeur: donnees.salles },
                { terme: 'Agents de surveillance', valeur: donnees.surveillants },
                { terme: 'Correcteurs', valeur: donnees.correcteurs },
                { terme: 'Jurys', valeur: donnees.jurys },
              ].map((entree) => (
                <div key={entree.terme} className="flex items-center justify-between gap-2">
                  <dt className="texte-doux">{entree.terme}</dt>
                  <dd className="font-semibold tabular-nums">{formaterNombre(entree.valeur)}</dd>
                </div>
              ))}
            </dl>
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <ShieldCheck size={19} aria-hidden /> Correction
              </span>
            }
          />
          <CorpsCarte className="space-y-4">
            <Jauge
              valeur={donnees.copies_corrigees}
              maximum={donnees.copies_totales || 1}
              etiquette={`${formaterNombre(donnees.copies_corrigees)} / ${formaterNombre(donnees.copies_totales)} copies corrigées`}
              ton="succes"
            />
            <div>
              <p className="mb-2 text-sm font-medium texte-doux">Contentieux</p>
              {Object.keys(donnees.contentieux).length > 0 ? (
                <ul className="flex flex-wrap gap-2">
                  {Object.entries(donnees.contentieux).map(([statut, effectif]) => (
                    <li key={statut}>
                      <Badge ton={tonDuStatut(statut)}>
                        {humaniser(statut)} · {effectif}
                      </Badge>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm texte-doux">Aucune réclamation déposée.</p>
              )}
            </div>
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <Scale size={19} aria-hidden /> Budget
              </span>
            }
          />
          <CorpsCarte>
            <dl className="space-y-2.5 text-sm">
              {[
                { terme: 'Prévu', valeur: donnees.budget.prevu },
                { terme: 'Engagé', valeur: donnees.budget.engage },
                { terme: 'Payé', valeur: donnees.budget.paye },
                { terme: 'Recettes', valeur: donnees.budget.recettes },
              ].map((entree) => (
                <div key={entree.terme} className="flex items-center justify-between gap-2">
                  <dt className="texte-doux">{entree.terme}</dt>
                  <dd className="font-semibold tabular-nums">{formaterMontant(entree.valeur)}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-3">
              <Jauge
                valeur={donnees.budget.paye}
                maximum={donnees.budget.prevu || 1}
                etiquette="Exécution budgétaire"
                ton="accent"
              />
            </div>
            {(budget.data?.items ?? []).map((ligne) => (
              <p
                key={ligne.id}
                className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3 text-xs texte-doux"
              >
                <span className="font-mono">{ligne.code}</span>
                {ligne.exercice ? <span>exercice {ligne.exercice}</span> : null}
                <span>{ligne.devise}</span>
                <Badge ton={ligne.valide ? 'succes' : 'alerte'}>
                  {ligne.valide ? 'Budget validé' : 'En attente de validation'}
                </Badge>
              </p>
            ))}
          </CorpsCarte>
        </Carte>
      </div>

      {/* Dossiers et territoires */}
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Carte>
          <EnteteCarte
            titre="État des dossiers"
            description="Répartition des candidatures par étape du workflow."
          />
          <CorpsCarte>
            <GraphiqueBarres
              titre="Dossiers par statut"
              donnees={dossiers}
              cleAbscisse="statut"
              series={[{ cle: 'effectif', libelle: 'Candidats', couleur: '#284f8b' }]}
              hauteur={250}
            />
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte titre="Résultats par département" />
          <Tableau
            legende="Résultats par département"
            lignes={donnees.resultats_par_departement}
            cleLigne={(ligne) => ligne.code}
            colonnes={[
              { cle: 'departement', entete: 'Département', rendu: (ligne) => ligne.departement },
              {
                cle: 'candidats',
                entete: 'Candidats',
                alignement: 'droite',
                rendu: (ligne) => formaterNombre(ligne.candidats),
              },
              {
                cle: 'admis',
                entete: 'Admis',
                alignement: 'droite',
                rendu: (ligne) => formaterNombre(ligne.admis),
              },
              {
                cle: 'taux',
                entete: 'Réussite',
                alignement: 'droite',
                rendu: (ligne) => (
                  <span
                    className={
                      ligne.taux_reussite >= 60
                        ? 'font-semibold text-[rgb(var(--succes))]'
                        : ligne.taux_reussite >= 40
                          ? 'font-semibold text-[rgb(var(--alerte))]'
                          : 'font-semibold text-[rgb(var(--danger))]'
                    }
                  >
                    {formaterPourcentage(ligne.taux_reussite)}
                  </span>
                ),
              },
              {
                cle: 'moyenne',
                entete: 'Moyenne',
                alignement: 'droite',
                secondaire: true,
                rendu: (ligne) => formaterNote(ligne.moyenne),
              },
            ]}
          />
        </Carte>
      </div>
    </>
  );
}
