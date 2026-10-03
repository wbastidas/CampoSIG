/**
 * El corpus de cédulas (RF-046), en la web. Los otros dos tercios del contrato están en
 * `backend/tests/unit/test_rf046_cedula_contract.py` y en `core:sync`'s `CedulaTest.kt`.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import { cedulaFields, isValidCedula } from './identification';

interface Case {
  id: string;
  value: string;
  valid: boolean;
}

const corpus = JSON.parse(
  readFileSync(resolve(__dirname, '../../../forms/contract/identification-cases.json'), 'utf-8'),
) as { cases: Case[] };

describe('RF-046: la cédula del cliente', () => {
  it.each(corpus.cases.map((item) => [item.id, item] as const))('%s', (_id, item) => {
    expect(isValidCedula(item.value)).toBe(item.valid);
  });

  it('el corpus está sano', () => {
    const ids = corpus.cases.map((item) => item.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(corpus.cases.filter((item) => item.valid).length).toBeGreaterThanOrEqual(5);
  });

  it('los campos con el formato salen del esquema, no de su nombre', () => {
    expect(
      cedulaFields({
        properties: {
          customer_id: { type: 'string', format: 'ec-cedula' },
          customer_signature: { type: 'string', format: 'uri' },
        },
      }),
    ).toEqual(['customer_id']);
  });
});
