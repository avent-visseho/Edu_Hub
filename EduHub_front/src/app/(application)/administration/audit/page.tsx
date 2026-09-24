'use client';

import { useQuery } from '@tanstack/react-query';

import { EntetePage } from '@/components/layout/entete-page';
import { Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Carte,
  Chargement,
  EnteteCarte,
  EtatVide,
  MessageErreur,
} from '@/components/ui/primitives';
import { api } from '@/lib/api';
import { formaterDateHeure, humaniser } from '@/lib/utils';

interface EntreeAudit {
  id: string;
  date: string;
  utilisateur: string | null;
  action: string;
  entite_type: string;
  entite_id: string | null;
  entite_libelle: string | null;
  adresse_ip: string | null;
  succes: boolean;
}

export default function PageAudit() {
  const journal = useQuery({
    queryKey: ['journal-audit'],
    queryFn: () => api.get<EntreeAudit[]>('/audit', { limite: 200 }),
  });

  if (journal.isLoading) return <Chargement libelle="Lecture du journal d'audit…" />;
  if (journal.isError) return <MessageErreur erreur={journal.error} />;

  return (
    <>
      <EntetePage
        titre="Journal d'audit"
        description="Trace horodatée des opérations sensibles : qui a fait quoi, sur quel objet, depuis quelle adresse."
      />

      <Carte>
        <EnteteCarte
          titre={`${journal.data?.length ?? 0} opération(s) récente(s)`}
          description="Les deux cents dernières entrées, de la plus récente à la plus ancienne."
        />
        <Tableau
          legende="Journal d'audit des opérations"
          lignes={journal.data ?? []}
          cleLigne={(entree) => entree.id}
          vide={<EtatVide titre="Aucune opération enregistrée" />}
          colonnes={[
            {
              cle: 'date',
              entete: 'Horodatage',
              rendu: (entree) => (
                <span className="tabular-nums">{formaterDateHeure(entree.date)}</span>
              ),
            },
            {
              cle: 'utilisateur',
              entete: 'Utilisateur',
              rendu: (entree) => entree.utilisateur ?? '—',
            },
            {
              cle: 'action',
              entete: 'Action',
              rendu: (entree) => <Badge ton="info">{humaniser(entree.action)}</Badge>,
            },
            {
              cle: 'entite',
              entete: 'Objet',
              rendu: (entree) => (
                <div className="min-w-0">
                  <p className="font-medium">{humaniser(entree.entite_type)}</p>
                  {entree.entite_libelle ? (
                    <p className="truncate text-xs texte-doux">{entree.entite_libelle}</p>
                  ) : null}
                </div>
              ),
            },
            {
              cle: 'ip',
              entete: 'Adresse',
              secondaire: true,
              rendu: (entree) => (
                <span className="font-mono text-xs">{entree.adresse_ip ?? '—'}</span>
              ),
            },
            {
              cle: 'succes',
              entete: 'Issue',
              alignement: 'centre',
              rendu: (entree) => (
                <Badge ton={entree.succes ? 'succes' : 'danger'}>
                  {entree.succes ? 'Succès' : 'Échec'}
                </Badge>
              ),
            },
          ]}
        />
      </Carte>
    </>
  );
}
