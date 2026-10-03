/**
 * El tablero de mantenimiento, renderizado (RF-133).
 *
 * Lo que se comprueba: que la definición de «abierto» esté a la vista, que el filtro de tipo de
 * defecto llegue al servidor y siga ofreciendo todos los tipos del periodo después de filtrar —si se
 * construyera del tablero filtrado, elegir un defecto dejaría al usuario sin forma de volver—, y que
 * un fallo del servidor se vea.
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { MaintenanceBoard } from '../../api/analytics';
import { MaintenanceScreen } from './MaintenanceScreen';

function board(overrides: Partial<MaintenanceBoard> = {}): MaintenanceBoard {
  return {
    since: '2026-08-21T12:00:00+00:00',
    until: '2026-09-20T12:00:00+00:00',
    defect_filter: null,
    findings: 30,
    heat: {
      by_feeder: [
        {
          feeder_code: 'ALIM-NORTE',
          defects: 18,
          share: 0.6,
          top_defect: { defect_code: 'cruceta_podrida', times: 12 },
        },
      ],
      without_feeder: 2,
    },
    recurrence: [
      {
        asset_code: 'P-TERCO',
        findings: 3,
        defects: { cruceta_podrida: 3 },
        worst_criticality: 'critica',
      },
    ],
    backlog: {
      open_by_criticality: { critica: 2, alta: 5 },
      open: 7,
      attended: 20,
      untrackable: 3,
      wants_order: 4,
      definition: 'abierto significa que no hay ninguna OT posterior cerrada sobre el mismo activo',
    },
    by_defect: { cruceta_podrida: 18, aislador_roto: 12 },
    open_findings: [
      {
        work_order_id: 'wo-1',
        order_code: 'OT-1',
        asset_code: 'P-TERCO',
        defect_code: 'cruceta_podrida',
        criticality: 'critica',
        feeder_code: 'ALIM-NORTE',
        recorded_at: '2026-09-18T10:00:00+00:00',
        wants_order: true,
      },
    ],
    ...overrides,
  };
}

function mockApi(body: MaintenanceBoard, filtered?: MaintenanceBoard) {
  const urls: string[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    urls.push(url);
    const payload = url.includes('defect_code=') ? (filtered ?? body) : body;
    return { ok: true, status: 200, json: async () => payload } as unknown as Response;
  });
  return { fetcher, urls };
}

afterEach(() => vi.unstubAllGlobals());

describe('los pendientes', () => {
  it('muestra la definición del servidor sin parafrasear', async () => {
    const { fetcher } = mockApi(board());
    vi.stubGlobal('fetch', fetcher);
    render(<MaintenanceScreen businessUnit="GYE" />);

    expect(await screen.findByText(/7 hallazgo\(s\) abierto\(s\) de 30/)).toBeTruthy();
    expect(screen.getByText(/no hay ninguna OT posterior cerrada/)).toBeTruthy();
  });

  it('lo que no se puede seguir se dice, y no se cuenta como abierto', async () => {
    const { fetcher } = mockApi(board());
    vi.stubGlobal('fetch', fetcher);
    render(<MaintenanceScreen businessUnit="GYE" />);
    expect(await screen.findByText(/ni como abiertos ni como atendidos/)).toBeTruthy();
  });

  it('una criticidad sin pendientes se muestra en cero', async () => {
    // «media: 0» es la frase que el planificador quiere leer.
    const { fetcher } = mockApi(board());
    vi.stubGlobal('fetch', fetcher);
    render(<MaintenanceScreen businessUnit="GYE" />);

    const pending = await screen.findByRole('region', { name: 'Pendientes' });
    expect(pending.textContent).toContain('Media');
  });
});

describe('el calor y la reincidencia', () => {
  it('cada alimentador con su reparto y su defecto dominante', async () => {
    const { fetcher } = mockApi(board());
    vi.stubGlobal('fetch', fetcher);
    render(<MaintenanceScreen businessUnit="GYE" />);

    const heat = await screen.findByRole('region', { name: 'Defectos por alimentador' });
    expect(within(heat).getByText(/ALIM-NORTE/)).toBeTruthy();
    expect(within(heat).getByText(/18 defecto\(s\), 60 %/)).toBeTruthy();
    expect(screen.getByText(/2 defecto\(s\) sin alimentador/)).toBeTruthy();
  });

  it('un activo que repite el mismo defecto se explica como reparación que no aguantó', async () => {
    const { fetcher } = mockApi(board());
    vi.stubGlobal('fetch', fetcher);
    render(<MaintenanceScreen businessUnit="GYE" />);
    expect(await screen.findByText(/no aguantó/)).toBeTruthy();
  });
});

describe('el filtro por tipo de defecto', () => {
  it('viaja al servidor', async () => {
    const { fetcher, urls } = mockApi(board());
    vi.stubGlobal('fetch', fetcher);
    render(<MaintenanceScreen businessUnit="GYE" />);
    await screen.findByLabelText('Tipo de defecto');

    fireEvent.change(screen.getByLabelText('Tipo de defecto'), {
      target: { value: 'aislador_roto' },
    });
    await waitFor(() =>
      expect(urls.some((url) => url.includes('defect_code=aislador_roto'))).toBe(true),
    );
  });

  it('después de filtrar sigue ofreciendo todos los tipos del periodo', async () => {
    // Si la lista se construyera del tablero filtrado, elegir un defecto dejaría al usuario sin
    // forma de volver a los demás.
    const narrowed = board({ by_defect: { aislador_roto: 12 }, findings: 12 });
    const { fetcher } = mockApi(board(), narrowed);
    vi.stubGlobal('fetch', fetcher);
    render(<MaintenanceScreen businessUnit="GYE" />);
    await screen.findByLabelText('Tipo de defecto');

    fireEvent.change(screen.getByLabelText('Tipo de defecto'), {
      target: { value: 'aislador_roto' },
    });
    await waitFor(() => expect(screen.getByText(/de 12 registrado/)).toBeTruthy());
    expect(screen.getByRole('option', { name: /cruceta_podrida/ })).toBeTruthy();
  });
});

describe('cuando falla', () => {
  it('avisa y no se queda diciendo «cargando»', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 503,
            statusText: 'Service Unavailable',
            json: async () => ({ detail: 'sin base de datos' }),
          }) as unknown as Response,
      ),
    );
    render(<MaintenanceScreen businessUnit="GYE" />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.queryByText(/Cargando el tablero/)).toBeNull();
  });
});
