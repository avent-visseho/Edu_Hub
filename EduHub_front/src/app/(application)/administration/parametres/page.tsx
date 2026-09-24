'use client';

import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import {
  Badge,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  MessageErreur,
} from '@/components/ui/primitives';
import { api } from '@/lib/api';
import { humaniser } from '@/lib/utils';

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
