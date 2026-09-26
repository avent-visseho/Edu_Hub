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
import Link from 'next/link';

const DOMAINES = [
  {
    titre: 'Scolarité',
    description:
      "De l'inscription au bulletin : classes, emploi du temps, présences, notes, moyennes, " +
      'rangs et conseils de classe.',
    icone: Users,
  },
  {
    titre: 'Examens et concours',
    description:
      'Sessions, candidatures, pièces jointes, centres, salles, surveillants, correcteurs, ' +
      'copies anonymées, jurys, résultats et contentieux.',
    icone: GraduationCap,
  },
  {
    titre: 'Diplômes vérifiables',
    description:
      "Chaque diplôme, relevé et bulletin porte un code et un QR code permettant d'en " +
      "contrôler l'authenticité en ligne.",
    icone: Award,
  },
  {
    titre: 'Vie étudiante',
    description:
      'Orientation, bourses et aides sociales, transport, logement, restauration, santé, ' +
      'bibliothèque, projets, stages et emploi.',
    icone: Bus,
  },
  {
    titre: 'Gouvernance',
    description:
      'Tableaux de bord nationaux, cartographie, indicateurs, alertes, moteur de règles et ' +
      'rapports automatiques.',
    icone: BarChart3,
  },
  {
    titre: 'Recherche avancée',
    description:
      'Constructeur visuel de requêtes et interrogation en français : « les élèves des CEG ' +
      'ayant plus de 18 de moyenne ».',
    icone: Search,
  },
];

export default function Accueil() {
  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <span className="flex items-center gap-2.5 font-semibold">
            <span
              aria-hidden
              className="grid h-9 w-9 place-items-center rounded-lg bg-[rgb(var(--accent))] text-sm font-bold text-[rgb(var(--accent-contraste))]"
            >
              EH
            </span>
            <span className="text-lg tracking-tight">EduHub</span>
          </span>
          <nav aria-label="Accès rapides" className="flex items-center gap-2">
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
              className="rounded-lg bg-[rgb(var(--accent))] px-4 py-2 text-sm font-medium text-[rgb(var(--accent-contraste))]"
            >
              Se connecter
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
          <p className="mb-3 text-sm font-medium uppercase tracking-wider text-[rgb(var(--accent))]">
            Prototype de démonstration
          </p>
          <h1 className="max-w-4xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            Un système unique pour toute la vie éducative,{' '}
            <span className="text-[rgb(var(--accent))]">
              de la maternelle à l&apos;insertion professionnelle
            </span>
            .
          </h1>
          <p className="mt-5 max-w-2xl text-lg texte-doux">
            EduHub relie apprenants, enseignants, établissements, directions départementales,
            directions des examens et ministères dans une même chaîne de données cohérente — pensée
            pour être utilisable par tous, y compris en connexion limitée.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/connexion"
              className="inline-flex h-12 items-center gap-2 rounded-lg bg-[rgb(var(--accent))] px-6 font-medium text-[rgb(var(--accent-contraste))]"
            >
              Entrer dans la plateforme
              <ArrowRight size={18} aria-hidden />
            </Link>
            <Link
              href="/resultats-publics"
              className="inline-flex h-12 items-center gap-2 rounded-lg border px-6 font-medium hover:bg-[rgb(var(--fond-doux))]"
            >
              Consulter un résultat d&apos;examen
            </Link>
          </div>
        </section>

        <section className="border-y surface-douce">
          <div className="mx-auto grid max-w-6xl gap-px px-4 py-12 sm:grid-cols-2 sm:px-6 lg:grid-cols-3">
            {DOMAINES.map((domaine) => {
              const Icone = domaine.icone;
              return (
                <article key={domaine.titre} className="p-5">
                  <Icone size={26} aria-hidden className="text-[rgb(var(--accent))]" />
                  <h2 className="mt-3 text-lg font-semibold">{domaine.titre}</h2>
                  <p className="mt-1.5 text-sm texte-doux">{domaine.description}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <div className="grid gap-8 lg:grid-cols-2">
            <div>
              <Accessibility size={28} aria-hidden className="text-[rgb(var(--accent))]" />
              <h2 className="mt-3 text-2xl font-semibold tracking-tight">
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
            </div>
            <div>
              <ShieldCheck size={28} aria-hidden className="text-[rgb(var(--accent))]" />
              <h2 className="mt-3 text-2xl font-semibold tracking-tight">
                Une chaîne institutionnelle respectée
              </h2>
              <p className="mt-3 texte-doux">
                Super administrateur, ministères, directions des examens et concours, directions
                départementales, établissements, candidats : chaque acteur dispose exactement des
                droits de son niveau, et chaque opération sensible est tracée.
              </p>
              <p className="mt-3 texte-doux">
                Toutes les données présentées sont fictives et générées automatiquement : le
                prototype ne dépend d&apos;aucun système externe.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-6 text-sm texte-doux sm:px-6">
          <p>EduHub — prototype de démonstration. Données fictives.</p>
        </div>
      </footer>
    </div>
  );
}
