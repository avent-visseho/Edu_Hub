'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CalendarCheck, Download, FileText, Gavel, Play } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { COULEURS, GraphiqueBarres } from '@/components/graphiques';
import { EmploiDuTemps, type Creneau } from '@/components/ui/emploi-du-temps';
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
  tonDuStatut,
} from '@/components/ui/primitives';
import { api, ErreurApi, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterDate, formaterNote, formaterPourcentage, humaniser } from '@/lib/utils';

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

interface LigneAssiduite {
  apprenant_id: string;
  nom_complet: string;
  seances: number;
  presences: number;
  absences_justifiees: number;
  absences_injustifiees: number;
  retards: number;
  taux_presence: number;
  alerte: boolean;
}

interface SalleSimple {
  id: string;
  code: string;
  nom: string;
  capacite: number;
}

interface Conflit {
  type: string;
  jour: string;
  heure_debut: string;
  heure_fin: string;
  message: string;
}

/** Jours ouvrés de l'emploi du temps, dans l'ordre de la semaine scolaire. */
const JOURS_OUVRES = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI'];

interface ConseilClasse {
  id: string;
  date_conseil: string;
  president_nom: string | null;
  moyenne_classe: number | null;
  taux_reussite: number | null;
  observations: string | null;
  cloture: boolean;
  classe_libelle: string | null;
  periode_libelle: string | null;
}

interface Matiere {
  id: string;
  code: string;
  libelle: string;
}

interface Enseignant {
  id: string;
  nom_complet: string;
}

