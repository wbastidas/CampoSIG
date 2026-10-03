/**
 * Lógica de la pantalla de integraciones (RF-125).
 *
 * La regla que es fácil invertir: **un evento pendiente no es un problema**, se reintenta
 * solo. Un evento fallido ya se rindió y no va a pasar nada hasta que alguien intervenga. Así
 * que "fallido" manda sobre "muchos pendientes" siempre, y eso tiene su test.
 */

import { describe, expect, it } from 'vitest';

import type { ConnectorHealth, IntegrationEvent } from '../../api/integrations';
import {
  canRetry,
  connectorHealth,
  nextAttemptIn,
  shortError,
  sortConnectors,
  sortEvents,
  summarise,
} from './ledger';

function connector(overrides: Partial<ConnectorHealth> = {}): ConnectorHealth {
  return {
    connector: 'sistema_ot',
    pending: 0,
    delivered: 12,
    waiting_for_a_person: 0,
    abandoned: 0,
    last_error: null,
    last_exchange_at: '2026-09-22T10:00:00Z',
    ...overrides,
  };
}

function event(overrides: Partial<IntegrationEvent> = {}): IntegrationEvent {
  return {
    id: 'e1',
    connector: 'call_center',
    direction: 'salida',
    kind: 'reclamo_cerrado',
    status: 'pendiente',
    idempotency_key: 'cierre:REC-1',
    external_ref: 'REC-1',
    work_order_id: null,
    attempts: 0,
    last_error: null,
    next_attempt_at: '2026-09-22T10:05:00Z',
    created_at: '2026-09-22T10:00:00Z',
    delivered_at: null,
    needs_attention: false,
    payload: {},
    response: null,
    ...overrides,
  };
}

describe('salud de un conector', () => {
  it('cualquier cosa esperando a una persona está roto, por pequeño que sea el número', () => {
    // Un solo reclamo sin cerrar es un cliente cuyo reclamo sigue abierto.
    expect(connectorHealth(connector({ waiting_for_a_person: 1 }))).toBe('roto');
  });

  it('eventos pendientes son el sistema funcionando, no un fallo', () => {
    expect(connectorHealth(connector({ pending: 40 }))).toBe('atencion');
  });

  it('sin pendientes ni fallidos está al día', () => {
    expect(connectorHealth(connector())).toBe('sano');
  });

  it('un fallido manda sobre muchos pendientes', () => {
    const rows = [
      connector({ connector: 'arcgis', pending: 99 }),
      connector({ connector: 'call_center', waiting_for_a_person: 1 }),
      connector({ connector: 'sistema_ot' }),
    ];
    expect(sortConnectors(rows).map((r) => r.connector)).toEqual([
      'call_center',
      'arcgis',
      'sistema_ot',
    ]);
  });

  it('no muta el arreglo recibido', () => {
    const rows = [connector({ connector: 'arcgis' }), connector({ connector: 'call_center', waiting_for_a_person: 1 })];
    const before = rows.map((r) => r.connector);
    sortConnectors(rows);
    expect(rows.map((r) => r.connector)).toEqual(before);
  });
});

describe('orden de los eventos', () => {
  it('fallidos primero y, dentro del grupo, el más reciente arriba', () => {
    const rows = [
      event({ id: 'a', status: 'entregado', created_at: '2026-09-22T09:00:00Z' }),
      event({ id: 'b', status: 'fallido', created_at: '2026-09-22T09:10:00Z' }),
      event({ id: 'c', status: 'fallido', created_at: '2026-09-22T09:30:00Z' }),
      event({ id: 'd', status: 'pendiente', created_at: '2026-09-22T09:20:00Z' }),
      event({ id: 'e', status: 'descartado', created_at: '2026-09-22T09:40:00Z' }),
    ];
    expect(sortEvents(rows).map((r) => r.id)).toEqual(['c', 'b', 'd', 'e', 'a']);
  });

  it('una fecha ausente no revienta el orden', () => {
    const rows = [event({ id: 'a', created_at: null }), event({ id: 'b' })];
    expect(sortEvents(rows).map((r) => r.id)).toEqual(['b', 'a']);
  });
});

describe('reintento', () => {
  it('solo tiene sentido sobre lo que ya se rindió', () => {
    expect(canRetry(event({ status: 'fallido' }))).toBe(true);
    expect(canRetry(event({ status: 'descartado' }))).toBe(true);
    expect(canRetry(event({ status: 'pendiente' }))).toBe(false);
    expect(canRetry(event({ status: 'entregado' }))).toBe(false);
  });
});

describe('resumen', () => {
  it('cuenta lo que hay que atender', () => {
    const summary = summarise(
      [connector({ waiting_for_a_person: 2 }), connector({ connector: 'arcgis' })],
      [
        event({ status: 'fallido' }),
        event({ status: 'fallido' }),
        event({ status: 'pendiente' }),
        event({ status: 'entregado' }),
        event({ status: 'descartado' }),
      ],
    );
    expect(summary.total).toBe(5);
    expect(summary.waitingForAPerson).toBe(2);
    expect(summary.pending).toBe(1);
    expect(summary.delivered).toBe(1);
    expect(summary.abandoned).toBe(1);
    expect(summary.connectorsBroken).toBe(1);
  });

  it('una bitácora vacía no revienta', () => {
    expect(summarise([], []).total).toBe(0);
  });
});

describe('presentación del error', () => {
  it('se queda con la primera línea, que es la que identifica el fallo', () => {
    const row = event({ last_error: '503 Service Unavailable\n  en el proxy corporativo' });
    expect(shortError(row)).toBe('503 Service Unavailable');
  });

  it('recorta sin ocultar de qué error se trata', () => {
    const row = event({ last_error: 'x'.repeat(200) });
    expect(shortError(row, 20)).toHaveLength(20);
    expect(shortError(row, 20)?.endsWith('…')).toBe(true);
  });

  it('sin error, nada', () => {
    expect(shortError(event())).toBeNull();
  });
});

describe('próximo intento', () => {
  const now = new Date('2026-09-22T10:00:00Z');

  it('minutos y horas', () => {
    expect(nextAttemptIn(event({ next_attempt_at: '2026-09-22T10:04:00Z' }), now)).toBe('en 4 min');
    expect(nextAttemptIn(event({ next_attempt_at: '2026-09-22T12:00:00Z' }), now)).toBe('en 2 h');
  });

  it('un intento vencido está para ahora', () => {
    expect(nextAttemptIn(event({ next_attempt_at: '2026-09-22T09:00:00Z' }), now)).toBe('ahora');
  });

  it('sin próximo intento —fallido o entregado— no hay nada que decir', () => {
    expect(nextAttemptIn(event({ next_attempt_at: null }), now)).toBeNull();
  });

  it('una fecha inválida se trata como desconocida', () => {
    expect(nextAttemptIn(event({ next_attempt_at: 'mañana' }), now)).toBeNull();
  });
});
