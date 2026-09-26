import {
  Accessibility,
  ArrowRight,
  Award,
  BarChart3,
  Bus,
  GraduationCap,
  Search,
  ShieldCheck,
  Users,
} from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';

import { ChiffresCles } from '@/components/accueil/chiffres-cles';

/**
 * Les six domaines fonctionnels. La teinte n'est pas décorative : elle range
 * les domaines par famille et se retrouve ensuite dans la navigation de
 * l'application, ce qui fait de l'accueil une première carte du service.
 */
const DOMAINES = [
  {
    titre: 'Scolarité',
    description:
      "De l'inscription au bulletin : classes, emploi du temps, présences, notes, moyennes, " +
      'rangs et conseils de classe.',
    icone: Users,
    teinte: 'var(--marque-bleu)',
  },
  {
    titre: 'Examens et concours',
    description:
      'Sessions, candidatures, pièces jointes, centres, salles, surveillants, correcteurs, ' +
      'copies anonymées, jurys, résultats et contentieux.',
    icone: GraduationCap,
    teinte: 'var(--benin-vert)',
  },
  {
    titre: 'Diplômes vérifiables',
    description:
      "Chaque diplôme, relevé et bulletin porte un code et un QR code permettant d'en " +
      "contrôler l'authenticité en ligne.",
    icone: Award,
    teinte: 'var(--marque-or)',
  },
  {
    titre: 'Vie étudiante',
    description:
      'Orientation, bourses et aides sociales, transport, logement, restauration, santé, ' +
      'bibliothèque, projets, stages et emploi.',
    icone: Bus,
    teinte: 'var(--marque-bleu-vif)',
  },
  {
    titre: 'Gouvernance',
    description:
      'Tableaux de bord nationaux, cartographie, indicateurs, alertes, moteur de règles et ' +
      'rapports automatiques.',
    icone: BarChart3,
    teinte: 'var(--benin-rouge)',
  },
  {
    titre: 'Recherche avancée',
    description:
      'Constructeur visuel de requêtes et interrogation en français : « les élèves des CEG ' +
      'ayant plus de 18 de moyenne ».',
    icone: Search,
    teinte: 'var(--marque-bleu)',
  },
];

/** Services ouverts sans compte, rappelés en bas de page. */
const SERVICES_PUBLICS = [
  {
    titre: "Consulter un résultat d'examen",
    description:
      'Par numéro de table ou par nom, pour toutes les sessions dont les résultats sont ' +
      'publiés.',
    href: '/resultats-publics',
  },
  {
    titre: 'Vérifier un diplôme',
    description:
      'Saisissez le code de vérification porté par le document pour en contrôler ' +
      "l'authenticité et télécharger l'original.",
    href: '/verification',
  },
];

