/**
 * El corpus común de validación condicional, en la web (I5, SRS 7.2).
 *
 * Un tercio de un contrato. Los otros dos están en
 * `backend/tests/unit/test_i5_shared_validation_contract.py` y en
 * `android/core/sync/.../FormRulesTest.kt`, y los tres ejecutan el **mismo**
 * `forms/contract/validation-cases.json`.
 *
 * Escribir el mismo algoritmo tres veces no produce acuerdo: produce tres algoritmos que
 * coinciden en los casos que a alguien se le ocurrieron. Lo que produce acuerdo es el corpus.
 */

import { readFileSync } from 'node:fs';
import { dirname, resolve as resolvePath } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import {
  type Answers,
  evaluateCondition,
  isAnswered,
  missingRequirements,
  requirementMessages,
} from './rules';

interface Case {
  id: string;
  why?: string;
  rules: unknown[];
  answers: Answers;
  expect: string[];
}

const CORPUS_PATH = resolvePath(
  dirname(fileURLToPath(import.meta.url)),
  '../../../forms/contract/validation-cases.json',
);

const corpus = JSON.parse(readFileSync(CORPUS_PATH, 'utf-8')) as {
  version: number;
  cases: Case[];
};

describe('el contrato compartido', () => {
  it.each(corpus.cases.map((item) => [item.id, item] as const))(
    '%s',
    (_id, item) => {
      const found = missingRequirements(item.rules, item.answers);
      expect(found.map((missing) => missing.field), item.why ?? item.id).toEqual(item.expect);
    },
  );

  it('el corpus está sano', () => {
    // Un corpus con ids repetidos o casos vacíos es un corpus que no compara nada.
    const ids = corpus.cases.map((item) => item.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(corpus.cases.length).toBeGreaterThanOrEqual(25);
    for (const item of corpus.cases) {
      expect(Array.isArray(item.rules)).toBe(true);
      expect(Array.isArray(item.expect)).toBe(true);
    }
  });

  it('el corpus distingue la implementación ingenua de la correcta', () => {
    // Un corpus que cualquier implementación razonable pasa no mide nada. La ingenua es la que
    // se escribe de primera intención en JavaScript: `if (!value)` y `==`.
    function naive(rules: unknown[], answers: Answers): string[] {
      const problems: string[] = [];
      for (const rule of rules) {
        const when = (rule as { when?: Record<string, unknown> }).when ?? {};
        if (!('==' in when)) continue;
        const [left, right] = when['=='] as [unknown, unknown];
        const read = (token: unknown): unknown =>
          token !== null && typeof token === 'object' && 'var' in token
            ? answers[(token as { var: string }).var]
            : token;
        if (read(left) != read(right)) continue;
        for (const field of (rule as { require?: string[] }).require ?? []) {
          if (!answers[field]) problems.push(field);
        }
      }
      return problems;
    }

    const disagreements = corpus.cases.filter((item) => {
      const got = naive(item.rules, item.answers);
      return JSON.stringify(got) !== JSON.stringify(item.expect);
    });
    expect(disagreements.length).toBeGreaterThan(0);
  });
});

describe('lo que el corpus no puede expresar', () => {
  it('el mensaje de la regla viaja con el campo, y hay uno por defecto', () => {
    const rules = [
      {
        when: { '==': [{ var: 'final_state' }, 'no_resuelto'] },
        require: ['cause'],
        message: 'Indique la causa cuando el trabajo no quedó resuelto',
      },
      { when: { '==': [{ var: 'stage' }, 'cierre'] }, require: ['signposted'] },
    ];
    const answers = { final_state: 'no_resuelto', stage: 'cierre' };
    expect(requirementMessages(rules, answers)).toEqual([
      'Indique la causa cuando el trabajo no quedó resuelto',
      'signposted: es obligatorio en este caso',
    ]);
  });

  it.each([
    [0, true],
    [false, true],
    [true, true],
    ['x', true],
    ['', false],
    ['   ', false],
    [null, false],
    [undefined, false],
    [[], false],
    [[1], true],
    [{}, false],
    [{ a: 1 }, true],
  ])('qué cuenta como respuesta: %o', (value, answered) => {
    expect(isAnswered(value)).toBe(answered);
  });

  it('un booleano no se compara igual a cero ni a uno', () => {
    // `false == 0` en JavaScript, y eso haría coincidir «¿señalizado?» con un conteo.
    expect(evaluateCondition({ '==': [{ var: 'signposted' }, 1] }, { signposted: true })).toBe(
      false,
    );
    expect(evaluateCondition({ '==': [{ var: 'count' }, false] }, { count: 0 })).toBe(false);
  });

  it('una lista de reglas que no es una lista no revienta', () => {
    // El catálogo llega por la red; un payload raro no puede dejar la pantalla en blanco.
    expect(missingRequirements(null, {})).toEqual([]);
    expect(missingRequirements('texto', {})).toEqual([]);
    expect(missingRequirements([null, 3, 'x'], {})).toEqual([]);
  });
});
