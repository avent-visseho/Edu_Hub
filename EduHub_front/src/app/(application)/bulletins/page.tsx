'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Selection, tonDuStatut } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { formaterNote, humaniser } from '@/lib/utils';
import type { Bulletin } from '@/types/api';

export default function PageBulletins() {
  const router = useRouter();
  const [publie, setPublie] = useState('');

  const liste = useListe<Bulletin>('/bulletins', {
    tri: 'numero',
    filtres: { publie: publie || undefined },
  });

  return (
    <>
      <EntetePage
        titre="Bulletins"
        description="Bulletins calculés par période, avec moyennes pondérées, rangs et décisions du conseil."
      />

      <ListeRessource
        legende="Liste des bulletins"
        placeholderRecherche="Rechercher par numéro de bulletin…"
        items={liste.items}
        total={liste.total}
        pages={liste.pages}
        page={liste.etat.page}
        taille={liste.etat.taille}
        chargement={liste.isLoading}
        erreur={liste.error}
        recherche={liste.etat.recherche}
        onRecherche={liste.changerRecherche}
        onPage={liste.changerPage}
        cleLigne={(bulletin) => bulletin.id}
        onLigneClic={(bulletin) => router.push(`/bulletins/${bulletin.id}`)}
        videTitre="Aucun bulletin"
        videDescription="Générez les bulletins depuis la fiche d'une classe."
        filtres={
          <Selection
            etiquette="Publication"
            aide="Un bulletin n'est visible par la famille qu'une fois publié."
            value={publie}
            onChange={(evenement) => setPublie(evenement.target.value)}
            options={[
              { valeur: '', libelle: 'Tous les bulletins' },
              { valeur: 'true', libelle: 'Publiés' },
              { valeur: 'false', libelle: 'En attente de publication' },
            ]}
          />
        }
        colonnes={[
          {
            cle: 'numero',
            entete: 'Numéro',
            rendu: (bulletin) => <span className="font-mono text-xs">{bulletin.numero}</span>,
          },
          {
            cle: 'moyenne',
            entete: 'Moyenne générale',
            alignement: 'droite',
            rendu: (bulletin) => (
              <span className="font-semibold">{formaterNote(bulletin.moyenne_generale)}</span>
            ),
          },
          {
            cle: 'rang',
            entete: 'Rang',
            alignement: 'droite',
            rendu: (bulletin) =>
              bulletin.rang ? `${bulletin.rang} / ${bulletin.effectif_classe ?? '—'}` : '—',
          },
          {
            cle: 'mention',
            entete: 'Mention',
            secondaire: true,
            rendu: (bulletin) => bulletin.mention ?? '—',
          },
          {
            cle: 'absences',
            entete: 'Absences',
            alignement: 'droite',
            secondaire: true,
            rendu: (bulletin) => `${bulletin.absences_heures} h`,
          },
          {
            cle: 'decision',
            entete: 'Décision',
            rendu: (bulletin) =>
              bulletin.decision ? (
                <Badge ton={tonDuStatut(bulletin.decision)}>{humaniser(bulletin.decision)}</Badge>
              ) : (
                '—'
              ),
          },
          {
            cle: 'publie',
            entete: 'Publié',
            alignement: 'centre',
            rendu: (bulletin) =>
              bulletin.publie ? <Badge ton="succes">Oui</Badge> : <Badge ton="alerte">Non</Badge>,
          },
        ]}
      />
    </>
  );
}
