/**
 * The crew administration screen, rendered (RF-005).
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Crew, CrewHistoryEntry } from '../../api/crews';
import { CrewsScreen } from './CrewsScreen';

function crew(overrides: Partial<Crew> = {}): Crew {
  return {
    id: 'c1',
    code: 'C-01',
    name: 'Cuadrilla 1',
    leader_name: 'Jorge Salas',
    vehicle: 'Camioneta 12',
    competencies: ['MV'],
    members: ['Ana Pérez'],
    zone: 'norte',
    active: true,
    created_by: 'admin.funcional',
    updated_by: 'admin.funcional',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

interface Stub {
  crews?: Crew[];
  history?: CrewHistoryEntry[];
  saved?: Crew;
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
    if (url.includes('/history')) {
      return { ok: true, status: 200, json: async () => stub.history ?? [] } as unknown as Response;
    }
    if (method === 'PUT') {
      return {
        ok: true,
        status: 200,
        json: async () => stub.saved ?? crew(),
      } as unknown as Response;
    }
    if (method === 'POST') {
      return { ok: true, status: 200, json: async () => crew() } as unknown as Response;
    }
    return { ok: true, status: 200, json: async () => stub.crews ?? [] } as unknown as Response;
  });
  return { fetcher, calls };
}

afterEach(() => vi.unstubAllGlobals());

describe('la lista', () => {
  it('muestra el jefe, los integrantes y la zona', async () => {
    const { fetcher } = mockApi({ crews: [crew()] });
    vi.stubGlobal('fetch', fetcher);
    render(<CrewsScreen businessUnit="GYE" />);

    const list = await screen.findByRole('region', { name: 'Cuadrillas de la unidad' });
    expect(within(list).getByText('Jorge Salas')).toBeTruthy();
    expect(within(list).getByText('norte')).toBeTruthy();
    expect(within(list).getByText('1')).toBeTruthy();
  });

  it('explica cuando todavía no hay ninguna', async () => {
    const { fetcher } = mockApi({ crews: [] });
    vi.stubGlobal('fetch', fetcher);
    render(<CrewsScreen businessUnit="GYE" />);
    expect(await screen.findByText(/todavía no tiene cuadrillas/)).toBeTruthy();
  });

  it('pide las inactivas al servidor, o no habría nada que reactivar', async () => {
    const { fetcher, calls } = mockApi({});
    vi.stubGlobal('fetch', fetcher);
    render(<CrewsScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Cuadrillas de la unidad' });
    expect(calls.some((call) => call.url.includes('include_inactive=true'))).toBe(true);
  });

  it('activas antes que inactivas', async () => {
    const { fetcher } = mockApi({
      crews: [crew({ code: 'B', active: false }), crew({ code: 'A', active: true })],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<CrewsScreen businessUnit="GYE" />);
    const list = await screen.findByRole('region', { name: 'Cuadrillas de la unidad' });
    const headers = within(list).getAllByRole('rowheader');
    expect(headers.map((cell) => cell.textContent)).toEqual(['A', 'B']);
  });

  it('desactivar una cuadrilla la manda al servidor y recarga', async () => {
    const { fetcher, calls } = mockApi({ crews: [crew()] });
    vi.stubGlobal('fetch', fetcher);
    render(<CrewsScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByText('Desactivar'));
    await waitFor(() => {
      const posted = calls.find((call) => call.url.includes('/active'));
      expect(posted?.body).toEqual({ active: false });
    });
  });
});

describe('crear o editar', () => {
  it('una cuadrilla nueva se manda con el código escrito', async () => {
    const { fetcher, calls } = mockApi({ crews: [] });
    vi.stubGlobal('fetch', fetcher);
    render(<CrewsScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Nueva cuadrilla' }));
    fireEvent.change(screen.getByLabelText('Código'), { target: { value: 'C-02' } });
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Cuadrilla Dos' } });
    fireEvent.change(screen.getByLabelText('Integrantes (separados por comas)'), {
      target: { value: 'Ana Pérez, Luis Toro' },
    });
    fireEvent.click(screen.getByText('Guardar'));

    await waitFor(() => {
      const put = calls.find((call) => call.method === 'PUT');
      expect(put?.url).toContain('/units/GYE/C-02');
      expect(put?.body).toMatchObject({
        code: 'C-02',
        name: 'Cuadrilla Dos',
        members: ['Ana Pérez', 'Luis Toro'],
      });
    });
  });

  it('editar una cuadrilla existente bloquea el código', async () => {
    const { fetcher } = mockApi({ crews: [crew()] });
    vi.stubGlobal('fetch', fetcher);
    render(<CrewsScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByText('Editar'));
    expect(screen.getByLabelText<HTMLInputElement>('Código').disabled).toBe(true);
    expect(screen.getByLabelText<HTMLInputElement>('Nombre').value).toBe('Cuadrilla 1');
  });

  it('no deja guardar sin nombre', async () => {
    const { fetcher } = mockApi({ crews: [] });
    vi.stubGlobal('fetch', fetcher);
    render(<CrewsScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Nueva cuadrilla' }));
    fireEvent.change(screen.getByLabelText('Código'), { target: { value: 'C-02' } });
    expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Guardar' }).disabled).toBe(true);
  });
});

describe('el historial', () => {
  it('se pide solo al abrirlo, y lista los cambios', async () => {
    const { fetcher, calls } = mockApi({
      crews: [crew()],
      history: [
        {
          sequence: 1,
          kind: 'creacion',
          actor: 'admin.funcional',
          occurred_at: '2026-01-01T12:00:00Z',
          payload: {},
          reason: null,
        },
      ],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<CrewsScreen businessUnit="GYE" />);

    expect(calls.some((call) => call.url.includes('/history'))).toBe(false);
    fireEvent.click(await screen.findByText('Historial'));
    await waitFor(() => {
      expect(calls.some((call) => call.url.includes('/history'))).toBe(true);
    });
    expect(await screen.findByText(/Creada/)).toBeTruthy();
  });
});

describe('el planificador', () => {
  it('ve la lista y no ve con qué escribir', async () => {
    const { fetcher } = mockApi({ crews: [crew()] });
    vi.stubGlobal('fetch', fetcher);
    render(<CrewsScreen businessUnit="GYE" mayEdit={false} />);

    await screen.findByRole('region', { name: 'Cuadrillas de la unidad' });
    expect(screen.queryByRole('region', { name: 'Crear o editar cuadrilla' })).toBeNull();
    expect(screen.queryByText('Desactivar')).toBeNull();
    expect(screen.queryByText('Editar')).toBeNull();
  });
});