export default function Accueil() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 bg-[rgb(var(--fond))]/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
          <Link href="/" className="flex items-center gap-3">
            <Image
              src="/images/logo-embleme.png"
              alt=""
              aria-hidden
              width={40}
              height={40}
              className="h-10 w-10 object-contain"
              priority
            />
            <span className="flex flex-col leading-tight">
              <span className="titre-marque text-lg font-semibold tracking-tight">
                Edu<span className="accentue">Hub</span>
              </span>
              <span className="hidden text-xs texte-doux sm:block">
                L&apos;éducation au service d&apos;un meilleur Bénin
              </span>
            </span>
          </Link>
          <nav aria-label="Accès rapides" className="flex items-center gap-1 sm:gap-2">
            <Link
              href="/resultats-publics"
              className="rounded-lg px-3 py-2 text-sm font-medium hover:bg-[rgb(var(--fond-doux))]"
            >
              Résultats
            </Link>
            <Link
              href="/verification"
              className="hidden rounded-lg px-3 py-2 text-sm font-medium hover:bg-[rgb(var(--fond-doux))] sm:inline-block"
            >
              Vérifier un diplôme
            </Link>
            <Link
              href="/connexion"
              className="inline-flex items-center gap-1.5 rounded-lg degrade-marque px-4 py-2 text-sm font-medium text-white"
            >
              Se connecter
              <ArrowRight size={15} aria-hidden />
            </Link>
          </nav>
        </div>
        <div className="filet-benin" aria-hidden />
      </header>

      <main>
        {/* Héros : le texte à gauche, la photographie à droite, sur un fond
            bleu très dilué qui sépare l'accroche du reste de la page. */}
        <section className="relative overflow-hidden border-b bg-[rgb(var(--marque-bleu))]/[0.04]">
          <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-14 sm:px-6 sm:py-20 lg:grid-cols-[1.2fr_1fr] lg:gap-14">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-[rgb(var(--marque-bleu))]/25 bg-[rgb(var(--fond-carte))] px-3 py-1 text-xs font-medium uppercase tracking-wider text-[rgb(var(--marque-bleu))]">
                <span className="filet-benin h-3 w-3 rounded-full" aria-hidden />
                République du Bénin — prototype
              </p>
              <h1 className="mt-5 text-pretty text-3xl font-semibold leading-[1.15] tracking-tight sm:text-4xl">
                Un système unique pour toute la vie éducative,{' '}
                <span className="text-[rgb(var(--marque-bleu))]">
                  de la maternelle à l&apos;insertion professionnelle
                </span>
                .
              </h1>
              <p className="mt-5 max-w-xl text-lg texte-doux">
                EduHub relie apprenants, enseignants, établissements, directions départementales,
                directions des examens et ministères dans une même chaîne de données cohérente —
                pensée pour être utilisable par tous, y compris en connexion limitée.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/connexion"
                  className="inline-flex h-12 items-center gap-2 rounded-lg degrade-marque px-6 font-medium text-white"
                >
                  Entrer dans la plateforme
                  <ArrowRight size={18} aria-hidden />
                </Link>
                <Link
                  href="/resultats-publics"
                  className="inline-flex h-12 items-center gap-2 rounded-lg border bg-[rgb(var(--fond-carte))] px-6 font-medium hover:bg-[rgb(var(--fond-doux))]"
                >
                  Consulter un résultat d&apos;examen
                </Link>
              </div>
            </div>

            {/* La photographie repose sur le filet tricolore, qui lui sert de
                socle plutôt que de traverser l'image. */}
            <div className="overflow-hidden rounded-2xl border shadow-sm">
              <div className="relative aspect-[4/3]">
                <Image
                  src="/images/image_banner.jpeg"
                  alt="Une élève devant un établissement scolaire aux couleurs du Bénin."
                  fill
                  sizes="(min-width: 1024px) 45vw, 100vw"
                  className="object-cover object-[60%_35%]"
                  priority
                />
              </div>
              <div className="filet-benin h-1.5" aria-hidden />
            </div>
          </div>
        </section>

        {/* Chiffres : ils viennent de la base, pas d'une liste écrite à la main. */}
        <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6" aria-labelledby="titre-chiffres">
          <h2 id="titre-chiffres" className="sr-only">
            Ce que couvre la plateforme
          </h2>
          <ChiffresCles />
          <p className="mt-3 text-sm texte-doux">
            Chiffres relevés en direct sur le jeu de démonstration, entièrement fictif.
          </p>
        </section>

        <section className="border-y surface-douce">
          <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Six domaines, une seule chaîne de données
            </h2>
            <p className="mt-2 max-w-2xl texte-doux">
              Une note saisie en classe alimente le bulletin, le bulletin alimente le dossier, le
              dossier alimente la candidature à l&apos;examen, et le diplôme délivré reste
              vérifiable en ligne.
            </p>

            <div className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {DOMAINES.map((domaine) => {
                const Icone = domaine.icone;
                return (
                  <article
                    key={domaine.titre}
                    className="rounded-xl border bg-[rgb(var(--fond-carte))] p-5 transition-shadow hover:shadow-sm"
                  >
                    <span
                      aria-hidden
                      className="grid h-11 w-11 place-items-center rounded-lg"
                      style={{
                        backgroundColor: `rgb(${domaine.teinte} / 0.12)`,
                        color: `rgb(${domaine.teinte})`,
                      }}
                    >
                      <Icone size={22} />
                    </span>
                    <h3 className="mt-4 text-lg font-semibold">{domaine.titre}</h3>
                    <p className="mt-1.5 text-sm texte-doux">{domaine.description}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <div className="grid gap-5 lg:grid-cols-2">
            <article className="rounded-xl border bg-[rgb(var(--fond-carte))] p-7">
              <span
                aria-hidden
                className="grid h-11 w-11 place-items-center rounded-lg bg-[rgb(var(--marque-bleu))]/10 text-[rgb(var(--marque-bleu))]"
              >
                <Accessibility size={22} />
              </span>
              <h2 className="mt-4 text-2xl font-semibold tracking-tight">
                Conçu pour être utilisable par tous
              </h2>
              <p className="mt-3 texte-doux">
                Contraste élevé, grande police, lecture vocale, navigation clavier complète,
                interface simplifiée à pictogrammes pour les personnes peu alphabétisées, et mode
                économie de données qui remplace les graphiques par des tableaux lisibles.
              </p>
              <p className="mt-3 texte-doux">
                Côté examens, les aménagements suivent le candidat : tiers temps, salle aménagée,
                secrétaire, sujets en braille ou interprète en langue des signes.
              </p>
            </article>

            <article className="rounded-xl border bg-[rgb(var(--fond-carte))] p-7">
              <span
                aria-hidden
                className="grid h-11 w-11 place-items-center rounded-lg bg-[rgb(var(--benin-vert))]/10 text-[rgb(var(--benin-vert))]"
              >
                <ShieldCheck size={22} />
              </span>
              <h2 className="mt-4 text-2xl font-semibold tracking-tight">
                Une chaîne institutionnelle respectée
              </h2>
              <p className="mt-3 texte-doux">
                Super administrateur, ministères, directions des examens et concours, directions
                départementales, établissements, candidats : chaque acteur dispose exactement des
                droits de son niveau, ne voit que son périmètre, et chaque opération sensible est
                tracée.
              </p>
              <p className="mt-3 texte-doux">
                Toutes les données présentées sont fictives et générées automatiquement : le
                prototype ne dépend d&apos;aucun système externe.
              </p>
            </article>
          </div>
        </section>

        <section className="border-t surface-douce">
          <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight">Services ouverts sans compte</h2>
            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              {SERVICES_PUBLICS.map((service) => (
                <Link
                  key={service.href}
                  href={service.href}
                  className="group rounded-xl border bg-[rgb(var(--fond-carte))] p-6 transition-shadow hover:shadow-sm"
                >
                  <h3 className="flex items-center gap-2 text-lg font-semibold">
                    {service.titre}
                    <ArrowRight
                      size={18}
                      aria-hidden
                      className="text-[rgb(var(--marque-bleu))] transition-transform group-hover:translate-x-1"
                    />
                  </h3>
                  <p className="mt-1.5 text-sm texte-doux">{service.description}</p>
                </Link>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t">
        <div className="filet-benin" aria-hidden />
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-sm texte-doux sm:px-6">
          <p>EduHub — prototype de démonstration. Toutes les données sont fictives.</p>
          <p>République du Bénin</p>
        </div>
      </footer>
    </div>
  );
}
