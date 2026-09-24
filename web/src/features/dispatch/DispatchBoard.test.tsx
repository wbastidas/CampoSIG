/**
 * El tablero de despliegue, renderizado (RF-104, RF-360).
 *
 * La lógica ya está probada en `readiness.test.ts`. Lo que aquí se comprueba es lo que esa prueba
 * no puede ver: que el número que arruina una mañana —trabajo asignado que ningún teléfono
 * recibió— aparece en pantalla, que un error de red no borra el tablero que ya se había cargado,
 * y que los motivos por los que un dispositivo no debería salir se muestran tal como los escribe
 * el servidor.
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { CrewDispatch, DeviceReadiness } from '../../api/dispatch';
import { DispatchBoard } from './DispatchBoard';

const NOW = new Date('2026-09-22T12:00:00Z');

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
    last_sync_at: '2026-09-22T11:56:00Z',
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
    last_sync_at: '2026-09-22T11:56:00Z',
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

function mockApi(crews: CrewDispatch[], devices: DeviceReadiness[]) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.includes('/devices') ? devices : crews;
    return {
      ok: true,
      status: 200,
      json: async () => body,
    } as unknown as Response;
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('el tablero', () => {
  it('muestra el trabajo que ninguna cuadrilla recibió', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi([crew({ assigned: 6, delivered: 2, undelivered: 4 })], [device()]),
    );
    render(<DispatchBoard businessUnit="GYE" now={() => NOW} />);

    await waitFor(() => expect(screen.getByText('C-01 — Cuadrilla 1')).toBeTruthy());

    // El número que arruina una mañana tiene que verse, no deducirse. Se busca dentro del
    // resumen: el mismo rótulo está también en la cabecera de la tabla, y eso está bien —
    // lo que no estaría bien es que el test no supiera cuál de los dos mira.
    const summary = document.querySelector('.dispatch-summary');
    expect(summary).not.toBeNull();
    const tile = within(summary as HTMLElement).getByText('Sin entregar').closest('div');
    expect(tile?.textContent).toContain('4');
    expect(tile?.className).toContain('alarming');
  });

  it('dice que el tablero es una fotografía y cuándo sincronizó cada teléfono', async () => {
    vi.stubGlobal('fetch', mockApi([crew()], [device()]));
    render(<DispatchBoard businessUnit="GYE" now={() => NOW} />);

    await waitFor(() => expect(screen.getByText(/es una\s+fotografía/)).toBeTruthy());
    expect(screen.getAllByText('hace 4 min').length).toBeGreaterThan(0);
  });

  it('lo peor va primero', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        [
          crew({ crew_id: 'a', code: 'C-09', name: 'Al día' }),
          crew({ crew_id: 'b', code: 'C-02', name: 'Sin entregar', undelivered: 3 }),
        ],
        [device()],
      ),
    );
    render(<DispatchBoard businessUnit="GYE" now={() => NOW} />);

    await waitFor(() => expect(screen.getByText('C-02 — Sin entregar')).toBeTruthy());
    const rows = screen.getAllByRole('row').map((row) => row.textContent ?? '');
    const first = rows.findIndex((text) => text.includes('C-02'));
    const second = rows.findIndex((text) => text.includes('C-09'));
    expect(first).toBeLessThan(second);
  });

  it('los motivos para no salir se muestran tal como los escribe el servidor', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        [crew()],
        [
          device({
            last_sync_at: null,
            package_current: false,
            blockers: ['nunca ha sincronizado', 'el paquete offline de su zona cambió'],
          }),
        ],
      ),
    );
    render(<DispatchBoard businessUnit="GYE" now={() => NOW} />);

    await waitFor(() => expect(screen.getByText('nunca ha sincronizado')).toBeTruthy());
    expect(screen.getByText('el paquete offline de su zona cambió')).toBeTruthy();
  });

  it('sin cuadrillas ni dispositivos lo dice, en vez de mostrar tablas vacías', async () => {
    vi.stubGlobal('fetch', mockApi([], []));
    render(<DispatchBoard businessUnit="GYE" now={() => NOW} />);

    await waitFor(() =>
      expect(screen.getByText(/No hay cuadrillas activas/)).toBeTruthy(),
    );
    expect(screen.getByText(/No hay dispositivos registrados/)).toBeTruthy();
  });

  it('un error de red se anuncia y no borra lo que se había cargado', async () => {
    const crews = [crew()];
    let calls = 0;
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        calls += 1;
        if (calls > 2) throw new Error('la red se cayó');
        const body = String(input).includes('/devices') ? [device()] : crews;
        return { ok: true, status: 200, json: async () => body } as unknown as Response;
      }),
    );

    const { rerender } = render(<DispatchBoard businessUnit="GYE" now={() => NOW} />);
    await waitFor(() => expect(screen.getByText('C-01 — Cuadrilla 1')).toBeTruthy());

    // Un cambio de unidad provoca otra carga, que ahora falla.
    rerender(<DispatchBoard businessUnit="MAN" now={() => NOW} />);
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('la red se cayó'));
    // Dejar la pantalla en blanco daría menos de lo que había un segundo antes.
    expect(screen.getByText('C-01 — Cuadrilla 1')).toBeTruthy();
  });
});
