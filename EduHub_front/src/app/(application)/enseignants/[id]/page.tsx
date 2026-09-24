'use client';

import { useQuery } from '@tanstack/react-query';
import { BookOpen, ClipboardCheck, GraduationCap, ShieldCheck } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeDescriptive, Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
} from '@/components/ui/primitives';
import { api } from '@/lib/api';
import { formaterNombre, initiales } from '@/lib/utils';

interface Service {
  enseignant: {
    id: string;
    matricule: string;
    nom_complet: string;
    grade: string | null;
    anciennete_annees: number;
  };
  etablissement: string | null;
  heures_hebdomadaires: number;
  matieres: Array<{ id: string; code: string; libelle: string; principale: boolean }>;
  classes_principales: Array<{
    id: string;
    libelle: string;
    effectif: number;
    etablissement: string | null;
  }>;
  aptitudes: { surveillance: boolean; correction: boolean; presidence_jury: boolean };
}

export default function PageServiceEnseignant() {
  const parametres = useParams<{ id: string }>();
  const router = useRouter();

  const service = useQuery({
    queryKey: ['service-enseignant', parametres.id],
    queryFn: () => api.get<Service>(`/enseignants/${parametres.id}/service`),
  });

  if (service.isLoading) return <Chargement libelle="Ouverture du service de l'enseignant…" />;
  if (service.isError) return <MessageErreur erreur={service.error} />;

  const donnees = service.data!;
  const enseignant = donnees.enseignant;

  return (
    <>
      <EntetePage
        fil={[{ libelle: 'Enseignants', href: '/enseignants' }, { libelle: enseignant.nom_complet }]}
        titre={enseignant.nom_complet}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs">{enseignant.matricule}</span>
            {enseignant.grade ? <Badge ton="info">{enseignant.grade}</Badge> : null}
            <span>{enseignant.anciennete_annees} an(s) d&apos;ancienneté</span>
          </span>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <Carte>
          <EnteteCarte titre="Affectation" />
          <CorpsCarte>
            <div className="mb-4 flex items-center gap-3">
              <span
                aria-hidden
                className="grid h-14 w-14 place-items-center rounded-full bg-[rgb(var(--accent))]/15 text-lg font-semibold text-[rgb(var(--accent))]"
              >
                {initiales(enseignant.nom_complet)}
              </span>
              <div className="min-w-0">
                <p className="font-medium">{donnees.etablissement ?? 'Non affecté'}</p>
                <p className="text-sm texte-doux">
                  {formaterNombre(donnees.heures_hebdomadaires)} heures hebdomadaires
                </p>
              </div>
            </div>
            <ListeDescriptive
              colonnes={1}
              entrees={[
                { terme: 'Matricule', valeur: enseignant.matricule },
                { terme: 'Grade', valeur: enseignant.grade ?? '—' },
                { terme: 'Ancienneté', valeur: `${enseignant.anciennete_annees} an(s)` },
              ]}
            />
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <BookOpen size={19} aria-hidden /> Matières enseignées
              </span>
            }
          />
          {donnees.matieres.length > 0 ? (
            <ul className="divide-y">
              {donnees.matieres.map((matiere) => (
                <li
                  key={matiere.id}
                  className="flex items-center justify-between gap-2 px-5 py-3"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{matiere.libelle}</span>
                    <span className="block font-mono text-xs texte-doux">{matiere.code}</span>
                  </span>
                  {matiere.principale ? <Badge ton="info">Principale</Badge> : null}
                </li>
              ))}
            </ul>
          ) : (
            <EtatVide titre="Aucune matière déclarée" />
          )}
        </Carte>

        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <ShieldCheck size={19} aria-hidden /> Aptitudes aux examens
              </span>
            }
            description="Rôles que l'enseignant peut tenir lors des sessions."
          />
          <CorpsCarte>
            <ul className="space-y-2 text-sm">
              {[
                {
                  libelle: 'Surveillance des épreuves',
                  valeur: donnees.aptitudes.surveillance,
                  icone: <ClipboardCheck size={16} aria-hidden />,
                },
                {
                  libelle: 'Correction des copies',
                  valeur: donnees.aptitudes.correction,
                  icone: <BookOpen size={16} aria-hidden />,
                },
                {
                  libelle: 'Présidence de jury',
                  valeur: donnees.aptitudes.presidence_jury,
                  icone: <GraduationCap size={16} aria-hidden />,
                },
              ].map((aptitude) => (
                <li key={aptitude.libelle} className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2">
                    {aptitude.icone}
                    {aptitude.libelle}
                  </span>
                  <Badge ton={aptitude.valeur ? 'succes' : 'neutre'}>
                    {aptitude.valeur ? 'Habilité' : 'Non habilité'}
                  </Badge>
                </li>
              ))}
            </ul>
          </CorpsCarte>
        </Carte>
      </div>

      <Carte className="mt-4">
        <EnteteCarte
          titre="Classes dont il est professeur principal"
          description={`${donnees.classes_principales.length} classe(s).`}
        />
        <Tableau
          legende="Classes sous la responsabilité de l'enseignant"
          lignes={donnees.classes_principales}
          cleLigne={(classe) => classe.id}
          onLigneClic={(classe) => router.push(`/classes/${classe.id}`)}
          vide={<EtatVide titre="Aucune classe en responsabilité" />}
          colonnes={[
            {
              cle: 'libelle',
              entete: 'Classe',
              rendu: (classe) => <span className="font-medium">{classe.libelle}</span>,
            },
            {
              cle: 'etablissement',
              entete: 'Établissement',
              secondaire: true,
              rendu: (classe) => classe.etablissement ?? '—',
            },
            {
              cle: 'effectif',
              entete: 'Effectif',
              alignement: 'droite',
              rendu: (classe) => formaterNombre(classe.effectif),
            },
          ]}
        />
      </Carte>
    </>
  );
}
