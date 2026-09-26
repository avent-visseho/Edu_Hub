'use client';

import { useQuery } from '@tanstack/react-query';
import { BadgeCheck, ShieldAlert, ShieldCheck } from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';

import { EntetePublique } from '@/components/layout/entete-publique';
import { ListeDescriptive } from '@/components/ui/donnees';
import { Bouton, Carte, Champ, CorpsCarte } from '@/components/ui/primitives';
import { api } from '@/lib/api';
import { formaterDate, humaniser } from '@/lib/utils';
import type { VerificationDocument } from '@/types/api';

function Verificateur() {
  const parametres = useSearchParams();
  const [code, setCode] = useState('');
  const [recherche, setRecherche] = useState<string | null>(null);

  // Un QR code amène directement sur la page avec son code.
  useEffect(() => {
    const initial = parametres.get('code');
    if (initial) {
      setCode(initial);
      setRecherche(initial);
    }
  }, [parametres]);

  const verification = useQuery({
    queryKey: ['verification', recherche],
    enabled: recherche !== null,
    retry: false,
    queryFn: () =>
      api.get<VerificationDocument>(`/public/verification/${recherche}`, undefined, {
        publique: true,
      }),
  });

  const resultat = verification.data;

  return (
    <>
      <h1 className="text-3xl font-semibold tracking-tight">Vérifier un document</h1>
      <p className="mt-2 max-w-2xl texte-doux">
        Saisissez le code figurant sur le diplôme, l&apos;attestation, le relevé de notes ou le
        bulletin — ou scannez son QR code.
      </p>

      <Carte className="mt-7">
        <CorpsCarte>
          <form
            onSubmit={(evenement) => {
              evenement.preventDefault();
              if (code.trim().length >= 6) setRecherche(code.trim().toUpperCase());
            }}
            className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end"
          >
            <Champ
              etiquette="Code de vérification"
              value={code}
              onChange={(evenement) => setCode(evenement.target.value.toUpperCase())}
              placeholder="A1B2C3D4E5F6G7H8"
              required
              aide="Seize caractères, imprimés sous le QR code."
              className="font-mono tracking-wider"
            />
            <Bouton type="submit" taille="lg" chargement={verification.isFetching}>
              <ShieldCheck size={18} aria-hidden /> Vérifier
            </Bouton>
          </form>
        </CorpsCarte>
      </Carte>

      {resultat ? (
        <Carte className="mt-6 animate-apparition">
          <div
            className={`flex items-center gap-3 rounded-t-xl px-5 py-4 ${
              resultat.valide ? 'bg-[rgb(var(--succes))]/12' : 'bg-[rgb(var(--danger))]/10'
            }`}
          >
            {resultat.valide ? (
              <BadgeCheck size={28} aria-hidden className="text-[rgb(var(--succes))]" />
            ) : (
              <ShieldAlert size={28} aria-hidden className="text-[rgb(var(--danger))]" />
            )}
            <div>
              <p className="text-lg font-semibold">{resultat.message}</p>
              {resultat.type_document ? (
                <p className="text-sm texte-doux">{humaniser(resultat.type_document)}</p>
              ) : null}
            </div>
          </div>

          {resultat.valide ? (
            <CorpsCarte>
              <ListeDescriptive
                colonnes={2}
                entrees={[
                  { terme: 'Numéro', valeur: resultat.numero ?? '—' },
                  { terme: 'Titulaire', valeur: resultat.titulaire ?? '—' },
                  { terme: 'Intitulé', valeur: resultat.intitule ?? '—' },
                  { terme: 'Session', valeur: resultat.session ?? '—' },
                  { terme: 'Année', valeur: resultat.annee ?? '—' },
                  { terme: 'Mention', valeur: resultat.mention ?? '—' },
                  {
                    terme: 'Date de délivrance',
                    valeur: formaterDate(resultat.date_delivrance),
                  },
                ]}
              />
              {resultat.type_document === 'DIPLOME' ? (
                <div className="mt-5">
                  <Bouton
                    variante="secondaire"
                    onClick={() => void api.ouvrir(`/public/diplomes/${recherche}/pdf`)}
                  >
                    Afficher le diplôme
                  </Bouton>
                </div>
              ) : null}
            </CorpsCarte>
          ) : null}
        </Carte>
      ) : null}
    </>
  );
}

export default function PageVerification() {
  return (
    <div className="min-h-screen">
      <EntetePublique />

      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <Suspense fallback={<p className="texte-doux">Chargement…</p>}>
          <Verificateur />
        </Suspense>
      </main>
    </div>
  );
}
