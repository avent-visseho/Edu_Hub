'use client';

import { useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  Download,
  Headphones,
  MonitorPlay,
  Signal,
  Subtitles,
} from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur, Jauge } from '@/components/ui/donnees';
import { ListeRessource } from '@/components/ui/liste';
import {
  Badge,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
} from '@/components/ui/primitives';
import {
  SelecteurApprenant,
  type ApprenantChoisi,
} from '@/components/ui/selecteur-apprenant';
import { useListe } from '@/hooks/useListe';
import { api } from '@/lib/api';
import { formaterNombre, formaterNote, humaniser } from '@/lib/utils';

interface Progression {
  lecons_terminees: number;
  lecons_totales: number;
  pourcentage: number;
  temps_passe_minutes: number;
  termine: boolean;
  note_finale: number | null;
  certificat_delivre: boolean;
}

interface Cours {
  id: string;
  code: string;
  titre: string;
  description: string | null;
  langue: string;
  duree_heures: number;
  statut: string;
  disponible_hors_ligne: boolean;
  transcription_disponible: boolean;
  sous_titres_disponibles: boolean;
  version_audio: boolean;
  nombre_inscrits: number;
  note_moyenne: number | null;
}

interface Ressource {
  id: string;
  code: string;
  titre: string;
  type_ressource: string;
  taille_ko: number;
  langue: string;
  licence: string | null;
  mots_cles: string | null;
  nombre_vues: number;
  nombre_telechargements: number;
  poids_leger: boolean;
}

interface PlanCours {
  cours: {
    id: string;
    titre: string;
    duree_heures: number;
    accessibilite: {
      version_audio: boolean;
      transcription: boolean;
      sous_titres: boolean;
      hors_ligne: boolean;
    };
  };
  modules: Array<{
    id: string;
    titre: string;
    ordre: number;
    duree_minutes: number;
    lecons: Array<{
      id: string;
      titre: string;
      ordre: number;
      duree_minutes: number;
      audio_url: string | null;
      contenu_simplifie: string | null;
      ressources: Array<{ id: string; titre: string; type: string; taille_ko: number }>;
    }>;
  }>;
}

