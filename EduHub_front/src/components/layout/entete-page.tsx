import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

/** En-tête de page : titre, description et actions contextuelles. */
export function EntetePage({
  titre,
  description,
  actions,
  fil,
  className,
}: {
  titre: string;
  description?: ReactNode;
  actions?: ReactNode;
  /** Fil d'Ariane, du plus général au plus précis. */
  fil?: Array<{ libelle: string; href?: string }>;
  className?: string;
}) {
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
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{titre}</h1>
          {description ? (
            <div className="mt-1.5 max-w-3xl text-sm texte-doux">{description}</div>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </div>
  );
}
