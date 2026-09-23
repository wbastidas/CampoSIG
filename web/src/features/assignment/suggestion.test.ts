/**
 * Las decisiones de la sugerencia de cuadrilla (RF-021).
 *
 * Lo que se prueba es lo que haría que un planificador siguiera un número sin poder discutirlo: un
 * puntaje sin sus razones, un factor de cero escondido, y una diferencia de dos puntos presentada
 * como una recomendación.
 */

import { describe, expect, it } from 'vitest';

import type { CrewSuggestion, SuggestedCrew } from '../../api/planning';
import {
  candidateHeadline,
  CLEAR_MARGIN,
  exclusionLines,
  hasCandidates,
  marginAdvice,
  reasonLines,
  requirementLine,
  signedPoints,
} from './suggestion';

function candidate(code: string, score: number, reasons: SuggestedCrew['reasons'] = []): SuggestedCrew {
  return { crew_id: `id-${code}`, code, name: `Cuadrilla ${code}`, score, reasons };
}

function suggestion(overrides: Partial<CrewSuggestion> = {}): CrewSuggestion {
  return {
    work_order_id: 'ot-1',
    required_competencies: [],
    candidates: [],
    excluded: [],
    caveats: [],
    ...overrides,
  };
}

describe('signedPoints', () => {
  it('un aporte positivo lleva su signo', () => {
    expect(signedPoints(40)).toBe('+40');
  });

  it('un cero se lee como cero y no como «+0»', () => {
    expect(signedPoints(0)).toBe('0');
  });

  it('un descuento conserva su signo', () => {
    expect(signedPoints(-5)).toBe('-5');
  });
});

describe('reasonLines', () => {
  it('cada razón viaja con su puntaje y su frase', () => {
    const lines = reasonLines(
      candidate('C-01', 40, [{ factor: 'zona', points: 40, detail: 'cae en NORTE' }]),
    );
    expect(lines[0]).toEqual({
      factor: 'zona',
      points: '+40',
      detail: 'cae en NORTE',
      empty: false,
    });
  });

  it('un factor que no aportó nada se muestra, marcado', () => {
    // Si se ocultara, una cuadrilla con 40 de cuatro factores se leería como una con 40 de uno.
    const lines = reasonLines(
      candidate('C-01', 0, [{ factor: 'cercanía', points: 0, detail: 'no se puede medir' }]),
    );
    expect(lines[0]?.empty).toBe(true);
    expect(lines).toHaveLength(1);
  });
});

describe('candidateHeadline', () => {
  it('lleva el puesto, el código y el puntaje', () => {
    expect(candidateHeadline(candidate('C-01', 72), 1)).toBe(
      '1. C-01 · Cuadrilla C-01 — 72 puntos',
    );
  });
});

describe('hasCandidates y requirementLine', () => {
  it('sin candidatas la pantalla no muestra una lista vacía', () => {
    expect(hasCandidates(suggestion())).toBe(false);
    expect(hasCandidates(suggestion({ candidates: [candidate('C-01', 10)] }))).toBe(true);
  });

  it('aguanta no haber pedido nada todavía', () => {
    expect(hasCandidates(null)).toBe(false);
    expect(requirementLine(null)).toBeNull();
  });

  it('cuando el formulario exige competencias, se dicen', () => {
    expect(requirementLine(suggestion({ required_competencies: ['APG', 'ALTURA'] }))).toBe(
      'Este formulario exige: APG, ALTURA.',
    );
  });

  it('cuando no exige nada, no se inventa una frase', () => {
    expect(requirementLine(suggestion())).toBeNull();
  });
});

describe('exclusionLines', () => {
  it('ordena por código, para que la lista se lea igual cada vez', () => {
    const found = exclusionLines(
      suggestion({
        excluded: [
          { crew_id: 'b', code: 'C-02', name: 'B', reason: 'sin APG' },
          { crew_id: 'a', code: 'C-01', name: 'A', reason: 'sin APG' },
        ],
      }),
    );
    expect(found.map((item) => item.code)).toEqual(['C-01', 'C-02']);
  });

  it('sin descartadas devuelve nada', () => {
    expect(exclusionLines(suggestion())).toEqual([]);
    expect(exclusionLines(null)).toEqual([]);
  });
});

describe('marginAdvice', () => {
  it('con una sola candidata no hay margen que comentar', () => {
    expect(marginAdvice(suggestion({ candidates: [candidate('C-01', 70)] }))).toBeNull();
  });

  it('una diferencia clara se dice como tal', () => {
    const advice = marginAdvice(
      suggestion({ candidates: [candidate('C-01', 80), candidate('C-02', 80 - CLEAR_MARGIN)] }),
    );
    expect(advice).toContain('por delante');
  });

  it('una diferencia pequeña no se presenta como recomendación', () => {
    // Dos puntos son ruido de redondeo; venderlos como consejo sería prestarle autoridad al número.
    const advice = marginAdvice(
      suggestion({ candidates: [candidate('C-01', 70), candidate('C-02', 68)] }),
    );
    expect(advice).toContain('parejas');
    expect(advice).toContain('lo que sepa del terreno');
  });
});
