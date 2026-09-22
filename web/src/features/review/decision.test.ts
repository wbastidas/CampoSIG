/**
 * Lógica de la pantalla de revisión (M11, ADR-007).
 *
 * Cada aserción corresponde a una forma en que una pantalla engaña a quien decide: un veredicto
 * provisional presentado como cita del texto oficial, un "sin medición" pintado del mismo verde
 * que un "cumple", una tasa de aceptación del 0 % donde no hubo propuestas, y la misma foto
 * mandada como antes y como después.
 */

import { describe, expect, it } from 'vitest';

import type { ComplianceFinding, Provenance, QueueItem, ReviewDetail } from '../../api/review';
import {
  acceptanceRate,
  attentionFor,
  citationFor,
  correctedAiValues,
  evidenceByStage,
  needsArcFm,
  reusedEvidence,
  sortFindings,
  sortQueue,
  tamperedEvidence,
  unconfirmedAiValues,
} from './decision';

function provenance(overrides: Partial<Provenance> = {}): Provenance {
  return {
    field_key: 'material',
    origin: 'vision',
    proposed_value: 'concrete',
    final_value: 'concrete',
    confidence: 0.91,
    model_name: 'mobilenetv3-pole',
    model_version: '2026.09',
    accepted_unchanged: true,
    confirmed_by: 'tecnico.1',
    source: 'evidencia:ev-1@0.300,0.200,0.200,0.600',
    is_ai: true,
    ...overrides,
  };
}

function finding(overrides: Partial<ComplianceFinding> = {}): ComplianceFinding {
  return {
    rule: 'resistencia_puesta_a_tierra',
    outcome: 'cumple',
    message: 'resistencia medida de 18 Ω dentro del máximo admisible de 25 Ω',
    severity: 'high',
    measured: 18,
    limit: 25,
    unit: 'ohm',
    norm_ref: 'Normas técnicas de distribución',
    article_ref: 'Numeral 5.3',
    limit_verified: true,
    parameter_code: 'grounding.max_resistance_ohm.poste',
    evaluated_on: '2026-06-01',
    blocking: false,
    ...overrides,
  };
}