export default function PageApprentissage() {
  const [onglet, setOnglet] = useState<'cours' | 'ressources'>('cours');
  const [coursId, setCoursId] = useState<string | null>(null);
  const [apprenant, setApprenant] = useState<ApprenantChoisi | null>(null);

  const cours = useListe<Cours>('/cours', { tri: 'titre', active: onglet === 'cours' });
  const ressources = useListe<Ressource>('/ressources', {
    tri: 'titre',
    active: onglet === 'ressources',
  });

  const plan = useQuery({
    queryKey: ['plan-cours', coursId],
    enabled: Boolean(coursId),
    queryFn: () => api.get<PlanCours>(`/cours/${coursId}/plan`),
  });

  const progression = useQuery({
    queryKey: ['progression-cours', coursId, apprenant?.id],
    enabled: Boolean(coursId) && Boolean(apprenant),
    queryFn: () =>
      api.get<Progression>(`/cours/${coursId}/progression/${apprenant!.id}`),
  });

  const accessibles = cours.items.filter((element) => element.version_audio).length;
  const horsLigne = cours.items.filter((element) => element.disponible_hors_ligne).length;

  return (
    <>
      <EntetePage
        titre="Cours et ressources pédagogiques"
        description="Cours structurés en modules et leçons, avec versions audio, transcriptions et disponibilité hors connexion."
      />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicateur
          libelle="Cours publiés"
          valeur={cours.total}
          icone={<MonitorPlay size={18} />}
          pictogramme="💻"
        />
        <Indicateur
          libelle="Ressources"
          valeur={ressources.total}
          icone={<BookOpen size={18} />}
          pictogramme="📚"
        />
        <Indicateur
          libelle="Avec version audio"
          valeur={accessibles}
          icone={<Headphones size={18} />}
          pictogramme="🎧"
        />
        <Indicateur
          libelle="Disponibles hors ligne"
          valeur={horsLigne}
          icone={<Signal size={18} />}
          pictogramme="📶"
        />
      </div>

      <div role="tablist" aria-label="Section" className="mb-4 inline-flex rounded-lg border p-1">
        {(
          [
            { cle: 'cours', libelle: 'Cours en ligne' },
            { cle: 'ressources', libelle: 'Ressources' },
          ] as const
        ).map((element) => (
          <button
            key={element.cle}
            type="button"
            role="tab"
            aria-selected={onglet === element.cle}
            onClick={() => setOnglet(element.cle)}
            className={`h-10 rounded px-4 text-sm font-medium transition ${
              onglet === element.cle
                ? 'bg-[rgb(var(--accent))] text-[rgb(var(--accent-contraste))]'
                : 'hover:bg-[rgb(var(--fond-doux))]'
            }`}
          >
            {element.libelle}
          </button>
        ))}
      </div>

      {onglet === 'cours' ? (
        <div className="space-y-4">
          <ListeRessource
            legende="Catalogue des cours en ligne"
            placeholderRecherche="Rechercher un cours…"
            items={cours.items}
            total={cours.total}
            pages={cours.pages}
            page={cours.etat.page}
            taille={cours.etat.taille}
            chargement={cours.isLoading}
            erreur={cours.error}
            recherche={cours.etat.recherche}
            onRecherche={cours.changerRecherche}
            onPage={cours.changerPage}
            cleLigne={(element) => element.id}
            onLigneClic={(element) => setCoursId(element.id)}
            videTitre="Aucun cours"
            colonnes={[
              {
                cle: 'titre',
                entete: 'Cours',
                rendu: (element) => (
                  <div className="min-w-0">
                    <p className="font-medium">{element.titre}</p>
                    {element.description ? (
                      <p className="truncate text-xs texte-doux">{element.description}</p>
                    ) : null}
                  </div>
                ),
              },
              {
                cle: 'duree',
                entete: 'Durée',
                alignement: 'centre',
                secondaire: true,
                rendu: (element) => `${element.duree_heures} h`,
              },
              {
                cle: 'inscrits',
                entete: 'Inscrits',
                alignement: 'droite',
                secondaire: true,
                rendu: (element) => formaterNombre(element.nombre_inscrits),
              },
              {
                cle: 'accessibilite',
                entete: 'Accessibilité',
                rendu: (element) => (
                  <span className="flex flex-wrap gap-1.5">
                    {element.version_audio ? (
                      <Badge ton="succes">
                        <Headphones size={13} aria-hidden /> Audio
                      </Badge>
                    ) : null}
                    {element.sous_titres_disponibles ? (
                      <Badge ton="info">
                        <Subtitles size={13} aria-hidden /> Sous-titres
                      </Badge>
                    ) : null}
                    {element.disponible_hors_ligne ? (
                      <Badge ton="neutre">
                        <Signal size={13} aria-hidden /> Hors ligne
                      </Badge>
                    ) : null}
                  </span>
                ),
              },
            ]}
          />

          {coursId ? (
            plan.isError ? (
              <MessageErreur erreur={plan.error} />
            ) : plan.data ? (
              <Carte>
                <EnteteCarte
                  titre={plan.data.cours.titre}
                  description={`${plan.data.modules.length} module(s) · ${plan.data.cours.duree_heures} heures`}
                  action={
                    <button
                      type="button"
                      onClick={() => setCoursId(null)}
                      className="text-sm font-medium hover:underline"
                    >
                      Fermer
                    </button>
                  }
                />
                <CorpsCarte className="space-y-5">
                  {plan.data.modules.map((module) => (
                    <section key={module.id}>
                      <h3 className="mb-2 flex items-center gap-2 font-semibold">
                        <span
                          aria-hidden
                          className="grid h-6 w-6 place-items-center rounded surface-douce text-xs"
                        >
                          {module.ordre}
                        </span>
                        {module.titre}
                        <span className="text-sm font-normal texte-doux">
                          {module.duree_minutes} min
                        </span>
                      </h3>
                      <ol className="space-y-1.5 border-l pl-5">
                        {module.lecons.map((lecon) => (
                          <li key={lecon.id} className="text-sm">
                            <span className="flex flex-wrap items-center gap-2">
                              <span className="font-medium">{lecon.titre}</span>
                              <span className="texte-doux">{lecon.duree_minutes} min</span>
                              {lecon.audio_url ? (
                                <Badge ton="succes">
                                  <Headphones size={12} aria-hidden /> Audio
                                </Badge>
                              ) : null}
                              {lecon.ressources.length > 0 ? (
                                <Badge ton="neutre">
                                  {lecon.ressources.length} ressource(s)
                                </Badge>
                              ) : null}
                            </span>
                            {lecon.contenu_simplifie ? (
                              <p className="mt-0.5 texte-doux">{lecon.contenu_simplifie}</p>
                            ) : null}
                          </li>
                        ))}
                      </ol>
                    </section>
                  ))}
                </CorpsCarte>
              </Carte>
            ) : (
              <Carte>
                <EtatVide titre="Chargement du plan de cours…" />
              </Carte>
            )
          ) : null}
        </div>
      ) : (
        <ListeRessource
          legende="Ressources pédagogiques"
          placeholderRecherche="Rechercher une ressource, un mot-clé…"
          items={ressources.items}
          total={ressources.total}
          pages={ressources.pages}
          page={ressources.etat.page}
          taille={ressources.etat.taille}
          chargement={ressources.isLoading}
          erreur={ressources.error}
          recherche={ressources.etat.recherche}
          onRecherche={ressources.changerRecherche}
          onPage={ressources.changerPage}
          cleLigne={(ressource) => ressource.id}
          videTitre="Aucune ressource"
          colonnes={[
            {
              cle: 'titre',
              entete: 'Ressource',
              rendu: (ressource) => (
                <div className="min-w-0">
                  <p className="font-medium">{ressource.titre}</p>
                  {ressource.mots_cles ? (
                    <p className="truncate text-xs texte-doux">{ressource.mots_cles}</p>
                  ) : null}
                </div>
              ),
            },
            {
              cle: 'type',
              entete: 'Type',
              rendu: (ressource) => (
                <Badge ton="neutre">{humaniser(ressource.type_ressource)}</Badge>
              ),
            },
            {
              cle: 'taille',
              entete: 'Taille',
              alignement: 'droite',
              secondaire: true,
              rendu: (ressource) => `${formaterNombre(ressource.taille_ko)} Ko`,
            },
            {
              cle: 'vues',
              entete: 'Vues',
              alignement: 'droite',
              secondaire: true,
              rendu: (ressource) => formaterNombre(ressource.nombre_vues),
            },
            {
              cle: 'telechargements',
              entete: 'Téléchargements',
              alignement: 'droite',
              secondaire: true,
              rendu: (ressource) => (
                <span className="inline-flex items-center gap-1.5">
                  <Download size={14} aria-hidden />
                  {formaterNombre(ressource.nombre_telechargements)}
                </span>
              ),
            },
            {
              cle: 'leger',
              entete: 'Connexion faible',
              alignement: 'centre',
              rendu: (ressource) =>
                ressource.poids_leger ? (
                  <Badge ton="succes">Adapté</Badge>
                ) : (
                  <span className="texte-doux">—</span>
                ),
            },
          ]}
        />
      )}

      {coursId && onglet === 'cours' ? (
        <Carte className="mt-4">
          <EnteteCarte
            titre="Suivi d'un apprenant sur ce cours"
            description="Leçons terminées, temps passé et certificat, pour l'apprenant désigné."
          />
          <CorpsCarte className="grid gap-4 xl:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
            <SelecteurApprenant
              etiquette="Apprenant suivi"
              choisi={apprenant}
              onChoisir={setApprenant}
            />
            {!apprenant ? (
              <p className="self-center text-sm texte-doux">
                Choisissez un apprenant pour afficher sa progression.
              </p>
            ) : progression.isLoading ? (
              <Chargement libelle="Chargement de la progression…" />
            ) : progression.data ? (
              <div className="space-y-3">
                <Jauge
                  valeur={progression.data.pourcentage}
                  etiquette={`${progression.data.lecons_terminees} / ${progression.data.lecons_totales} leçon(s)`}
                  ton={progression.data.termine ? 'succes' : 'accent'}
                />
                <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
                  {[
                    {
                      terme: 'Temps passé',
                      valeur: `${formaterNombre(progression.data.temps_passe_minutes)} min`,
                    },
                    {
                      terme: 'Note finale',
                      valeur:
                        progression.data.note_finale != null
                          ? formaterNote(progression.data.note_finale)
                          : '—',
                    },
                    {
                      terme: 'Cours terminé',
                      valeur: progression.data.termine ? 'Oui' : 'Non',
                    },
                    {
                      terme: 'Certificat',
                      valeur: progression.data.certificat_delivre ? 'Délivré' : 'Non délivré',
                    },
                  ].map((entree) => (
                    <div key={entree.terme} className="min-w-0">
                      <dt className="text-xs font-medium uppercase tracking-wide texte-doux">
                        {entree.terme}
                      </dt>
                      <dd className="mt-0.5 font-medium">{entree.valeur}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ) : null}
          </CorpsCarte>
        </Carte>
      ) : null}
    </>
  );
}