export default function PageDetailClasse() {
  const parametres = useParams<{ id: string }>();
  const router = useRouter();
  const { peut } = useSession();
  const client = useQueryClient();
  const [periodeId, setPeriodeId] = useState('');
  const [nouveauCreneau, setNouveauCreneau] = useState({
    matiere_id: '',
    enseignant_id: '',
    salle_id: '',
    jour: 'LUNDI',
    heure_debut: '08:00',
    heure_fin: '10:00',
  });
  const [journalCreneau, setJournalCreneau] = useState<string | null>(null);

  const annee = useQuery({
    queryKey: ['annee-courante'],
    queryFn: () =>
      api.get<{ id: string; libelle: string; periodes: Periode[] }>('/annees-academiques/courante'),
  });

  const periodeActive = periodeId || annee.data?.periodes[0]?.id || '';

  const apprenants = useQuery({
    queryKey: ['classe-apprenants', parametres.id],
    queryFn: () => api.get<ApprenantClasse[]>(`/classes/${parametres.id}/apprenants`),
  });

  const creneaux = useQuery({
    queryKey: ['classe-emploi-du-temps', parametres.id],
    queryFn: () => api.get<Creneau[]>(`/classes/${parametres.id}/emploi-du-temps`),
  });

  const salles = useQuery({
    queryKey: ['salles-classe', parametres.id],
    queryFn: () => api.get<Page<SalleSimple>>('/salles', { size: 200, sort_by: 'code' }),
  });

  const matieres = useQuery({
    queryKey: ['matieres-resume'],
    queryFn: () => api.get<{ items: Matiere[] }>('/matieres', { size: 100 }),
  });

  const enseignants = useQuery({
    queryKey: ['enseignants-resume'],
    queryFn: () => api.get<{ items: Enseignant[] }>('/enseignants', { size: 300 }),
  });

  // La charge est calculée à part pour servir à la fois la détection de
  // conflits et la création : les deux doivent porter exactement le même
  // créneau, sinon le contrôle ne vaut rien.
  const chargeCreneau = {
    classe_id: parametres.id,
    matiere_id: nouveauCreneau.matiere_id,
    enseignant_id: nouveauCreneau.enseignant_id || null,
    salle_id: nouveauCreneau.salle_id || null,
    jour: nouveauCreneau.jour,
    heure_debut: `${nouveauCreneau.heure_debut}:00`,
    heure_fin: `${nouveauCreneau.heure_fin}:00`,
  };

  const creneauComplet =
    Boolean(nouveauCreneau.matiere_id) && nouveauCreneau.heure_debut < nouveauCreneau.heure_fin;

  const conflits = useQuery({
    queryKey: ['conflits-creneau', chargeCreneau],
    queryFn: () =>
      api.post<{ conflit: boolean; conflits: Conflit[] }>(
        '/creneaux/verifier-conflits',
        chargeCreneau,
      ),
    enabled: creneauComplet && peut('emploi_du_temps', 'CREATE'),
  });

  const ajouterCreneau = useMutation({
    mutationFn: () => api.post<Creneau>('/creneaux', chargeCreneau),
    onSuccess: () => {
      setJournalCreneau('Créneau ajouté à l’emploi du temps.');
      void client.invalidateQueries({ queryKey: ['classe-emploi-du-temps', parametres.id] });
      void client.invalidateQueries({ queryKey: ['conflits-creneau'] });
    },
    onError: (erreurBrute: unknown) => {
      setJournalCreneau(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "Le créneau n'a pas pu être ajouté.",
      );
    },
  });

  const supprimerCreneau = useMutation({
    mutationFn: (creneau: Creneau) => api.delete(`/creneaux/${creneau.id}`),
    onSuccess: () => {
      setJournalCreneau('Créneau retiré de l’emploi du temps.');
      void client.invalidateQueries({ queryKey: ['classe-emploi-du-temps', parametres.id] });
    },
    onError: (erreurBrute: unknown) => {
      setJournalCreneau(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "Le créneau n'a pas pu être retiré.",
      );
    },
  });

  const conseils = useQuery({
    queryKey: ['conseils-classe', parametres.id],
    queryFn: () =>
      api.get<Page<ConseilClasse>>('/conseils-classe', {
        classe_id: parametres.id,
        size: 20,
        sort_by: 'date_conseil',
        sort_dir: 'desc',
      }),
  });

  const assiduite = useQuery({
    queryKey: ['classe-assiduite', parametres.id],
    queryFn: () => api.get<LigneAssiduite[]>(`/classes/${parametres.id}/assiduite`),
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
        // Les bulletins sont produits non publiés : la publication est un acte
        // distinct, tenu après le conseil de classe.
        { classe_id: parametres.id, periode_id: periodeActive, publier: false },
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
        fil={[
          { libelle: 'Classes', href: '/classes' },
          { libelle: stats?.classe_libelle ?? 'Classe' },
        ]}
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
            {peut('bulletins', 'EXPORT') ? (
              <Bouton
                variante="secondaire"
                icone={<Download size={17} aria-hidden />}
                onClick={() =>
                  void api
                    .telecharger(
                      `/bulletins/classe/${parametres.id}/export`,
                      `bulletins-${stats?.classe_libelle ?? 'classe'}.csv`,
                      periodeActive ? { periode_id: periodeActive } : undefined,
                    )
                    .catch(() => undefined)
                }
              >
                Exporter les bulletins
              </Bouton>
            ) : null}
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
                  series={[{ cle: 'effectif', libelle: 'Apprenants', couleur: COULEURS.bleu }]}
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
                  series={[{ cle: 'moyenne', libelle: 'Moyenne', couleur: COULEURS.vert }]}
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
        <EnteteCarte
          titre="Emploi du temps"
          description="Grille hebdomadaire des cours, avec l'enseignant affecté à chaque créneau."
        />
        <EmploiDuTemps
          onSupprimer={
            peut('emploi_du_temps', 'DELETE')
              ? (creneau) => supprimerCreneau.mutate(creneau)
              : undefined
          }
          creneaux={creneaux.data ?? []}
          libelleMatiere={(id) =>
            matieres.data?.items.find((matiere) => matiere.id === id)?.libelle ?? 'Matière'
          }
          libelleEnseignant={(id) =>
            id
              ? (enseignants.data?.items.find((enseignant) => enseignant.id === id)?.nom_complet ??
                null)
              : null
          }
        />

        {peut('emploi_du_temps', 'CREATE') ? (
          <CorpsCarte className="border-t">
            <h3 className="mb-3 font-medium">Ajouter un créneau</h3>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <Selection
                etiquette="Matière"
                required
                value={nouveauCreneau.matiere_id}
                onChange={(evenement) =>
                  setNouveauCreneau((precedent) => ({
                    ...precedent,
                    matiere_id: evenement.target.value,
                  }))
                }
                options={[
                  { valeur: '', libelle: 'Choisir une matière…' },
                  ...(matieres.data?.items ?? []).map((matiere) => ({
                    valeur: matiere.id,
                    libelle: matiere.libelle,
                  })),
                ]}
              />
              <Selection
                etiquette="Enseignant"
                value={nouveauCreneau.enseignant_id}
                onChange={(evenement) =>
                  setNouveauCreneau((precedent) => ({
                    ...precedent,
                    enseignant_id: evenement.target.value,
                  }))
                }
                options={[
                  { valeur: '', libelle: 'Non affecté' },
                  ...(enseignants.data?.items ?? []).map((enseignant) => ({
                    valeur: enseignant.id,
                    libelle: enseignant.nom_complet,
                  })),
                ]}
              />
              <Selection
                etiquette="Salle"
                value={nouveauCreneau.salle_id}
                onChange={(evenement) =>
                  setNouveauCreneau((precedent) => ({
                    ...precedent,
                    salle_id: evenement.target.value,
                  }))
                }
                options={[
                  { valeur: '', libelle: 'Non précisée' },
                  ...(salles.data?.items ?? []).map((salle) => ({
                    valeur: salle.id,
                    libelle: `${salle.nom} (${salle.capacite} places)`,
                  })),
                ]}
              />
              <Selection
                etiquette="Jour"
                value={nouveauCreneau.jour}
                onChange={(evenement) =>
                  setNouveauCreneau((precedent) => ({ ...precedent, jour: evenement.target.value }))
                }
                options={JOURS_OUVRES.map((jour) => ({ valeur: jour, libelle: humaniser(jour) }))}
              />
              <Champ
                etiquette="Début"
                type="time"
                value={nouveauCreneau.heure_debut}
                onChange={(evenement) =>
                  setNouveauCreneau((precedent) => ({
                    ...precedent,
                    heure_debut: evenement.target.value,
                  }))
                }
              />
              <Champ
                etiquette="Fin"
                type="time"
                value={nouveauCreneau.heure_fin}
                onChange={(evenement) =>
                  setNouveauCreneau((precedent) => ({
                    ...precedent,
                    heure_fin: evenement.target.value,
                  }))
                }
              />
            </div>

            {creneauComplet && conflits.data?.conflit ? (
              <div
                role="alert"
                className="mt-3 rounded-lg border border-[rgb(var(--danger))]/40 bg-[rgb(var(--danger))]/10 px-4 py-3 text-sm"
              >
                <p className="font-medium">
                  Ce créneau en chevauche {conflits.data.conflits.length} autre(s) :
                </p>
                <ul className="mt-1 space-y-0.5">
                  {conflits.data.conflits.map((conflit, index) => (
                    <li key={`${conflit.type}-${index}`}>
                      {conflit.message} ({conflit.heure_debut.slice(0, 5)} –{' '}
                      {conflit.heure_fin.slice(0, 5)})
                    </li>
                  ))}
                </ul>
              </div>
            ) : creneauComplet && conflits.data ? (
              <p className="mt-3 text-sm text-[rgb(var(--succes))]">
                Aucun chevauchement : la classe, l&apos;enseignant et la salle sont libres.
              </p>
            ) : null}

            {nouveauCreneau.heure_debut >= nouveauCreneau.heure_fin ? (
              <p className="mt-3 text-sm text-[rgb(var(--danger))]">
                L&apos;heure de fin doit suivre l&apos;heure de début.
              </p>
            ) : null}

            <Bouton
              className="mt-3"
              disabled={!creneauComplet || conflits.data?.conflit === true}
              chargement={ajouterCreneau.isPending}
              onClick={() => ajouterCreneau.mutate()}
            >
              Ajouter le créneau
            </Bouton>

            {journalCreneau ? (
              <p role="status" className="mt-2 text-sm texte-doux">
                {journalCreneau}
              </p>
            ) : null}
          </CorpsCarte>
        ) : null}
      </Carte>

      <Carte className="mt-4">
        <EnteteCarte
          titre={
            <span className="flex items-center gap-2">
              <Gavel size={19} aria-hidden /> Conseils de classe
            </span>
          }
          description="Une séance par période : moyenne de classe arrêtée, taux de réussite et observations."
        />
        <Tableau
          legende="Conseils de classe tenus pour cette classe"
          lignes={conseils.data?.items ?? []}
          cleLigne={(conseil) => conseil.id}
          vide={
            <EtatVide
              titre="Aucun conseil de classe"
              description="Les conseils sont tenus après la génération des bulletins de la période."
            />
          }
          colonnes={[
            {
              cle: 'periode',
              entete: 'Période',
              rendu: (conseil) => (
                <span className="min-w-0">
                  <span className="block font-medium">{conseil.periode_libelle ?? '—'}</span>
                  <span className="block text-xs texte-doux">
                    {formaterDate(conseil.date_conseil)}
                  </span>
                </span>
              ),
            },
            {
              cle: 'president',
              entete: 'Président',
              secondaire: true,
              rendu: (conseil) => conseil.president_nom ?? 'Non désigné',
            },
            {
              cle: 'moyenne',
              entete: 'Moyenne de classe',
              alignement: 'droite',
              rendu: (conseil) =>
                conseil.moyenne_classe != null ? formaterNote(conseil.moyenne_classe) : '—',
            },
            {
              cle: 'reussite',
              entete: 'Taux de réussite',
              largeur: '14rem',
              rendu: (conseil) => (
                <Jauge
                  valeur={conseil.taux_reussite ?? 0}
                  ton={
                    (conseil.taux_reussite ?? 0) >= 60
                      ? 'succes'
                      : (conseil.taux_reussite ?? 0) >= 40
                        ? 'alerte'
                        : 'danger'
                  }
                />
              ),
            },
            {
              cle: 'cloture',
              entete: 'État',
              rendu: (conseil) => (
                <Badge ton={conseil.cloture ? 'succes' : 'alerte'}>
                  {conseil.cloture ? 'Clôturé' : 'En cours'}
                </Badge>
              ),
            },
          ]}
        />
      </Carte>

      <Carte className="mt-4">
        <EnteteCarte
          titre="Assiduité"
          description="Taux de présence par apprenant. Une alerte est levée en dessous de 80 %."
          action={
            <Bouton
              variante="secondaire"
              taille="sm"
              icone={<CalendarCheck size={16} aria-hidden />}
              onClick={() => router.push(`/classes/${parametres.id}/appel`)}
            >
              Faire l&apos;appel
            </Bouton>
          }
        />
        <Tableau
          legende="Assiduité des apprenants de la classe"
          lignes={assiduite.data ?? []}
          cleLigne={(ligne) => ligne.apprenant_id}
          vide={<EtatVide titre="Aucun relevé d'assiduité" />}
          colonnes={[
            {
              cle: 'nom',
              entete: 'Apprenant',
              rendu: (ligne) => <span className="font-medium">{ligne.nom_complet}</span>,
            },
            {
              cle: 'presences',
              entete: 'Présences',
              alignement: 'droite',
              rendu: (ligne) => `${ligne.presences} / ${ligne.seances}`,
            },
            {
              cle: 'justifiees',
              entete: 'Absences justifiées',
              alignement: 'droite',
              secondaire: true,
              rendu: (ligne) => ligne.absences_justifiees,
            },
            {
              cle: 'injustifiees',
              entete: 'Absences injustifiées',
              alignement: 'droite',
              rendu: (ligne) => (
                <span
                  className={
                    ligne.absences_injustifiees > 0
                      ? 'font-semibold text-[rgb(var(--danger))]'
                      : undefined
                  }
                >
                  {ligne.absences_injustifiees}
                </span>
              ),
            },
            {
              cle: 'retards',
              entete: 'Retards',
              alignement: 'droite',
              secondaire: true,
              rendu: (ligne) => ligne.retards,
            },
            {
              cle: 'taux',
              entete: 'Taux de présence',
              largeur: '14rem',
              rendu: (ligne) => (
                <Jauge
                  valeur={ligne.taux_presence}
                  ton={
                    ligne.taux_presence >= 90
                      ? 'succes'
                      : ligne.taux_presence >= 80
                        ? 'alerte'
                        : 'danger'
                  }
                />
              ),
            },
            {
              cle: 'alerte',
              entete: 'Alerte',
              alignement: 'centre',
              rendu: (ligne) =>
                ligne.alerte ? (
                  <Badge ton="danger">Assiduité</Badge>
                ) : (
                  <span className="texte-doux">—</span>
                ),
            },
          ]}
        />
      </Carte>

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
