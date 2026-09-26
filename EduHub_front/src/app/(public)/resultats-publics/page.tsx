'use client';

import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Award, Search, Volume2 } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

import { BarreAccessibilite } from '@/components/layout/barre-accessibilite';
import {
  Badge,
  Bouton,
  Carte,
  Champ,
  CorpsCarte,
  Selection,
  tonDuStatut,
} from '@/components/ui/primitives';
import { ListeDescriptive } from '@/components/ui/donnees';
import { ErreurApi, api } from '@/lib/api';
import { useAccessibilite } from '@/lib/accessibilite';
import { formaterNote, formaterPourcentage, humaniser } from '@/lib/utils';
import type { ResultatPublic } from '@/types/api';

interface SessionPubliee {
  id: string;
  code: string;
  libelle: string;
  examen: string;
  sigle: string | null;
  annee: number;
  nombre_inscrits: number;
  nombre_admis: number;
  taux_reussite: number | null;
}

export default function PageResultatsPublics() {
  const { lectureVocale, lire } = useAccessibilite();
  const [numero, setNumero] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [recherche, setRecherche] = useState<{ numero: string; session: string } | null>(null);

  const sessions = useQuery({
    queryKey: ['sessions-publiques'],
    queryFn: () => api.get<SessionPubliee[]>('/public/sessions', undefined, { publique: true }),
  });

  const resultat = useQuery({
    queryKey: ['resultat-public', recherche],
    enabled: recherche !== null,
    retry: false,
    queryFn: () =>
      api.get<ResultatPublic>(
        '/public/resultats',
        { numero: recherche!.numero, session_id: recherche!.session || undefined },
        { publique: true },
      ),
  });

  function soumettre(evenement: React.FormEvent) {
    evenement.preventDefault();
    if (numero.trim().length < 3) return;
    setRecherche({ numero: numero.trim(), session: sessionId });
  }

  const donnees = resultat.data;
  const admis = donnees?.decision === 'ADMIS';

  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm font-medium hover:underline"
          >
            <ArrowLeft size={17} aria-hidden /> Accueil
          </Link>
          <BarreAccessibilite />
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <h1 className="text-3xl font-semibold tracking-tight">Résultats des examens</h1>
        <p className="mt-2 max-w-2xl texte-doux">
          Saisissez votre numéro de table ou votre numéro de candidat. Seuls les résultats
          officiellement publiés sont consultables.
        </p>

        <Carte className="mt-7">
          <CorpsCarte>
            <form onSubmit={soumettre} className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
              <div className="grid gap-4 sm:grid-cols-2">
                <Champ
                  etiquette="Numéro de table ou de candidat"
                  value={numero}
                  onChange={(evenement) => setNumero(evenement.target.value)}
                  placeholder="BEPC-2026-0000001"
                  required
                  aide="Il figure sur votre convocation."
                />
                <Selection
                  etiquette="Session (facultatif)"
                  value={sessionId}
                  onChange={(evenement) => setSessionId(evenement.target.value)}
                  options={[
                    { valeur: '', libelle: 'Toutes les sessions publiées' },
                    ...(sessions.data ?? []).map((session) => ({
                      valeur: session.id,
                      libelle: session.libelle,
                    })),
                  ]}
                />
              </div>
              <Bouton type="submit" taille="lg" chargement={resultat.isFetching}>
                <Search size={18} aria-hidden /> Rechercher
              </Bouton>
            </form>
          </CorpsCarte>
        </Carte>

        {/* Résultat */}
        {recherche && resultat.isError ? (
          <div
            role="alert"
            className="mt-6 rounded-xl border border-[rgb(var(--alerte))]/40 bg-[rgb(var(--alerte))]/8 px-5 py-4"
          >
            <p className="font-medium">
              {resultat.error instanceof ErreurApi
                ? resultat.error.message
                : 'Aucun résultat ne correspond à ce numéro.'}
            </p>
            <p className="mt-1 text-sm texte-doux">
              Vérifiez le numéro saisi, ou attendez la publication officielle de votre session.
            </p>
          </div>
        ) : null}

        {donnees ? (
          <Carte className="mt-6 animate-apparition">
            <div
              className={`rounded-t-xl px-5 py-4 ${
                admis ? 'bg-[rgb(var(--succes))]/12' : 'bg-[rgb(var(--danger))]/10'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm texte-doux">{donnees.examen}</p>
                  <p className="text-2xl font-semibold tracking-tight">{donnees.nom_complet}</p>
                </div>
                <Badge ton={tonDuStatut(donnees.decision)} className="text-sm">
                  <Award size={15} aria-hidden /> {humaniser(donnees.decision)}
                </Badge>
              </div>
            </div>

            <CorpsCarte>
              <ListeDescriptive
                colonnes={3}
                entrees={[
                  { terme: 'Numéro de candidat', valeur: donnees.numero_candidat },
                  { terme: 'Numéro de table', valeur: donnees.numero_table ?? '—' },
                  { terme: 'Session', valeur: donnees.session },
                  { terme: 'Série', valeur: donnees.serie ?? '—' },
                  { terme: 'Centre de composition', valeur: donnees.centre ?? '—' },
                  {
                    terme: 'Moyenne',
                    valeur: (
                      <span className="text-lg tabular-nums">
                        {formaterNote(donnees.moyenne)} / 20
                      </span>
                    ),
                  },
                  { terme: 'Mention', valeur: donnees.mention ?? '—' },
                  { terme: 'Rang national', valeur: donnees.rang_national ?? '—' },
                  { terme: 'Code de vérification', valeur: donnees.code_verification ?? '—' },
                ]}
              />

              <div className="mt-5 flex flex-wrap gap-2">
                {donnees.code_verification ? (
                  <Link
                    href={`/verification?code=${donnees.code_verification}`}
                    className="inline-flex h-11 items-center rounded-lg border px-4 font-medium hover:bg-[rgb(var(--fond-doux))]"
                  >
                    Vérifier l&apos;authenticité
                  </Link>
                ) : null}
                {lectureVocale ? (
                  <Bouton
                    variante="secondaire"
                    onClick={() =>
                      lire(
                        `${donnees.nom_complet}. ${donnees.examen}. Décision : ${humaniser(
                          donnees.decision,
                        )}. Moyenne : ${formaterNote(donnees.moyenne)} sur 20. ${
                          donnees.mention ? `Mention ${donnees.mention}.` : ''
                        }`,
                      )
                    }
                    icone={<Volume2 size={17} aria-hidden />}
                  >
                    Écouter le résultat
                  </Bouton>
                ) : null}
              </div>
            </CorpsCarte>
          </Carte>
        ) : null}

        {/* Sessions publiées */}
        <section className="mt-12" aria-labelledby="sessions-publiees">
          <h2 id="sessions-publiees" className="text-xl font-semibold tracking-tight">
            Sessions dont les résultats sont publiés
          </h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {(sessions.data ?? []).map((session) => (
              <Carte key={session.id}>
                <CorpsCarte className="p-4">
                  <p className="font-medium">{session.libelle}</p>
                  <dl className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm texte-doux">
                    <div className="flex gap-1.5">
                      <dt>Inscrits</dt>
                      <dd className="font-medium tabular-nums">{session.nombre_inscrits}</dd>
                    </div>
                    <div className="flex gap-1.5">
                      <dt>Admis</dt>
                      <dd className="font-medium tabular-nums">{session.nombre_admis}</dd>
                    </div>
                    <div className="flex gap-1.5">
                      <dt>Réussite</dt>
                      <dd className="font-medium tabular-nums">
                        {formaterPourcentage(session.taux_reussite)}
                      </dd>
                    </div>
                  </dl>
                </CorpsCarte>
              </Carte>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
