import type { Metadata, Viewport } from 'next';

import { Fournisseurs } from './fournisseurs';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: "EduHub — Système intégré de gestion de l'éducation",
    template: '%s · EduHub',
  },
  description:
    "Plateforme numérique intégrée de gestion de l'éducation : apprenants, enseignants, " +
    'établissements, scolarité, examens, concours, vie étudiante et gouvernance.',
  applicationName: 'EduHub',
  authors: [{ name: 'EduHub' }],
  keywords: ['éducation', 'Bénin', 'examens', 'concours', 'scolarité', 'bulletins'],
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // La plateforme doit rester zoomable : c'est une exigence d'accessibilité.
  maximumScale: 5,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#f8fafc' },
    { media: '(prefers-color-scheme: dark)', color: '#0d1525' },
  ],
};

export default function RacineLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body>
        <Fournisseurs>{children}</Fournisseurs>
      </body>
    </html>
  );
}
