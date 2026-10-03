/**
 * Las decisiones de la pantalla de planes preventivos (RF-012).
 *
 * Tres cosas que se prueban porque son tres formas de que un plan parezca sano mientras falla:
 * emitido no es hecho, un alcance expandido es un subconjunto, y un periodo que no emitió nada está
 * atrasado y no al día — su conteo, cero, se ve igual que el de un plan sin nada que hacer.
 */

import { describe, expect, it } from 'vitest';

import type { PlanCompletion, PlanCoverage, PlanDetail, PlanRow } from '../../api/plans';
import {
  cadenceLabel,
  canSubmit,
  caveatsOf,
  completionLabel,
  coverageLabel,
  draftAdvice,
  draftProblems,
  EMPTY_PLAN,
  headline,
  healthOf,
  historyRows,
  isExpanded,
  MAX_DAY_OF_MONTH,
  outcomeLabel,
  parseAssets,
  planRows,
  runSummary,
  scopeLabel,
} from './plans';

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
  return { period: '2026-09', issued: 3, submitted: 3, ...overrides };
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

describe('el estado de un plan', () => {
  it('un periodo que no emitió nada por trabajo pendiente está atrasado, no al día', () => {
    const behind = plan({
      coverage: coverage({ issued: 0, skipped_pending: 3 }),
    });
    expect(healthOf(behind)).toBe('atrasado');
  });

  it('un plan sin activos en el alcance no se confunde con uno atrasado', () => {
    expect(healthOf(plan({ coverage: coverage({ targets: 0, issued: 0 }) }))).toBe('sin-alcance');
  });

  it('un plan inactivo se dice inactivo y no atrasado', () => {
    expect(
      healthOf(
        plan({
          active: false,
          coverage: coverage({ issued: 0, skipped_recent: 3 }),
        }),
      ),
    ).toBe('inactivo');
  });

  it('un plan que emitió lo suyo está al día', () => {
    expect(healthOf(plan())).toBe('al-dia');
  });

  it('lo peor primero, y después por código', () => {
    const rows = planRows([
      plan({ code: 'B-OK' }),
      plan({ code: 'A-OK' }),
      plan({
        code: 'Z-ATRASADO',
        coverage: coverage({ issued: 0, skipped_pending: 1 }),
      }),
    ]);
    expect(rows.map((row) => row.code)).toEqual(['Z-ATRASADO', 'A-OK', 'B-OK']);
  });

  it('el titular nombra cuántos están atrasados, que es el número que se puede accionar', () => {
    const text = headline([
      plan({ code: 'A' }),
      plan({
        code: 'B',
        coverage: coverage({ issued: 0, skipped_pending: 2 }),
      }),
    ]);
    expect(text).toContain('2 plan(es)');
    expect(text).toContain('1 atrasado(s)');
  });

  it('sin planes lo dice en vez de quedarse en blanco', () => {
    expect(headline([])).toBe('No hay ningún plan preventivo cargado.');
    expect(headline(null)).toBe('Cargando…');
  });
});

describe('emitido no es hecho', () => {
  it('la emisión lleva su denominador', () => {
    expect(coverageLabel(coverage({ issued: 8, targets: 11 }))).toBe('8 de 11 emitidas en 2026-09');
  });

  it('el cumplimiento lleva el suyo, y es otro número', () => {
    expect(completionLabel(completion({ issued: 11, submitted: 2 }))).toBe('2 de 11 ejecutadas');
  });

  it('sin nada emitido no se reporta 0 % sino que no hay dato', () => {
    expect(completionLabel(completion({ issued: 0, submitted: 0 }))).toContain('Nada emitido');
  });

  it('un alcance vacío no se lee como una emisión de cero', () => {
    expect(coverageLabel(coverage({ targets: 0 }))).toBe('Sin activos en el alcance');
  });
});

describe('el alcance expandido', () => {
  it('se distingue de una lista escrita por el área', () => {
    expect(isExpanded(plan({ scope: 'alimentador' }))).toBe(true);
    expect(isExpanded(plan())).toBe(false);
  });

  it('los caveats se muestran una sola vez aunque vengan repetidos del historial', () => {
    const detail = {
      caveats: ['El inventario vive en el SIG'],
      history: [
        { caveats: ['El inventario vive en el SIG'] },
        { caveats: ['El inventario vive en el SIG'] },
      ],
    } as unknown as PlanDetail;
    expect(caveatsOf(detail)).toEqual(['El inventario vive en el SIG']);
  });

  it('sin detalle no hay caveats y no revienta', () => {
    expect(caveatsOf(null)).toEqual([]);
  });

  it('el historial se lee del más nuevo al más viejo', () => {
    const detail = {
      caveats: [],
      history: [
        { period: '2026-08', issued_at: '2026-08-05T00:00:00Z', caveats: [] },
        { period: '2026-09', issued_at: '2026-09-05T00:00:00Z', caveats: [] },
      ],
    } as unknown as PlanDetail;
    expect(historyRows(detail).map((row) => row.period)).toEqual(['2026-09', '2026-08']);
  });
});

