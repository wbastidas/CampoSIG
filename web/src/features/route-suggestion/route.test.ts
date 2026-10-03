/**
 * Los juicios del panel de ruta sugerida (RF-025).
 *
 * Lo que se prueba: que el ahorro se diga con las dos distancias detrás y no como un porcentaje
 * suelto, y que no se pueda pedir una ruta con menos de dos OT.
 */

import { describe, expect, it } from 'vitest';

import type { RouteSuggestion } from '../../api/routing';
import { km, requestProblems, savingsHeadline } from './route';

function suggestion(overrides: Partial<RouteSuggestion> = {}): RouteSuggestion {
  return {
    stops: [],
    total_distance_m: 12_000,
    naive_distance_m: 20_000,
    start: null,
    caveats: [],
    ...overrides,
  };
}

describe('km', () => {
  it('usa coma decimal, la de Ecuador (regla 11)', () => {
    expect(km(12_340)).toBe('12,3');
  });
});

describe('savingsHeadline', () => {
  it('dice las dos distancias, nunca solo el porcentaje', () => {
    const headline = savingsHeadline(
      suggestion({ total_distance_m: 12_000, naive_distance_m: 20_000 }),
    );

    expect(headline).toContain('12,0 km');
    expect(headline).toContain('20,0 km');
    expect(headline).toContain('40 %');
  });

  it('cuando el pedido ya era el mejor orden, lo dice en vez de un 0 % vacío', () => {
    const headline = savingsHeadline(
      suggestion({ total_distance_m: 15_000, naive_distance_m: 15_000 }),
    );

    expect(headline).toContain('ya era el mejor orden');
  });

  it('sin comparación válida, dice solo la distancia', () => {
    expect(savingsHeadline(suggestion({ naive_distance_m: 0 }))).toBe('12,0 km');
  });
});

describe('requestProblems', () => {
  it('con menos de dos OT no se puede pedir', () => {
    expect(requestProblems(0)).toHaveLength(1);
    expect(requestProblems(1)).toHaveLength(1);
  });

  it('con dos o más, no hay problema', () => {
    expect(requestProblems(2)).toEqual([]);
    expect(requestProblems(5)).toEqual([]);
  });
});
