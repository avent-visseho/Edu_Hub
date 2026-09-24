'use client';

import { ArrowRight, Lock, Mail } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { BarreAccessibilite } from '@/components/layout/barre-accessibilite';
import { Bouton, Champ } from '@/components/ui/primitives';
import { ErreurApi } from '@/lib/api';
import { useSession } from '@/lib/session';

/** Comptes de démonstration, pour entrer dans la plateforme sans préparation. */
const COMPTES_DEMO = [
  { role: 'Super administrateur', email: 'super.admin@eduhub.bj', pictogramme: '🛡️' },
  { role: 'Ministère (MEMP)', email: 'admin.memp@eduhub.bj', pictogramme: '🏛️' },
  { role: 'Direction des examens', email: 'admin.dec.memp@eduhub.bj', pictogramme: '🎓' },
  { role: 'Direction départementale', email: 'admin.ddeps.atlantique@eduhub.bj', pictogramme: '📍' },
  { role: 'Compte de démonstration', email: 'demo@education.local', pictogramme: '👁️' },
];

const MOT_DE_PASSE_DEMO = 'EduHub2026!';

export default function PageConnexion() {
  const { connexion, connecte, chargement } = useSession();
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [motDePasse, setMotDePasse] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (!chargement && connecte) router.replace('/tableau-de-bord');
  }, [chargement, connecte, router]);

  async function soumettre(evenement: React.FormEvent) {
    evenement.preventDefault();
    setErreur(null);
    setEnvoi(true);
    try {
      await connexion(email, motDePasse);
      router.push('/tableau-de-bord');
    } catch (cause) {
      setErreur(
        cause instanceof ErreurApi
          ? cause.message
          : 'La connexion a échoué. Vérifiez que l’API est démarrée.',
      );
    } finally {
      setEnvoi(false);
    }
  }

  function remplir(adresse: string) {
    setEmail(adresse);
    setMotDePasse(MOT_DE_PASSE_DEMO);
    setErreur(null);
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-2">
      {/* Colonne de présentation */}
      <aside className="hidden flex-col justify-between bg-[rgb(var(--accent))] p-10 text-[rgb(var(--accent-contraste))] lg:flex">
        <Link href="/" className="flex items-center gap-2.5 font-semibold">
          <span
            aria-hidden
            className="grid h-9 w-9 place-items-center rounded-lg bg-white/20 text-sm font-bold"
          >
            EH
          </span>
          <span className="text-lg tracking-tight">EduHub</span>
        </Link>

        <div>
          <h1 className="max-w-md text-3xl font-semibold leading-tight tracking-tight">
            Toute la vie éducative dans un système unique.
          </h1>
          <p className="mt-4 max-w-md opacity-90">
            Scolarité, examens et concours, diplômes vérifiables, vie étudiante, projets, stages
            et gouvernance — reliés de bout en bout.
          </p>
        </div>

        <p className="text-sm opacity-80">
          Prototype de démonstration. Toutes les données sont fictives.
        </p>
      </aside>

      {/* Colonne de connexion */}
      <main className="flex min-h-screen flex-col px-4 py-8 sm:px-8">
        <div className="flex items-center justify-between lg:justify-end">
          <Link href="/" className="flex items-center gap-2 font-semibold lg:hidden">
            <span
              aria-hidden
              className="grid h-8 w-8 place-items-center rounded-lg bg-[rgb(var(--accent))] text-xs font-bold text-[rgb(var(--accent-contraste))]"
            >
              EH
            </span>
            EduHub
          </Link>
          <BarreAccessibilite />
        </div>

        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <h2 className="text-2xl font-semibold tracking-tight">Connexion</h2>
          <p className="mt-1.5 text-sm texte-doux">
            Identifiez-vous avec l&apos;adresse fournie par votre administration.
          </p>

          <form onSubmit={soumettre} className="mt-7 space-y-4" noValidate>
            <Champ
              etiquette="Adresse électronique"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(evenement) => setEmail(evenement.target.value)}
              placeholder="prenom.nom@eduhub.bj"
            />
            <Champ
              etiquette="Mot de passe"
              type="password"
              autoComplete="current-password"
              required
              value={motDePasse}
              onChange={(evenement) => setMotDePasse(evenement.target.value)}
              placeholder="••••••••"
            />

            {erreur ? (
              <p
                role="alert"
                className="rounded-lg border border-[rgb(var(--danger))]/40 bg-[rgb(var(--danger))]/8 px-3 py-2.5 text-sm font-medium text-[rgb(var(--danger))]"
              >
                {erreur}
              </p>
            ) : null}

            <Bouton type="submit" chargement={envoi} taille="lg" className="w-full">
              Se connecter
              <ArrowRight size={18} aria-hidden />
            </Bouton>
          </form>

          <section className="mt-9" aria-labelledby="comptes-demo">
            <h3 id="comptes-demo" className="mb-2 text-sm font-medium texte-doux">
              Comptes de démonstration — mot de passe {MOT_DE_PASSE_DEMO}
            </h3>
            <ul className="space-y-1.5">
              {COMPTES_DEMO.map((compte) => (
                <li key={compte.email}>
                  <button
                    type="button"
                    onClick={() => remplir(compte.email)}
                    className="flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition hover:bg-[rgb(var(--fond-doux))]"
                  >
                    <span aria-hidden className="text-lg">
                      {compte.pictogramme}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium">{compte.role}</span>
                      <span className="block truncate text-xs texte-doux">{compte.email}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <nav className="mt-8 flex flex-wrap gap-4 text-sm" aria-label="Services publics">
            <Link href="/resultats-publics" className="inline-flex items-center gap-1.5 hover:underline">
              <Mail size={15} aria-hidden /> Consulter un résultat
            </Link>
            <Link href="/verification" className="inline-flex items-center gap-1.5 hover:underline">
              <Lock size={15} aria-hidden /> Vérifier un diplôme
            </Link>
          </nav>
        </div>
      </main>
    </div>
  );
}
