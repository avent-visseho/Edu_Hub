'use client';

import { useQuery } from '@tanstack/react-query';
import {
  Award,
  Briefcase,
  Bus,
  CalendarCheck,
  FileText,
  GraduationCap,
  Landmark,
  Lightbulb,
  User,
} from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';

import { EntetePage } from '@/components/layout/entete-page';
import { Jauge, ListeDescriptive, Tableau } from '@/components/ui/donnees';
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
import { api } from '@/lib/api';
import { formaterDate, formaterNote, humaniser, initiales } from '@/lib/utils';
import type { Apprenant } from '@/types/api';

interface Dossier {
  apprenant: Apprenant;
  parents: Array<{
    id: string;
    nom_complet: string;
    lien: string;
    contact_principal: boolean;
    telephone: string | null;
    profession: string | null;
  }>;
  parcours: Array<{
    annee: string;
    etablissement: string | null;
    classe: string | null;
    statut: string;
    moyenne_annuelle: number | null;
    rang: number | null;
    decision: string | null;
  }>;
  bulletins: Array<{
    id: string;
    numero: string;
    periode: string;
    classe: string;
    moyenne_generale: number | null;
    rang: number | null;
    effectif_classe: number | null;
    mention: string | null;
    decision: string | null;
    publie: boolean;
  }>;
  examens: Array<{
    numero_candidat: string;
    examen: string;
    session: string;
    serie: string | null;
    statut_dossier: string;
    moyenne: number | null;
    mention: string | null;
    decision: string | null;
  }>;
  diplomes: Array<{
    id: string;
    numero: string;
    intitule: string;
    annee: number;
    mention: string | null;
    moyenne: number | null;
    code_verification: string;
    date_delivrance: string;
  }>;
  assiduite: {
    seances: number;
    presences: number;
    absences_justifiees: number;
    absences_injustifiees: number;
    retards: number;
    taux_presence: number;
  } | null;
  bourses: Array<{ numero: string; statut: string; montant_attribue: number }>;
  projets: Array<{ id: string; titre: string; domaine: string | null; role: string; statut: string }>;
  stages: Array<{
    reference: string;
    sujet: string;
    date_debut: string;
    date_fin: string;
    note_finale: number | null;
    valide: boolean;
  }>;
  competences: Array<{ libelle: string; niveau: string; source: string | null }>;
  transport: Array<{ ligne: string; numero_carte: string; date_fin: string; actif: boolean }>;
}

