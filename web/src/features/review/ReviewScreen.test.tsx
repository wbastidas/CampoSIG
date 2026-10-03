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
      pre_review_state: 'terminado',
      risk_level: 'medium',
    },
  ],
};

const NO_SAMPLE = {
  both_clear: 0,
  both_flagged: 0,
  supervisor_only: 0,
  agent_only: 0,
  pending: 0,
  unpaired: 0,
  paired: 0,
  observed_agreement: null,
  kappa: null,
  kappa_floor: 0.6,
  meets_floor: null,
  min_sample: 10,
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
      rules: [],
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
    degradations: [],
    agent_report: null,
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
    if (url.includes('/agent-agreement')) {
      return { ok: true, status: 200, json: async () => NO_SAMPLE } as unknown as Response;
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
      if (url.includes('/agent-agreement')) {
        return { ok: true, status: 200, json: async () => NO_SAMPLE } as unknown as Response;
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
                pre_review_state: null,
                risk_level: null,
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

describe('el aviso de IA no disponible (RF-204)', () => {
  it('se muestra con su motivo, y dice que la decisión no depende de eso', async () => {
    const withGap = detail({
      degradations: [
        {
          alias: 'vlm-audit',
          purpose: 'Auditoría de evidencia visual',
          placement: 'unavailable',
          reason: "'vlm-audit' necesita GPU y el perfil A no tiene; se omite con aviso",
        },
      ],
    });
    vi.stubGlobal('fetch', mockApi(withGap));
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" />);

    (await screen.findByRole('button', { name: /OT-/ })).click();
    expect(await screen.findByText(/No se va a ejecutar/)).not.toBeNull();
    expect(screen.getByText(/necesita GPU y el perfil A no tiene/)).not.toBeNull();
    // Y lo importante: que el supervisor sepa que puede decidir igual.
    expect(screen.getByText(/La decisión no depende de esto/)).not.toBeNull();
  });

  it('sin degradaciones no aparece la sección', async () => {
    vi.stubGlobal('fetch', mockApi(detail({ degradations: [] })));
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" />);

    (await screen.findByRole('button', { name: /OT-/ })).click();
    await screen.findByText(/Decisión/);
    expect(screen.queryByText(/Lo que la IA no va a aportar/)).toBeNull();
  });
});

describe('el informe de pre-revisión en pantalla (RF-111)', () => {
  const observation = {
    id: 'coh-gps-distance',
    category: 'coherence' as const,
    severity: 'high' as const,
    message: 'La captura se registró a 6,5 km del activo P-000452.',
    evidence: [
      { type: 'field' as const, span: null, json_path: '$.gps', evidence_id: null, detail: null },
      {
        type: 'computed' as const,
        span: null,
        json_path: null,
        evidence_id: null,
        detail: 'distancia haversine: 6,5 km, tolerancia 250 m',
      },
    ],
    source: null,
    suggested_action: 'Confirmar que se trabajó en el activo de la OT.',
    confidence: null,
    node: 'coherence',
  };

  const report = {
    work_order_id: 'wo-1',
    graph_version: 'prereview-0.1.0',
    hardware_profile: 'A',
    risk_level: 'high' as const,
    status: 'partial' as const,
    summary: '1 observación (1 de severidad alta). No se ejecutó: auditoría de evidencia visual.',
    observations: [observation],
    models: {},
    budget: { llm_calls: 0, tokens: 0, duration_s: 0.02 },
    skipped: ['auditoría de evidencia visual: sin GPU'],
    discarded: 0,
  };

  it('muestra el riesgo en palabras, el resumen y la evidencia que la observación señala', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(detail({ agent_report: { run_state: 'parcial', error: null, report, blind: false } })),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" />);

    (await screen.findByRole('button', { name: /OT-/ })).click();
    expect(await screen.findByText(/Riesgo alto/)).not.toBeNull();
    expect(screen.getByText(/6,5 km del activo/)).not.toBeNull();
    // La evidencia: sin esto el supervisor tendría que ir a buscarla, que es el trabajo que el
    // informe existe para ahorrar.
    expect(screen.getByText(/distancia haversine/)).not.toBeNull();
    expect(screen.getByText(/Confirmar que se trabajó/)).not.toBeNull();
  });

  it('sin informe muestra por qué no lo hay, no un hueco', async () => {
    vi.stubGlobal('fetch', mockApi(detail({ agent_report: null })));
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" />);

    (await screen.findByRole('button', { name: /OT-/ })).click();
    expect(await screen.findByText(/todavía no se ha ejecutado/)).not.toBeNull();
  });

  it('una ejecución fallida se distingue de una que no corrió', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        detail({
          agent_report: {
            run_state: 'fallido',
            error: 'RuntimeError: el grafo se rompió',
            report: null,
            blind: false,
          },
        }),
      ),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" />);

    (await screen.findByRole('button', { name: /OT-/ })).click();
    expect(await screen.findByText(/falló/)).not.toBeNull();
    expect(screen.getByText(/el grafo se rompió/)).not.toBeNull();
  });

  it('un descarte del guardrail se anuncia', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        detail({
          agent_report: {
            run_state: 'terminado',
            error: null,
            report: { ...report, discarded: 2, observations: [] },
            blind: false,
          },
        }),
      ),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" />);

    (await screen.findByRole('button', { name: /OT-/ })).click();
    expect(await screen.findByText(/descartó 2 observación/)).not.toBeNull();
  });
});

