/**
 * Los juicios del tablero de consignaciones (RF-024).
 *
 * Se prueba lo que decide si la cuadrilla puede trabajar y si la línea está desenergizada para
 * nada: que el número sea la autoridad y no el estado, que una otorgada sin OT se vea, que una
 * ventana cerrada con el descargo vigente se diga, y que quien pidió no otorgue.
 */

import { describe, expect, it } from 'vitest';

import type { OutageList, OutageRequestRow } from '../../api/outages';
import {
  authorityLine,
  awaitingCount,
  canDecide,
  canHandBack,
  decisionAdvice,
  decisionProblems,
  EMPTY_DECISION,
  isOwnRequest,
  overdueWarning,
  requestProblems,
  rows,
  stateLabel,
  unusedWarning,
  windowLabel,
} from './outages';

const NOW = new Date('2026-09-26T18:00:00Z');

function request(overrides: Partial<OutageRequestRow> = {}): OutageRequestRow {
  return {
    id: 'c1',
    number: null,
    state: 'solicitada',
    equipment: 'Alimentador 04BH070T11, tramo sur',
    feeder_code: '04BH070T11',
    substation_code: null,
    window_start: '2026-09-26T11:00:00Z',
    window_end: '2026-09-26T17:00:00Z',
    requested_by: 'kc|planificador.demo',
    decided_by: null,
    decided_at: null,
    returned_at: null,
    returned_by: null,
    note: null,
    grants_permit: false,
    orders: 0,
    unused: false,
    ...overrides,
  };
}

function list(...requests: OutageRequestRow[]): OutageList {
  const counts: Record<string, number> = {};
  for (const row of requests) counts[row.state] = (counts[row.state] ?? 0) + 1;
  return { counts, requests };
}

const GRANTED = request({
  id: 'c2',
  state: 'aprobada',
  number: 'DESC-2026-0771',
  grants_permit: true,
  decided_by: 'kc|centro.control',
  orders: 3,
});

describe('authorityLine', () => {
  it('con número dice que habilita el permiso, y lo nombra', () => {
    expect(authorityLine(GRANTED)).toContain('DESC-2026-0771');
    expect(authorityLine(GRANTED)).toContain('F-TR-02');
  });

  it('otorgada sin número no habilita nada, y lo dice', () => {
    // Una fila así solo llega por carga directa o migración a medias, y es justo la que engaña:
    // el estado dice «aprobada» y no abre el permiso.
    const halfway = request({ state: 'aprobada', number: null, grants_permit: false });

    expect(authorityLine(halfway)).toContain('no habilita');
    expect(authorityLine(halfway)).toContain('autoridad');
  });

  it('una solicitud no habilita el permiso', () => {
    expect(authorityLine(request())).toBe('No habilita el F-TR-02');
  });
});

describe('rows', () => {
  it('pone primero lo que espera decisión, que es la cola del Centro de Control', () => {
    const view = rows(list(GRANTED, request()), NOW);

    expect(view[0]?.request.id).toBe('c1');
    expect(view[0]?.awaiting).toBe(true);
  });

  it('marca la otorgada cuya ventana ya cerró: el equipo puede estar energizado', () => {
    const view = rows(
      list(
        request({
          id: 'c3',
          state: 'aprobada',
          number: 'DESC-1',
          grants_permit: true,
          window_end: '2026-09-26T12:00:00Z',
        }),
      ),
      NOW,
    );

    expect(view[0]?.overdue).toBe(true);
  });

  it('una ventana abierta todavía no está vencida', () => {
    const view = rows(
      list(
        request({
          state: 'aprobada',
          number: 'DESC-1',
          grants_permit: true,
          window_end: '2026-09-26T23:00:00Z',
        }),
      ),
      NOW,
    );

    expect(view[0]?.overdue).toBe(false);
  });

  it('una negada con la ventana pasada no es una vigente vencida', () => {
    const view = rows(
      list(request({ state: 'rechazada', window_end: '2026-09-26T12:00:00Z' })),
      NOW,
    );

    expect(view[0]?.overdue).toBe(false);
  });

  it('sin datos no inventa filas', () => {
    expect(rows(null, NOW)).toEqual([]);
  });
});

describe('unusedWarning', () => {
  it('dice el conteo: una es una llamada y seis son un problema', () => {
    const one = unusedWarning(rows(list({ ...GRANTED, unused: true }), NOW));
    const two = unusedWarning(
      rows(list({ ...GRANTED, unused: true }, { ...GRANTED, id: 'c9', unused: true }), NOW),
    );

    expect(one).toContain('Una consignación otorgada');
    expect(two).toContain('2 consignaciones');
  });

  it('calla cuando todas las otorgadas tienen trabajo', () => {
    expect(unusedWarning(rows(list(GRANTED), NOW))).toBeNull();
  });
});

