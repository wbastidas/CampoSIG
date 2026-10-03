/**
 * La pantalla de planes preventivos, renderizada (RF-012).
 *
 * Lo que se comprueba: que la emisión y el cumplimiento aparezcan juntos —nunca uno en vez del
 * otro—, que un plan atrasado se vea atrasado aunque su conteo sea cero igual que el de un plan sin
 * nada que hacer, que el caveat del alcance expandido esté en pantalla, y que generar sea un botón
 * y no un efecto de abrir la página.
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { PlanCompletion, PlanCoverage, PlanDetail, PlanRow } from '../../api/plans';
import { PlansScreen } from './PlansScreen';

function coverage(overrides: Partial<PlanCoverage> = {}): PlanCoverage {
  return {
    period: '2026-09',
    targets: 3,
    issued: 3,
    skipped_pending: 0,
    skipped_recent: 0,
    caveats: [],
    note: null,
    ...overrides,
  };
}

function completion(overrides: Partial<PlanCompletion> = {}): PlanCompletion {
  return { period: '2026-09', issued: 3, submitted: 1, ...overrides };
}

function plan(overrides: Partial<PlanRow> = {}): PlanRow {
  return {
    code: 'PLAN-MT-01',
    name: 'Inspección preventiva de estructuras',
    description: null,
    work_type: 'inspeccion_preventiva',
    form_code: 'F-MT-01',
    priority: 'media',
    asset_type_key: 'support_structure',
    cadence: 'mensual',
    cadence_days: null,
    day_of_month: 5,
    scope: 'activos',
    scope_value: null,
    skip_if_attended_within_days: null,
    starts_on: '2026-01-05',
    ends_on: null,
    active: true,
    created_by: 'kc|planificador.demo',
    updated_by: null,
    targets: 3,
    coverage: coverage(),
    completion: completion(),
    ...overrides,
  };
}

function detail(overrides: Partial<PlanDetail> = {}): PlanDetail {
  return {
    ...plan(),
    targets: [
      {
        asset_code: 'P-001',
        asset_type_key: null,
        feeder_code: null,
        zone: null,
        sort_order: 0,
      },
    ],
    expanded: [{ asset_code: 'P-001', asset_type_key: null, feeder_code: null }],
    caveats: [],
    note: null,
    history: [
      {
        period: '2026-09',
        asset_code: 'P-002',
        outcome: 'trabajo_pendiente',
        reason: 'ya hay trabajo pendiente en campo sobre este activo',
        work_order_id: null,
        caveats: [],
        issued_at: '2026-09-05T10:00:00Z',
      },
    ],
    ...overrides,
  };
}

function mockApi(stub: { plans?: PlanRow[]; detail?: PlanDetail } = {}) {
  const calls: { url: string; method: string; body: unknown }[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    calls.push({
      url,
      method,
      body: typeof init?.body === 'string' ? JSON.parse(init.body) : null,
    });
    if (url.endsWith('/run')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          plan_code: 'PLAN-MT-01',
          period: '2026-09',
          targets: 3,
          issued: ['a', 'b'],
          skipped_pending: ['P-003'],
          skipped_recent: [],
          already_issued: [],
          caveats: [],
          note: null,
        }),
      } as unknown as Response;
    }
    if (method === 'PUT') {
      return {
        ok: true,
        status: 200,
        json: async () => plan(),
      } as unknown as Response;
    }
    if (url.includes('/plan/')) {
      return {
        ok: true,
        status: 200,
        json: async () => stub.detail ?? detail(),
      } as unknown as Response;
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ plans: stub.plans ?? [plan()] }),
    } as unknown as Response;
  });
  return { fetcher, calls };
}

afterEach(() => vi.unstubAllGlobals());

describe('la lista', () => {
  it('muestra la emisión y el cumplimiento juntos', async () => {
    const { fetcher } = mockApi({
      plans: [
        plan({
          coverage: coverage({ issued: 8, targets: 11 }),
          completion: completion({ issued: 8, submitted: 2 }),
        }),
      ],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);

    expect(await screen.findByText('8 de 11 emitidas en 2026-09')).toBeTruthy();
    expect(screen.getByText('2 de 8 ejecutadas')).toBeTruthy();
  });

  it('un plan cuyo periodo no emitió nada se ve atrasado', async () => {
    const { fetcher } = mockApi({
      plans: [plan({ coverage: coverage({ issued: 0, skipped_pending: 3 }) })],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);

    expect(await screen.findByText(/Atrasado/)).toBeTruthy();
  });

  it('un plan sin activos no se confunde con uno atrasado', async () => {
    const { fetcher } = mockApi({
      plans: [plan({ coverage: coverage({ targets: 0, issued: 0 }) })],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);

    expect(await screen.findByText(/Sin alcance/)).toBeTruthy();
  });

  it('abrir la pantalla no genera ninguna OT', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);

    await screen.findByText('PLAN-MT-01');
    expect(calls.every((call) => call.method === 'GET')).toBe(true);
  });

  it('quien no edita no ve el botón de generar', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" mayEdit={false} />);

    await screen.findByText('PLAN-MT-01');
    expect(screen.queryByRole('button', { name: 'Generar ahora' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Nuevo plan' })).toBeNull();
  });
});

describe('generar ahora', () => {
  it('informa cuántas emitió y qué se saltó', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Generar ahora' }));

    expect(await screen.findByText(/2 OT emitida\(s\) en 2026-09/)).toBeTruthy();
    expect(screen.getByRole('status').textContent).toContain('1 con trabajo pendiente');
    expect(calls.some((call) => call.method === 'POST' && call.url.endsWith('/run'))).toBe(true);
  });

  it('un error del servidor se muestra tal cual', async () => {
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/run')) {
        return {
          ok: false,
          status: 422,
          statusText: 'Unprocessable',
          json: async () => ({
            detail: 'el formulario «F-MT-01» no está en el catálogo',
          }),
        } as unknown as Response;
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ plans: [plan()] }),
      } as unknown as Response;
    });
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Generar ahora' }));

    expect(await screen.findByText(/no está en el catálogo/)).toBeTruthy();
  });
});

describe('el detalle', () => {
  it('muestra el caveat del alcance expandido en las palabras del servidor', async () => {
    const caveat =
      'El inventario de activos vive en el SIG: la expansión cubre solo los activos con trabajo.';
    const { fetcher } = mockApi({
      plans: [plan({ scope: 'alimentador', scope_value: 'ALIM-SUR' })],
      detail: detail({
        scope: 'alimentador',
        scope_value: 'ALIM-SUR',
        caveats: [caveat],
      }),
    });
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Ver' }));

    expect(await screen.findByText(caveat)).toBeTruthy();
    expect(screen.getByText(/expande a 1 activo/)).toBeTruthy();
  });

  it('el historial muestra el motivo de lo que no se emitió', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Ver' }));

    const table = await screen.findByRole('table', { name: /Historial/ });
    expect(within(table).getByText('Ya había trabajo pendiente')).toBeTruthy();
    expect(
      within(table).getByText('ya hay trabajo pendiente en campo sobre este activo'),
    ).toBeTruthy();
  });
});

describe('el formulario de un plan nuevo', () => {
  async function openForm() {
    fireEvent.click(await screen.findByRole('button', { name: 'Nuevo plan' }));
    return screen.getByRole('form', { name: 'Nuevo plan preventivo' });
  }

  it('el día 31 se rechaza en pantalla y se explica por qué', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);
    await openForm();

    fireEvent.change(screen.getByLabelText(/Día del mes/), {
      target: { value: '31' },
    });

    expect(screen.getByText(/febrero/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Guardar el plan' }).hasAttribute('disabled')).toBe(
      true,
    );
  });

  it('manda la lista de activos en el orden escrito, que es la ruta', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);
    await openForm();

    fireEvent.change(screen.getByLabelText('Código'), {
      target: { value: 'PLAN-B' },
    });
    fireEvent.change(screen.getByLabelText('Nombre'), {
      target: { value: 'Ruta sur' },
    });
    fireEvent.change(screen.getByLabelText('Formulario'), {
      target: { value: 'F-MT-01' },
    });
    fireEvent.change(screen.getByLabelText(/Activos/), {
      target: { value: 'P-003\nP-001' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar el plan' }));

    await waitFor(() => expect(calls.some((call) => call.method === 'PUT')).toBe(true));
    const sent = calls.find((call) => call.method === 'PUT');
    expect(sent?.url).toContain('/plan/PLAN-B');
    expect((sent?.body as { targets: unknown }).targets).toEqual([
      { asset_code: 'P-003', sort_order: 0 },
      { asset_code: 'P-001', sort_order: 1 },
    ]);
  });

  it('al elegir un alcance por alimentador advierte que la expansión puede ser menor', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);
    await openForm();

    fireEvent.change(screen.getByLabelText('Alcance'), {
      target: { value: 'alimentador' },
    });
    fireEvent.change(screen.getByLabelText(/Código del alimentador/), {
      target: { value: 'ALIM-SUR' },
    });

    expect(screen.getByText(/SIG/)).toBeTruthy();
    expect(screen.queryByLabelText(/Activos/)).toBeNull();
  });

  it('una frecuencia en días pide los días en vez del día del mes', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PlansScreen businessUnit="GYE" />);
    await openForm();

    fireEvent.change(screen.getByLabelText('Frecuencia'), {
      target: { value: 'dias' },
    });

    expect(screen.getByLabelText(/Cada cuántos días/)).toBeTruthy();
    expect(screen.queryByLabelText(/Día del mes/)).toBeNull();
  });
});
