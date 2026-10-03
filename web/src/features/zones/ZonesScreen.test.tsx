/**
 * La pantalla de zonas, renderizada (RF-152).
 *
 * Lo que se comprueba es lo que engañaría a un administrador: una lista de doce zonas bien
 * nombradas mientras once OT abiertas no caen en ninguna; una importación que reemplaza once
 * polígonos sin decirlo antes; y un planificador que ve botones que el servidor le va a negar.
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { BackfillReport, CoverageReport, ImportReport, ZoneCollection } from '../../api/zones';
import { ZonesScreen } from './ZonesScreen';

const POLYGON = { type: 'MultiPolygon', coordinates: [] };

function zone(code: string, overrides: Record<string, unknown> = {}) {
  return {
    type: 'Feature' as const,
    geometry: POLYGON,
    properties: {
      code,
      name: `Sector ${code}`,
      description: null,
      origin: 'importada',
      active: true,
      updated_by: 'admin.funcional',
      updated_at: '2026-09-20T10:00:00+00:00',
      ...overrides,
    },
  };
}

function collection(...codes: string[]): ZoneCollection {
  return { type: 'FeatureCollection', features: codes.map((code) => zone(code)) };
}

function coverage(
  overrides: Partial<CoverageReport['coverage']> = {},
  overlaps: CoverageReport['overlaps'] = [],
): CoverageReport {
  return {
    coverage: {
      open_orders: 0,
      inside_one: 0,
      ambiguous: 0,
      outside: 0,
      without_location: 0,
      covered_share: null,
      ...overrides,
    },
    overlaps,
  };
}

interface Stub {
  zones?: ZoneCollection;
  coverage?: CoverageReport;
  imported?: ImportReport;
  backfill?: BackfillReport;
  failCoverage?: boolean;
}

function mockApi(stub: Stub = {}) {
  const calls: { url: string; method: string; body: unknown }[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    calls.push({
      url,
      method,
      body: typeof init?.body === 'string' ? JSON.parse(init.body) : null,
    });
    if (url.includes('/coverage')) {
      if (stub.failCoverage) {
        return {
          ok: false,
          status: 500,
          statusText: 'Server Error',
          json: async () => ({ detail: 'la base no responde' }),
        } as unknown as Response;
      }
      return { ok: true, status: 200, json: async () => stub.coverage ?? coverage() } as unknown as Response;
    }
    if (url.includes('/import')) {
      return {
        ok: true,
        status: 200,
        json: async () =>
          stub.imported ?? { created: [], updated: [], accepted: 0, rejected: [] },
      } as unknown as Response;
    }
    if (url.includes('/backfill')) {
      return {
        ok: true,
        status: 200,
        json: async () =>
          stub.backfill ?? { dry_run: true, filled: {}, ambiguous: {}, outside: [] },
      } as unknown as Response;
    }
    return {
      ok: true,
      status: 200,
      json: async () => stub.zones ?? collection(),
    } as unknown as Response;
  });
  return { fetcher, calls };
}

const GEOJSON = JSON.stringify({
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [-80, -2],
            [-79.9, -2],
            [-79.9, -2.1],
            [-80, -2.1],
            [-80, -2],
          ],
        ],
      },
      properties: { code: 'NORTE' },
    },
  ],
});

afterEach(() => vi.unstubAllGlobals());

describe('la cobertura', () => {
  it('pone el número que hay que corregir antes de la lista de zonas', async () => {
    const { fetcher } = mockApi({
      zones: collection('NORTE', 'SUR'),
      coverage: coverage({ open_orders: 200, inside_one: 189, outside: 11, covered_share: 0.945 }),
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);

    const panel = await screen.findByRole('region', { name: 'Cobertura' });
    expect(within(panel).getByText(/11 no cae\(n\) en ninguna zona/)).toBeTruthy();
    expect(within(panel).getByText(/94,5 %/)).toBeTruthy();
  });

  it('dice que no puede calcular el porcentaje en vez de mostrar 0 %', async () => {
    const { fetcher } = mockApi({
      coverage: coverage({ open_orders: 4, without_location: 4, covered_share: null }),
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);

    const panel = await screen.findByRole('region', { name: 'Cobertura' });
    expect(within(panel).getByText(/no se puede calcular el porcentaje/)).toBeTruthy();
    expect(panel.textContent).not.toContain('0 %');
  });

  it('muestra los solapamientos con la frase del servidor', async () => {
    const { fetcher } = mockApi({
      coverage: coverage({}, [
        { left: 'A', right: 'B', area_m2: 3.2e7, text: 'A y B se solapan en 32.000.000 m²' },
      ]),
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);
    expect(await screen.findByText('A y B se solapan en 32.000.000 m²')).toBeTruthy();
  });

  it('dice explícitamente que ninguna se solapa, que es el estado esperado', async () => {
    const { fetcher } = mockApi({});
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);
    expect(await screen.findByText(/Ninguna zona se solapa/)).toBeTruthy();
  });

  it('un fallo del servidor se ve', async () => {
    const { fetcher } = mockApi({ failCoverage: true });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);
    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText('la base no responde')).toBeTruthy();
  });
});

describe('la lista', () => {
  it('explica qué significa no tener ninguna zona todavía', async () => {
    const { fetcher } = mockApi({ zones: collection() });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);
    expect(await screen.findByText(/todavía no tiene zonas dibujadas/)).toBeTruthy();
  });

  it('trae también las inactivas, con su estado a la vista', async () => {
    const { fetcher } = mockApi({
      zones: {
        type: 'FeatureCollection',
        features: [zone('NORTE'), zone('SUR', { active: false })],
      },
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);

    const list = await screen.findByRole('region', { name: 'Zonas de la unidad' });
    expect(within(list).getByText('Inactiva')).toBeTruthy();
    expect(within(list).getByText('Reactivar')).toBeTruthy();
  });

  it('pide las inactivas al servidor, o no habría nada que reactivar', async () => {
    const { fetcher, calls } = mockApi({});
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Zonas de la unidad' });
    expect(calls.some((call) => call.url.includes('include_inactive=true'))).toBe(true);
  });

  it('desactivar una zona la manda al servidor y recarga', async () => {
    const { fetcher, calls } = mockApi({ zones: collection('NORTE') });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByText('Desactivar'));
    await waitFor(() => {
      const posted = calls.find((call) => call.url.includes('/active'));
      expect(posted?.body).toEqual({ active: false });
    });
  });
});

describe('la importación', () => {
  it('avisa antes de reemplazar un polígono que ya existe', async () => {
    const { fetcher } = mockApi({ zones: collection('NORTE') });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Importar GeoJSON' });

    fireEvent.change(screen.getByLabelText(/Pegue aquí/), { target: { value: GEOJSON } });
    expect(screen.getByText(/1 reemplazaría\(n\) una zona existente: NORTE/)).toBeTruthy();
  });

  it('dice que no se reemplaza nada cuando el código es nuevo', async () => {
    const { fetcher } = mockApi({ zones: collection('SUR') });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Importar GeoJSON' });

    fireEvent.change(screen.getByLabelText(/Pegue aquí/), { target: { value: GEOJSON } });
    expect(screen.getByText(/Ninguna zona existente se reemplazaría/)).toBeTruthy();
  });

  it('rechaza localmente lo que no es GeoJSON, sin gastar un viaje al servidor', async () => {
    const { fetcher, calls } = mockApi({});
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Importar GeoJSON' });

    fireEvent.change(screen.getByLabelText(/Pegue aquí/), { target: { value: '{no json' } });
    expect(screen.getByText('El texto no es JSON válido.')).toBeTruthy();
    const button = screen.getByRole('button', { name: 'Importar' });
    expect(button.getAttribute('disabled')).not.toBeNull();
    expect(calls.some((call) => call.url.includes('/import'))).toBe(false);
  });

  it('enumera los rasgos rechazados con el motivo del servidor', async () => {
    const { fetcher } = mockApi({
      imported: {
        created: ['BUENA-1', 'BUENA-2'],
        updated: [],
        accepted: 2,
        rejected: [{ index: 1, code: 'MALA', reason: 'geometría inválida: Self-intersection' }],
      },
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Importar GeoJSON' });

    fireEvent.change(screen.getByLabelText(/Pegue aquí/), { target: { value: GEOJSON } });
    fireEvent.click(screen.getByText('Importar'));

    const result = await screen.findByLabelText('Resultado de la importación');
    expect(within(result).getByText(/2 creada\(s\)/)).toBeTruthy();
    expect(within(result).getByText(/Self-intersection/)).toBeTruthy();
  });

  it('manda la propiedad del código que el usuario nombró', async () => {
    const { fetcher, calls } = mockApi({ imported: { created: ['X'], updated: [], accepted: 1, rejected: [] } });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Importar GeoJSON' });

    fireEvent.change(screen.getByLabelText(/Pegue aquí/), { target: { value: GEOJSON } });
    fireEvent.change(screen.getByLabelText(/Propiedad con el código/), {
      target: { value: 'sector' },
    });
    fireEvent.click(screen.getByText('Importar'));

    await waitFor(() => {
      const posted = calls.find((call) => call.url.includes('/import'));
      expect((posted?.body as { code_property?: string }).code_property).toBe('sector');
    });
  });
});

describe('la asignación desde el polígono', () => {
  it('la simulación dice que no escribió nada', async () => {
    const { fetcher, calls } = mockApi({
      backfill: { dry_run: true, filled: { a: 'N', b: 'N' }, ambiguous: {}, outside: [] },
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByText('Simular'));
    const result = await screen.findByLabelText('Resultado de la asignación');
    expect(within(result).getByText(/todavía no se escribió nada/)).toBeTruthy();
    expect(calls.some((call) => call.url.includes('dry_run=true'))).toBe(true);
  });

  it('explica por qué dejó sin tocar las ambiguas', async () => {
    const { fetcher } = mockApi({
      backfill: { dry_run: false, filled: {}, ambiguous: { a: ['N', 'S'] }, outside: [] },
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByText('Aplicar'));
    const result = await screen.findByLabelText('Resultado de la asignación');
    expect(within(result).getByText(/nadie podría revisar/)).toBeTruthy();
  });
});

describe('el planificador', () => {
  it('ve las zonas y la cobertura, y no ve con qué mover un límite', async () => {
    const { fetcher } = mockApi({ zones: collection('NORTE') });
    vi.stubGlobal('fetch', fetcher);
    render(<ZonesScreen businessUnit="GYE" mayEdit={false} />);

    await screen.findByRole('region', { name: 'Zonas de la unidad' });
    expect(screen.queryByRole('region', { name: 'Importar GeoJSON' })).toBeNull();
    expect(screen.queryByText('Desactivar')).toBeNull();
    expect(screen.queryByText('Simular')).toBeNull();
  });
});
