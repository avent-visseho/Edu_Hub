'use client';

import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Lock, Mail } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { BarreAccessibilite } from '@/components/layout/barre-accessibilite';
import { Bouton, Champ } from '@/components/ui/primitives';
import { api, ErreurApi } from '@/lib/api';
import { useSession } from '@/lib/session';

/** Comptes de démonstration, pour entrer dans la plateforme sans préparation. */
/**
 * Comptes proposés, du sommet de la chaîne jusqu'à la salle de classe. Les
 * quatre derniers ne sont pas des comptes créés pour la vitrine : ce sont de
 * vrais comptes du jeu de données — l'élève est inscrit dans sa classe,
 * l'enseignant garde ses matières, le parent ses enfants — auxquels le
 * générateur donne une adresse mémorable.
 */
const COMPTES_DEMO = [
  { role: 'Super administrateur', email: 'super.admin@eduhub.bj' },
  { role: 'Ministère (MEMP)', email: 'admin.memp@eduhub.bj' },
  { role: 'Direction des examens', email: 'admin.dec.memp@eduhub.bj' },
  { role: 'Direction départementale', email: 'admin.ddeps.atlantique@eduhub.bj' },
  { role: "Chef d'établissement", email: 'directeur@eduhub.bj' },
  { role: 'Enseignant', email: 'enseignant@eduhub.bj' },
  { role: 'Élève', email: 'eleve@eduhub.bj' },
  { role: "Parent d'élève", email: 'parent@eduhub.bj' },
  { role: 'Compte de démonstration', email: 'demo@education.local' },
];

const MOT_DE_PASSE_DEMO = 'EduHub2026!';

interface OptionsAccessibilite {
  affichage: Array<{ cle: string; libelle: string }>;
  audio: Array<{ cle: string; libelle: string }>;
  navigation: Array<{ cle: string; libelle: string }>;
  langues: string[];
}

export default function PageConnexion() {
  const { connexion, connecte, chargement } = useSession();
  const router = useRouter();

  // Point d'entrée public : ce que le service offre en matière d'accessibilité
  // se lit avant même d'avoir un compte.
  const accessibilite = useQuery({
    queryKey: ['options-accessibilite'],
    queryFn: () => api.get<OptionsAccessibilite>('/public/accessibilite', undefined, {
      publique: true,
    }),
  });

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

            <Bouton type="submit" chargement={envoi} taille="lg" className="h-14 w-full text-lg">
              Se connecter
              <ArrowRight size={18} aria-hidden />
            </Bouton>
          </form>

          <section className="mt-9" aria-labelledby="comptes-demo">
            <h3 id="comptes-demo" className="mb-2 text-sm font-medium texte-doux">
              Comptes de démonstration — mot de passe {MOT_DE_PASSE_DEMO}
            </h3>
            {/*
              Disposition en ligne qui repasse d'elle-même : neuf comptes
              empilés poussaient le reste de la page hors de l'écran. Chaque
              bouton garde une largeur minimale pour que l'adresse reste
              lisible, et s'étire pour remplir sa ligne.
            */}
            <ul className="flex flex-wrap gap-2">
              {COMPTES_DEMO.map((compte) => (
                <li key={compte.email} className="min-w-[13.5rem] flex-1">
                  <button
                    type="button"
                    onClick={() => remplir(compte.email)}
                    className="flex h-full w-full items-center gap-2.5 rounded-lg border px-3 py-2 text-left transition hover:bg-[rgb(var(--fond-doux))]"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium">{compte.role}</span>
                      <span className="block truncate text-xs texte-doux">{compte.email}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>

          {accessibilite.data ? (
            <section className="mt-8" aria-labelledby="accessibilite-offerte">
              <h2 id="accessibilite-offerte" className="mb-2 text-sm font-semibold">
                Accessibilité du service
              </h2>
              <p className="mb-2 text-sm texte-doux">
                Ces réglages sont disponibles sans compte, depuis le bouton
                «&nbsp;Accessibilité&nbsp;» de l&apos;en-tête.
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {[
                  ...accessibilite.data.affichage,
                  ...accessibilite.data.audio,
                  ...accessibilite.data.navigation,
                ].map((option) => (
                  <li
                    key={option.cle}
                    className="surface-douce rounded-full px-3 py-1 text-xs"
                  >
                    {option.libelle}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs texte-doux">
                Langues prises en charge : {accessibilite.data.langues.join(', ')}.
              </p>
            </section>
          ) : null}

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