/**
 * La aprobación en lote, en pantalla (RF-176).
 *
 * Lo que se comprueba es lo que el requerimiento cobra por conceder el bloque: que solo se pueda
 * marcar las de riesgo bajo, que la muestra se diga **antes** de pulsar, que haga falta una segunda
 * pulsación, y que después el resultado nombre las apartadas. «12 aprobadas» sin «1 apartada» se lee
 * como un lote terminado, y la apartada es justo el punto.
 */
describe('aprobación en lote (RF-176)', () => {
  function queueItem(id: string, risk: 'low' | 'medium' | 'high' | null) {
    return {
      work_order_id: id,
      code: `OT-${id.toUpperCase()}`,
      work_type: 'inspeccion_preventiva',
      form_code: 'F-MT-01',
      state: 'sincronizada',
      priority: 'media',
      asset_code: null,
      crew_id: null,
      sla_due_at: null,
      updated_at: '2026-09-22T10:00:00Z',
      pre_review_state: risk === null ? null : 'terminado',
      risk_level: risk,
    };
  }

  function mockBatchApi(
    items: ReturnType<typeof queueItem>[],
    outcome?: Record<string, unknown>,
  ) {
    const posted: unknown[] = [];
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/batch-approval/preview')) {
        const size = Number(new URL(url, 'http://x').searchParams.get('size'));
        // La misma política del servidor: techo del 5 %, piso de uno.
        const held = size === 0 ? 0 : Math.max(1, Math.ceil(size * 0.05));
        return {
          ok: true,
          status: 200,
          json: async () => ({ batch_size: size, sampled: held, would_approve: size - held }),
        } as unknown as Response;
      }
      if (url.includes('/batch-approval')) {
        posted.push(JSON.parse(String(init?.body)));
        return {
          ok: true,
          status: 200,
          json: async () =>
            outcome ?? {
              approved: items.slice(1).map((item) => item.work_order_id),
              sampled: [items[0]!.work_order_id],
              refused: [],
              sample_note: '1 OT quedaron apartadas para verificación individual obligatoria',
            },
        } as unknown as Response;
      }
      if (url.includes('/agent-agreement')) {
        return { ok: true, status: 200, json: async () => NO_SAMPLE } as unknown as Response;
      }
      if (url.includes('/gis-tray')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ proposals: [], batches: [] }),
        } as unknown as Response;
      }
      if (url.includes('/queue')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ total: items.length, items }),
        } as unknown as Response;
      }
      return { ok: true, status: 200, json: async () => detail() } as unknown as Response;
    });
    return { fetcher, posted };
  }

  it('solo las de riesgo bajo se pueden marcar, y de las demás se dice por qué', async () => {
    const { fetcher } = mockBatchApi([
      queueItem('a', 'low'),
      queueItem('b', 'medium'),
      queueItem('c', null),
    ]);
    vi.stubGlobal('fetch', fetcher);
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" now={() => NOW} />);

    await waitFor(() => expect(screen.getByText(/3 orden\(es\)/)).toBeTruthy());
    const boxes = screen.getAllByRole('checkbox');
    expect(boxes).toHaveLength(1);
    expect(boxes[0]!.getAttribute('aria-label')).toContain('OT-A');
    expect(screen.getByText(/Riesgo medio: se revisa una por una/)).toBeTruthy();
    expect(screen.getByText(/Sin pre-revisión: se revisa una por una/)).toBeTruthy();
  });

  it('dice cuántas quedarán apartadas antes de pulsar', async () => {
    const { fetcher } = mockBatchApi(
      Array.from({ length: 4 }, (_, index) => queueItem(`l${index}`, 'low')),
    );
    vi.stubGlobal('fetch', fetcher);
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" now={() => NOW} />);

    const boxes = await screen.findAllByRole('checkbox');
    for (const box of boxes) box.click();

    await waitFor(() => expect(screen.getByText(/se aprobarán 3/)).toBeTruthy());
    expect(screen.getByText(/1 apartada\(s\)/)).toBeTruthy();
  });

  it('hace falta confirmar: una sola pulsación no aprueba nada', async () => {
    const { fetcher, posted } = mockBatchApi(
      Array.from({ length: 4 }, (_, index) => queueItem(`l${index}`, 'low')),
    );
    vi.stubGlobal('fetch', fetcher);
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" now={() => NOW} />);

    const boxes = await screen.findAllByRole('checkbox');
    for (const box of boxes) box.click();
    await waitFor(() => expect(screen.getByText(/se aprobarán 3/)).toBeTruthy());

    (await screen.findByRole('button', { name: /Aprobar 4 en lote/ })).click();
    // La primera pulsación solo pregunta. Un lote libera propuestas as-built de cada OT hacia el
    // SIG corporativo, y eso no se hace con un clic mal dado.
    expect(posted).toHaveLength(0);
    expect(await screen.findByText(/No se puede deshacer en bloque/)).toBeTruthy();

    (await screen.findByRole('button', { name: /Confirmar aprobación en lote/ })).click();
    await waitFor(() => expect(posted).toHaveLength(1));
    expect((posted[0] as { work_order_ids: string[] }).work_order_ids).toHaveLength(4);
  });

  it('el resultado nombra las apartadas, no solo las aprobadas', async () => {
    const { fetcher } = mockBatchApi(
      Array.from({ length: 4 }, (_, index) => queueItem(`l${index}`, 'low')),
      {
        approved: ['l1', 'l2'],
        sampled: ['l0'],
        refused: [{ work_order_id: 'l3', code: 'OT-L3', reason: 'faltan fotos de «antes»' }],
        sample_note: '1 apartada',
      },
    );
    vi.stubGlobal('fetch', fetcher);
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" now={() => NOW} />);

    const boxes = await screen.findAllByRole('checkbox');
    for (const box of boxes) box.click();
    await waitFor(() => expect(screen.getByText(/se aprobarán 3/)).toBeTruthy());
    (await screen.findByRole('button', { name: /Aprobar 4 en lote/ })).click();
    (await screen.findByRole('button', { name: /Confirmar aprobación en lote/ })).click();

    expect(await screen.findByText(/No están aprobadas/)).toBeTruthy();
    expect(screen.getByText(/Aprobadas: 2/)).toBeTruthy();
    // Y el motivo del rechazo, que es lo que el supervisor tiene que arreglar.
    expect(screen.getByText(/faltan fotos de «antes»/)).toBeTruthy();
  });

  it('sin nada marcado no hay botón que aprobar', async () => {
    const { fetcher } = mockBatchApi([queueItem('a', 'low')]);
    vi.stubGlobal('fetch', fetcher);
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" now={() => NOW} />);

    const button = await screen.findByRole('button', { name: /Aprobar 0 en lote/ });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Seleccione OT de riesgo bajo/)).toBeTruthy();
  });
});

