'use client';

import { Bell, LogOut, Menu, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState, type ReactNode } from 'react';

import { useAccessibilite } from '@/lib/accessibilite';
import { useSession } from '@/lib/session';
import { cn, initiales } from '@/lib/utils';

import { Bouton } from '../ui/primitives';
import { BarreAccessibilite } from './barre-accessibilite';
import { NAVIGATION } from './navigation';
import { RechercheGlobale } from './recherche-globale';

/**
 * Coquille applicative : barre latérale, en-tête et zone de contenu.
 *
 * La navigation s'adapte au rôle (les entrées sans permission disparaissent)
 * et au mode simplifié (pictogrammes et libellés courts).
 */
export function Coquille({ children }: { children: ReactNode }) {
  const { utilisateur, chargement, connecte, deconnexion, peut } = useSession();
  const { modeSimplifie } = useAccessibilite();
  const chemin = usePathname();
  const router = useRouter();
  const [menuOuvert, setMenuOuvert] = useState(false);

  // Redirection vers la connexion dès que la session est confirmée absente.
  useEffect(() => {
    if (!chargement && !connecte) router.replace('/connexion');
  }, [chargement, connecte, router]);

  // La navigation mobile se referme à chaque changement de page.
  useEffect(() => setMenuOuvert(false), [chemin]);

  if (chargement) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div
          role="status"
          aria-live="polite"
          className="flex flex-col items-center gap-3 texte-doux"
        >
          <span
            aria-hidden
            className="h-8 w-8 animate-spin rounded-full border-2 border-current border-r-transparent"
          />
          <span>Ouverture de votre espace…</span>
        </div>
      </div>
    );
  }

  if (!connecte || !utilisateur) return null;

  const groupes = NAVIGATION.map((groupe) => ({
    ...groupe,
    entrees: groupe.entrees.filter((entree) => {
      if (!entree.permission) return true;
      const [ressource, action] = entree.permission.split(':');
      return peut(ressource, action);
    }),
  })).filter((groupe) => groupe.entrees.length > 0);

  const navigation = (
    <nav aria-label="Navigation principale" className="space-y-6 px-3 py-4">
      {groupes.map((groupe) => (
        <div key={groupe.titre}>
          <h2 className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider texte-doux">
            {groupe.titre}
          </h2>
          <ul className="space-y-0.5">
            {groupe.entrees.map((entree) => {
              const actif = chemin === entree.href || chemin.startsWith(`${entree.href}/`);
              const Icone = entree.icone;
              return (
                <li key={entree.href}>
                  <Link
                    href={entree.href}
                    aria-current={actif ? 'page' : undefined}
                    className={cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2.5 transition',
                      actif
                        ? 'bg-[rgb(var(--accent))]/12 font-semibold text-[rgb(var(--accent))]'
                        : 'hover:bg-[rgb(var(--fond-doux))]',
                    )}
                  >
                    <span aria-hidden className="shrink-0">
                      {modeSimplifie ? (
                        <span className="text-xl leading-none">{entree.pictogramme}</span>
                      ) : (
                        <Icone size={19} />
                      )}
                    </span>
                    <span className="truncate">
                      {modeSimplifie ? entree.libelleSimple : entree.libelle}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );

  return (
    <div className="flex min-h-screen">
      <a href="#contenu" className="lien-evitement">
        Aller au contenu principal
      </a>

      {/* Barre latérale — écrans larges */}
      <aside className="sans-impression hidden w-72 shrink-0 border-r lg:block">
        <div className="sticky top-0 flex h-screen flex-col">
          <Link
            href="/tableau-de-bord"
            className="flex items-center gap-2.5 border-b px-5 py-4 font-semibold"
          >
            <span
              aria-hidden
              className="grid h-9 w-9 place-items-center rounded-lg bg-[rgb(var(--accent))] text-sm font-bold text-[rgb(var(--accent-contraste))]"
            >
              EH
            </span>
            <span className="text-lg tracking-tight">EduHub</span>
          </Link>
          <div className="defilement-fin flex-1 overflow-y-auto">{navigation}</div>
        </div>
      </aside>

      {/* Tiroir de navigation — mobile */}
      {menuOuvert ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-black/45"
            onClick={() => setMenuOuvert(false)}
            aria-hidden
          />
          <div className="absolute left-0 top-0 h-full w-72 overflow-y-auto border-r bg-[rgb(var(--fond-carte))]">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <span className="font-semibold">Navigation</span>
              <button
                type="button"
                onClick={() => setMenuOuvert(false)}
                aria-label="Fermer la navigation"
                className="rounded p-1.5 hover:bg-[rgb(var(--fond-doux))]"
              >
                <X size={20} aria-hidden />
              </button>
            </div>
            {navigation}
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sans-impression sticky top-0 z-30 border-b bg-[rgb(var(--fond-carte))]/95 backdrop-blur">
          <div className="flex items-center gap-2 px-4 py-3 sm:px-6">
            <button
              type="button"
              onClick={() => setMenuOuvert(true)}
              aria-label="Ouvrir la navigation"
              className="rounded-lg p-2 hover:bg-[rgb(var(--fond-doux))] lg:hidden"
            >
              <Menu size={22} aria-hidden />
            </button>

            <RechercheGlobale />

            <BarreAccessibilite />

            <Link
              href="/notifications"
              aria-label="Notifications"
              className="rounded-lg border p-2.5 hover:bg-[rgb(var(--fond-doux))]"
            >
              <Bell size={19} aria-hidden />
            </Link>

            <div className="flex items-center gap-2 border-l pl-2">
              <Link
                href="/mon-profil"
                className="flex items-center gap-2 rounded-lg px-1.5 py-1 hover:bg-[rgb(var(--fond-doux))]"
              >
                <span
                  aria-hidden
                  className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[rgb(var(--accent))]/15 text-sm font-semibold text-[rgb(var(--accent))]"
                >
                  {initiales(utilisateur.nom_complet)}
                </span>
                <span className="hidden min-w-0 text-left md:block">
                  <span className="block truncate text-sm font-medium">
                    {utilisateur.nom_complet}
                  </span>
                  <span className="block truncate text-xs texte-doux">
                    {utilisateur.roles[0] ?? '—'}
                  </span>
                </span>
              </Link>
              <Bouton
                variante="fantome"
                taille="sm"
                onClick={() => void deconnexion()}
                aria-label="Se déconnecter"
                className="px-2"
              >
                <LogOut size={18} aria-hidden />
              </Bouton>
            </div>
          </div>
        </header>

        <main id="contenu" className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>

        <footer className="sans-impression border-t px-4 py-4 text-xs texte-doux sm:px-6">
          <p>
            EduHub — prototype de démonstration. Toutes les données présentées sont fictives et
            générées automatiquement.
          </p>
        </footer>
      </div>
    </div>
  );
}
