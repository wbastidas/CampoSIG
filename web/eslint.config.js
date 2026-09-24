// @ts-check
/**
 * ESLint, en formato plano.
 *
 * `pnpm lint` estaba documentado en CLAUDE.md y no funcionaba: no había configuración, así que
 * el comando fallaba con "couldn't find eslint.config.js". Un comando documentado que no corre
 * es peor que uno ausente, porque quien llega nuevo pierde la tarde averiguando si el problema
 * es suyo.
 *
 * Las reglas que se añaden sobre las recomendadas están todas ahí por un fallo concreto que
 * `tsc` no ve: dependencias de hooks que faltan —la causa de los "no se actualiza hasta que
 * cambio de pestaña"—, promesas sin esperar, y comparaciones que el compilador considera
 * válidas pero que en tiempo de ejecución no lo son.
 */

import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    ignores: ['dist/**', 'node_modules/**', 'playwright-report/**', 'test-results/**'],
  },
  js.configs.recommended,
  // `recommendedTypeChecked` y no solo `recommended`: las reglas que valen la pena aquí
  // —promesas sin esperar, comparaciones imposibles— necesitan el grafo de tipos.
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        // `projectService` con `allowDefaultProject` para los archivos de configuración y los
        // e2e, que viven fuera de `include: ["src"]` del tsconfig de la aplicación.
        // `tsconfig.node.json` cubre los archivos de configuración y los e2e, que viven fuera
        // del `include: ["src"]` de la aplicación.
        project: ['./tsconfig.json', './tsconfig.node.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      globals: { ...globals.browser },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // Una promesa sin `await` ni `void` es trabajo que ocurre fuera del flujo que se lee.
      '@typescript-eslint/no-floating-promises': 'error',
      // Un `any` explícito es a veces la respuesta correcta; que sea un aviso y no un error
      // obliga a mirarlo sin bloquear a nadie.
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
  {
    // Los tests usan `any` y aserciones con más libertad; medirlos con la misma vara produce
    // ruido, no calidad.
    files: ['**/*.test.ts', '**/*.test.tsx', 'e2e/**/*.ts'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
      '@typescript-eslint/no-unsafe-argument': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',
      // `json: async () => ({...})` es la forma idiomática de simular una Response, y no lleva
      // await porque no tiene nada que esperar.
      '@typescript-eslint/require-await': 'off',
      // `String(input)` sobre un `RequestInfo | URL` es correcto: URL tiene un toString útil.
      '@typescript-eslint/no-base-to-string': 'off',
    },
  },
  {
    // Archivos de configuración y e2e: Node, no navegador.
    files: ['*.config.ts', '*.config.js', 'e2e/**/*.ts'],
    languageOptions: { globals: { ...globals.node } },
  },
  {
    // El hook y su proveedor van juntos a propósito: es el patrón estándar de React, y la regla
    // solo advierte de que el refresco en caliente recargará el módulo entero.
    files: ['src/auth/SessionProvider.tsx'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
  {
    // `eslint.config.js` no es TypeScript; las reglas con tipos no aplican.
    files: ['eslint.config.js'],
    ...tseslint.configs.disableTypeChecked,
  },
);
