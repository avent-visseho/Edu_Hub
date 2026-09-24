'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

/**
 * Préférences d'accessibilité.
 *
 * Elles sont appliquées sur <html> par des attributs de données, mémorisées
 * dans le navigateur, et volontairement indépendantes de la session : un poste
 * partagé garde ses réglages même après déconnexion.
 */

export type Theme = 'clair' | 'sombre';
export type Contraste = 'normal' | 'eleve';
export type TaillePolice = 'normale' | 'grande' | 'tres-grande';

export interface Preferences {
  theme: Theme;
  contraste: Contraste;
  police: TaillePolice;
  /** Interface à pictogrammes, pensée pour les personnes peu alphabétisées. */
  modeSimplifie: boolean;
  /** Synthèse vocale des contenus importants. */
  lectureVocale: boolean;
  /** Réduit les images et les graphiques lourds. */
  economieDonnees: boolean;
}

const DEFAUTS: Preferences = {
  theme: 'clair',
  contraste: 'normal',
  police: 'normale',
  modeSimplifie: false,
  lectureVocale: false,
  economieDonnees: false,
};

const CLE = 'eduhub.accessibilite';

interface ContexteAccessibilite extends Preferences {
  definir: <C extends keyof Preferences>(cle: C, valeur: Preferences[C]) => void;
  basculer: (cle: 'modeSimplifie' | 'lectureVocale' | 'economieDonnees') => void;
  reinitialiser: () => void;
  /** Lit un texte à voix haute si la lecture vocale est activée. */
  lire: (texte: string) => void;
  /** Vrai lorsque la synthèse vocale est disponible dans ce navigateur. */
  vocalDisponible: boolean;
}

const Contexte = createContext<ContexteAccessibilite | null>(null);

function appliquer(preferences: Preferences): void {
  if (typeof document === 'undefined') return;
  const racine = document.documentElement;
  racine.dataset.theme = preferences.theme;
  racine.dataset.contraste = preferences.contraste;
  racine.dataset.police = preferences.police;
  racine.dataset.simplifie = String(preferences.modeSimplifie);
  racine.lang = 'fr';
}

export function FournisseurAccessibilite({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<Preferences>(DEFAUTS);
  const [vocalDisponible, setVocalDisponible] = useState(false);

  // Restauration au montage : lecture du stockage puis application immédiate.
  useEffect(() => {
    let restaurees = DEFAUTS;
    try {
      const brut = window.localStorage.getItem(CLE);
      if (brut) restaurees = { ...DEFAUTS, ...(JSON.parse(brut) as Partial<Preferences>) };
    } catch {
      /* Stockage indisponible : on reste sur les valeurs par défaut. */
    }

    // Sans préférence enregistrée, on suit le réglage du système.
    if (!window.localStorage.getItem(CLE)) {
      const sombre = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
      const contraste = window.matchMedia?.('(prefers-contrast: more)').matches;
      restaurees = {
        ...restaurees,
        theme: sombre ? 'sombre' : 'clair',
        contraste: contraste ? 'eleve' : 'normal',
      };
    }

    setPreferences(restaurees);
    appliquer(restaurees);
    setVocalDisponible(typeof window !== 'undefined' && 'speechSynthesis' in window);
  }, []);

  const persister = useCallback((suivantes: Preferences) => {
    setPreferences(suivantes);
    appliquer(suivantes);
    try {
      window.localStorage.setItem(CLE, JSON.stringify(suivantes));
    } catch {
      /* Navigation privée : les réglages valent pour la session. */
    }
  }, []);

  const definir = useCallback(
    <C extends keyof Preferences>(cle: C, valeur: Preferences[C]) => {
      persister({ ...preferences, [cle]: valeur });
    },
    [preferences, persister],
  );

  const basculer = useCallback(
    (cle: 'modeSimplifie' | 'lectureVocale' | 'economieDonnees') => {
      persister({ ...preferences, [cle]: !preferences[cle] });
    },
    [preferences, persister],
  );

  const reinitialiser = useCallback(() => persister(DEFAUTS), [persister]);

  const lire = useCallback(
    (texte: string) => {
      if (!preferences.lectureVocale || typeof window === 'undefined') return;
      if (!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const enonce = new SpeechSynthesisUtterance(texte);
      enonce.lang = 'fr-FR';
      enonce.rate = 0.95;
      window.speechSynthesis.speak(enonce);
    },
    [preferences.lectureVocale],
  );

  const valeur = useMemo<ContexteAccessibilite>(
    () => ({ ...preferences, definir, basculer, reinitialiser, lire, vocalDisponible }),
    [preferences, definir, basculer, reinitialiser, lire, vocalDisponible],
  );

  return <Contexte.Provider value={valeur}>{children}</Contexte.Provider>;
}

export function useAccessibilite(): ContexteAccessibilite {
  const contexte = useContext(Contexte);
  if (!contexte) {
    throw new Error("useAccessibilite doit être utilisé dans FournisseurAccessibilite.");
  }
  return contexte;
}
