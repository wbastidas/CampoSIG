/**
 * Las decisiones de la pantalla de catálogos (RF-034).
 *
 * Lo que se prueba son las tres distinciones que se parecen y no son lo mismo: vacío porque espera
 * una lista contra vacío sin motivo, nuestro contra del ERP, y nacional contra de la unidad.
 */

import { describe, expect, it } from 'vitest';

import type { CatalogIndex, CatalogSummary, ResolvedCatalog } from '../../api/catalogs';
import {
  describeAttributes,
  emptyAdvice,
  entryRows,
  gisNote,
  HEALTH_LABEL,
  healthOf,
  indexHeadline,
  indexRows,
  isEditable,
  sourceLabel,
} from './catalogs';

function summary(overrides: Partial<CatalogSummary> = {}): CatalogSummary {
  return {
    code: 'defect',
    title: 'Defecto encontrado',
    source: 'manual',
    version: 3,
    note: null,
    active_entries: 23,
    retired_entries: 0,
    empty: false,
    ...overrides,
  };
}

function index(catalogs: CatalogSummary[], gis: string[] = ['feeder', 'substation']): CatalogIndex {
  return { catalogs, gis_backed: gis };
}

function resolved(overrides: Partial<ResolvedCatalog> = {}): ResolvedCatalog {
  return {
    code: 'defect',
    title: 'Defecto encontrado',
    source: 'manual',
    version: 3,
    note: null,
    empty: false,
    entries: [
      {
        code: 'cruceta_podrida',
        label: 'Cruceta deteriorada',
        synonyms: ['cruceta podrida'],
        parent_code: null,
        attributes: { suggested_criticality: 'alta' },
        local: false,
      },
    ],
    ...overrides,
  };
}

describe('healthOf', () => {
  it('con valores está bien', () => {
    expect(healthOf(summary())).toBe('ok');
  });

  it('vacío con motivo es una decisión, no una falla', () => {
    // La división política se queda vacía hasta que llegue la lista oficial del INEC.
    expect(healthOf(summary({ empty: true, active_entries: 0, note: 'falta el INEC' }))).toBe(
      'esperando',
    );
  });

  it('vacío sin motivo sí es una falla', () => {
    expect(healthOf(summary({ empty: true, active_entries: 0, note: null }))).toBe(
      'vacio-sin-motivo',
    );
  });

  it('cada situación tiene su palabra', () => {
    expect(Object.keys(HEALTH_LABEL).sort()).toEqual(['esperando', 'ok', 'vacio-sin-motivo']);
  });
});

describe('indexRows', () => {
  it('lo peor primero, luego por código', () => {
    const rows = indexRows(
      index([
        summary({ code: 'c' }),
        summary({ code: 'b', empty: true, active_entries: 0, note: 'espera' }),
        summary({ code: 'a', empty: true, active_entries: 0, note: null }),
      ]),
    );
    expect(rows.map((row) => row.code)).toEqual(['a', 'b', 'c']);
  });

  it('aguanta no haber cargado', () => {
    expect(indexRows(null)).toEqual([]);
  });
});

describe('indexHeadline', () => {
  it('solo dice que está todo bien cuando nada está vacío', () => {
    expect(indexHeadline(index([summary()]))).toBe('1 catálogo(s) con 23 valor(es) activos.');
  });

  it('cuenta aparte los vacíos sin motivo y los que esperan', () => {
    const line = indexHeadline(
      index([
        summary({ code: 'a', empty: true, active_entries: 0, note: null }),
        summary({ code: 'b', empty: true, active_entries: 0, note: 'espera' }),
      ]),
    );
    expect(line).toContain('1 vacío(s) sin motivo');
    expect(line).toContain('1 a la espera');
  });

  it('un catálogo inexistente lo dice', () => {
    expect(indexHeadline(index([]))).toContain('No hay ningún catálogo');
  });
});

describe('gisNote', () => {
  it('explica dónde están los del SIG, para que nadie los busque aquí', () => {
    expect(gisNote(index([summary()]))).toContain('feeder, substation');
    expect(gisNote(index([summary()]))).toContain('difieren por unidad');
  });

  it('no dice nada cuando no hay ninguno', () => {
    expect(gisNote(index([summary()], []))).toBeNull();
  });
});

describe('isEditable y sourceLabel', () => {
  it('lo que mantiene una integración no se edita desde la web', () => {
    expect(isEditable(summary({ source: 'integracion' }))).toBe(false);
    expect(isEditable(summary())).toBe(true);
  });

  it('el origen se dice en palabras', () => {
    expect(sourceLabel('integracion')).toContain('ERP');
    expect(sourceLabel('manual')).toContain('administración funcional');
  });

  it('un origen nuevo del servidor se muestra tal cual', () => {
    expect(sourceLabel('algo_nuevo')).toBe('algo_nuevo');
  });
});

describe('entryRows', () => {
  it('distingue el valor nacional del propio de la unidad', () => {
    const rows = entryRows(
      resolved({
        entries: [
          { code: 'a', label: 'A', synonyms: [], parent_code: null, attributes: {}, local: false },
          { code: 'b', label: 'B', synonyms: [], parent_code: null, attributes: {}, local: true },
        ],
      }),
    );
    expect(rows.map((row) => row.origin)).toEqual(['Nacional', 'De la unidad']);
  });

  it('un valor sin sinónimos no queda en blanco', () => {
    const rows = entryRows(
      resolved({
        entries: [
          { code: 'a', label: 'A', synonyms: [], parent_code: null, attributes: {}, local: false },
        ],
      }),
    );
    expect(rows[0]?.synonyms).toBe('—');
  });

  it('aguanta no haber cargado', () => {
    expect(entryRows(null)).toEqual([]);
  });
});

describe('describeAttributes', () => {
  it('la criticidad se dice «sugerida», para que nadie la tome por el valor', () => {
    expect(describeAttributes({ suggested_criticality: 'alta' })).toBe('criticidad sugerida: alta');
  });

  it('sin atributos no queda en blanco', () => {
    expect(describeAttributes({})).toBe('—');
  });

  it('un objeto anidado no se muestra como [object Object]', () => {
    expect(describeAttributes({ x: { a: 1 } })).toBe('x: {"a":1}');
  });
});

describe('emptyAdvice', () => {
  it('un catálogo con valores no necesita aviso', () => {
    expect(emptyAdvice(resolved())).toBeNull();
  });

  it('un vacío con motivo muestra el motivo del servidor', () => {
    expect(emptyAdvice(resolved({ empty: true, entries: [], note: 'falta el INEC' }))).toBe(
      'falta el INEC',
    );
  });

  it('un vacío sin motivo explica la consecuencia', () => {
    const advice = emptyAdvice(resolved({ empty: true, entries: [], note: null }));
    expect(advice).toContain('no declara por qué');
    expect(advice).toContain('observaciones');
  });
});
