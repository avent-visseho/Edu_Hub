'use client';

import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Lock, Mail } from 'lucide-react';
import Image from 'next/image';
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
    queryFn: () =>
      api.get<OptionsAccessibilite>('/public/accessibilite', undefined, {
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
      {/*
        Colonne de présentation : la photographie d'un établissement béninois.
        Le cadrage décale l'image vers la droite pour que l'élève reste dans la
        moitié claire, et le voile dégradé va de gauche (dense, sous le texte) à
        droite (léger, sur la photo). Le voile n'est pas un effet de style —
        sans lui, le contraste du texte tombe sous le seuil d'accessibilité sur
        les zones claires du ciel.
      */}
      <aside className="relative hidden flex-col justify-between overflow-hidden p-10 text-white lg:flex">
        <Image
          src="/images/image_banner.jpeg"
          alt=""
          aria-hidden
          fill
          sizes="50vw"
          className="object-cover object-[58%_38%]"
          priority
        />
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-r from-[rgb(var(--marque-bleu))]/95 via-[rgb(var(--marque-bleu))]/70 to-[rgb(var(--marque-bleu-vif))]/25"
        />
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-t from-[rgb(var(--marque-bleu))]/92 via-[rgb(var(--marque-bleu))]/35 to-[rgb(var(--marque-bleu))]/55"
        />

        <Link href="/" className="relative flex items-center gap-3 font-semibold">
          <span className="grid h-12 w-12 place-items-center rounded-xl bg-white/95 p-1.5">
            <Image
              src="/images/logo-embleme.png"
              alt=""
              aria-hidden
              width={40}
              height={40}
              className="h-full w-full object-contain"
            />
          </span>
          <span className="flex flex-col leading-tight">
            <span className="text-xl tracking-tight">EduHub</span>
            <span className="text-xs font-normal opacity-85">
              L&apos;éducation au service d&apos;un meilleur Bénin
            </span>
          </span>
        </Link>

        <div className="relative">
          <h1 className="max-w-md text-4xl font-semibold leading-tight tracking-tight">
            Ensemble pour une éducation de qualité au Bénin.
          </h1>
          <p className="mt-4 max-w-md text-white/90">
            Scolarité, examens et concours, diplômes vérifiables, vie étudiante, projets, stages et
            gouvernance — reliés de bout en bout.
          </p>
          <ul className="mt-7 flex flex-wrap gap-2">
            {['Apprendre', 'Enseigner', 'Réussir', "Construire l'avenir"].map((mot) => (
              <li
                key={mot}
                className="rounded-full bg-white/15 px-3.5 py-1.5 text-sm backdrop-blur-sm"
              >
                {mot}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-sm text-white/80">
          Prototype de démonstration. Toutes les données sont fictives.
        </p>
      </aside>

      {/* Colonne de connexion */}
      <main className="flex min-h-screen flex-col px-4 py-8 sm:px-8">
        <div className="flex items-center justify-between lg:justify-end">
          <Link href="/" className="flex items-center gap-2 font-semibold lg:hidden">
            <Image
              src="/images/logo-embleme.png"
              alt=""
              aria-hidden
              width={32}
              height={32}
              className="h-8 w-8 object-contain"
            />
            <span className="titre-marque tracking-tight">
              Edu<span className="accentue">Hub</span>
            </span>
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
                  <li key={option.cle} className="surface-douce rounded-full px-3 py-1 text-xs">
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
            <Link
              href="/resultats-publics"
              className="inline-flex items-center gap-1.5 hover:underline"
            >
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
