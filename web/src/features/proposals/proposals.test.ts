/**
 * Las decisiones de la bandeja de propuestas (RF-013, RF-114).
 *
 * Lo que se prueba es la distinción que sostiene toda la pantalla: una prioridad **calculada** con
 * datos declarados y una **estimada** con omisiones son el mismo número y cosas distintas. Y que el
 * motivo de rechazo nunca sea un texto libre, porque es una etiqueta de entrenamiento.
 */

import { describe, expect, it } from 'vitest';

import type { Criticality, Proposal, Tray } from '../../api/proposals';
import {
  canDecide,
  confidenceLabel,
  countRows,
  deadlineLabel,
  decisionAdvice,
  decisionProblems,
  EMPTY_DECISION,
  originLabel,
  priorityLabel,
  reasonOptions,
  reasonsAdvice,
  signalLabel,
  signalOf,
  stateLabel,
  trayHeadline,
  trayRows,
} from './proposals';

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

describe('el orden de la bandeja', () => {
  it('pone lo peor primero y lo más viejo antes', () => {
    const rows = trayRows(
      tray({
        proposals: [
          proposal({ id: 'baja', priority: 'baja', created_at: '2026-09-01T00:00:00+00:00' }),
          proposal({ id: 'critica-nueva', priority: 'critica', created_at: '2026-09-10T00:00:00+00:00' }),
          proposal({ id: 'critica-vieja', priority: 'critica', created_at: '2026-09-02T00:00:00+00:00' }),
        ],
      }),
    );
    expect(rows.map((row) => row.id)).toEqual(['critica-vieja', 'critica-nueva', 'baja']);
  });

  it('una prioridad que no conoce no se cuela arriba', () => {
    const rows = trayRows(
      tray({
        proposals: [
          proposal({ id: 'rara', priority: 'urgentisima' }),
          proposal({ id: 'baja', priority: 'baja' }),
        ],
      }),
    );
    expect(rows[0]?.id).toBe('baja');
  });

  it('sin bandeja no hay filas y no revienta', () => {
    expect(trayRows(null)).toEqual([]);
  });
});

describe('calculada contra estimada', () => {
  it('lo dice con una palabra, que es lo que un supervisor busca', () => {
    expect(confidenceLabel(criticality())).toBe('Calculada');
    expect(confidenceLabel(criticality({ estimated: true, caveats: ['sin severidad'] }))).toBe(
      'Estimada',
    );
  });

  it('el titular cuenta cuántas son estimadas, porque es la advertencia', () => {
    const headline = trayHeadline(
      tray({
        proposals: [
          proposal({ id: 'a', criticality: criticality({ estimated: true, caveats: ['x'] }) }),
          proposal({ id: 'b' }),
        ],
      }),
    );
    expect(headline).toContain('2 propuesta(s)');
    expect(headline).toContain('1 con prioridad estimada');
  });

  it('cuenta las críticas aparte', () => {
    expect(
      trayHeadline(tray({ proposals: [proposal({ priority: 'critica' })] })),
    ).toContain('1 crítica(s)');
  });

  it('una bandeja vacía lo dice en vez de quedarse en blanco', () => {
    expect(trayHeadline(tray({ proposals: [] }))).toBe('No hay propuestas en este estado.');
  });
});

describe('el plazo sugerido', () => {
  it('sin plazo es una respuesta, no un cero', () => {
    expect(deadlineLabel(null)).toContain('Sin plazo');
  });

  it('el cero del anexo es «inmediato»', () => {
    expect(deadlineLabel(0)).toBe('Inmediato');
  });

  it('las horas se leen en horas y los días en días', () => {
    expect(deadlineLabel(8)).toBe('8 h');
    expect(deadlineLabel(72)).toBe('3 día(s)');
  });
});

describe('los conteos', () => {
  it('van en el orden en que se trabaja la bandeja y omiten lo que no hay', () => {
    const rows = countRows(tray({ counts: { rechazada: 2, propuesta: 5, fusionada: 0 } }));
    expect(rows.map((row) => row.state)).toEqual(['propuesta', 'rechazada']);
    expect(rows[0]?.label).toBe('En la bandeja');
  });
});

