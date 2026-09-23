/**
 * La pantalla de catálogos, renderizada (RF-034).
 *
 * Lo que se comprueba: que un catálogo vacío nunca aparezca como una tabla en blanco, que el del ERP
 * no ofrezca editar, y que retirar un valor explique que viaja al teléfono como lápida.
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { CatalogIndex, CatalogSummary, ResolvedCatalog } from '../../api/catalogs';
import { CatalogsScreen } from './CatalogsScreen';

function summary(overrides: Partial<CatalogSummary> = {}): CatalogSummary {
  return {
    code: 'defect',
    title: 'Defecto encontrado',
    source: 'manual',
    version: 3,
    note: null,
    active_entries: 23,
    retired_entries: 0,
    empty: false,
    ...overrides,
  };
}

function resolved(overrides: Partial<ResolvedCatalog> = {}): ResolvedCatalog {
  return {
    code: 'defect',
    title: 'Defecto encontrado',
    source: 'manual',
    version: 3,
    note: null,
    empty: false,
    entries: [
      {
        code: 'cruceta_podrida',
        label: 'Cruceta deteriorada',
        synonyms: ['cruceta podrida'],
        parent_code: null,
        attributes: { suggested_criticality: 'alta' },
        local: false,
      },
    ],
    ...overrides,
  };
}

function mockApi(stub: { index?: CatalogIndex; catalog?: ResolvedCatalog } = {}) {
  const calls: { url: string; method: string }[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    calls.push({ url, method });
    if (method === 'DELETE') {
      return { ok: true, status: 200, json: async () => ({}) } as unknown as Response;
    }
    if (url.includes('/catalog/')) {
      return {
        ok: true,
        status: 200,
        json: async () => stub.catalog ?? resolved(),
      } as unknown as Response;
    }
    return {
      ok: true,
      status: 200,
      json: async () => stub.index ?? { catalogs: [summary()], gis_backed: ['feeder'] },
    } as unknown as Response;
  });
  return { fetcher, calls };
}

afterEach(() => vi.unstubAllGlobals());

describe('el índice', () => {
  it('distingue el vacío que espera del vacío sin motivo', async () => {
    const { fetcher } = mockApi({
      index: {
        catalogs: [
          summary({ code: 'administrative.canton', empty: true, active_entries: 0, note: 'falta el INEC' }),
          summary({ code: 'roto', empty: true, active_entries: 0, note: null }),
        ],
        gis_backed: ['feeder'],
      },
    });
    vi.stubGlobal('fetch', fetcher);
    render(<CatalogsScreen businessUnit="GYE" />);

    const panel = await screen.findByRole('region', { name: 'Catálogos de la plataforma' });
    expect(within(panel).getByText('Vacío, a la espera')).toBeTruthy();
    expect(within(panel).getByText('Vacío sin motivo declarado')).toBeTruthy();
    // Lo peor primero.
    expect(within(panel).getAllByRole('rowheader')[0]?.textContent).toBe('roto');
  });

  it('dice dónde están los catálogos del SIG, para que nadie los busque aquí', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<CatalogsScreen businessUnit="GYE" />);
    expect(await screen.findByText(/feeder no están aquí/)).toBeTruthy();
  });

  it('cuenta los retirados aparte de los activos', async () => {
    const { fetcher } = mockApi({
      index: { catalogs: [summary({ retired_entries: 2 })], gis_backed: [] },
    });
    vi.stubGlobal('fetch', fetcher);
    render(<CatalogsScreen businessUnit="GYE" />);
    expect(await screen.findByText(/\+2 retirados/)).toBeTruthy();
  });

  it('un fallo del servidor se ve', async () => {
    const fetcher = vi.fn(
      async () =>
        ({
          ok: false,
          status: 500,
          statusText: 'Server Error',
          json: async () => ({ detail: 'la base no responde' }),
        }) as unknown as Response,
    );
    vi.stubGlobal('fetch', fetcher);
    render(<CatalogsScreen businessUnit="GYE" />);
    expect(await screen.findByRole('alert')).toBeTruthy();
  });
});

describe('los valores de un catálogo', () => {
  it('no pide nada hasta que se elige uno', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<CatalogsScreen businessUnit="GYE" />);
    await screen.findByLabelText('Catálogo');
    expect(calls.some((call) => call.url.includes('/catalog/'))).toBe(false);
  });

  it('muestra los sinónimos y la criticidad como sugerencia', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<CatalogsScreen businessUnit="GYE" />);

    fireEvent.change(await screen.findByLabelText('Catálogo'), { target: { value: 'defect' } });
    const panel = await screen.findByRole('region', { name: 'Valores de un catálogo' });
    expect(within(panel).getByText('cruceta podrida')).toBeTruthy();
    expect(within(panel).getByText('criticidad sugerida: alta')).toBeTruthy();
  });

  it('un catálogo vacío muestra su motivo en vez de una tabla en blanco', async () => {
    const { fetcher } = mockApi({
      index: {
        catalogs: [summary({ code: 'administrative.canton', empty: true, active_entries: 0, note: 'falta la lista del INEC' })],
        gis_backed: [],
      },
      catalog: resolved({
        code: 'administrative.canton',
        empty: true,
        entries: [],
        note: 'falta la lista del INEC',
      }),
    });
    vi.stubGlobal('fetch', fetcher);
    render(<CatalogsScreen businessUnit="GYE" />);

    fireEvent.change(await screen.findByLabelText('Catálogo'), {
      target: { value: 'administrative.canton' },
    });
    expect(await screen.findByText('falta la lista del INEC')).toBeTruthy();
  });

  it('el catálogo del ERP no ofrece retirar y explica por qué', async () => {
    const { fetcher } = mockApi({
      index: { catalogs: [summary({ code: 'material', source: 'integracion' })], gis_backed: [] },
      catalog: resolved({ code: 'material', source: 'integracion' }),
    });
    vi.stubGlobal('fetch', fetcher);
    render(<CatalogsScreen businessUnit="GYE" />);

    fireEvent.change(await screen.findByLabelText('Catálogo'), { target: { value: 'material' } });
    expect(await screen.findByText(/sobreescribiría lo que se teclee/)).toBeTruthy();
    expect(screen.queryByText('Retirar')).toBeNull();
  });

  it('retirar un valor explica que viaja como lápida', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<CatalogsScreen businessUnit="GYE" />);

    fireEvent.change(await screen.findByLabelText('Catálogo'), { target: { value: 'defect' } });
    fireEvent.click(await screen.findByText('Retirar'));
    await waitFor(() => {
      expect(calls.some((call) => call.method === 'DELETE')).toBe(true);
    });
    expect(await screen.findByText(/lápida/)).toBeTruthy();
  });
});

describe('quien no administra', () => {
  it('ve los valores y no ve con qué retirarlos', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<CatalogsScreen businessUnit="GYE" mayEdit={false} />);

    fireEvent.change(await screen.findByLabelText('Catálogo'), { target: { value: 'defect' } });
    await screen.findByText('Cruceta deteriorada');
    expect(screen.queryByText('Retirar')).toBeNull();
  });
});
