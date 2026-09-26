'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Handshake, Headphones, Hand, Undo2 } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import { Badge, Bouton, Selection } from '@/components/ui/primitives';
import { useListe } from '@/hooks/useListe';
import { api, ErreurApi } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterDate, formaterMontant } from '@/lib/utils';
import type { LivreLecture } from '@/types/bibliotheque';

type Onglet = 'catalogue' | 'prets';

interface Pret {
  id: string;
  date_pret: string;
  date_retour_prevue: string;
  date_retour_effective: string | null;
  jours_retard: number;
  penalite: number;
  rendu: boolean;
  ouvrage_titre: string | null;
  ouvrage_auteur: string | null;
  code_barre: string | null;
  emprunteur_nom: string | null;
}

/** Un prêt est en retard dès que la date de retour prévue est dépassée. */
function enRetard(pret: Pret): boolean {
  if (pret.rendu) return pret.jours_retard > 0;
  return new Date(pret.date_retour_prevue) < new Date();
}

export default function PageBibliotheque() {
  const fileAttente = useQueryClient();
  const { peut } = useSession();
  const [onglet, setOnglet] = useState<Onglet>('catalogue');
  const [rendu, setRendu] = useState('false');
  const [journal, setJournal] = useState<string | null>(null);

  const catalogue = useListe<LivreLecture>('/bibliotheque/livres', {
    tri: 'titre',
    active: onglet === 'catalogue',
  });

  const prets = useListe<Pret>('/bibliotheque/prets', {
    tri: 'date_retour_prevue',
    active: onglet === 'prets',
    filtres: { rendu: rendu || undefined },
  });

  const retourner = useMutation({
    mutationFn: (pret: Pret) => api.post<Pret>(`/bibliotheque/prets/${pret.id}/retour`),
    onSuccess: (pret) => {
      setJournal(
        pret.jours_retard > 0
          ? `Retour enregistré avec ${pret.jours_retard} jour(s) de retard — pénalité de ${formaterMontant(pret.penalite)}.`
          : 'Retour enregistré dans les délais.',
      );
      void fileAttente.invalidateQueries({ queryKey: ['/bibliotheque/prets'] });
    },
    onError: (erreurBrute: unknown) => {
      setJournal(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "Le retour n'a pas pu être enregistré.",
      );
    },
  });

  const enCours = prets.items.filter((pret) => !pret.rendu);
  const retards = enCours.filter(enRetard).length;

  return (
    <>
      <EntetePage
        titre="Bibliothèque"
        description="Catalogue des ouvrages, avec leurs formats accessibles — audio, braille, gros caractères — et suivi des prêts."
        personnel={{
          titre: 'Mes emprunts',
          description: 'Vos emprunts en cours et le fonds consultable.',
        }}
      />

      {journal ? (
        <p role="status" className="surface mb-4 rounded-lg border px-4 py-3 text-sm">
          {journal}
        </p>
      ) : null}

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <Indicateur
          libelle="Ouvrages au catalogue"
          valeur={catalogue.total || '—'}
          icone={<BookOpen size={19} aria-hidden />}
          pictogramme="📚"
        />
        <Indicateur
          libelle="Prêts en cours"
          valeur={onglet === 'prets' ? prets.total : '—'}
          icone={<Handshake size={19} aria-hidden />}
          pictogramme="🤝"
        />
        <Indicateur
          libelle="En retard"
          valeur={onglet === 'prets' ? retards : '—'}
          unite={onglet === 'prets' ? 'sur la page affichée' : undefined}
          pictogramme="⏰"
        />
      </div>

      <div
        role="tablist"
        aria-label="Section de la bibliothèque"
        className="mb-4 flex flex-wrap gap-2"
      >
        {(
          [
            { cle: 'catalogue', libelle: 'Catalogue', icone: BookOpen },
            { cle: 'prets', libelle: 'Prêts', icone: Handshake },
          ] as const
        ).map((element) => {
          const Icone = element.icone;
          const actif = onglet === element.cle;
          return (
            <button
              key={element.cle}
              type="button"
              role="tab"
              aria-selected={actif}
              onClick={() => setOnglet(element.cle)}
              className={
                actif
                  ? 'inline-flex items-center gap-2 rounded-lg bg-[rgb(var(--accent))] px-4 py-2 text-sm font-medium text-white'
                  : 'surface inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-[rgb(var(--fond-doux))]'
              }
            >
              <Icone size={17} aria-hidden />
              {element.libelle}
            </button>
          );
        })}
      </div>

      {onglet === 'catalogue' ? (
        <ListeRessource
          legende="Catalogue de la bibliothèque"
          placeholderRecherche="Rechercher par titre, auteur ou ISBN…"
          items={catalogue.items}
          total={catalogue.total}
          pages={catalogue.pages}
          page={catalogue.etat.page}
          taille={catalogue.etat.taille}
          chargement={catalogue.isLoading}
          erreur={catalogue.error}
          recherche={catalogue.etat.recherche}
          onRecherche={catalogue.changerRecherche}
          onPage={catalogue.changerPage}
          cleLigne={(livre) => livre.id}
          videTitre="Aucun ouvrage"
          colonnes={[
            {
              cle: 'titre',
              entete: 'Ouvrage',
              rendu: (livre) => (
                <span className="min-w-0">
                  <span className="block truncate font-medium">{livre.titre}</span>
                  <span className="block truncate text-xs texte-doux">{livre.auteur}</span>
                </span>
              ),
            },
            {
              cle: 'categorie',
              entete: 'Catégorie',
              secondaire: true,
              rendu: (livre) => livre.categorie ?? '—',
            },
            {
              cle: 'edition',
              entete: 'Édition',
              alignement: 'droite',
              secondaire: true,
              rendu: (livre) =>
                [livre.langue, livre.annee_publication].filter(Boolean).join(' · ') || '—',
            },
            {
              cle: 'accessibilite',
              entete: 'Accessibilité',
              rendu: (livre) => (
                <span className="flex flex-wrap gap-1.5">
                  {livre.audio_disponible ? (
                    <Badge ton="info">
                      <Headphones size={13} aria-hidden /> Audio
                    </Badge>
                  ) : null}
                  {livre.braille_disponible ? (
                    <Badge ton="info">
                      <Hand size={13} aria-hidden /> Braille
                    </Badge>
                  ) : null}
                  {livre.format_accessible ? <Badge ton="succes">Gros caractères</Badge> : null}
                  {!livre.format_accessible &&
                  !livre.audio_disponible &&
                  !livre.braille_disponible ? (
                    <span className="texte-doux">—</span>
                  ) : null}
                </span>
              ),
            },
          ]}
        />
      ) : (
        <ListeRessource
          legende="Prêts de la bibliothèque"
          placeholderRecherche="Rechercher un prêt…"
          items={prets.items}
          total={prets.total}
          pages={prets.pages}
          page={prets.etat.page}
          taille={prets.etat.taille}
          chargement={prets.isLoading}
          erreur={prets.error}
          recherche={prets.etat.recherche}
          onRecherche={prets.changerRecherche}
          onPage={prets.changerPage}
          cleLigne={(pret) => pret.id}
          videTitre="Aucun prêt"
          filtres={
            <Selection
              etiquette="État du prêt"
              value={rendu}
              onChange={(evenement) => setRendu(evenement.target.value)}
              options={[
                { valeur: 'false', libelle: 'En cours' },
                { valeur: 'true', libelle: 'Rendus' },
                { valeur: '', libelle: 'Tous les prêts' },
              ]}
            />
          }
          colonnes={[
            {
              cle: 'ouvrage',
              entete: 'Ouvrage',
              rendu: (pret) => (
                <span className="block max-w-[22rem]">
                  <span className="block truncate font-medium">{pret.ouvrage_titre ?? '—'}</span>
                  <span className="block truncate text-xs texte-doux">
                    {pret.ouvrage_auteur ?? ''} · {pret.code_barre ?? ''}
                  </span>
                </span>
              ),
            },
            {
              cle: 'emprunteur',
              entete: 'Emprunteur',
              rendu: (pret) => pret.emprunteur_nom ?? '—',
            },
            {
              cle: 'dates',
              entete: 'Emprunt / retour prévu',
              secondaire: true,
              rendu: (pret) => (
                <span className="min-w-0">
                  <span className="block">{formaterDate(pret.date_pret)}</span>
                  <span className="block text-xs texte-doux">
                    {formaterDate(pret.date_retour_prevue)}
                  </span>
                </span>
              ),
            },
            {
              cle: 'etat',
              entete: 'État',
              rendu: (pret) => (
                <span className="flex flex-wrap gap-1.5">
                  <Badge ton={pret.rendu ? 'succes' : 'neutre'}>
                    {pret.rendu ? 'Rendu' : 'En cours'}
                  </Badge>
                  {enRetard(pret) ? (
                    <Badge ton="danger">
                      {pret.rendu ? `${pret.jours_retard} j de retard` : 'En retard'}
                    </Badge>
                  ) : null}
                  {pret.penalite > 0 ? (
                    <Badge ton="alerte">{formaterMontant(pret.penalite)}</Badge>
                  ) : null}
                </span>
              ),
            },
            {
              cle: 'actions',
              entete: 'Retour',
              alignement: 'droite',
              largeur: '12rem',
              rendu: (pret) =>
                pret.rendu ? (
                  <span className="texte-doux">
                    {pret.date_retour_effective ? formaterDate(pret.date_retour_effective) : '—'}
                  </span>
                ) : (
                  <Bouton
                    taille="sm"
                    variante="secondaire"
                    icone={<Undo2 size={15} aria-hidden />}
                    disabled={!peut('bibliotheque', 'UPDATE') || retourner.isPending}
                    onClick={() => retourner.mutate(pret)}
                  >
                    Enregistrer le retour
                  </Bouton>
                ),
            },
          ]}
        />
      )}
    </>
  );
}
