/**
 * La bandeja de propuestas, renderizada (RF-013, RF-114).
 *
 * Lo que se comprueba: que una prioridad estimada muestre en pantalla lo que no se pudo saber, que
 * el rechazo no ofrezca ningún campo libre como motivo, y que las tres decisiones lleguen al
 * servidor con lo que el supervisor eligió y sin nada que el supervisor no eligió.
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Criticality, Proposal, Tray } from '../../api/proposals';
import { ProposalsScreen } from './ProposalsScreen';

function criticality(overrides: Partial<Criticality> = {}): Criticality {
  return {
    severity: 4,
    consequence: 3,
    score: 12,
    priority: 'alta',
    annex_band: 'P2',
    exposed: false,
    estimated: false,
    caveats: [],
    explanation: 'severidad 4 × consecuencia 3 = 12 → P2 alta',
    ...overrides,
  };
}

function proposal(overrides: Partial<Proposal> = {}): Proposal {
  return {
    id: 'p-1',
    state: 'propuesta',
    origin: 'hallazgo_campo',
    asset_code: 'P-000452',
    asset_type_key: 'support_structure',
    feeder_code: '04BH070T11',
    zone: 'Urbano',
    defect_code: 'puesta_tierra_faltante',
    work_type: 'correctivo',
    form_code: 'F-MT-01',
    priority: 'alta',
    criticality: criticality(),
    suggested_deadline_hours: 72,
    justification: 'Falta puesta a tierra en P-000452',
    findings: [],
    source_work_order_id: 'ot-1',
    work_order_id: null,
    merged_into_id: null,
    reject_reason_code: null,
    reject_note: null,
    decided_by: null,
    decided_at: null,
    created_at: '2026-09-20T12:00:00+00:00',
    model_name: null,
    model_version: null,
    confidence: null,
    ...overrides,
  };
}

function tray(overrides: Partial<Tray> = {}): Tray {
  return {
    state: 'propuesta',
    counts: { propuesta: 1 },
    reject_reasons: [
      { code: 'no_es_defecto', label: 'No es un defecto', signal: 'falso_positivo' },
      { code: 'ya_resuelto', label: 'Ya está resuelto', signal: 'ninguna' },
    ],
    proposals: [proposal()],
    ...overrides,
  };
}

function mockApi(stub: { tray?: Tray } = {}) {
  const calls: { url: string; method: string; body: unknown }[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    calls.push({
      url,
      method,
      body: typeof init?.body === 'string' ? JSON.parse(init.body) : null,
    });
    if (method === 'POST') {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          work_order_id: 'ot-nueva',
          state: 'planificada',
          proposal: proposal({ state: 'aprobada' }),
        }),
      } as unknown as Response;
    }
    return { ok: true, status: 200, json: async () => stub.tray ?? tray() } as unknown as Response;
  });
  return { fetcher, calls };
}

afterEach(() => vi.unstubAllGlobals());

async function openDecision() {
  fireEvent.click(await screen.findByRole('button', { name: 'Decidir' }));
}

describe('la bandeja', () => {
  it('muestra la banda del anexo y la aritmética, para que se pueda rehacer', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" />);

    expect(await screen.findByText(/P2 Alta/)).toBeTruthy();
    expect(screen.getByText(/severidad 4/)).toBeTruthy();
    expect(screen.getByText('Plazo sugerido: 3 día(s)')).toBeTruthy();
  });

  it('una prioridad estimada muestra lo que no se pudo saber', async () => {
    const { fetcher } = mockApi({
      tray: tray({
        proposals: [
          proposal({
            criticality: criticality({
              estimated: true,
              caveats: ['Se asume ramal de media tensión.'],
            }),
          }),
        ],
      }),
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" />);

    expect(await screen.findByText(/Estimada/)).toBeTruthy();
    expect(screen.getByText('Se asume ramal de media tensión.')).toBeTruthy();
  });

  it('una calculada no muestra ninguna advertencia que no haya', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" />);

    expect(await screen.findByText(/Calculada/)).toBeTruthy();
    expect(screen.queryByLabelText(/Lo que no se pudo saber/)).toBeNull();
  });

  it('una propuesta de visión muestra el modelo y la confianza (regla 8)', async () => {
    const { fetcher } = mockApi({
      tray: tray({
        proposals: [
          proposal({
            origin: 'deteccion_visual',
            model_name: 'defectos-mv',
            model_version: '2.1.0',
            confidence: 0.82,
          }),
        ],
      }),
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" />);

    expect(await screen.findByText('Detección visual')).toBeTruthy();
    expect(screen.getByText(/defectos-mv 2.1.0 — confianza 82 %/)).toBeTruthy();
  });

  it('quien no decide no ve el botón de decidir', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" mayDecide={false} />);

    await screen.findByText(/P2 Alta/);
    expect(screen.queryByRole('button', { name: 'Decidir' })).toBeNull();
  });
});

describe('las tres decisiones', () => {
  it('aprobar manda la prioridad que el supervisor eligió y nada más', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" />);
    await openDecision();

    fireEvent.change(screen.getByLabelText('Prioridad'), { target: { value: 'critica' } });
    expect(screen.getByText(/en lugar de la Alta/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));

    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    const sent = calls.find((call) => call.method === 'POST');
    expect(sent?.url).toContain('/approve');
    expect(sent?.body).toEqual({ priority: 'critica' });
  });

  it('aprobar sin tocar nada no manda prioridad: la calculada manda', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" />);
    await openDecision();
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));

    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    expect(calls.find((call) => call.method === 'POST')?.body).toEqual({});
  });

  it('fusionar no se puede confirmar sin la OT de destino', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" />);
    await openDecision();

    fireEvent.click(screen.getByRole('radio', { name: 'fusionar' }));
    expect(screen.getByRole('button', { name: 'Confirmar' }).hasAttribute('disabled')).toBe(true);

    fireEvent.change(screen.getByLabelText('OT de destino'), { target: { value: 'ot-9' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));

    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    const sent = calls.find((call) => call.method === 'POST');
    expect(sent?.url).toContain('/merge');
    expect(sent?.body).toEqual({ work_order_id: 'ot-9' });
  });

  it('el motivo de rechazo es un selector del catálogo y nunca un campo libre', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" />);
    await openDecision();

    fireEvent.click(screen.getByRole('radio', { name: 'rechazar' }));
    const picker = screen.getByLabelText('Motivo');
    expect(picker.tagName).toBe('SELECT');
    expect(within(picker).getByRole('option', { name: 'No es un defecto' })).toBeTruthy();

    fireEvent.change(picker, { target: { value: 'ya_resuelto' } });
    // Qué enseña el motivo elegido, que es lo que decide si sirve como ejemplo negativo.
    expect(screen.getByText(/no enseña nada/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Nota'), { target: { value: 'ya lo cambiaron' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));

    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    const sent = calls.find((call) => call.method === 'POST');
    expect(sent?.url).toContain('/reject');
    expect(sent?.body).toEqual({ reason_code: 'ya_resuelto', note: 'ya lo cambiaron' });
  });

  it('sin catálogo de motivos lo dice y manda a cargarlo', async () => {
    const { fetcher } = mockApi({ tray: tray({ reject_reasons: [] }) });
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" />);

    expect(await screen.findByText(/no se puede rechazar/)).toBeTruthy();
  });

  it('un error del servidor se muestra tal cual y no se traga', async () => {
    const fetcher = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if ((init?.method ?? 'GET') === 'POST') {
        return {
          ok: false,
          status: 409,
          statusText: 'Conflict',
          json: async () => ({ detail: 'la propuesta ya está «aprobada»' }),
        } as unknown as Response;
      }
      return { ok: true, status: 200, json: async () => tray() } as unknown as Response;
    });
    vi.stubGlobal('fetch', fetcher);
    render(<ProposalsScreen businessUnit="GYE" />);
    await openDecision();
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));

    expect(await screen.findByText('la propuesta ya está «aprobada»')).toBeTruthy();
  });
});
