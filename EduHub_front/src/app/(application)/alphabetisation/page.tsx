'use client';

import { useQuery } from '@tanstack/react-query';
import { Award, Languages, Users } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { GraphiqueBarres } from '@/components/graphiques';
import { Indicateur, Jauge, Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
} from '@/components/ui/primitives';
import { api, type Page } from '@/lib/api';
import { formaterNombre, formaterPourcentage, humaniser } from '@/lib/utils';

interface CentreAlphabetisation {
  id: string;
  code: string;
  nom: string;
  langue_enseignement: string;
  responsable: string | null;
  telephone: string | null;
  nombre_formateurs: number;
  nombre_apprenants: number;
  actif: boolean;
}

interface Parcours {
  id: string;
  nom_complet: string;
  age: number | null;
  langue: string;
  niveau_initial: string;
  niveau_atteint: string | null;
  progression_pourcentage: number;
  certifie: boolean;
}

interface Statistiques {
  centres: number;
  apprenants: number;
  certifies: number;
  taux_certification: number;
  par_langue: Array<{
    langue: string;
    apprenants: number;
    progression_moyenne: number;
    certifies: number;
  }>;
}

export default function PageAlphabetisation() {
  const [centreId, setCentreId] = useState<string | null>(null);

  const statistiques = useQuery({
    queryKey: ['alphabetisation-statistiques'],
    queryFn: () => api.get<Statistiques>('/alphabetisation/statistiques'),
  });

  const centres = useQuery({
    queryKey: ['centres-alphabetisation'],
    queryFn: () =>
      api.get<Page<CentreAlphabetisation>>('/alphabetisation/centres', { size: 100 }),
  });

  const actif = centreId ?? centres.data?.items[0]?.id ?? null;

  const parcours = useQuery({
    queryKey: ['parcours-alphabetisation', actif],
    enabled: Boolean(actif),
    queryFn: () => api.get<Parcours[]>(`/alphabetisation/centres/${actif}/parcours`),
  });

  if (statistiques.isLoading) return <Chargement libelle="Chargement de l'alphabétisation…" />;
  if (statistiques.isError) return <MessageErreur erreur={statistiques.error} />;

  const stats = statistiques.data!;
  const liste = centres.data?.items ?? [];
  const centre = liste.find((element) => element.id === actif);

  return (
    <>
      <EntetePage
        titre="Alphabétisation et éducation non formelle"
        description="Centres d'alphabétisation en langues nationales : fon, yoruba, bariba, dendi et adja."
      />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicateur
          libelle="Centres"
          valeur={stats.centres}
          icone={<Languages size={18} />}
          pictogramme="🏫"
        />
        <Indicateur
          libelle="Apprenants suivis"
          valeur={stats.apprenants}
          icone={<Users size={18} />}
          pictogramme="🧑‍🤝‍🧑"
        />
        <Indicateur
          libelle="Certifiés"
          valeur={stats.certifies}
          icone={<Award size={18} />}
          pictogramme="🏅"
        />
        <Indicateur
          libelle="Taux de certification"
          valeur={formaterPourcentage(stats.taux_certification)}
          pictogramme="📈"
        />
      </div>

      <Carte className="mb-4">
        <EnteteCarte
          titre="Répartition par langue nationale"
          description="Effectifs suivis et progression moyenne, langue par langue."
        />
        <CorpsCarte>
          <GraphiqueBarres
            titre="Apprenants par langue nationale"
            donnees={stats.par_langue}
            cleAbscisse="langue"
            series={[
              { cle: 'apprenants', libelle: 'Apprenants' },
              { cle: 'certifies', libelle: 'Certifiés', couleur: '#16a153' },
            ]}
            hauteur={260}
          />
        </CorpsCarte>
      </Carte>

      {liste.length === 0 ? (
        <Carte>
          <EtatVide titre="Aucun centre d'alphabétisation" />
        </Carte>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[22rem_1fr]">
          <Carte className="h-fit">
            <EnteteCarte titre="Centres" description={`${liste.length} centre(s).`} />
            <ul className="defilement-fin max-h-[32rem] divide-y overflow-y-auto">
              {liste.map((element) => (
                <li key={element.id}>
                  <button
                    type="button"
                    onClick={() => setCentreId(element.id)}
                    aria-current={element.id === actif ? 'true' : undefined}
                    className={`w-full px-4 py-3 text-left transition ${
                      element.id === actif
                        ? 'bg-[rgb(var(--accent))]/10'
                        : 'hover:bg-[rgb(var(--fond-doux))]'
                    }`}
                  >
                    <span className="flex items-start justify-between gap-2">
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">{element.nom}</span>
                        <span className="block truncate text-xs texte-doux">
                          {element.nombre_apprenants} apprenant(s) ·{' '}
                          {element.nombre_formateurs} formateur(s)
                        </span>
                      </span>
                      <Badge ton="neutre">{element.langue_enseignement}</Badge>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </Carte>

          <Carte>
            <EnteteCarte
              titre={centre ? centre.nom : 'Parcours'}
              description={
                centre
                  ? `Langue d'enseignement : ${centre.langue_enseignement}${
                      centre.responsable ? ` · responsable : ${centre.responsable}` : ''
                    }`
                  : undefined
              }
            />
            <Tableau
              legende="Parcours des apprenants du centre"
              lignes={parcours.data ?? []}
              cleLigne={(ligne) => ligne.id}
              vide={<EtatVide titre="Aucun parcours enregistré" />}
              colonnes={[
                {
                  cle: 'nom',
                  entete: 'Apprenant',
                  rendu: (ligne) => <span className="font-medium">{ligne.nom_complet}</span>,
                },
                {
                  cle: 'age',
                  entete: 'Âge',
                  alignement: 'droite',
                  secondaire: true,
                  rendu: (ligne) => ligne.age ?? '—',
                },
                {
                  cle: 'niveau',
                  entete: 'Niveau',
                  secondaire: true,
                  rendu: (ligne) =>
                    `${humaniser(ligne.niveau_initial)} → ${humaniser(ligne.niveau_atteint ?? ligne.niveau_initial)}`,
                },
                {
                  cle: 'progression',
                  entete: 'Progression',
                  largeur: '14rem',
                  rendu: (ligne) => (
                    <Jauge
                      valeur={ligne.progression_pourcentage}
                      etiquette=""
                      ton={
                        ligne.progression_pourcentage >= 75
                          ? 'succes'
                          : ligne.progression_pourcentage >= 40
                            ? 'accent'
                            : 'alerte'
                      }
                    />
                  ),
                },
                {
                  cle: 'certifie',
                  entete: 'Certification',
                  alignement: 'centre',
                  rendu: (ligne) =>
                    ligne.certifie ? (
                      <Badge ton="succes">Certifié</Badge>
                    ) : (
                      <span className="texte-doux">En cours</span>
                    ),
                },
              ]}
            />
          </Carte>
        </div>
      )}
    </>
  );
}
