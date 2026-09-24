'use client';

import { useRouter } from 'next/navigation';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { ErreurApi, api, jetons } from '@/lib/api';
import type { Jetons, Utilisateur } from '@/types/api';

interface ContexteSession {
  utilisateur: Utilisateur | null;
  chargement: boolean;
  connecte: boolean;
  connexion: (email: string, motDePasse: string) => Promise<void>;
  deconnexion: () => Promise<void>;
  rafraichirProfil: () => Promise<void>;
  /** Vrai si l'utilisateur détient la permission `ressource:action`. */
  peut: (ressource: string, action: string) => boolean;
  /** Vrai si l'utilisateur exerce l'un des rôles indiqués. */
  aRole: (...codes: string[]) => boolean;
}

const Contexte = createContext<ContexteSession | null>(null);

export function FournisseurSession({ children }: { children: ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null);
  const [chargement, setChargement] = useState(true);
  const router = useRouter();

  const chargerProfil = useCallback(async () => {
    if (!jetons.acces()) {
      setUtilisateur(null);
      setChargement(false);
      return;
    }
    try {
      setUtilisateur(await api.get<Utilisateur>('/auth/moi'));
    } catch (erreur) {
      if (erreur instanceof ErreurApi && erreur.estAuthentification) {
        jetons.effacer();
      }
      setUtilisateur(null);
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => {
    void chargerProfil();
  }, [chargerProfil]);

  const connexion = useCallback(
    async (email: string, motDePasse: string) => {
      const reponse = await api.post<Jetons>(
        '/auth/connexion',
        { email, mot_de_passe: motDePasse },
        { publique: true },
      );
      jetons.enregistrer(reponse.access_token, reponse.refresh_token);
      const profil = await api.get<Utilisateur>('/auth/moi');
      setUtilisateur(profil);
    },
    [],
  );

  const deconnexion = useCallback(async () => {
    try {
      await api.post('/auth/deconnexion');
    } catch {
      /* La session locale est effacée dans tous les cas. */
    }
    jetons.effacer();
    setUtilisateur(null);
    router.push('/connexion');
  }, [router]);

  const peut = useCallback(
    (ressource: string, action: string) => {
      if (!utilisateur) return false;
      if (utilisateur.roles.includes('SUPER_ADMIN')) return true;
      return utilisateur.permissions.includes(`${ressource}:${action}`);
    },
    [utilisateur],
  );

  const aRole = useCallback(
    (...codes: string[]) => {
      if (!utilisateur) return false;
      return codes.some((code) => utilisateur.roles.includes(code));
    },
    [utilisateur],
  );

  const valeur = useMemo<ContexteSession>(
    () => ({
      utilisateur,
      chargement,
      connecte: utilisateur !== null,
      connexion,
      deconnexion,
      rafraichirProfil: chargerProfil,
      peut,
      aRole,
    }),
    [utilisateur, chargement, connexion, deconnexion, chargerProfil, peut, aRole],
  );

  return <Contexte.Provider value={valeur}>{children}</Contexte.Provider>;
}

export function useSession(): ContexteSession {
  const contexte = useContext(Contexte);
  if (!contexte) {
    throw new Error('useSession doit être utilisé dans FournisseurSession.');
  }
  return contexte;
}
