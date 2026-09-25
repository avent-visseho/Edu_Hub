'use client';

import { useQuery } from '@tanstack/react-query';
import { Building2, DoorOpen, Users, UserSquare2 } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';

import { EntetePage } from '@/components/layout/entete-page';
import { DocumentsEntite } from '@/components/ui/documents-entite';
import { Indicateur, ListeDescriptive, Tableau } from '@/components/ui/donnees';
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
import { formaterNombre, formaterNote, formaterPourcentage, humaniser } from '@/lib/utils';

interface DetailEtablissement {
  id: string;
  code: string;
  nom: string;
  sigle: string | null;
  type_libelle: string | null;
  statut_libelle: string | null;
  commune_libelle: string | null;
  departement_libelle: string | null;
  adresse: string | null;
  directeur_nom: string | null;
  telephone: string | null;
  email: string | null;
  annee_creation: number | null;
  capacite_accueil: number;
  effectif_actuel: number;
  est_centre_examen: boolean;
  internat: boolean;
  cantine: boolean;
  electricite: boolean;
  eau_potable: boolean;
  connexion_internet: boolean;
  accessibilite: string;
  zone_rurale: boolean;
  nombre_salles: number;
  nombre_batiments: number;
  nombre_classes: number;
  nombre_enseignants: number;
}

interface TableauBordEtablissement {
  etablissement: { id: string; code: string; nom: string };
  indicateurs: {
    effectif: number;
    filles: number;
    garcons: number;
    taux_filles: number;
    classes: number;
    salles: number;
    enseignants: number;
    eleves_par_classe: number;
    eleves_par_salle: number;
    eleves_par_enseignant: number;
    moyenne_etablissement: number | null;
  };
}

interface ClasseResume {
  id: string;
  code: string;
  libelle: string;
  niveau: string | null;
  serie: string | null;
  effectif: number;
  effectif_max: number;
  moyenne_classe: number | null;
}

