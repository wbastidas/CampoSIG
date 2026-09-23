/**
 * El tablero de alumbrado, renderizado (RF-131, ADR-007).
 *
 * Lo que se comprueba es lo que protege al número: que un plazo sin verificar no se presente como
 * cita del texto oficial, que la exportación pida el archivo con el token —un `<a href>` bajaría una
 * página de login llamada «.csv»— y que un fallo del servidor se vea.
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ApgBoard } from '../../api/analytics';
import { ApgScreen } from './ApgScreen';

function board(overrides: Partial<ApgBoard> = {}): ApgBoard {
  return {
    computed_at: '2026-09-20T12:00:00+00:00',
    since: '2026-08-21T12:00:00+00:00',
    until: '2026-09-20T12:00:00+00:00',
    attentions: 30,
    restoration: {
      within: 24,
      breached: 6,
      judged: 30,
      not_measurable: 0,
      against_unverified_limit: 0,
      compliance: 0.8,
      median_hours: 10,
      p90_hours: 40,
      worst_hours: 90,
      min_sample: 5,
    },
    fleet: { by_technology: { led: 18, sodium_hp: 12 }, without_technology: 0 },
    failures: {
      by_cause: { fotocontrol: 12 },
      distinct_luminaires: 20,
      failures_per_luminaire: 1.5,
      denominator: 'luminarias con al menos una falla en el periodo, no el total instalado',
      repeat_offenders: [{ asset_code: 'LUM-A', failures: 3 }],
    },
    breaches: [
      {
        work_order_id: 'wo-1',
        order_code: 'OT-77',
        asset_code: 'LUM-A',
        hours: 60,
        limit_hours: 48,
        within_limit: false,
        limit_verified: true,
        norm_ref: 'ARCERNNR 007/23',
        article_ref: 'Art. 21',
        message: 'tomó 60 h',
      },
    ],
    ...overrides,
  };
}

function mockApi(body: ApgBoard) {
  const urls: string[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    urls.push(url);
    if (url.endsWith('.csv')) {
      // El token viaja en la cabecera: por eso la exportación es un fetch y no un enlace.
      expect(init?.headers).toBeDefined();
      return {
        ok: true,
        status: 200,
        blob: async () => new Blob(['﻿ot;luminaria\r\n'], { type: 'text/csv' }),
      } as unknown as Response;
    }
    return { ok: true, status: 200, json: async () => body } as unknown as Response;
  });
  return { fetcher, urls };
}

afterEach(() => vi.unstubAllGlobals());

describe('el cumplimiento', () => {
  it('muestra el porcentaje con las atenciones que lo sostienen', async () => {
    const { fetcher } = mockApi(board());
    vi.stubGlobal('fetch', fetcher);
    render(<ApgScreen businessUnit="GYE" />);
    expect(await screen.findByText(/80,0 % dentro del plazo \(24 de 30\)/)).toBeTruthy();
  });

  it('un plazo sin verificar se marca como provisional en la tabla', async () => {
    const rows = board();
    rows.restoration.against_unverified_limit = 6;
    rows.breaches[0]!.limit_verified = false;
    const { fetcher } = mockApi(rows);
    vi.stubGlobal('fetch', fetcher);
    render(<ApgScreen businessUnit="GYE" />);

    expect(await screen.findByText(/no citable como cumplimiento normativo/)).toBeTruthy();
    // Dentro de la tabla, no en la advertencia de arriba: las dos dicen «provisional» y lo que
    // importa aquí es que la celda de la norma no cite la norma.
    const table = screen.getByRole('region', { name: 'Incumplimientos' });
    const cell = within(table).getByText(/resultado provisional/i);
    expect(cell.className).toContain('apg-provisional');
    // Y no aparece la norma junto a un límite que nadie verificó.
    expect(screen.queryByText('ARCERNNR 007/23 · Art. 21')).toBeNull();
  });

  it('el denominador de la tasa de falla se muestra tal como lo manda el servidor', async () => {
    const { fetcher } = mockApi(board());
    vi.stubGlobal('fetch', fetcher);
    render(<ApgScreen businessUnit="GYE" />);
    expect(await screen.findByText(/no el total instalado/)).toBeTruthy();
  });

  it('la cuota de LED se muestra, que es la medida de la modernización', async () => {
    const { fetcher } = mockApi(board());
    vi.stubGlobal('fetch', fetcher);
    render(<ApgScreen businessUnit="GYE" />);
    expect(await screen.findByText(/60,0 % de las atendidas son LED/)).toBeTruthy();
  });
});

describe('la exportación', () => {
  it('pide el archivo con el token, no con un enlace', async () => {
    const { fetcher, urls } = mockApi(board());
    vi.stubGlobal('fetch', fetcher);
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:x'),
      revokeObjectURL: vi.fn(),
    });
    render(<ApgScreen businessUnit="GYE" />);

    (await screen.findByRole('button', { name: /Exportar a CSV/ })).click();
    await waitFor(() => expect(urls.some((url) => url.endsWith('.csv'))).toBe(true));
  });

  it('si la exportación falla se avisa', async () => {
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('.csv')) {
        return { ok: false, status: 500, statusText: 'Server Error' } as unknown as Response;
      }
      return { ok: true, status: 200, json: async () => board() } as unknown as Response;
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ApgScreen businessUnit="GYE" />);

    (await screen.findByRole('button', { name: /Exportar a CSV/ })).click();
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
  });
});

describe('cuando no hay nada que mostrar', () => {
  it('sin incumplimientos lo dice en vez de una tabla vacía', async () => {
    const { fetcher } = mockApi(board({ breaches: [] }));
    vi.stubGlobal('fetch', fetcher);
    render(<ApgScreen businessUnit="GYE" />);
    expect(await screen.findByText(/Ninguna atención por encima del plazo/)).toBeTruthy();
  });

  it('si falla la carga no se queda diciendo «cargando»', async () => {
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
    render(<ApgScreen businessUnit="GYE" />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.queryByText(/Cargando el tablero/)).toBeNull();
  });
});
