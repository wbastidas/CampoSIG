/**
 * La pantalla de parámetros, renderizada (RF-150).
 *
 * Lo que se comprueba: que los dos pendientes aparezcan separados, que la verificación se firme sin
 * que el navegador diga quién fue, y que quien no es administración funcional no vea el botón.
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Parameter, ParameterIndex, Revision } from '../../api/regulatory';
import { RegulatoryScreen } from './RegulatoryScreen';

function index(overrides: Partial<ParameterIndex> = {}): ParameterIndex {
  return {
    loaded: ['apg.max_restoration_hours'],
    required_by_rules: ['apg.max_restoration_hours', 'grounding.max_resistance_ohm'],
    missing: ['grounding.max_resistance_ohm'],
    unverified: ['apg.max_restoration_hours'],
    ...overrides,
  };
}

function parameter(overrides: Partial<Parameter> = {}): Parameter {
  return {
    code: 'apg.max_restoration_hours',
    value: { v: 24 },
    unit: 'h',
    description: null,
    norm_ref: 'Regulación ARCONEL',
    article_ref: 'num. 5.2',
    source_url: null,
    effective_from: '2026-01-01',
    effective_to: null,
    verified: false,
    verified_by: null,
    verified_at: null,
    strict: false,
    created_by: 'maria.perez',
    updated_by: 'maria.perez',
    updated_at: '2026-01-02T10:00:00+00:00',
    ...overrides,
  };
}

const REVISIONS: Revision[] = [
  {
    at: '2026-01-02T10:00:00+00:00',
    action: 'creado',
    actor: 'maria.perez',
    changed: {},
    note: null,
  },
  {
    at: '2026-01-05T10:00:00+00:00',
    action: 'corregido',
    actor: 'jose.vera',
    changed: { value: { from: 24, to: 30 } },
    note: 'corrige el numeral citado',
  },
];

function mockApi(stub: { index?: ParameterIndex; periods?: Parameter[]; revisions?: Revision[] } = {}) {
  const calls: { url: string; method: string; body: unknown }[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    calls.push({
      url,
      method,
      body: typeof init?.body === 'string' ? JSON.parse(init.body) : null,
    });
    if (url.endsWith('/revisions')) {
      return {
        ok: true,
        status: 200,
        json: async () => stub.revisions ?? REVISIONS,
      } as unknown as Response;
    }
    if (url.includes('/verify')) {
      return {
        ok: true,
        status: 200,
        json: async () => parameter({ verified: true, verified_by: 'kc|admin' }),
      } as unknown as Response;
    }
    if (url.endsWith('/parameters')) {
      return { ok: true, status: 200, json: async () => stub.index ?? index() } as unknown as Response;
    }
    return {
      ok: true,
      status: 200,
      json: async () => stub.periods ?? [parameter()],
    } as unknown as Response;
  });
  return { fetcher, calls };
}

afterEach(() => vi.unstubAllGlobals());

describe('los pendientes', () => {
  it('separa lo que falta de lo que no está verificado', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<RegulatoryScreen />);

    const panel = await screen.findByRole('region', { name: 'Pendientes antes del piloto' });
    expect(within(panel).getByText(/Ninguna regla puede juzgar/)).toBeTruthy();
    expect(within(panel).getByText(/nadie lo comparó con el texto oficial/)).toBeTruthy();
  });

  it('solo dice que está todo cuando las dos listas están vacías', async () => {
    const { fetcher } = mockApi({ index: index({ missing: [], unverified: [] }) });
    vi.stubGlobal('fetch', fetcher);
    render(<RegulatoryScreen />);
    expect(await screen.findByText(/Sin huecos/)).toBeTruthy();
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
    render(<RegulatoryScreen />);
    expect(await screen.findByRole('alert')).toBeTruthy();
  });
});

describe('la historia de un código', () => {
  it('no pide nada hasta que se elige un código', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<RegulatoryScreen />);
    await screen.findByLabelText('Código');
    expect(calls.some((call) => call.url.endsWith('/revisions'))).toBe(false);
  });

  it('muestra el valor con su vigencia y su norma', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<RegulatoryScreen />);

    fireEvent.change(await screen.findByLabelText('Código'), {
      target: { value: 'apg.max_restoration_hours' },
    });
    const detail = await screen.findByRole('region', { name: 'Historia de un código' });
    expect(within(detail).getByText(/desde 01\/01\/2026 · vigente/)).toBeTruthy();
    expect(within(detail).getByText('24 h')).toBeTruthy();
    expect(within(detail).getByText(/Regulación ARCONEL · num. 5.2/)).toBeTruthy();
  });

  it('dice quién lo cargó y quién lo editó', async () => {
    const { fetcher } = mockApi({
      periods: [parameter({ created_by: 'maria.perez', updated_by: 'jose.vera' })],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<RegulatoryScreen />);

    fireEvent.change(await screen.findByLabelText('Código'), {
      target: { value: 'apg.max_restoration_hours' },
    });
    expect(await screen.findByText(/última edición de jose.vera/)).toBeTruthy();
  });

  it('la bitácora de ediciones dice desde qué valor', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<RegulatoryScreen />);

    fireEvent.change(await screen.findByLabelText('Código'), {
      target: { value: 'apg.max_restoration_hours' },
    });
    expect(await screen.findByText(/value: 24 → 30/)).toBeTruthy();
    expect(screen.getByText(/corrige el numeral citado/)).toBeTruthy();
  });
});

describe('la verificación', () => {
  it('se firma sin que el navegador diga quién fue', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<RegulatoryScreen />);

    fireEvent.change(await screen.findByLabelText('Código'), {
      target: { value: 'apg.max_restoration_hours' },
    });
    fireEvent.click(await screen.findByText(/Declaro haber leído el texto oficial/));

    await waitFor(() => {
      const posted = calls.find((call) => call.url.includes('/verify'));
      expect(posted?.body).toEqual({ effective_from: '2026-01-01', note: null });
      expect(JSON.stringify(posted?.body)).not.toContain('verified_by');
    });
  });

  it('un período ya verificado no ofrece volver a verificarlo', async () => {
    const { fetcher } = mockApi({
      periods: [parameter({ verified: true, verified_by: 'jose.vera', verified_at: '2026-02-01' })],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<RegulatoryScreen />);

    fireEvent.change(await screen.findByLabelText('Código'), {
      target: { value: 'apg.max_restoration_hours' },
    });
    expect(await screen.findByText(/Verificado por jose.vera/)).toBeTruthy();
    expect(screen.queryByText(/Declaro haber leído/)).toBeNull();
  });

  it('quien no administra no ve el botón', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<RegulatoryScreen mayEdit={false} />);

    fireEvent.change(await screen.findByLabelText('Código'), {
      target: { value: 'apg.max_restoration_hours' },
    });
    await screen.findByRole('region', { name: 'Historia de un código' });
    expect(screen.queryByText(/Declaro haber leído/)).toBeNull();
  });
});
