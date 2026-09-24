'use client';

import {
  Accessibility,
  Contrast,
  Moon,
  RotateCcw,
  Signal,
  Sun,
  Type,
  Volume2,
  X,
} from 'lucide-react';
import { useEffect, useId, useRef, useState } from 'react';

import { useAccessibilite } from '@/lib/accessibilite';
import { cn } from '@/lib/utils';

import { Bouton, Interrupteur } from '../ui/primitives';

/**
 * Panneau d'accessibilité.
 *
 * Toujours joignable depuis n'importe quel écran, il regroupe les réglages qui
 * conditionnent l'usage de la plateforme par les personnes en situation de
 * handicap ou disposant d'une connexion limitée.
 */
export function BarreAccessibilite() {
  const {
    theme,
    contraste,
    police,
    modeSimplifie,
    lectureVocale,
    economieDonnees,
    vocalDisponible,
    definir,
    basculer,
    reinitialiser,
  } = useAccessibilite();

  const [ouvert, setOuvert] = useState(false);
  const panneau = useRef<HTMLDivElement>(null);
  const identifiant = useId();

  // Fermeture à la touche Échap et au clic extérieur.
  useEffect(() => {
    if (!ouvert) return;

    const auClavier = (evenement: KeyboardEvent) => {
      if (evenement.key === 'Escape') setOuvert(false);
    };
    const auClic = (evenement: MouseEvent) => {
      if (panneau.current && !panneau.current.contains(evenement.target as Node)) {
        setOuvert(false);
      }
    };

    document.addEventListener('keydown', auClavier);
    document.addEventListener('mousedown', auClic);
    return () => {
      document.removeEventListener('keydown', auClavier);
      document.removeEventListener('mousedown', auClic);
    };
  }, [ouvert]);

  const tailles: Array<{ valeur: typeof police; libelle: string; exemple: string }> = [
    { valeur: 'normale', libelle: 'Normale', exemple: 'Aa' },
    { valeur: 'grande', libelle: 'Grande', exemple: 'Aa' },
    { valeur: 'tres-grande', libelle: 'Très grande', exemple: 'Aa' },
  ];

  return (
    <div className="relative sans-impression" ref={panneau}>
      <button
        type="button"
        onClick={() => setOuvert((valeur) => !valeur)}
        aria-expanded={ouvert}
        aria-controls={identifiant}
        className={cn(
          'inline-flex h-11 items-center gap-2 rounded-lg border px-3 font-medium transition',
          ouvert
            ? 'border-[rgb(var(--accent))] bg-[rgb(var(--accent))]/10'
            : 'surface hover:bg-[rgb(var(--fond-doux))]',
        )}
      >
        <Accessibility size={20} aria-hidden />
        <span className="hidden sm:inline">Accessibilité</span>
      </button>

      {ouvert ? (
        <div
          id={identifiant}
          role="dialog"
          aria-label="Réglages d'accessibilité"
          className="absolute right-0 z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] animate-apparition rounded-xl border bg-[rgb(var(--fond-carte))] p-4 shadow-eleve"
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Confort de lecture</h2>
            <button
              type="button"
              onClick={() => setOuvert(false)}
              aria-label="Fermer les réglages"
              className="rounded p-1 hover:bg-[rgb(var(--fond-doux))]"
            >
              <X size={18} aria-hidden />
            </button>
          </div>

          <div className="space-y-4">
            {/* Thème */}
            <fieldset>
              <legend className="mb-1.5 text-sm font-medium">Thème</legend>
              <div className="grid grid-cols-2 gap-2">
                {(
                  [
                    { valeur: 'clair', libelle: 'Clair', icone: <Sun size={16} aria-hidden /> },
                    { valeur: 'sombre', libelle: 'Sombre', icone: <Moon size={16} aria-hidden /> },
                  ] as const
                ).map((option) => (
                  <button
                    key={option.valeur}
                    type="button"
                    onClick={() => definir('theme', option.valeur)}
                    aria-pressed={theme === option.valeur}
                    className={cn(
                      'inline-flex h-10 items-center justify-center gap-2 rounded-lg border text-sm font-medium transition',
                      theme === option.valeur
                        ? 'border-[rgb(var(--accent))] bg-[rgb(var(--accent))]/10'
                        : 'surface hover:bg-[rgb(var(--fond-doux))]',
                    )}
                  >
                    {option.icone}
                    {option.libelle}
                  </button>
                ))}
              </div>
            </fieldset>

            {/* Taille du texte */}
            <fieldset>
              <legend className="mb-1.5 text-sm font-medium">Taille du texte</legend>
              <div className="grid grid-cols-3 gap-2">
                {tailles.map((option, index) => (
                  <button
                    key={option.valeur}
                    type="button"
                    onClick={() => definir('police', option.valeur)}
                    aria-pressed={police === option.valeur}
                    aria-label={option.libelle}
                    className={cn(
                      'inline-flex h-11 items-center justify-center rounded-lg border font-semibold transition',
                      police === option.valeur
                        ? 'border-[rgb(var(--accent))] bg-[rgb(var(--accent))]/10'
                        : 'surface hover:bg-[rgb(var(--fond-doux))]',
                    )}
                  >
                    <span style={{ fontSize: `${0.85 + index * 0.25}rem` }}>{option.exemple}</span>
                  </button>
                ))}
              </div>
            </fieldset>

            <div className="space-y-2">
              <Interrupteur
                etiquette="Contraste élevé"
                description="Noir et blanc francs, bordures renforcées"
                actif={contraste === 'eleve'}
                onChange={() => definir('contraste', contraste === 'eleve' ? 'normal' : 'eleve')}
                icone={<Contrast size={18} aria-hidden />}
              />
              <Interrupteur
                etiquette="Interface simplifiée"
                description="Pictogrammes et libellés courts"
                actif={modeSimplifie}
                onChange={() => basculer('modeSimplifie')}
                icone={<Type size={18} aria-hidden />}
              />
              {vocalDisponible ? (
                <Interrupteur
                  etiquette="Lecture vocale"
                  description="Écouter les chiffres et les résultats"
                  actif={lectureVocale}
                  onChange={() => basculer('lectureVocale')}
                  icone={<Volume2 size={18} aria-hidden />}
                />
              ) : null}
              <Interrupteur
                etiquette="Économie de données"
                description="Remplace les graphiques par des tableaux"
                actif={economieDonnees}
                onChange={() => basculer('economieDonnees')}
                icone={<Signal size={18} aria-hidden />}
              />
            </div>

            <Bouton
              variante="fantome"
              taille="sm"
              onClick={reinitialiser}
              icone={<RotateCcw size={15} aria-hidden />}
              className="w-full"
            >
              Rétablir les réglages par défaut
            </Bouton>
          </div>
        </div>
      ) : null}
    </div>
  );
}
