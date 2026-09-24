import type { Config } from 'tailwindcss';

/**
 * Palette institutionnelle : un bleu profond pour l'administration, un vert
 * pour la réussite et un ocre pour les alertes — des teintes lisibles aussi
 * bien sur un grand écran que sur un téléphone d'entrée de gamme.
 */
const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  darkMode: ['class', '[data-theme="sombre"]'],
  theme: {
    extend: {
      colors: {
        encre: {
          50: '#f3f6fb',
          100: '#e5ebf6',
          200: '#c6d5ea',
          300: '#95b1d8',
          400: '#5d86c1',
          500: '#3966a8',
          600: '#284f8b',
          700: '#1f3f71',
          800: '#1c355e',
          900: '#1b2e4f',
          950: '#121e35',
        },
        savane: {
          50: '#f0fdf6',
          100: '#dcfce9',
          200: '#bbf7d4',
          300: '#86efb5',
          400: '#4ade8d',
          500: '#22c56a',
          600: '#16a153',
          700: '#157f44',
          800: '#166439',
          900: '#145231',
        },
        ocre: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde589',
          300: '#fbd24b',
          400: '#f9be22',
          500: '#f39d0b',
          600: '#d77706',
          700: '#b25309',
          800: '#90400e',
          900: '#76350f',
        },
        brique: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },
      },
      fontFamily: {
        sans: [
          'var(--police-interface)',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'sans-serif',
        ],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        // Échelle pilotée par la préférence « grande police ».
        base: ['var(--taille-base)', { lineHeight: '1.6' }],
      },
      borderRadius: {
        DEFAULT: '0.5rem',
        lg: '0.75rem',
        xl: '1rem',
      },
      boxShadow: {
        carte: '0 1px 2px rgb(18 30 53 / 0.06), 0 8px 24px -12px rgb(18 30 53 / 0.18)',
        eleve: '0 2px 4px rgb(18 30 53 / 0.08), 0 16px 40px -16px rgb(18 30 53 / 0.28)',
      },
      keyframes: {
        apparition: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        pulsation: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.45' },
        },
      },
      animation: {
        apparition: 'apparition 220ms ease-out',
        pulsation: 'pulsation 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;
