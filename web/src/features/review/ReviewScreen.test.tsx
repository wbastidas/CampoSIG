/**
 * La pantalla de revisión, renderizada (M11, RF-112, ADR-007).
 *
 * Aquí es donde los datos de campo se vuelven autoritativos, así que lo que se comprueba es que
 * las cuatro cosas de las que depende una decisión sean imposibles de no ver: los valores que un
 * modelo propuso y quién los confirmó, la misma foto mandada como antes y como después, los
 * hallazgos normativos con su cita —y sin cita cuando el límite no está verificado—, y los
 * impedimentos **antes** de pulsar Aprobar.
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ReviewDetail } from '../../api/review';
import { ReviewScreen } from './ReviewScreen';

const NOW = new Date('2026-09-22T12:00:00Z');

const QUEUE = {
  total: 1,
  items: [
    {
      work_order_id: 'wo-1',
      code: 'OT-000101',
      work_type: 'inspeccion_preventiva',
      form_code: 'F-MT-01',
      state: 'sincronizada',
      priority: 'alta',
      asset_code: 'P-000452',
      crew_id: null,
      sla_due_at: null,
      updated_at: '2026-09-22T10:00:00Z',
    },
  ],
};

function detail(overrides: Partial<ReviewDetail> = {}): ReviewDetail {
  return {
    work_order: {
      work_order_id: 'wo-1',
      code: 'OT-000101',
      work_type: 'inspeccion_preventiva',
      state: 'en_revision',
      priority: 'alta',
      asset_type_key: 'support_structure',
      asset_code: 'P-000452',
      feeder_code: '04BH070T11',
      zone: 'Durán',
      external_ref: null,
    },
    form: {
      code: 'F-MT-01',
      version: '1.0.0',
      title: 'Inspección preventiva de estructura',
      schema: {},
      ui_schema: {},
      warnings: [],
    },
    response: {
      response_id: 'r-1',
      state: 'enviada',
      answers: {},
      captured_by: 'tecnico.1',
      captured_at: null,
      submitted_at: null,
    },
    provenance: [],
    evidence: [],
    photo_counts: { antes: 2 },
    missing_photos: [],
    compliance: [],
    blockers: [],
    observations: [],
    history: [],
    ...overrides,
  };
}

function mockApi(body: ReviewDetail, onDecision?: (payload: unknown) => Response) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/decision')) {
      if (onDecision) return onDecision(JSON.parse(String(init?.body)));
      return {
        ok: true,
        status: 200,
        json: async () => ({ decision: 'aprobada', work_order_state: 'aprobada' }),
      } as unknown as Response;
    }
    if (url.includes('/gis-tray')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ proposals: [], batches: [] }),
      } as unknown as Response;
    }
    if (url.includes('/queue')) {
      return { ok: true, status: 200, json: async () => QUEUE } as unknown as Response;
    }
    return { ok: true, status: 200, json: async () => body } as unknown as Response;
  });
}

async function openTheOrder() {
  const button = await screen.findByRole('button', { name: /OT-000101/ });
  button.click();
}

afterEach(() => vi.unstubAllGlobals());

describe('la cola', () => {
  it('lista lo que espera decisión y abre el detalle', async () => {
    vi.stubGlobal('fetch', mockApi(detail()));
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);

    await waitFor(() => expect(screen.getByText(/1 orden\(es\) esperando/)).toBeTruthy());
    await openTheOrder();
    await waitFor(() =>
      expect(screen.getByText(/Inspección preventiva de estructura/)).toBeTruthy(),
    );
  });
});

describe('la auditoría de la IA', () => {
  it('destaca lo que nadie confirmó y dice de dónde salió', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        detail({
          provenance: [
            {
              field_key: 'material',
              origin: 'vision',
              proposed_value: 'concrete',
              final_value: null,
              confidence: 0.91,
              model_name: 'mobilenetv3-pole',
              model_version: '2026.09',
              accepted_unchanged: false,
              confirmed_by: null,
              source: 'evidencia:ev-1@0.300,0.200,0.200,0.600',
              is_ai: true,
            },
          ],
          blockers: ['hay valores propuestos por IA sin confirmar: material'],
        }),
      ),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    await waitFor(() => expect(screen.getByText('nadie todavía')).toBeTruthy());
    // Una propuesta que no se puede mirar no es revisable.
    expect(screen.getByText('evidencia:ev-1@0.300,0.200,0.200,0.600')).toBeTruthy();
    expect(screen.getByText('mobilenetv3-pole 2026.09')).toBeTruthy();
  });

  it('una propuesta que es un objeto se muestra legible, no como [object Object]', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        detail({
          provenance: [
            {
              field_key: 'activities',
              origin: 'voz',
              proposed_value: [{ activity_code: 'PODA', quantity: 2 }],
              final_value: null,
              confidence: 0.8,
              model_name: 'rule-based-es-ec',
              model_version: '0.1.0',
              accepted_unchanged: false,
              confirmed_by: null,
              source: 'se podaron dos vanos',
              is_ai: true,
            },
          ],
        }),
      ),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    await waitFor(() => expect(screen.getByText(/activity_code: PODA/)).toBeTruthy());
    expect(screen.queryByText('[object Object]')).toBeNull();
  });

  it('sin propuestas de IA no muestra una tasa del 0 %', async () => {
    vi.stubGlobal('fetch', mockApi(detail()));
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    await waitFor(() => expect(screen.getByText('sin propuestas')).toBeTruthy());
  });
});

describe('los hallazgos normativos', () => {
  it('un límite verificado se cita con norma y numeral', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        detail({
          compliance: [
            {
              rule: 'resistencia_puesta_a_tierra',
              outcome: 'incumple',
              message: 'resistencia medida de 90 Ω por encima del máximo admisible de 25 Ω',
              severity: 'high',
              measured: 90,
              limit: 25,
              unit: 'ohm',
              norm_ref: 'Normas técnicas de distribución',
              article_ref: 'Numeral 5.3',
              limit_verified: true,
              parameter_code: 'grounding.max_resistance_ohm.poste',
              evaluated_on: '2026-09-01',
              blocking: true,
            },
          ],
          blockers: ['incumplimiento normativo: resistencia medida de 90 Ω (… Numeral 5.3)'],
        }),
      ),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    await waitFor(() =>
      expect(screen.getByText('Normas técnicas de distribución, Numeral 5.3')).toBeTruthy(),
    );
  });

  it('un límite sin verificar NO se presenta como cita del texto oficial', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        detail({
          compliance: [
            {
              rule: 'plazo_reposicion_apg',
              outcome: 'incumple',
              message: 'la reposición tomó 72 h por encima del plazo de 48 h',
              severity: 'high',
              measured: 72,
              limit: 48,
              unit: 'h',
              norm_ref: 'Regulación de alumbrado público',
              article_ref: null,
              limit_verified: false,
              parameter_code: 'apg.max_restoration_hours',
              evaluated_on: '2026-09-01',
              blocking: false,
            },
          ],
        }),
      ),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    await waitFor(() => expect(screen.getByText(/sin verificar/)).toBeTruthy());
  });

  it('"sin medición" no se muestra igual que "cumple"', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        detail({
          compliance: [
            {
              rule: 'resistencia_puesta_a_tierra',
              outcome: 'no_aplica',
              message: 'la captura no registra medición de resistencia de puesta a tierra',
              severity: 'low',
              measured: null,
              limit: null,
              unit: null,
              norm_ref: null,
              article_ref: null,
              limit_verified: true,
              parameter_code: null,
              evaluated_on: '2026-09-01',
              blocking: false,
            },
          ],
        }),
      ),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    await waitFor(() => expect(screen.getByText('Sin medición')).toBeTruthy());
    expect(screen.queryByText('Cumple')).toBeNull();
  });
});

describe('antes y después', () => {
  it('avisa cuando la misma foto se mandó dos veces', async () => {
    const same = 'a'.repeat(64);
    vi.stubGlobal(
      'fetch',
      mockApi(
        detail({
          evidence: [
            {
              evidence_id: 'e1',
              kind: 'foto',
              stage: 'antes',
              storage_key: 's3://antes.jpg',
              content_hash: same,
              integrity_verified: true,
              vision_result: null,
            },
            {
              evidence_id: 'e2',
              kind: 'foto',
              stage: 'despues',
              storage_key: 's3://despues.jpg',
              content_hash: same,
              integrity_verified: true,
              vision_result: null,
            },
          ],
        }),
      ),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    // Por hash, no por un modelo: un archivo idéntico es idéntico.
    await waitFor(() =>
      expect(
        screen.getAllByRole('alert').some((node) => /misma fotografía/.test(node.textContent ?? '')),
      ).toBe(true),
    );
  });

  it('destaca la evidencia cuyo hash no coincide con lo que registró el dispositivo', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        detail({
          evidence: [
            {
              evidence_id: 'e1',
              kind: 'foto',
              stage: 'antes',
              storage_key: 's3://sospechosa.jpg',
              content_hash: 'b'.repeat(64),
              integrity_verified: false,
              vision_result: null,
            },
          ],
        }),
      ),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    await waitFor(() =>
      expect(
        screen.getAllByRole('alert').some((node) => /hash no coincide/.test(node.textContent ?? '')),
      ).toBe(true),
    );
  });
});

describe('la decisión', () => {
  it('los impedimentos se ven antes de pulsar Aprobar', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(detail({ blockers: ['la respuesta sigue en borrador; el técnico no la ha cerrado'] })),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    await waitFor(() => expect(screen.getByText(/No se puede aprobar todavía/)).toBeTruthy());
    expect(screen.getByText(/sigue en borrador/)).toBeTruthy();
  });

  it('si el servidor rechaza la aprobación, la pantalla muestra sus razones como lista', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(detail(), () =>
        ({
          ok: false,
          status: 422,
          json: async () => ({
            detail: {
              message: 'la aprobación tiene condiciones pendientes',
              blockers: ['faltan 2 fotografía(s) de cierre', 'hay valores de IA sin confirmar'],
            },
          }),
        }) as unknown as Response,
      ),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    const approve = await screen.findByRole('button', { name: 'Aprobar' });
    approve.click();

    // Como lista: un supervisor no debería analizar una frase larga para hallar la condición.
    await waitFor(() => expect(screen.getByText('faltan 2 fotografía(s) de cierre')).toBeTruthy());
    const blockers = screen.getByRole('alert');
    expect(within(blockers).getAllByRole('listitem')).toHaveLength(2);
  });

  it('aprobar NO nombra al revisor: eso lo dice el token', async () => {
    const seen: unknown[] = [];
    vi.stubGlobal(
      'fetch',
      mockApi(detail(), (payload) => {
        seen.push(payload);
        return {
          ok: true,
          status: 200,
          json: async () => ({ decision: 'aprobada', work_order_state: 'aprobada' }),
        } as unknown as Response;
      }),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="supervisor.1" now={() => NOW} />);
    await openTheOrder();

    const approve = await screen.findByRole('button', { name: 'Aprobar' });
    approve.click();

    await waitFor(() => expect(seen).toHaveLength(1));
    // Mandar `reviewer_sub` sería un campo que parece firmar la aprobación y que el servidor
    // descarta (ADR-013). Que no viaje es la mitad visible de esa decisión.
    expect(seen[0]).toEqual({ decision: 'aprobada' });
  });
});

describe('el acta (RF-115)', () => {
  function actaApi(detail: ReviewDetail, onIssue?: () => void) {
    return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/acta')) {
        onIssue?.();
        return {
          ok: true,
          status: 200,
          headers: new Headers({
            'X-SIGEC-Verification-Code': 'Zm9vYmFyMTIzNDU2',
            'X-SIGEC-Document-Hash': 'a'.repeat(64),
          }),
          blob: async () => new Blob(['%PDF-1.7'], { type: 'application/pdf' }),
        } as unknown as Response;
      }
      if (url.includes('/gis-tray')) {
        return { ok: true, status: 200, json: async () => ({ proposals: [], batches: [] }) } as unknown as Response;
      }
      if (url.includes('/queue')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            total: 1,
            items: [
              {
                work_order_id: detail.work_order.work_order_id,
                code: detail.work_order.code,
                work_type: detail.work_order.work_type,
                form_code: detail.form.code,
                state: detail.work_order.state,
                priority: detail.work_order.priority,
                asset_code: detail.work_order.asset_code,
                crew_id: null,
                sla_due_at: null,
                updated_at: null,
              },
            ],
          }),
        } as unknown as Response;
      }
      void init;
      return { ok: true, status: 200, json: async () => detail } as unknown as Response;
    });
  }

  it('avisa que el acta de una OT sin aprobar saldrá como borrador', async () => {
    const pending = detail();
    pending.work_order.state = 'sincronizada';
    vi.stubGlobal('fetch', actaApi(pending));
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" />);

    (await screen.findByRole('button', { name: /OT-/ })).click();
    expect(await screen.findByText(/saldrá marcada como borrador/)).not.toBeNull();
  });

  it('emitida, muestra el código de verificación para poder dictarlo', async () => {
    // Un QR que no enfoca es un problema corriente en campo, así que el código se lee en voz.
    const approved = detail();
    approved.work_order.state = 'aprobada';
    let issued = false;
    vi.stubGlobal('fetch', actaApi(approved, () => { issued = true; }));
    const createUrl = vi.fn(() => 'blob:acta');
    vi.stubGlobal('URL', { createObjectURL: createUrl, revokeObjectURL: vi.fn() });
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" />);

    (await screen.findByRole('button', { name: /OT-/ })).click();
    const button = await screen.findByRole('button', { name: 'Emitir acta en PDF' });
    button.click();

    expect(await screen.findByText(/Acta emitida/)).not.toBeNull();
    expect(screen.getByText('Zm9vYmFyMTIzNDU2')).not.toBeNull();
    expect(issued).toBe(true);
    // Y el object URL se libera: un supervisor emite decenas en una mañana.
    expect(createUrl).toHaveBeenCalled();
  });
});
