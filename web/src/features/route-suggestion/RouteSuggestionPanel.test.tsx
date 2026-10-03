/**
 * El panel de ruta sugerida, renderizado (RF-025).
 *
 * Lo que se prueba: que el botón pida la ruta al servidor con las OT seleccionadas, que muestre
 * el orden y el ahorro, y que no llegue a pedir nada con menos de dos OT.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { RouteSuggestion } from '../../api/routing';
import { RouteSuggestionPanel } from './RouteSuggestionPanel';

function suggestion(overrides: Partial<RouteSuggestion> = {}): RouteSuggestion {
  return {
    stops: [
      { work_order_id: 'ot-2', code: 'OT-2', longitude: -79.9, latitude: -2.17, leg_distance_m: 0 },
      {
        work_order_id: 'ot-1',
        code: 'OT-1',
        longitude: -79.91,
        latitude: -2.18,
        leg_distance_m: 1200,
      },
    ],
    total_distance_m: 1200,
    naive_distance_m: 2400,
    start: null,
    caveats: ['La distancia es en línea recta, no por la red vial.'],
    ...overrides,
  };
}

function mockApi(body: RouteSuggestion, onPost?: (payload: unknown) => void) {
  return vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    onPost?.(init?.body ? JSON.parse(String(init.body)) : null);
    return { ok: true, status: 200, json: async () => body } as unknown as Response;
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('pedir una ruta', () => {
  it('manda las OT seleccionadas al servidor', async () => {
    const posted: unknown[] = [];
    vi.stubGlobal(
      'fetch',
      mockApi(suggestion(), (payload) => posted.push(payload)),
    );
    render(<RouteSuggestionPanel businessUnit="GYE" workOrderIds={['ot-1', 'ot-2']} />);

    fireEvent.click(screen.getByRole('button', { name: 'Sugerir ruta' }));

    await waitFor(() => expect(posted).toHaveLength(1));
    expect(posted[0]).toEqual({ work_order_ids: ['ot-1', 'ot-2'] });
  });

  it('muestra el orden y el ahorro frente al pedido', async () => {
    vi.stubGlobal('fetch', mockApi(suggestion()));
    render(<RouteSuggestionPanel businessUnit="GYE" workOrderIds={['ot-1', 'ot-2']} />);

    fireEvent.click(screen.getByRole('button', { name: 'Sugerir ruta' }));

    await waitFor(() => expect(screen.getByText(/1,2 km/)).toBeTruthy());
    expect(screen.getByText(/OT-2/)).toBeTruthy();
    expect(screen.getByText(/OT-1/)).toBeTruthy();
    expect(screen.getByText(/línea recta/)).toBeTruthy();
  });

  it('con menos de dos OT no llega a pedir nada', () => {
    const calls = vi.fn();
    vi.stubGlobal('fetch', calls);
    render(<RouteSuggestionPanel businessUnit="GYE" workOrderIds={['ot-1']} />);

    const button = screen.getByRole<HTMLButtonElement>('button', { name: 'Sugerir ruta' });
    expect(button.disabled).toBe(true);
    fireEvent.click(button);

    expect(calls).not.toHaveBeenCalled();
    expect(screen.getByText(/al menos dos OT/)).toBeTruthy();
  });

  it('el error del servidor se muestra tal cual', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 422,
            statusText: 'Unprocessable',
            json: async () => ({ detail: 'estas OT no tienen ubicación registrada' }),
          }) as unknown as Response,
      ),
    );
    render(<RouteSuggestionPanel businessUnit="GYE" workOrderIds={['ot-1', 'ot-2']} />);

    fireEvent.click(screen.getByRole('button', { name: 'Sugerir ruta' }));

    await waitFor(() =>
      expect(screen.getByText('estas OT no tienen ubicación registrada')).toBeTruthy(),
    );
  });
});