/**
 * La muestra ciega, en pantalla (RF-111a).
 *
 * Las dos mitades del requerimiento son comprobables aquí: el informe **no se muestra** antes de la
 * decisión —con el motivo, porque una sección oculta sin explicación se lee como una pantalla rota— y
 * **se muestra después**, con la OT todavía abierta. Retenerlo y no mostrarlo nunca le costaría al
 * supervisor la realimentación y a la plataforma su única oportunidad de que le digan que se equivocó.
 */
describe('muestra ciega (RF-111a)', () => {
  const REPORT = {
    work_order_id: 'wo-1',
    graph_version: 'prereview-0.1.0',
    hardware_profile: 'A',
    risk_level: 'high' as const,
    status: 'complete' as const,
    summary: 'una foto repetida entre dos OT',
    observations: [],
    models: {},
    budget: { llm_calls: 0, tokens: 0, duration_s: 0 },
    skipped: [],
    discarded: 0,
  };

  function blindApi(accord: unknown = NO_SAMPLE) {
    let decided = false;
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/decision')) {
        decided = true;
        return {
          ok: true,
          status: 200,
          json: async () => ({
            decision: 'devuelta',
            decided_at: null,
            work_order_state: 'devuelta',
            was_blind: true,
          }),
        } as unknown as Response;
      }
      if (url.includes('/agent-agreement')) {
        return { ok: true, status: 200, json: async () => accord } as unknown as Response;
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
      // El informe viaja solo después de la decisión: es el servidor quien lo retiene (RF-111a).
      return {
        ok: true,
        status: 200,
        json: async () =>
          detail({
            agent_report: decided
              ? { run_state: 'terminado', error: null, report: REPORT, blind: false }
              : { run_state: 'terminado', error: null, report: null, blind: true },
          }),
      } as unknown as Response;
    });
    return fetcher;
  }

  it('antes de decidir no se ve el informe, y se dice por qué', async () => {
    vi.stubGlobal('fetch', blindApi());
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" now={() => NOW} />);

    await openTheOrder();
    expect(await screen.findByText(/está en la muestra ciega/)).toBeTruthy();
    // Nada del informe: ni el riesgo ni el resumen. El anclaje lo produce el veredicto.
    expect(screen.queryByText(/Riesgo alto/)).toBeNull();
    expect(screen.queryByText(/una foto repetida/)).toBeNull();
  });

  it('el aviso dice que lo determinista sigue completo', async () => {
    // Si no, el supervisor cree que le falta información para decidir y espera —y RF-204 dice que
    // se puede aprobar sin informe ninguno.
    vi.stubGlobal('fetch', blindApi());
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" now={() => NOW} />);

    await openTheOrder();
    expect(await screen.findByText(/normativa, impedimentos, fotos/)).toBeTruthy();
  });

  it('después de decidir el informe aparece y la OT sigue abierta', async () => {
    vi.stubGlobal('fetch', blindApi());
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" now={() => NOW} />);

    await openTheOrder();
    (await screen.findByRole('button', { name: /Devolver con observaciones/ })).click();

    expect(await screen.findByText(/Esto es lo que había visto el agente/)).toBeTruthy();
    expect(screen.getByText(/una foto repetida entre dos OT/)).toBeTruthy();
  });

  it('el kappa se muestra con el piso de RNF-060', async () => {
    vi.stubGlobal(
      'fetch',
      blindApi({
        ...NO_SAMPLE,
        both_clear: 30,
        both_flagged: 20,
        supervisor_only: 2,
        agent_only: 3,
        paired: 55,
        observed_agreement: 0.909,
        kappa: 0.81,
        meets_floor: true,
      }),
    );
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" now={() => NOW} />);

    expect(await screen.findByText(/Kappa 0,81/)).toBeTruthy();
    expect(screen.getByText(/cumple el piso de 0,6/)).toBeTruthy();
    // Los dos desacuerdos, nombrados por lo que cuestan.
    expect(screen.getByText(/no vio lo que el supervisor sí: 2/)).toBeTruthy();
  });

  it('una respuesta de concordancia malformada no deja la cola en blanco', async () => {
    // Pasó al escribir esto: el panel reventó en el render y la pantalla entera se quedó vacía. Es
    // realimentación secundaria; no puede tumbar la pantalla con la que se aprueba trabajo.
    vi.stubGlobal('fetch', blindApi({ kappa: null }));
    render(<ReviewScreen businessUnit="GYE" reviewer="sup.1" now={() => NOW} />);

    expect(await screen.findByRole('button', { name: /OT-000101/ })).toBeTruthy();
    expect(screen.queryByText(/Concordancia con el agente/)).toBeNull();
  });
});
