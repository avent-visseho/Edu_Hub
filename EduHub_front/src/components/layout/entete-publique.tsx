import { ArrowLeft } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';

import { BarreAccessibilite } from '@/components/layout/barre-accessibilite';

/**
 * En-tête des pages ouvertes sans compte — résultats d'examen, vérification de
 * document. Elle porte la même marque que le reste du service : un visiteur qui
 * arrive par un QR code doit reconnaître l'institution avant de lire la page.
 *
 * Le retour vers l'accueil reste le premier élément : ces pages sont souvent
 * atteintes directement, sans être passé par la page d'accueil.
 */
export function EntetePublique() {
  return (
    <header>
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
        <Link href="/" className="inline-flex items-center gap-3">
          <ArrowLeft size={17} aria-hidden className="texte-doux" />
          <Image
            src="/images/logo-embleme.png"
            alt=""
            aria-hidden
            width={32}
            height={32}
            className="h-8 w-8 object-contain"
          />
          <span className="flex flex-col leading-tight">
            <span className="titre-marque font-semibold tracking-tight">
              Edu<span className="accentue">Hub</span>
            </span>
            <span className="hidden text-xs texte-doux sm:block">
              L&apos;éducation au service d&apos;un meilleur Bénin
            </span>
          </span>
        </Link>
        <BarreAccessibilite />
      </div>
      <div className="filet-benin" aria-hidden />
    </header>
  );
}
