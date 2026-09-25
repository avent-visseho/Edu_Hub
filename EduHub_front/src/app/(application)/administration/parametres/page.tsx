'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CalendarCheck } from 'lucide-react';
import { useMemo, useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
} from '@/components/ui/primitives';
import { api, ErreurApi, type Page } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterDate, humaniser } from '@/lib/utils';

interface AnneeAcademique {
  id: string;
  code: string;
  libelle: string;
  date_debut: string;
  date_fin: string;
  courante: boolean;
  cloturee: boolean;
}

interface Parametre {
  cle: string;
  libelle: string;
  valeur: string;
  type: string;
  categorie: string;
  modifiable: boolean;
  description: string | null;
}

export default function PageParametres() {
  const fileAttente = useQueryClient();
  const { peut } = useSession();
  const [journal, setJournal] = useState<string | null>(null);

  const annees = useQuery({
    queryKey: ['annees'],
    queryFn: () => api.get<Page<AnneeAcademique>>('/annees', { size: 20, sort_by: 'code' }),
  });

  const definirCourante = useMutation({
    mutationFn: (annee: AnneeAcademique) =>
      api.post<{ message: string }>(`/annees/${annee.id}/definir-courante`),
    onSuccess: (reponse) => {
      setJournal(reponse.message);
      void fileAttente.invalidateQueries({ queryKey: ['annees'] });
      void fileAttente.invalidateQueries({ queryKey: ['annee-courante'] });
    },
    onError: (erreurBrute: unknown) => {
      setJournal(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "L'année courante n'a pas pu être changée.",
      );
    },
  });

  const parametres = useQuery({
    queryKey: ['parametres-systeme'],
    queryFn: () => api.get<Parametre[]>('/parametres'),
  });

  const categories = useMemo(() => {
    const groupes = new Map<string, Parametre[]>();
    for (const parametre of parametres.data ?? []) {
      const liste = groupes.get(parametre.categorie) ?? [];
      liste.push(parametre);
      groupes.set(parametre.categorie, liste);
    }
    return Array.from(groupes.entries());
  }, [parametres.data]);

  if (parametres.isLoading) return <Chargement libelle="Chargement des paramètres…" />;
  if (parametres.isError) return <MessageErreur erreur={parametres.error} />;

  return (
    <>
      <EntetePage
        titre="Paramètres du système"
        description="Règles de calcul, seuils d'alerte et options d'accessibilité applicables à l'ensemble de la plateforme."
      />

      {journal ? (
        <p role="status" className="surface mb-4 rounded-lg border px-4 py-3 text-sm">
          {journal}
        </p>
      ) : null}

      <Carte className="mb-4">
        <EnteteCarte
          titre={
            <span className="flex items-center gap-2">
              <CalendarCheck size={19} aria-hidden /> Années académiques
            </span>
          }
          description="L'année courante sert de référence par défaut aux inscriptions, aux bulletins et aux tableaux de bord."
        />
        <Tableau
          legende="Années académiques et année de référence"
          lignes={annees.data?.items ?? []}
          cleLigne={(annee) => annee.id}
          vide={<EtatVide titre="Aucune année académique" />}
          colonnes={[
            {
              cle: 'libelle',
              entete: 'Année',
              rendu: (annee) => (
                <span className="min-w-0">
                  <span className="block font-medium">{annee.libelle}</span>
                  <span className="block font-mono text-xs texte-doux">{annee.code}</span>
                </span>
              ),
            },
            {
              cle: 'periode',
              entete: 'Du … au',
              secondaire: true,
              rendu: (annee) =>
                `${formaterDate(annee.date_debut)} → ${formaterDate(annee.date_fin)}`,
            },
            {
              cle: 'etat',
              entete: 'État',
              rendu: (annee) => (
                <span className="flex flex-wrap gap-1.5">
                  {annee.courante ? <Badge ton="succes">Année courante</Badge> : null}
                  {annee.cloturee ? <Badge ton="neutre">Clôturée</Badge> : null}
                  {!annee.courante && !annee.cloturee ? (
                    <span className="texte-doux">Ouverte</span>
                  ) : null}
                </span>
              ),
            },
            {
              cle: 'action',
              entete: 'Référence',
              alignement: 'droite',
              rendu: (annee) =>
                annee.courante ? (
                  <span className="texte-doux">Année de référence</span>
                ) : (
                  <Bouton
                    taille="sm"
                    variante="secondaire"
                    disabled={!peut('referentiels', 'UPDATE') || definirCourante.isPending}
                    onClick={() => definirCourante.mutate(annee)}
                  >
                    Définir comme courante
                  </Bouton>
                ),
            },
          ]}
        />
      </Carte>

      <div className="grid gap-4 md:grid-cols-2">
        {categories.map(([categorie, liste]) => (
          <Carte key={categorie}>
            <EnteteCarte titre={humaniser(categorie)} />
            <CorpsCarte>
              <dl className="space-y-3">
                {liste.map((parametre) => (
                  <div key={parametre.cle} className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <dt className="font-medium">{parametre.libelle}</dt>
                      <dd className="font-mono text-xs texte-doux">{parametre.cle}</dd>
                    </div>
                    <dd className="shrink-0">
                      <Badge ton={parametre.modifiable ? 'info' : 'neutre'}>
                        {parametre.valeur}
                      </Badge>
                    </dd>
                  </div>
                ))}
              </dl>
            </CorpsCarte>
          </Carte>
        ))}
      </div>
    </>
  );
}