describe('overdueWarning', () => {
  it('avisa de la ventana cerrada y dice qué hacer', () => {
    const warning = overdueWarning(
      rows(
        list(
          request({
            state: 'aprobada',
            number: 'DESC-1',
            grants_permit: true,
            window_end: '2026-09-26T12:00:00Z',
          }),
        ),
        NOW,
      ),
    );

    expect(warning).toContain('devuélvala');
  });
});

describe('quién puede qué', () => {
  it('solo se decide lo que está solicitado: una decisión no se toma dos veces', () => {
    expect(canDecide(rows(list(request()), NOW)[0]!)).toBe(true);
    expect(canDecide(rows(list(GRANTED), NOW)[0]!)).toBe(false);
  });

  it('solo se devuelve lo otorgado', () => {
    expect(canHandBack(rows(list(GRANTED), NOW)[0]!)).toBe(true);
    expect(canHandBack(rows(list(request()), NOW)[0]!)).toBe(false);
  });

  it('quien pidió no otorga, y se sabe antes del 403 del servidor', () => {
    const row = rows(list(request()), NOW)[0]!;

    expect(isOwnRequest(row, 'kc|planificador.demo')).toBe(true);
    expect(isOwnRequest(row, 'kc|centro.control')).toBe(false);
    expect(isOwnRequest(row, null)).toBe(false);
  });
});

describe('decisionProblems', () => {
  it('otorgar sin número no sale: el número es la autoridad', () => {
    expect(decisionProblems({ ...EMPTY_DECISION, decision: 'otorgar' })).toHaveLength(1);
    expect(
      decisionProblems({ ...EMPTY_DECISION, decision: 'otorgar', number: 'DESC-2026-0771' }),
    ).toEqual([]);
  });

  it('negar sin motivo no sale: manda al planificador al teléfono', () => {
    expect(decisionProblems({ ...EMPTY_DECISION, decision: 'negar' })).toHaveLength(1);
    expect(decisionProblems({ ...EMPTY_DECISION, decision: 'negar', note: 'hay carga' })).toEqual(
      [],
    );
  });

  it('sin elegir decisión tampoco', () => {
    expect(decisionProblems(EMPTY_DECISION)).toHaveLength(1);
  });
});

describe('decisionAdvice', () => {
  it('dice qué se va a habilitar, con el número y la ventana', () => {
    const row = rows(list(request()), NOW)[0]!;
    const advice = decisionAdvice(row, {
      decision: 'otorgar',
      number: 'DESC-2026-0771',
      note: '',
    });

    expect(advice).toContain('DESC-2026-0771');
    expect(advice).toContain('F-TR-02');
  });

  it('sin decisión no adelanta nada', () => {
    expect(decisionAdvice(rows(list(request()), NOW)[0]!, EMPTY_DECISION)).toBeNull();
  });
});

describe('requestProblems', () => {
  it('una ventana invertida no se envía', () => {
    const problems = requestProblems({
      equipment: 'Tramo sur',
      windowStart: '2026-09-26T12:00',
      windowEnd: '2026-09-26T06:00',
    });

    expect(problems).toEqual(['La ventana termina antes de empezar.']);
  });

  it('sin equipo y sin ventana lo dice todo junto', () => {
    expect(requestProblems({ equipment: '  ', windowStart: '', windowEnd: '' })).toHaveLength(2);
  });

  it('una solicitud completa no tiene problemas', () => {
    expect(
      requestProblems({
        equipment: 'Alimentador sur',
        windowStart: '2026-09-26T06:00',
        windowEnd: '2026-09-26T12:00',
      }),
    ).toEqual([]);
  });
});

describe('windowLabel', () => {
  it('una ventana del mismo día dice el día una vez, en hora de Guayaquil', () => {
    // 11:00 UTC son 06:00 en Guayaquil (UTC-5): la hora que el Centro de Control dice por radio.
    expect(windowLabel(request())).toBe('26/09/2026, 06:00 a 12:00');
  });

  it('una ventana que cruza la medianoche dice los dos días', () => {
    const label = windowLabel(
      request({ window_start: '2026-09-26T23:00:00Z', window_end: '2026-09-27T09:00:00Z' }),
    );

    expect(label).toContain('26/09/2026');
    expect(label).toContain('27/09/2026');
  });
});

describe('awaitingCount y stateLabel', () => {
  it('el conteo sale de lo que dice el servidor, no de la página visible', () => {
    expect(awaitingCount(list(request(), GRANTED))).toBe(1);
    expect(awaitingCount(null)).toBe(0);
  });

  it('traduce los estados y deja pasar uno desconocido', () => {
    expect(stateLabel('aprobada')).toBe('Otorgada');
    expect(stateLabel('vencida')).toBe('Vencida');
    expect(stateLabel('otro')).toBe('otro');
  });
});
