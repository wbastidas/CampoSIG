/**
 * Los juicios del mapa de despacho (RF-020).
 *
 * El mapa contesta «¿quién está más cerca de esta falla?», y lo que se prueba aquí es lo que evita
 * que la conteste mal: que una posición vieja se vea vieja, que una precisión de 900 m no se
 * presente como una calle, y que un teléfono sin trabajo de cuadrilla no lleve la etiqueta de otra.
 */

import { describe, expect, it } from 'vitest';

import type { CrewPositionCollection, CrewPositionFeature } from '../../api/dispatch';
import {
  accuracyLabel,
  ageLabel,
  confidenceOf,
  crewLabel,
  headline,
  positionCaveats,
  rows,
} from './positions';

function feature(overrides: Partial<CrewPositionFeature['properties']> = {}): CrewPositionFeature {
  return {
    type: 'Feature',
    id: overrides.device_key ?? 'phone-1',
    geometry: { type: 'Point', coordinates: [-79.9, -2.17] },
    properties: {
      device_key: 'phone-1',
      user_sub: 'kc|tecnico.demo',
      accuracy_m: 8,
      reported_at: '2026-09-24T15:00:00Z',
      minutes_old: 10,
      stale: false,
      doubtful: false,
      crews: [{ crew_id: 'c1', code: 'C-01', name: 'Cuadrilla norte' }],
      ...overrides,
    },
  };
}

function collection(...features: CrewPositionFeature[]): CrewPositionCollection {
  return {
    type: 'FeatureCollection',
    features,
    stale_after_minutes: 120,
    doubtful_accuracy_m: 200,
  };
}

describe('ageLabel', () => {
  it('dice la edad en las unidades en que se piensa un despacho', () => {
    expect(ageLabel(0)).toBe('ahora mismo');
    expect(ageLabel(25)).toBe('hace 25 min');
    expect(ageLabel(60)).toBe('hace 1 h');
    expect(ageLabel(190)).toBe('hace 3 h 10 min');
    expect(ageLabel(60 * 26)).toBe('hace más de un día');
    expect(ageLabel(60 * 50)).toBe('hace 2 días');
  });
});

describe('confidenceOf', () => {
  it('una posición fresca y precisa es reciente', () => {
    expect(confidenceOf(feature())).toBe('reciente');
  });

  it('una precisión mala la vuelve dudosa', () => {
    expect(confidenceOf(feature({ doubtful: true }))).toBe('dudosa');
  });

  it('vieja gana a dudosa: una hora ya no dice dónde está la cuadrilla', () => {
    expect(confidenceOf(feature({ stale: true, doubtful: true }))).toBe('vieja');
  });
});

describe('crewLabel', () => {
  it('nombra la cuadrilla cuyo trabajo lleva el teléfono', () => {
    expect(crewLabel(feature())).toBe('C-01 — Cuadrilla norte');
  });

  it('un teléfono con trabajo de dos cuadrillas las nombra las dos', () => {
    const label = crewLabel(
      feature({
        crews: [
          { crew_id: 'c1', code: 'C-01', name: 'Cuadrilla norte' },
          { crew_id: 'c2', code: 'C-02', name: 'Cuadrilla sur' },
        ],
      }),
    );

    expect(label).toContain('C-01');
    expect(label).toContain('C-02');
  });

  it('sin trabajo de cuadrilla lo dice, en vez de la etiqueta de otra', () => {
    expect(crewLabel(feature({ crews: [] }))).toBe('Sin trabajo de cuadrilla');
  });
});

describe('rows', () => {
  it('pone primero lo más fresco, que es lo que se puede despachar', () => {
    const view = rows(
      collection(
        feature({ device_key: 'viejo', minutes_old: 200, stale: true }),
        feature({ device_key: 'fresco', minutes_old: 3 }),
      ),
    );

    expect(view.map((row) => row.feature.properties.device_key)).toEqual(['fresco', 'viejo']);
    expect(view[0]?.ageLabel).toBe('hace 3 min');
    expect(view[1]?.confidence).toBe('vieja');
  });

  it('sin datos no inventa filas', () => {
    expect(rows(null)).toEqual([]);
  });
});

describe('positionCaveats', () => {
  it('dice cuántas posiciones son viejas y con qué umbral, en horas', () => {
    const caveats = positionCaveats(
      collection(feature({ minutes_old: 200, stale: true }), feature()),
    );

    expect(caveats[0]).toContain('1 de 2');
    expect(caveats[0]).toContain('2 h');
  });

  it('cuenta las dudosas aparte, y no cuenta dos veces una vieja y dudosa', () => {
    const caveats = positionCaveats(
      collection(feature({ stale: true, doubtful: true }), feature({ doubtful: true })),
    );

    expect(caveats).toHaveLength(2);
    expect(caveats[1]).toContain('1 posiciones');
    expect(caveats[1]).toContain('200 m');
  });

  it('con todo fresco no advierte nada', () => {
    expect(positionCaveats(collection(feature()))).toEqual([]);
  });
});

describe('headline', () => {
  it('distingue cuántas hay de cuántas sirven', () => {
    expect(headline(collection(feature(), feature({ stale: true })))).toBe(
      '2 teléfonos con posición; 1 reportaron hace poco.',
    );
  });

  it('sin posiciones lo dice, en vez de un cero suelto', () => {
    expect(headline(collection())).toContain('Ningún teléfono');
    expect(headline(null)).toContain('Ningún teléfono');
  });
});

describe('accuracyLabel', () => {
  it('lleva su unidad', () => {
    expect(accuracyLabel(feature({ accuracy_m: 8.4 }))).toBe('± 8 m');
  });

  it('una precisión que el teléfono no reportó no se inventa', () => {
    expect(accuracyLabel(feature({ accuracy_m: null }))).toBe('Precisión no reportada');
  });
});