describe('las etiquetas', () => {
  it('la frecuencia en días dice cuántos', () => {
    expect(cadenceLabel('dias', 45)).toBe('Cada 45 días');
    expect(cadenceLabel('mensual', null)).toBe('Mensual');
  });

  it('una frecuencia que no conoce se muestra tal cual', () => {
    expect(cadenceLabel('quincenal', null)).toBe('quincenal');
  });

  it('el alcance dice de qué alimentador o zona habla', () => {
    expect(scopeLabel('alimentador', 'ALIM-SUR')).toBe('Por alimentador: ALIM-SUR');
    expect(scopeLabel('activos', null)).toBe('Lista de activos (o ruta)');
  });

  it('los resultados del historial se traducen, y lo desconocido no desaparece', () => {
    expect(outcomeLabel('trabajo_pendiente')).toBe('Ya había trabajo pendiente');
    expect(outcomeLabel('otra_cosa')).toBe('otra_cosa');
  });
});

describe('la lista de activos', () => {
  it('conserva el orden, porque el orden es la ruta', () => {
    expect(parseAssets('P-003\nP-001\nP-002')).toEqual(['P-003', 'P-001', 'P-002']);
  });

  it('descarta repetidos y líneas en blanco', () => {
    expect(parseAssets('P-001\n\nP-001\n  \nP-002')).toEqual(['P-001', 'P-002']);
  });

  it('acepta comas y punto y coma, que es como se pegan de una hoja de cálculo', () => {
    expect(parseAssets('P-001, P-002; P-003')).toEqual(['P-001', 'P-002', 'P-003']);
  });
});

describe('el borrador antes de guardarlo', () => {
  const base = {
    ...EMPTY_PLAN,
    code: 'PLAN-A',
    name: 'Plan',
    formCode: 'F-MT-01',
    assets: 'P-001',
  };

  it('un plan por activos sin activos no se puede guardar', () => {
    expect(draftProblems({ ...base, assets: '' })).toContain(
      'Un plan por activos necesita al menos un activo: la lista es el alcance.',
    );
  });

  it('el día 31 se rechaza en la pantalla y se explica por qué', () => {
    const problems = draftProblems({ ...base, dayOfMonth: '31' });
    expect(problems.some((problem) => problem.includes('febrero'))).toBe(true);
  });

  it('el tope del día del mes es el mismo que el del servidor', () => {
    expect(MAX_DAY_OF_MONTH).toBe(28);
    expect(canSubmit({ ...base, dayOfMonth: String(MAX_DAY_OF_MONTH) })).toBe(true);
  });

  it('una frecuencia en días sin días no se puede guardar', () => {
    expect(canSubmit({ ...base, cadence: 'dias', cadenceDays: '' })).toBe(false);
    expect(canSubmit({ ...base, cadence: 'dias', cadenceDays: '45' })).toBe(true);
  });

  it('un plan por alimentador sin alimentador no se puede guardar', () => {
    expect(canSubmit({ ...base, scope: 'alimentador', scopeValue: '' })).toBe(false);
    expect(canSubmit({ ...base, scope: 'alimentador', scopeValue: 'ALIM-SUR' })).toBe(true);
  });

  it('sin código y sin nombre tampoco', () => {
    expect(canSubmit({ ...base, code: '' })).toBe(false);
    expect(canSubmit({ ...base, name: '' })).toBe(false);
    expect(canSubmit({ ...base, formCode: '' })).toBe(false);
  });

  it('un borrador correcto se puede guardar', () => {
    expect(draftProblems(base)).toEqual([]);
  });

  it('dice cuántas OT emitirá y cuándo', () => {
    const advice = draftAdvice({
      ...base,
      assets: 'P-001\nP-002',
      dayOfMonth: '5',
    });
    expect(advice).toContain('hasta 2 OT');
    expect(advice).toContain('el día 5');
    expect(advice).toContain('orden de la lista');
  });

  it('en un alcance expandido advierte que puede ser menor que el alimentador real', () => {
    const advice = draftAdvice({
      ...base,
      scope: 'alimentador',
      scopeValue: 'ALIM-SUR',
    });
    expect(advice).toContain('ALIM-SUR');
    expect(advice).toContain('SIG');
  });
});

describe('el resultado de una corrida', () => {
  const run = {
    period: '2026-09',
    issued: ['a', 'b'],
    skipped_pending: [],
    skipped_recent: [],
    already_issued: [],
    note: null as string | null,
  };

  it('dice cuántas emitió y en qué periodo', () => {
    expect(runSummary(run)).toBe('2 OT emitida(s) en 2026-09.');
  });

  it('cuenta lo que ya estaba emitido, para que una segunda corrida no parezca un fallo', () => {
    expect(runSummary({ ...run, issued: [], already_issued: ['P-001'] })).toContain(
      '1 ya estaban emitidas',
    );
  });

  it('cuenta lo que se saltó y por qué', () => {
    const text = runSummary({
      ...run,
      skipped_pending: ['P-001'],
      skipped_recent: ['P-002'],
    });
    expect(text).toContain('1 con trabajo pendiente');
    expect(text).toContain('1 atendidas hace poco');
  });

  it('cuando el servidor explica por qué no emitió nada, se muestra esa explicación', () => {
    expect(runSummary({ ...run, issued: [], note: 'no hay activos en ALIM-NUEVO' })).toBe(
      'no hay activos en ALIM-NUEVO',
    );
  });
});
