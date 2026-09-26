'use client';

import type { ReactNode } from 'react';

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
  personnel?: { titre: string; description?: ReactNode };
}) {
  const { utilisateur } = useSession();
  const adapte = personnel && utilisateur?.niveau_scope === 'PERSONNEL' ? personnel : null;
  const titreAffiche = adapte?.titre ?? titre;
  const descriptionAffichee = adapte ? adapte.description : description;

  return (
    <div className={cn('mb-6', className)}>
      {fil && fil.length > 0 ? (
        <nav aria-label="Fil d'Ariane" className="mb-2">
          <ol className="flex flex-wrap items-center gap-1.5 text-sm texte-doux">
            {fil.map((element, index) => (
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