export default function PageDossierApprenant() {
  const parametres = useParams<{ id: string }>();
  const router = useRouter();

  const dossier = useQuery({
    queryKey: ['dossier-apprenant', parametres.id],
    queryFn: () => api.get<Dossier>(`/apprenants/${parametres.id}/dossier`),
  });

  if (dossier.isLoading) return <Chargement libelle="Ouverture du dossier scolaire…" />;
  if (dossier.isError) return <MessageErreur erreur={dossier.error} />;

  const donnees = dossier.data!;
  const apprenant = donnees.apprenant;

  return (
    <>
      <EntetePage
        fil={[
          { libelle: 'Apprenants', href: '/apprenants' },
          { libelle: apprenant.nom_complet },
        ]}
        titre={apprenant.nom_complet}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs">{apprenant.identifiant_educatif}</span>
            <Badge ton={tonDuStatut(apprenant.statut)}>{humaniser(apprenant.statut)}</Badge>
            {apprenant.type_handicap !== 'AUCUN' ? (
              <Badge ton="info">{humaniser(apprenant.type_handicap)}</Badge>
            ) : null}
            {apprenant.tiers_temps ? <Badge ton="alerte">Tiers temps</Badge> : null}
          </span>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        {/* Identité */}
        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <User size={19} aria-hidden /> Identité
              </span>
            }
          />
          <CorpsCarte>
            <div className="mb-4 flex items-center gap-3">
              <span
                aria-hidden
                className="grid h-14 w-14 place-items-center rounded-full bg-[rgb(var(--accent))]/15 text-lg font-semibold text-[rgb(var(--accent))]"
              >
                {initiales(apprenant.nom_complet)}
              </span>
              <div className="min-w-0">
                <p className="font-medium">{apprenant.nom_complet}</p>
                <p className="text-sm texte-doux">
                  Né(e) le {formaterDate(apprenant.date_naissance)}
                </p>
              </div>
            </div>
            <ListeDescriptive
              colonnes={1}
              entrees={[
                { terme: 'Lieu de naissance', valeur: apprenant.lieu_naissance ?? '—' },
                { terme: 'Sexe', valeur: apprenant.sexe === 'FEMININ' ? 'Féminin' : 'Masculin' },
                {
                  terme: 'Besoins spécifiques',
                  valeur: apprenant.besoins_specifiques ?? 'Aucun besoin déclaré',
                },
                {
                  terme: 'Situation',
                  valeur: [
                    apprenant.orphelin ? 'Orphelin' : null,
                    apprenant.situation_vulnerable ? 'Situation vulnérable' : null,
                  ]
                    .filter(Boolean)
                    .join(' · ') || 'Ordinaire',
                },
              ]}
            />
          </CorpsCarte>
        </Carte>

        {/* Assiduité */}
        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <CalendarCheck size={19} aria-hidden /> Assiduité
              </span>
            }
          />
          <CorpsCarte>
            {donnees.assiduite ? (
              <div className="space-y-4">
                <Jauge
                  valeur={donnees.assiduite.taux_presence}
                  etiquette="Taux de présence"
                  ton={
                    donnees.assiduite.taux_presence >= 90
                      ? 'succes'
                      : donnees.assiduite.taux_presence >= 75
                        ? 'alerte'
                        : 'danger'
                  }
                />
                <ListeDescriptive
                  colonnes={2}
                  entrees={[
                    { terme: 'Séances suivies', valeur: donnees.assiduite.seances },
                    { terme: 'Présences', valeur: donnees.assiduite.presences },
                    {
                      terme: 'Absences justifiées',
                      valeur: donnees.assiduite.absences_justifiees,
                    },
                    {
                      terme: 'Absences injustifiées',
                      valeur: donnees.assiduite.absences_injustifiees,
                    },
                    { terme: 'Retards', valeur: donnees.assiduite.retards },
                  ]}
                />
              </div>
            ) : (
              <p className="py-6 text-center text-sm texte-doux">
                Aucun relevé d&apos;assiduité disponible.
              </p>
            )}
          </CorpsCarte>
        </Carte>

        {/* Parents */}
        <Carte>
          <EnteteCarte titre="Parents et tuteurs" />
          {donnees.parents.length > 0 ? (
            <ul className="divide-y">
              {donnees.parents.map((parent) => (
                <li key={parent.id} className="px-5 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-medium">{parent.nom_complet}</p>
                      <p className="text-sm texte-doux">
                        {humaniser(parent.lien)}
                        {parent.profession ? ` · ${parent.profession}` : ''}
                      </p>
                      {parent.telephone ? (
                        <p className="text-sm texte-doux">{parent.telephone}</p>
                      ) : null}
                    </div>
                    {parent.contact_principal ? <Badge ton="info">Contact</Badge> : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EtatVide titre="Aucun parent rattaché" />
          )}
        </Carte>
      </div>

      {/* Parcours */}
      <Carte className="mt-4">
        <EnteteCarte
          titre={
            <span className="flex items-center gap-2">
              <GraduationCap size={19} aria-hidden /> Parcours scolaire
            </span>
          }
          description="Historique des inscriptions, année par année."
        />
        <Tableau
          legende="Parcours scolaire de l'apprenant"
          lignes={donnees.parcours}
          cleLigne={(ligne, index) => `${ligne.annee}-${index}`}
          vide={<EtatVide titre="Aucune inscription enregistrée" />}
          colonnes={[
            { cle: 'annee', entete: 'Année', rendu: (ligne) => ligne.annee },
            {
              cle: 'etablissement',
              entete: 'Établissement',
              rendu: (ligne) => ligne.etablissement ?? '—',
            },
            { cle: 'classe', entete: 'Classe', rendu: (ligne) => ligne.classe ?? '—' },
            {
              cle: 'moyenne',
              entete: 'Moyenne',
              alignement: 'droite',
              rendu: (ligne) => formaterNote(ligne.moyenne_annuelle),
            },
            {
              cle: 'rang',
              entete: 'Rang',
              alignement: 'droite',
              secondaire: true,
              rendu: (ligne) => ligne.rang ?? '—',
            },
            {
              cle: 'decision',
              entete: 'Décision',
              rendu: (ligne) =>
                ligne.decision ? (
                  <Badge ton={tonDuStatut(ligne.decision)}>{humaniser(ligne.decision)}</Badge>
                ) : (
                  '—'
                ),
            },
          ]}
        />
      </Carte>

      {/* Bulletins */}
      <Carte className="mt-4">
        <EnteteCarte
          titre={
            <span className="flex items-center gap-2">
              <FileText size={19} aria-hidden /> Bulletins
            </span>
          }
        />
        <Tableau
          legende="Bulletins de l'apprenant"
          lignes={donnees.bulletins}
          cleLigne={(ligne) => ligne.id}
          onLigneClic={(ligne) => router.push(`/bulletins/${ligne.id}`)}
          vide={<EtatVide titre="Aucun bulletin publié" />}
          colonnes={[
            { cle: 'periode', entete: 'Période', rendu: (ligne) => ligne.periode },
            { cle: 'classe', entete: 'Classe', secondaire: true, rendu: (ligne) => ligne.classe },
            {
              cle: 'moyenne',
              entete: 'Moyenne',
              alignement: 'droite',
              rendu: (ligne) => (
                <span className="font-semibold">{formaterNote(ligne.moyenne_generale)}</span>
              ),
            },
            {
              cle: 'rang',
              entete: 'Rang',
              alignement: 'droite',
              rendu: (ligne) =>
                ligne.rang ? `${ligne.rang} / ${ligne.effectif_classe ?? '—'}` : '—',
            },
            { cle: 'mention', entete: 'Mention', secondaire: true, rendu: (ligne) => ligne.mention ?? '—' },
            {
              cle: 'decision',
              entete: 'Décision',
              rendu: (ligne) =>
                ligne.decision ? (
                  <Badge ton={tonDuStatut(ligne.decision)}>{humaniser(ligne.decision)}</Badge>
                ) : (
                  '—'
                ),
            },
          ]}
        />
      </Carte>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        {/* Examens */}
        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <Award size={19} aria-hidden /> Examens et concours
              </span>
            }
          />
          <Tableau
            legende="Candidatures aux examens"
            lignes={donnees.examens}
            cleLigne={(ligne) => ligne.numero_candidat}
            vide={<EtatVide titre="Aucune candidature" />}
            colonnes={[
              { cle: 'examen', entete: 'Examen', rendu: (ligne) => ligne.examen },
              { cle: 'serie', entete: 'Série', secondaire: true, rendu: (ligne) => ligne.serie ?? '—' },
              {
                cle: 'moyenne',
                entete: 'Moyenne',
                alignement: 'droite',
                rendu: (ligne) => formaterNote(ligne.moyenne),
              },
              {
                cle: 'decision',
                entete: 'Décision',
                rendu: (ligne) =>
                  ligne.decision ? (
                    <Badge ton={tonDuStatut(ligne.decision)}>{humaniser(ligne.decision)}</Badge>
                  ) : (
                    <Badge ton={tonDuStatut(ligne.statut_dossier)}>
                      {humaniser(ligne.statut_dossier)}
                    </Badge>
                  ),
              },
            ]}
          />
        </Carte>

        {/* Diplômes */}
        <Carte>
          <EnteteCarte titre="Diplômes obtenus" />
          {donnees.diplomes.length > 0 ? (
            <ul className="divide-y">
              {donnees.diplomes.map((diplome) => (
                <li key={diplome.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
                  <div className="min-w-0">
                    <p className="font-medium">{diplome.intitule}</p>
                    <p className="text-sm texte-doux">
                      {diplome.numero} · {diplome.annee}
                      {diplome.mention ? ` · mention ${diplome.mention}` : ''}
                    </p>
                  </div>
                  <Link
                    href={`/verification?code=${diplome.code_verification}`}
                    className="text-sm font-medium hover:underline"
                  >
                    Vérifier
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <EtatVide titre="Aucun diplôme délivré" />
          )}
        </Carte>
      </div>

      {/* Vie étudiante */}
      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2 text-base">
                <Landmark size={17} aria-hidden /> Bourses
              </span>
            }
          />
          <CorpsCarte className="p-4">
            {donnees.bourses.length > 0 ? (
              <ul className="space-y-2 text-sm">
                {donnees.bourses.map((bourse) => (
                  <li key={bourse.numero} className="flex items-center justify-between gap-2">
                    <span className="truncate">{bourse.numero}</span>
                    <Badge ton={tonDuStatut(bourse.statut)}>{humaniser(bourse.statut)}</Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm texte-doux">Aucune candidature.</p>
            )}
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2 text-base">
                <Bus size={17} aria-hidden /> Transport
              </span>
            }
          />
          <CorpsCarte className="p-4">
            {donnees.transport.length > 0 ? (
              <ul className="space-y-2 text-sm">
                {donnees.transport.map((abonnement) => (
                  <li key={abonnement.numero_carte}>
                    <p className="font-medium">{abonnement.ligne}</p>
                    <p className="texte-doux">
                      Carte {abonnement.numero_carte} — jusqu&apos;au{' '}
                      {formaterDate(abonnement.date_fin)}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm texte-doux">Aucun abonnement.</p>
            )}
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2 text-base">
                <Lightbulb size={17} aria-hidden /> Projets
              </span>
            }
          />
          <CorpsCarte className="p-4">
            {donnees.projets.length > 0 ? (
              <ul className="space-y-2 text-sm">
                {donnees.projets.map((projet) => (
                  <li key={projet.id}>
                    <p className="font-medium">{projet.titre}</p>
                    <p className="texte-doux">
                      {humaniser(projet.role)} · {humaniser(projet.statut)}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm texte-doux">Aucun projet.</p>
            )}
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2 text-base">
                <Briefcase size={17} aria-hidden /> Stages
              </span>
            }
          />
          <CorpsCarte className="p-4">
            {donnees.stages.length > 0 ? (
              <ul className="space-y-2 text-sm">
                {donnees.stages.map((stage) => (
                  <li key={stage.reference}>
                    <p className="font-medium">{stage.sujet}</p>
                    <p className="texte-doux">
                      {formaterDate(stage.date_debut)} → {formaterDate(stage.date_fin)}
                      {stage.note_finale !== null ? ` · ${formaterNote(stage.note_finale)}/20` : ''}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm texte-doux">Aucun stage.</p>
            )}
          </CorpsCarte>
        </Carte>
      </div>

      {donnees.competences.length > 0 ? (
        <Carte className="mt-4">
          <EnteteCarte titre="Compétences acquises" description="Portfolio de l'apprenant." />
          <CorpsCarte>
            <ul className="flex flex-wrap gap-2">
              {donnees.competences.map((competence) => (
                <li key={competence.libelle}>
                  <Badge ton="neutre">
                    {competence.libelle} · {humaniser(competence.niveau)}
                  </Badge>
                </li>
              ))}
            </ul>
          </CorpsCarte>
        </Carte>
      ) : null}
    </>
  );
}