export default function PageDetailEtablissement() {
  const parametres = useParams<{ id: string }>();
  const router = useRouter();

  const detail = useQuery({
    queryKey: ['etablissement', parametres.id],
    queryFn: () => api.get<DetailEtablissement>(`/etablissements/${parametres.id}/detail`),
  });

  const tableau = useQuery({
    queryKey: ['etablissement-tableau', parametres.id],
    queryFn: () =>
      api.get<TableauBordEtablissement>(`/etablissements/${parametres.id}/tableau-de-bord`),
  });

  const classes = useQuery({
    queryKey: ['etablissement-classes', parametres.id],
    queryFn: () => api.get<ClasseResume[]>(`/etablissements/${parametres.id}/classes`),
  });

  if (detail.isLoading) return <Chargement libelle="Ouverture de la fiche établissement…" />;
  if (detail.isError) return <MessageErreur erreur={detail.error} />;

  const etablissement = detail.data!;
  const indicateurs = tableau.data?.indicateurs;

  return (
    <>
      <EntetePage
        fil={[{ libelle: 'Établissements', href: '/etablissements' }, { libelle: etablissement.nom }]}
        titre={etablissement.nom}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs">{etablissement.code}</span>
            {etablissement.type_libelle ? (
              <Badge ton="info">{etablissement.type_libelle}</Badge>
            ) : null}
            {etablissement.statut_libelle ? (
              <Badge ton="neutre">{etablissement.statut_libelle}</Badge>
            ) : null}
            {etablissement.est_centre_examen ? (
              <Badge ton="succes">Centre d&apos;examen</Badge>
            ) : null}
            {etablissement.zone_rurale ? <Badge ton="neutre">Zone rurale</Badge> : null}
          </span>
        }
      />

      {indicateurs ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Indicateur
            libelle="Effectif"
            valeur={indicateurs.effectif}
            icone={<Users size={18} />}
            pictogramme="🧑‍🎓"
          />
          <Indicateur
            libelle="Part des filles"
            valeur={formaterPourcentage(indicateurs.taux_filles)}
            pictogramme="👧"
          />
          <Indicateur
            libelle="Classes"
            valeur={indicateurs.classes}
            icone={<Building2 size={18} />}
            pictogramme="📚"
          />
          <Indicateur
            libelle="Salles"
            valeur={indicateurs.salles}
            icone={<DoorOpen size={18} />}
            pictogramme="🚪"
          />
          <Indicateur
            libelle="Enseignants"
            valeur={indicateurs.enseignants}
            icone={<UserSquare2 size={18} />}
            pictogramme="👩‍🏫"
          />
          <Indicateur
            libelle="Moyenne"
            valeur={formaterNote(indicateurs.moyenne_etablissement)}
            unite="/ 20"
            pictogramme="📈"
          />
        </div>
      ) : null}

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Carte className="xl:col-span-2">
          <EnteteCarte titre="Identité et localisation" />
          <CorpsCarte>
            <ListeDescriptive
              colonnes={3}
              entrees={[
                { terme: 'Département', valeur: etablissement.departement_libelle ?? '—' },
                { terme: 'Commune', valeur: etablissement.commune_libelle ?? '—' },
                { terme: 'Adresse', valeur: etablissement.adresse ?? '—' },
                { terme: 'Directeur', valeur: etablissement.directeur_nom ?? '—' },
                { terme: 'Téléphone', valeur: etablissement.telephone ?? '—' },
                { terme: 'Courriel', valeur: etablissement.email ?? '—' },
                { terme: 'Année de création', valeur: etablissement.annee_creation ?? '—' },
                {
                  terme: 'Capacité',
                  valeur: `${formaterNombre(etablissement.capacite_accueil)} places`,
                },
                { terme: 'Bâtiments', valeur: etablissement.nombre_batiments },
              ]}
            />
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte titre="Services et accessibilité" />
          <CorpsCarte>
            <ul className="space-y-2 text-sm">
              {[
                { libelle: 'Électricité', valeur: etablissement.electricite },
                { libelle: 'Eau potable', valeur: etablissement.eau_potable },
                { libelle: 'Connexion internet', valeur: etablissement.connexion_internet },
                { libelle: 'Cantine', valeur: etablissement.cantine },
                { libelle: 'Internat', valeur: etablissement.internat },
              ].map((service) => (
                <li key={service.libelle} className="flex items-center justify-between gap-2">
                  <span>{service.libelle}</span>
                  <Badge ton={service.valeur ? 'succes' : 'neutre'}>
                    {service.valeur ? 'Disponible' : 'Non disponible'}
                  </Badge>
                </li>
              ))}
              <li className="flex items-center justify-between gap-2 border-t pt-2">
                <span>Accessibilité</span>
                <Badge
                  ton={
                    etablissement.accessibilite === 'NON_ACCESSIBLE'
                      ? 'danger'
                      : etablissement.accessibilite === 'PARTIELLEMENT'
                        ? 'alerte'
                        : 'succes'
                  }
                >
                  {humaniser(etablissement.accessibilite)}
                </Badge>
              </li>
            </ul>
          </CorpsCarte>
        </Carte>
      </div>

      <Carte className="mt-4">
        <EnteteCarte
          titre="Classes"
          description={`${formaterNombre(classes.data?.length ?? 0)} classe(s) pour l'année en cours.`}
        />
        <Tableau
          legende="Classes de l'établissement"
          lignes={classes.data ?? []}
          cleLigne={(classe) => classe.id}
          onLigneClic={(classe) => router.push(`/classes/${classe.id}`)}
          vide={<EtatVide titre="Aucune classe enregistrée" />}
          colonnes={[
            { cle: 'libelle', entete: 'Classe', rendu: (classe) => <span className="font-medium">{classe.libelle}</span> },
            { cle: 'niveau', entete: 'Niveau', secondaire: true, rendu: (classe) => classe.niveau ?? '—' },
            { cle: 'serie', entete: 'Série', secondaire: true, rendu: (classe) => classe.serie ?? '—' },
            {
              cle: 'effectif',
              entete: 'Effectif',
              alignement: 'droite',
              rendu: (classe) => `${classe.effectif} / ${classe.effectif_max}`,
            },
            {
              cle: 'moyenne',
              entete: 'Moyenne',
              alignement: 'droite',
              rendu: (classe) => formaterNote(classe.moyenne_classe),
            },
          ]}
        />
      </Carte>

      <div className="mt-4">
        <DocumentsEntite
          entiteType="etablissements"
          entiteId={parametres.id}
          titre="Documents de l'établissement"
          description="Arrêté d'ouverture, plan de masse, conventions, rapports d'inspection — conservés avec leur version et leur état de validation."
        />
      </div>
    </>
  );
}
