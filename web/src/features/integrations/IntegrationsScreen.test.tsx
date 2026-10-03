/**
 * La pantalla de integraciones, renderizada (RF-125).
 *
 * El botón de reintentar es la razón por la que esta pantalla existe: una bitácora que se puede
 * leer y no accionar solo cuenta el problema dos veces al día. Así que lo que se prueba es que el
 * botón reencole de verdad, que esté deshabilitado donde no tiene sentido, y que un pendiente no
 * se presente como un fallo — un pendiente es el sistema funcionando.
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ConnectorHealth, IntegrationEvent } from '../../api/integrations';
import { IntegrationsScreen } from './IntegrationsScreen';

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
    status: 'fallido',
    idempotency_key: 'cierre:REC-1',
    external_ref: 'REC-1',
    work_order_id: null,
    attempts: 5,
    last_error: '503 Service Unavailable\n  en el proxy corporativo',
    next_attempt_at: null,
    created_at: '2026-09-22T10:00:00Z',
    delivered_at: null,
    needs_attention: true,
    payload: { claim_id: 'REC-1' },
    response: null,
    ...overrides,
  };
}

function mockApi(
  connectors: ConnectorHealth[],
  events: IntegrationEvent[],
  onRetry?: (url: string) => void,
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/retry')) {
      onRetry?.(url);
      return {
        ok: true,
        status: 200,
        json: async () => ({ ...events[0], status: 'pendiente' }),
      } as unknown as Response;
    }
    const body = url.includes('/connectors') ? connectors : events;
    void init;
    return { ok: true, status: 200, json: async () => body } as unknown as Response;
  });
}

const NOW = new Date('2026-09-22T12:00:00Z');

afterEach(() => vi.unstubAllGlobals());

describe('el estado de los conectores', () => {
  it('lo que espera a una persona se cuenta y se destaca', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi([connector({ connector: 'call_center', waiting_for_a_person: 1 })], [event()]),
    );
    render(<IntegrationsScreen businessUnit="GYE" operator="soporte.1" now={() => NOW} />);

    await waitFor(() => expect(screen.getAllByText('Requiere intervención').length).toBeGreaterThan(0));
    const summary = document.querySelector('.integrations-summary');
    const tile = within(summary as HTMLElement).getByText('Esperando a una persona').closest('div');
    expect(tile?.textContent).toContain('1');
    expect(tile?.className).toContain('alarming');
  });

  it('muchos pendientes no se presentan como un fallo', async () => {
    // Un pendiente se reintenta solo; eso es el sistema funcionando.
    vi.stubGlobal(
      'fetch',
      mockApi(
        [connector({ pending: 40 })],
        [event({ status: 'pendiente', needs_attention: false, next_attempt_at: '2026-09-22T12:04:00Z' })],
      ),
    );
    render(<IntegrationsScreen businessUnit="GYE" operator="soporte.1" now={() => NOW} />);

    await waitFor(() => expect(screen.getByText('Con reintentos en curso')).toBeTruthy());
    expect(screen.queryByText('Requiere intervención')).toBeNull();
    expect(screen.getByText('en 4 min')).toBeTruthy();
  });
});

describe('la bitácora', () => {
  it('muestra la primera línea del error y el detalle completo al desplegarlo', async () => {
    vi.stubGlobal('fetch', mockApi([connector()], [event()]));
    render(<IntegrationsScreen businessUnit="GYE" operator="soporte.1" now={() => NOW} />);

    const short = await screen.findByRole('button', { name: '503 Service Unavailable' });
    short.click();

    await waitFor(() => expect(screen.getByText(/proxy corporativo/)).toBeTruthy());
    expect(screen.getByText('Payload enviado')).toBeTruthy();
  });

  it('el reintento reencola de verdad', async () => {
    const retried: string[] = [];
    vi.stubGlobal('fetch', mockApi([connector()], [event()], (url) => retried.push(url)));
    render(<IntegrationsScreen businessUnit="GYE" operator="soporte.1" now={() => NOW} />);

    const retry = await screen.findByRole('button', { name: 'Reintentar' });
    retry.click();

    await waitFor(() => expect(retried).toHaveLength(1));
    expect(retried[0]).toContain('/units/GYE/events/e1/retry');
  });

  it('no se puede reintentar lo que ya se entregó', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi([connector()], [event({ status: 'entregado', needs_attention: false })]),
    );
    render(<IntegrationsScreen businessUnit="GYE" operator="soporte.1" now={() => NOW} />);

    const retry = await screen.findByRole('button', { name: 'Reintentar' });
    expect((retry as HTMLButtonElement).disabled).toBe(true);
  });

  it('sin intercambios lo dice, en vez de mostrar una tabla vacía', async () => {
    vi.stubGlobal('fetch', mockApi([], []));
    render(<IntegrationsScreen businessUnit="GYE" operator="soporte.1" now={() => NOW} />);

    await waitFor(() => expect(screen.getByText(/Nada que reintentar/)).toBeTruthy());
  });
});
