/**
 * Configuration ESLint au format « plat », seul reconnu depuis ESLint 9.
 *
 * Le projet portait un .eslintrc.json, format hérité qu'ESLint 9 ne lit plus :
 * « npm run lint » s'interrompait sur « couldn't find eslint.config.js » sans
 * qu'aucune règle ne soit jamais appliquée. Le contrôle passait donc, faute
 * d'avoir eu lieu.
 *
 * FlatCompat traduit les configurations partagées de Next, qui ne sont pas
 * encore publiées au format plat. Ce pont disparaîtra le jour où
 * eslint-config-next le sera.
 */

import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { FlatCompat } from '@eslint/eslintrc';

const compat = new FlatCompat({
  baseDirectory: dirname(fileURLToPath(import.meta.url)),
});

const configuration = [
  {
    // Le format plat n'hérite d'aucune exclusion implicite : sans cette
    // entrée, ESLint parcourrait le résultat de construction et les
    // dépendances, pour des milliers d'erreurs sans objet.
    ignores: ['.next/**', 'node_modules/**', 'next-env.d.ts', 'src/data/frontiere-benin.ts'],
  },
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
  {
    rules: {
      // Un paramètre préfixé d'un tiret bas signale une valeur volontairement
      // ignorée : la signaler serait du bruit.
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
];

export default configuration;
