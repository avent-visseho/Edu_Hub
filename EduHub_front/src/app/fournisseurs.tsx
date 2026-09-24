'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';

import { ErreurApi } from '@/lib/api';
import { FournisseurAccessibilite } from '@/lib/accessibilite';
import { FournisseurSession } from '@/lib/session';

/** Fournisseurs globaux : requêtes, session et préférences d'accessibilité. */
export function Fournisseurs({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Connectivité limitée : on garde les données en cache plus longtemps
            // et l'on évite les rechargements automatiques inutiles.
            staleTime: 60_000,
            gcTime: 30 * 60_000,
            refetchOnWindowFocus: false,
            retry: (tentative, erreur) => {
              if (erreur instanceof ErreurApi) {
                // Inutile de réessayer une erreur de droits ou de saisie.
                if (erreur.statut >= 400 && erreur.statut < 500) return false;
              }
              return tentative < 2;
            },
          },
          mutations: { retry: false },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <FournisseurAccessibilite>
        <FournisseurSession>{children}</FournisseurSession>
      </FournisseurAccessibilite>
    </QueryClientProvider>
  );
}