describe('el motivo de rechazo', () => {
  it('sale del catálogo', () => {
    expect(reasonOptions(tray()).map((reason) => reason.code)).toEqual([
      'no_es_defecto',
      'ya_resuelto',
    ]);
  });

  it('sin catálogo cargado no se ofrece rechazar, y se explica por qué', () => {
    const advice = reasonsAdvice(tray({ reject_reasons: [] }));
    expect(advice).toContain('etiqueta de entrenamiento');
    expect(advice).toContain('Catálogos');
  });

  it('con catálogo cargado no hay nada que advertir', () => {
    expect(reasonsAdvice(tray())).toBeNull();
  });

  it('muestra qué enseña cada motivo, porque no todos enseñan lo mismo', () => {
    expect(signalLabel(signalOf(tray(), 'no_es_defecto'))).toContain('se equivocó');
    expect(signalLabel(signalOf(tray(), 'ya_resuelto'))).toContain('No enseña nada');
  });

  it('una señal que no conoce se muestra tal cual en vez de desaparecer', () => {
    expect(signalLabel('inventada')).toBe('inventada');
    expect(signalLabel(null)).toBeNull();
  });
});

describe('la decisión antes de enviarla', () => {
  it('fusionar sin OT de destino no se puede', () => {
    const draft = { ...EMPTY_DECISION, decision: 'fusionar' as const };
    expect(decisionProblems(draft)).toEqual(['Indique la OT en la que se fusiona.']);
    expect(canDecide(draft)).toBe(false);
    expect(canDecide({ ...draft, workOrderId: 'ot-9' })).toBe(true);
  });

  it('rechazar sin motivo de catálogo no se puede', () => {
    const draft = { ...EMPTY_DECISION, decision: 'rechazar' as const };
    expect(decisionProblems(draft)).toEqual(['Elija un motivo de rechazo del catálogo.']);
    expect(canDecide({ ...draft, reasonCode: 'no_es_defecto' })).toBe(true);
  });

  it('aprobar no exige nada: la prioridad calculada ya está', () => {
    expect(canDecide(EMPTY_DECISION)).toBe(true);
  });

  it('dice que se crea una OT planificada con la prioridad del anexo', () => {
    const advice = decisionAdvice(EMPTY_DECISION, proposal());
    expect(advice).toContain('OT planificada');
    expect(advice).toContain('Alta');
  });

  it('cuando el supervisor cambia la prioridad, lo dice y dice desde cuál', () => {
    const advice = decisionAdvice(
      { ...EMPTY_DECISION, priority: 'critica' },
      proposal({ priority: 'alta' }),
    );
    expect(advice).toContain('Crítica');
    expect(advice).toContain('Alta');
    expect(advice).toContain('bitácora');
  });

  it('elegir la misma prioridad no se anuncia como un cambio', () => {
    const advice = decisionAdvice(
      { ...EMPTY_DECISION, priority: 'alta' },
      proposal({ priority: 'alta' }),
    );
    expect(advice).not.toContain('en lugar de');
  });

  it('fusionar dice que no se crea ninguna OT', () => {
    expect(decisionAdvice({ ...EMPTY_DECISION, decision: 'fusionar' }, proposal())).toContain(
      'No se crea ninguna OT',
    );
  });

  it('rechazar dice que el motivo va al entrenamiento', () => {
    expect(decisionAdvice({ ...EMPTY_DECISION, decision: 'rechazar' }, proposal())).toContain(
      'entrenamiento',
    );
  });
});

describe('las etiquetas', () => {
  it('traducen lo que el servidor manda y no inventan lo que no conocen', () => {
    expect(priorityLabel('critica')).toBe('Crítica');
    expect(priorityLabel('rarisima')).toBe('rarisima');
    expect(stateLabel('propuesta')).toBe('En la bandeja');
    expect(stateLabel('otra')).toBe('otra');
    expect(originLabel('deteccion_visual')).toBe('Detección visual');
    expect(originLabel('otro')).toBe('otro');
  });
});
