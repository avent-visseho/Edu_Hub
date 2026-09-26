'use client';

import type { ReactNode } from 'react';

import { libelleEntree, NAVIGATION } from '@/components/layout/navigation';
import { useSession } from '@/lib/session';
import { cn } from '@/lib/utils';

/** En-tête de page : titre, description et actions contextuelles. */
export function EntetePage({
  titre,
  description,
  actions,
  fil,
  className,
  personnel,
}: {
  titre: string;
  description?: ReactNode;
  actions?: ReactNode;
  /** Fil d'Ariane, du plus général au plus précis. */
  fil?: Array<{ libelle: string; href?: string }>;
  className?: string;
  /**
   * Titre et description employés pour les comptes à portée personnelle.
   *
   * La même page sert au ministère et à l'élève, mais elle ne montre pas la
   * même chose : annoncer « Élèves et étudiants inscrits dans le système » à
   * qui n'y verra que sa propre fiche serait trompeur.
   */
  personnel?: {
    titre: string;
    description?: ReactNode;
    /**
     * Variantes par rôle, prioritaires sur le titre ci-dessus.
     *
     * « Mes résultats » convient à l'élève mais pas au parent, qui n'en a pas :
     * ce sont ceux de ses enfants.
     */
    parRole?: Record<string, { titre: string; description?: ReactNode }>;
  };
}) {
  const { utilisateur } = useSession();
  const portePersonnelle = utilisateur?.niveau_scope === 'PERSONNEL';
  const parRole = personnel?.parRole
    ? (utilisateur?.roles ?? []).map((role) => personnel.parRole?.[role]).find(Boolean)
    : undefined;
  const adapte = personnel && portePersonnelle ? (parRole ?? personnel) : null;
  const titreAffiche = adapte?.titre ?? titre;
  const descriptionAffichee = adapte ? adapte.description : description;

  // Le fil d'Ariane des pages de détail remonte vers la liste : il doit porter
  // le même nom qu'elle. Sans cela, l'élève lit « Mon dossier » dans le menu et
  // « Apprenants » au-dessus de sa propre fiche.
  const filAffiche = portePersonnelle
    ? fil?.map((element) => {
        const entree = NAVIGATION.flatMap((groupe) => groupe.entrees).find(
          (candidat) => candidat.href === element.href,
        );
        if (!entree) return element;
        return {
          ...element,
          libelle: libelleEntree(entree, utilisateur.niveau_scope, utilisateur.roles),
        };
      })
    : fil;

  return (
    <div className={cn('mb-6', className)}>
      {filAffiche && filAffiche.length > 0 ? (
        <nav aria-label="Fil d'Ariane" className="mb-2">
          <ol className="flex flex-wrap items-center gap-1.5 text-sm texte-doux">
            {filAffiche.map((element, index) => (
              <li key={`${element.libelle}-${index}`} className="flex items-center gap-1.5">
                {index > 0 ? <span aria-hidden>/</span> : null}
                {element.href ? (
                  <a href={element.href} className="hover:underline">
                    {element.libelle}
                  </a>
                ) : (
                  <span aria-current="page">{element.libelle}</span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      ) : null}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{titreAffiche}</h1>
          {descriptionAffichee ? (
            <div className="mt-1.5 max-w-3xl text-sm texte-doux">{descriptionAffichee}</div>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </div>
  );
}
