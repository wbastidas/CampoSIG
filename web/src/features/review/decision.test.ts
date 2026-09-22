/**
 * Lógica de la pantalla de revisión (M11, ADR-007).
 *
 * Cada aserción corresponde a una forma en que una pantalla engaña a quien decide: un veredicto
 * provisional presentado como cita del texto oficial, un "sin medición" pintado del mismo verde
 * que un "cumple", una tasa de aceptación del 0 % donde no hubo propuestas, y la misma foto
 * mandada como antes y como después.
 */

import { describe, expect, it } from 'vitest';

import type {
  AgentObservation,
  AgentReport,
  ComplianceFinding,
  Provenance,
  QueueItem,
  ReviewDetail,
} from '../../api/review';
import {
  CATEGORY_LABEL,
  PLACEMENT_LABEL,
  RISK_LABEL,
  acceptanceRate,
  attentionFor,
  citationFor,
  correctedAiValues,
  displayValue,
  evidenceByStage,
  hasDegradations,
  missingReportReason,
  needsArcFm,
  observationCitation,
  reusedEvidence,
  sortDegradations,
  sortFindings,
  sortObservations,
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

describe('mostrar un valor de respuesta', () => {
  it('un valor de JSONB puede ser un objeto, y String() lo convierte en [object Object]', () => {
    // El defecto que este test fija: el supervisor veía "[object Object]" donde debía ver el
    // valor propuesto, y creía que se le había mostrado algo.
    const objeto = { activity_code: 'PODA', quantity: 2 };
    expect(`${objeto as unknown as string}`).toBe('[object Object]');
    expect(displayValue({ activity_code: 'PODA', quantity: 2 })).toBe(
      'activity_code: PODA; quantity: 2',
    );
  });

  it('una tabla repetible se lee como una lista', () => {
    expect(displayValue([{ material_code: 'LED-50' }, { material_code: 'FOTO-01' }])).toBe(
      'material_code: LED-50, material_code: FOTO-01',
    );
  });

  it('escalares y vacíos', () => {
    expect(displayValue('concrete')).toBe('concrete');
    expect(displayValue(11.5)).toBe('11.5');
    // Sí/No, no `true`/`false`: la UI está en español del Ecuador (regla 11) y un supervisor
    // leyendo `true` bajo «¿Quedó señalizado?» está viendo el formato de almacenamiento en vez de
    // la respuesta. El acta imprime las mismas palabras, así que papel y pantalla concuerdan.
    expect(displayValue(true)).toBe('Sí');
    expect(displayValue(false)).toBe('No');
    expect(displayValue('   ')).toBe('—');
    expect(displayValue(null)).toBe('—');
    expect(displayValue(undefined)).toBe('—');
    expect(displayValue('')).toBe('—');
    expect(displayValue([])).toBe('—');
    expect(displayValue({})).toBe('—');
  });

  it('un límite regulatorio con rango se muestra entero', () => {
    expect(displayValue({ min: 5, max: 25 })).toBe('min: 5; max: 25');
  });
});

describe('lo que la IA no va a aportar (RF-204)', () => {
  const unavailable = {
    alias: 'vlm-audit',
    purpose: 'Auditoría de evidencia visual',
    placement: 'unavailable' as const,
    reason: 'el perfil A no tiene GPU',
  };
  const tonight = {
    alias: 'llm-judge',
    purpose: 'Juez y redactor de observaciones',
    placement: 'night_batch' as const,
    reason: 'pasa al lote nocturno',
  };

  it('lo que no va a volver se lee primero', () => {
    // Es lo que el supervisor tiene que absorber: ese informe no llega, así que decide con la
    // evidencia determinista. Un aviso de espera es una cosa más pequeña que saber.
    expect(sortDegradations([tonight, unavailable]).map((e) => e.alias)).toEqual([
      'vlm-audit',
      'llm-judge',
    ]);
  });

  it('sin nada degradado la sección no se muestra', () => {
    // Un aviso permanente se vuelve parte del decorado, y entonces nadie lo lee el día que
    // significa algo.
    expect(hasDegradations(detail({ degradations: [] }))).toBe(false);
    expect(
      hasDegradations(
        detail({
          degradations: [{ ...tonight, placement: 'interactive' }],
        }),
      ),
    ).toBe(false);
  });

  it('con algo degradado sí se muestra', () => {
    expect(hasDegradations(detail({ degradations: [unavailable] }))).toBe(true);
  });

  it('cada destino tiene una etiqueta en castellano', () => {
    expect(PLACEMENT_LABEL.unavailable).toBe('No se va a ejecutar');
    expect(PLACEMENT_LABEL.night_batch).toBe('Queda para el lote nocturno');
  });
});

describe('el informe de pre-revisión (RF-111, RF-175)', () => {
  function observation(overrides: Partial<AgentObservation> = {}): AgentObservation {
    return {
      id: 'obs-1',
      category: 'coherence',
      severity: 'medium',
      message: 'algo que revisar',
      evidence: [
        { type: 'field', span: null, json_path: '$.x', evidence_id: null, detail: null },
      ],
      source: null,
      suggested_action: null,
      confidence: null,
      node: 'coherence',
      ...overrides,
    };
  }

  function report(overrides: Partial<AgentReport> = {}): AgentReport {
    return {
      work_order_id: 'wo-1',
      graph_version: 'prereview-0.1.0',
      hardware_profile: 'A',
      risk_level: 'medium',
      status: 'partial',
      summary: 'dos observaciones',
      observations: [],
      models: {},
      budget: { llm_calls: 0, tokens: 0, duration_s: 0.1 },
      skipped: ['auditoría de evidencia visual: sin GPU'],
      discarded: 0,
      ...overrides,
    };
  }

  it('las observaciones se leen de la peor a la más leve', () => {
    const ordered = sortObservations([
      observation({ id: 'c', severity: 'low' }),
      observation({ id: 'a', severity: 'high' }),
      observation({ id: 'b', severity: 'medium' }),
    ]);
    expect(ordered.map((item) => item.id)).toEqual(['a', 'b', 'c']);
  });

  it('un límite sin verificar no se presenta como cita del texto oficial', () => {
    // ADR-007: darle a alguien un veredicto con una referencia de aspecto oficial debajo es peor
    // que darle el veredicto solo, porque lo invita a dejar de comprobar.
    const unverified = observation({
      category: 'regulatory',
      source: { document: 'ARCERNNR 002/20', version: '2023', section: 'Art. 12', verified: false },
    });
    const citation = observationCitation(unverified);
    expect(citation).toContain('sin verificar');
    expect(citation).not.toContain('ARCERNNR');
  });

  it('un límite verificado sí se cita con documento, versión y numeral', () => {
    const verified = observation({
      category: 'regulatory',
      source: { document: 'ARCERNNR 002/20', version: '2023', section: 'Art. 12', verified: true },
    });
    expect(observationCitation(verified)).toBe('ARCERNNR 002/20 · v2023 · Art. 12');
  });

  it('una observación sin fuente no inventa una cita', () => {
    expect(observationCitation(observation())).toBeNull();
  });

  it('distingue «falló» de «todavía no corrió»', () => {
    // Son cosas distintas para quien está por decidir sin informe, y ninguna es motivo de esperar.
    expect(missingReportReason(detail({ agent_report: null }))).toContain('todavía no se ha ejecutado');
    expect(
      missingReportReason(
        detail({ agent_report: { run_state: 'fallido', error: 'RuntimeError: x', report: null } }),
      ),
    ).toContain('falló');
    expect(
      missingReportReason(
        detail({ agent_report: { run_state: 'pendiente', error: null, report: null } }),
      ),
    ).toContain('pendiente');
  });

  it('con informe no hay motivo que mostrar', () => {
    expect(
      missingReportReason(
        detail({ agent_report: { run_state: 'terminado', error: null, report: report() } }),
      ),
    ).toBeNull();
  });

  it('cada nivel de riesgo y cada categoría tienen etiqueta en palabras', () => {
    // En palabras y no solo en color: una señal solo por color es una que un supervisor con
    // daltonismo no recibe.
    expect(RISK_LABEL.high).toBe('Riesgo alto');
    expect(CATEGORY_LABEL.regulatory).toBe('Normativa');
    expect(CATEGORY_LABEL.anomaly).toBe('Anomalía');
  });
});
