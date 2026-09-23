/**
 * Cómo se lee el tablero operativo (RF-130).
 *
 * Las duraciones son donde un tablero operativo engaña con más facilidad, así que casi todo lo que
 * se prueba aquí es sobre ellas: una duración en la unidad equivocada no se puede leer, una mediana
 * suprimida pintada como raya parece que no hubo trabajo, y un tramo con trabajos en curso parece
 * más lento de lo que es si la pantalla no dice cuántos siguen fuera.
 */

import { describe, expect, it } from 'vitest';

import type { Leg, OperationalBoard } from '../../api/analytics';
import {
  duration,
  freshness,
  legCaveats,
  legHeadline,
  legTail,
  openTotal,
  orderedStates,
  stateLabel,
} from './board';

function leg(overrides: Partial<Leg> = {}): Leg {
  return {
    key: 'despacho_llegada',
    label: 'Despacho → llegada',
    measured: 20,
    in_progress: 0,
    unrecorded: 0,
    median_minutes: 45,
    p90_minutes: 120,
    worst_minutes: 300,
    min_sample: 5,
    ...overrides,
  };
}

function board(overrides: Partial<OperationalBoard> = {}): OperationalBoard {
  return {
    computed_at: '2026-09-20T12:00:00+00:00',
    since: '2026-08-21T12:00:00+00:00',
    by_state: {},
    sla: { overdue: 0, due_soon: 0, due_soon_hours: 8, without_sla: 0 },
    legs: [],
    crews: [],
    ...overrides,
  };
}

describe('las duraciones se escriben como se leen en Ecuador', () => {
  it('minutos por debajo de una hora', () => {
    expect(duration(45)).toBe('45 min');
  });

  it('horas con coma decimal por encima', () => {
    // «1.5 h» se lee como quince aquí: es la misma familia del «6,480 m» de las distancias.
    expect(duration(90)).toBe('1,5 h');
    expect(duration(90)).not.toContain('.');
  });

  it('días cuando pasa de uno', () => {
    expect(duration(60 * 36)).toBe('1,5 d');
  });

  it('sin dato, una raya y no un cero', () => {
    expect(duration(null)).toBe('—');
  });
});

describe('el titular de un tramo', () => {
  it('da la mediana con la muestra que la sostiene', () => {
    expect(legHeadline(leg())).toContain('Mediana 45 min sobre 20');
  });

  it('con muestra pequeña dice cuántos trabajos faltan, no una raya', () => {
    const said = legHeadline(leg({ measured: 2, median_minutes: null }));
    expect(said).toContain('2 de 5');
    expect(said).not.toBe('—');
  });

  it('sin trabajos completos lo dice, que no es lo mismo que «rápido»', () => {
    expect(legHeadline(leg({ measured: 0, median_minutes: null }))).toContain('Sin trabajos');
  });
});

describe('lo que el titular no cubre', () => {
  it('los trabajos en curso se dicen, y se dice que no cuentan como cero', () => {
    // Contarlos arrastraría el promedio hacia abajo justo cuando las cuadrillas están ocupadas.
    const lines = legCaveats(leg({ in_progress: 4 }));
    expect(lines[0]).toContain('4 en curso');
    expect(lines[0]).toContain('no cuentan como cero');
  });

  it('los trabajos sin registro se dicen aparte: son cosas distintas', () => {
    // Uno es la operación funcionando; el otro es la medición fallando.
    const lines = legCaveats(leg({ in_progress: 2, unrecorded: 7 }));
    expect(lines).toHaveLength(2);
    expect(lines[1]).toContain('7 sin registro');
  });

  it('sin salvedades no molesta con ninguna', () => {
    expect(legCaveats(leg())).toEqual([]);
  });

  it('la cola se muestra con el peor caso, que la mediana esconde', () => {
    const said = legTail(leg({ p90_minutes: 57, worst_minutes: 300 }));
    expect(said).toContain('57 min');
    expect(said).toContain('5,0 h');
  });

  it('sin percentil no se inventa una cola', () => {
    expect(legTail(leg({ p90_minutes: null }))).toBeNull();
  });
});

describe('los estados', () => {
  it('se ordenan por lo que se está moviendo primero', () => {
    const rows = orderedStates({ cerrada: 5, en_ejecucion: 2, planificada: 9 });
    expect(rows.map((row) => row.state)).toEqual(['en_ejecucion', 'planificada', 'cerrada']);
  });

  it('un estado desconocido aparece al final y no desaparece', () => {
    // Un estado que la pantalla no conoce es uno que alguien añadió, y esconderlo escondería el
    // trabajo que está parado en él.
    const rows = orderedStates({ en_ejecucion: 1, estado_nuevo: 4 });
    expect(rows.at(-1)).toEqual({ state: 'estado_nuevo', count: 4 });
    expect(stateLabel('estado_nuevo')).toBe('estado_nuevo');
  });

  it('las abiertas no incluyen lo terminado', () => {
    const rows = board({
      by_state: { en_ejecucion: 3, planificada: 2, aprobada: 10, cerrada: 40, anulada: 1 },
    });
    expect(openTotal(rows)).toBe(5);
  });
});

describe('la frescura del tablero', () => {
  it('dice cuántos minutos tiene el dato', () => {
    // RF-130 pide datos de menos de cinco minutos: quien mira tiene que poder saber si los suyos
    // lo son, porque un tablero que se refresca en silencio parece igual de fresco cuando el
    // refresco lleva una hora fallando.
    const said = freshness('2026-09-20T12:00:00+00:00', new Date('2026-09-20T12:07:00+00:00'));
    expect(said).toContain('7 minuto');
  });

  it('recién calculado no dice «hace 0 minutos»', () => {
    const said = freshness('2026-09-20T12:00:00+00:00', new Date('2026-09-20T12:00:10+00:00'));
    expect(said).toContain('menos de un minuto');
  });

  it('un reloj adelantado no produce un tiempo negativo', () => {
    const said = freshness('2026-09-20T12:00:00+00:00', new Date('2026-09-20T11:59:00+00:00'));
    expect(said).not.toContain('-');
  });
});
