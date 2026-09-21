/**
 * Dispatch board logic (RF-104, RF-360).
 *
 * The ordering and the severity rules are the screen: a supervisor with fourteen crews reads
 * the top three rows and nothing else. Getting the order wrong hides exactly the crew that
 * needs a phone call.
 */

import { describe, expect, it } from 'vitest';

import type { CrewDispatch, DeviceReadiness } from '../../api/dispatch';
import {
  crewSeverity,
  deviceSeverity,
  formatSync,
  minutesSinceSync,
  sortCrews,
  sortDevices,
  summarise,
} from './readiness';

function crew(overrides: Partial<CrewDispatch> = {}): CrewDispatch {
  return {
    crew_id: 'c1',
    code: 'C-01',
    name: 'Cuadrilla 1',
    zone: 'Durán',
    assigned: 4,
    delivered: 4,
    undelivered: 0,
    stale_on_device: 0,
    in_progress: 1,
    returned: 2,
    overdue: 0,
    devices: ['dev-001'],
    last_sync_at: '2026-09-21T12:00:00Z',
    ...overrides,
  };
}

function device(overrides: Partial<DeviceReadiness> = {}): DeviceReadiness {
  return {
    device_key: 'dev-001',
    user_sub: 'tecnico.1',
    status: 'activo',
    app_version: '1.0.0',
    model_package_version: '2026.09',
    last_sync_at: '2026-09-21T12:00:00Z',
    held_orders: 4,
    stale_orders: 0,
    pending_uploads: 0,
    package_zone: 'Durán',
    package_version: 3,
    package_current: true,
    blockers: [],
    ...overrides,
  };
}

describe('severidad de una cuadrilla', () => {
  it('trabajo no entregado bloquea, por encima de todo lo demás', () => {
    expect(crewSeverity(crew({ assigned: 4, delivered: 1, undelivered: 3 }))).toBe('bloqueado');
  });

  it('una copia vieja en el teléfono requiere atención, no bloquea', () => {
    expect(crewSeverity(crew({ stale_on_device: 2 }))).toBe('atencion');
  });

  it('SLA vencido requiere atención', () => {
    expect(crewSeverity(crew({ overdue: 1 }))).toBe('atencion');
  });

  it('todo entregado y al día está listo', () => {
    expect(crewSeverity(crew())).toBe('listo');
  });

  it('una cuadrilla sin trabajo asignado está lista, no bloqueada', () => {
    expect(crewSeverity(crew({ assigned: 0, delivered: 0, undelivered: 0 }))).toBe('listo');
  });
});

describe('orden del tablero', () => {
  it('lo peor va primero, y dentro de cada nivel manda el código', () => {
    const rows = [
      crew({ crew_id: 'a', code: 'C-09' }),
      crew({ crew_id: 'b', code: 'C-02', undelivered: 1 }),
      crew({ crew_id: 'c', code: 'C-05', stale_on_device: 1 }),
      crew({ crew_id: 'd', code: 'C-01' }),
    ];
    expect(sortCrews(rows).map((row) => row.code)).toEqual(['C-02', 'C-05', 'C-01', 'C-09']);
  });

  it('no muta el arreglo recibido', () => {
    const rows = [crew({ code: 'C-09' }), crew({ code: 'C-01', undelivered: 1 })];
    const before = rows.map((row) => row.code);
    sortCrews(rows);
    expect(rows.map((row) => row.code)).toEqual(before);
  });

  it('los dispositivos siguen la misma regla', () => {
    const rows = [
      device({ device_key: 'dev-003' }),
      device({ device_key: 'dev-001', last_sync_at: null, blockers: ['nunca ha sincronizado'] }),
      device({ device_key: 'dev-002', stale_orders: 1, blockers: ['tiene 1 OT con cambios'] }),
    ];
    expect(sortDevices(rows).map((row) => row.device_key)).toEqual([
      'dev-001',
      'dev-002',
      'dev-003',
    ]);
  });
});

describe('severidad de un dispositivo', () => {
  it('sin impedimentos está listo', () => {
    expect(deviceSeverity(device())).toBe('listo');
  });

  it('un dispositivo bloqueado por administración está bloqueado', () => {
    expect(
      deviceSeverity(device({ status: 'bloqueado', blockers: ["el dispositivo está bloqueado"] })),
    ).toBe('bloqueado');
  });

  it('uno que nunca sincronizó está bloqueado', () => {
    expect(
      deviceSeverity(device({ last_sync_at: null, blockers: ['nunca ha sincronizado'] })),
    ).toBe('bloqueado');
  });

  it('uno activo con paquete viejo requiere atención', () => {
    expect(
      deviceSeverity(device({ package_current: false, blockers: ['el paquete offline cambió'] })),
    ).toBe('atencion');
  });
});

describe('resumen', () => {
  it('suma lo que importa y calcula la tasa de entrega', () => {
    const summary = summarise([
      crew({ assigned: 4, delivered: 4 }),
      crew({ crew_id: 'b', code: 'C-02', assigned: 6, delivered: 3, undelivered: 3, overdue: 1 }),
    ]);
    expect(summary.crews).toBe(2);
    expect(summary.assigned).toBe(10);
    expect(summary.delivered).toBe(7);
    expect(summary.undelivered).toBe(3);
    expect(summary.overdue).toBe(1);
    expect(summary.crewsBlocked).toBe(1);
    expect(summary.deliveryRate).toBeCloseTo(0.7);
  });

  it('sin trabajo asignado la tasa es 1, no 0', () => {
    // Un día tranquilo no es un fallo de despliegue, y un 0 % haría inútil el número.
    expect(summarise([crew({ assigned: 0, delivered: 0 })]).deliveryRate).toBe(1);
  });

  it('un tablero vacío no revienta', () => {
    const summary = summarise([]);
    expect(summary.crews).toBe(0);
    expect(summary.deliveryRate).toBe(1);
  });
});

describe('antigüedad de la sincronización', () => {
  const now = new Date('2026-09-21T12:00:00Z');

  it('nunca sincronizó', () => {
    expect(minutesSinceSync({ last_sync_at: null }, now)).toBeNull();
    expect(formatSync({ last_sync_at: null }, now)).toBe('nunca');
  });

  it('una fecha inválida se trata como desconocida, no como cero', () => {
    expect(minutesSinceSync({ last_sync_at: 'no es una fecha' }, now)).toBeNull();
  });

  it('minutos, horas y días', () => {
    expect(formatSync({ last_sync_at: '2026-09-21T11:56:00Z' }, now)).toBe('hace 4 min');
    expect(formatSync({ last_sync_at: '2026-09-21T09:00:00Z' }, now)).toBe('hace 3 h');
    expect(formatSync({ last_sync_at: '2026-09-18T12:00:00Z' }, now)).toBe('hace 3 d');
  });

  it('un reloj adelantado en el teléfono no produce tiempos negativos', () => {
    expect(minutesSinceSync({ last_sync_at: '2026-09-21T12:30:00Z' }, now)).toBe(0);
    expect(formatSync({ last_sync_at: '2026-09-21T12:30:00Z' }, now)).toBe('recién');
  });
});