function detail(overrides: Partial<ReviewDetail> = {}): ReviewDetail {
  return {
    work_order: {
      work_order_id: 'wo-1',
      code: 'OT-1',
      work_type: 'inspeccion_preventiva',
      state: 'en_revision',
      priority: 'media',
      asset_type_key: 'support_structure',
      asset_code: 'P-1',
      feeder_code: '04BH070T11',
      zone: 'Urbano',
      external_ref: null,
    },
    form: {
      code: 'F-MT-01',
      version: '1.0.0',
      title: 'Inspección preventiva',
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

function evidence(stage: string, hash: string, verified = true): ReviewDetail['evidence'][0] {
  return {
    evidence_id: `e-${hash}`,
    kind: 'foto',
    stage,
    storage_key: `s3://${stage}-${hash}.jpg`,
    content_hash: hash,
    integrity_verified: verified,
    vision_result: null,
  };
}

describe('cuánta atención necesita una captura', () => {
  it('un impedimento bloquea: decirlo antes de que presione aprobar', () => {
    expect(attentionFor(detail({ blockers: ['la respuesta sigue en borrador'] }))).toBe('bloqueado');
  });

  it('un valor de IA sin confirmar pide lectura', () => {
    expect(
      attentionFor(detail({ provenance: [provenance({ confirmed_by: null })] })),
    ).toBe('revisar');
  });

  it('un incumplimiento normativo pide lectura aunque no bloquee', () => {
    expect(
      attentionFor(detail({ compliance: [finding({ outcome: 'incumple', blocking: false })] })),
    ).toBe('revisar');
  });

  it('sin impedimentos ni pendientes, es aprobable', () => {
    expect(attentionFor(detail({ provenance: [provenance()] }))).toBe('listo');
  });
});

describe('auditoría de los valores de IA', () => {
  it('separa lo que nadie confirmó', () => {
    const rows = [provenance(), provenance({ field_key: 'height_m', confirmed_by: null })];
    expect(unconfirmedAiValues(rows).map((r) => r.field_key)).toEqual(['height_m']);
  });

  it('un valor manual no cuenta como propuesta de IA', () => {
    const rows = [provenance({ is_ai: false, origin: 'manual', confirmed_by: null })];
    expect(unconfirmedAiValues(rows)).toEqual([]);
  });

  it('separa lo que una persona corrigió', () => {
    const rows = [provenance(), provenance({ field_key: 'x', accepted_unchanged: false })];
    expect(correctedAiValues(rows).map((r) => r.field_key)).toEqual(['x']);
  });

  it('la tasa de aceptación cuenta solo lo confirmado', () => {
    const rows = [
      provenance(),
      provenance({ field_key: 'b', accepted_unchanged: false }),
      provenance({ field_key: 'c', confirmed_by: null }),
    ];
    expect(acceptanceRate(rows)).toBeCloseTo(0.5);
  });

  it('sin propuestas de IA no hay tasa, y no es cero', () => {
    // Un 0 % se leería como "el modelo se equivocó en todo".
    expect(acceptanceRate([])).toBeNull();
    expect(acceptanceRate([provenance({ is_ai: false })])).toBeNull();
  });
});

describe('hallazgos normativos', () => {
  it('los incumplimientos primero y "sin medición" al final', () => {
    const rows = [
      finding({ rule: 'a', outcome: 'no_aplica' }),
      finding({ rule: 'b', outcome: 'cumple' }),
      finding({ rule: 'c', outcome: 'incumple' }),
      finding({ rule: 'd', outcome: 'no_determinable' }),
    ];
    expect(sortFindings(rows).map((r) => r.rule)).toEqual(['c', 'd', 'b', 'a']);
  });

  it('no muta el arreglo recibido', () => {
    const rows = [finding({ rule: 'z' }), finding({ rule: 'a', outcome: 'incumple' })];
    const before = rows.map((r) => r.rule);
    sortFindings(rows);
    expect(rows.map((r) => r.rule)).toEqual(before);
  });

  it('un límite verificado se cita con norma y numeral', () => {
    expect(citationFor(finding())).toBe('Normas técnicas de distribución, Numeral 5.3');
  });

  it('un límite sin verificar NO se presenta como cita del texto oficial', () => {
    // Es la diferencia entre una comparación útil y una afirmación que nadie comprobó.
    expect(citationFor(finding({ limit_verified: false }))).toContain('sin verificar');
  });

  it('sin norma no hay cita', () => {
    expect(citationFor(finding({ norm_ref: null }))).toBeNull();
  });
});

describe('evidencias', () => {
  it('se separan por etapa', () => {
    const rows = detail({
      evidence: [evidence('antes', 'a'), evidence('despues', 'b'), evidence('durante', 'c')],
    });
    const split = evidenceByStage(rows);
    expect(split.before).toHaveLength(1);
    expect(split.after).toHaveLength(1);
    expect(split.other).toHaveLength(1);
  });

  it('la misma foto como antes y como después se detecta por hash', () => {
    const rows = detail({ evidence: [evidence('antes', 'igual'), evidence('despues', 'igual')] });
    expect(reusedEvidence(rows)).toEqual(['s3://despues-igual.jpg']);
  });

  it('fotos distintas no se reportan como reutilizadas', () => {
    const rows = detail({ evidence: [evidence('antes', 'a'), evidence('despues', 'b')] });
    expect(reusedEvidence(rows)).toEqual([]);
  });

  it('una evidencia cuyo hash no cuadra se destaca', () => {
    const rows = detail({ evidence: [evidence('antes', 'a', false), evidence('despues', 'b')] });
    expect(tamperedEvidence(rows).map((e) => e.content_hash)).toEqual(['a']);
  });
});

describe('orden de la cola', () => {
  const now = new Date('2026-09-22T12:00:00Z');

  function item(overrides: Partial<QueueItem> = {}): QueueItem {
    return {
      work_order_id: 'wo',
      code: 'OT',
      work_type: 'x',
      form_code: 'F-MT-01',
      state: 'sincronizada',
      priority: 'media',
      asset_code: null,
      crew_id: null,
      sla_due_at: null,
      updated_at: '2026-09-22T10:00:00Z',
      ...overrides,
    };
  }

  it('lo vencido primero, luego por prioridad, luego lo que más lleva esperando', () => {
    const rows = [
      item({ work_order_id: 'a', priority: 'baja' }),
      item({ work_order_id: 'b', priority: 'critica' }),
      item({ work_order_id: 'c', priority: 'baja', sla_due_at: '2026-09-21T00:00:00Z' }),
      item({ work_order_id: 'd', priority: 'critica', updated_at: '2026-09-22T08:00:00Z' }),
    ];
    expect(sortQueue(rows, now).map((r) => r.work_order_id)).toEqual(['c', 'd', 'b', 'a']);
  });

  it('un SLA futuro no cuenta como vencido', () => {
    const rows = [
      item({ work_order_id: 'a', sla_due_at: '2026-09-23T00:00:00Z' }),
      item({ work_order_id: 'b', priority: 'critica' }),
    ];
    expect(sortQueue(rows, now).map((r) => r.work_order_id)).toEqual(['b', 'a']);
  });

  it('una prioridad desconocida va al final, no revienta', () => {
    const rows = [item({ work_order_id: 'a', priority: 'inventada' }), item({ work_order_id: 'b' })];
    expect(sortQueue(rows, now).map((r) => r.work_order_id)).toEqual(['b', 'a']);
  });
});

describe('bandeja GIS', () => {
  it('cuenta lo que un editor tiene que aplicar a mano en ArcFM', () => {
    const tray = {
      proposals: [{ requires_arcfm: true }, { requires_arcfm: false }, { requires_arcfm: true }],
    };
    expect(needsArcFm(tray)).toBe(2);
  });
});
