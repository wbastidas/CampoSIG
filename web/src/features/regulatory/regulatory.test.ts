/**
 * Las decisiones de la pantalla de parámetros (RF-150, ADR-007).
 *
 * Lo que se prueba es lo que haría que alguien diera por bueno un límite: que «sin verificar» se
 * lea como una frase y no como un detalle, que un valor no aparezca sin su vigencia, y que un
 * código que falta no se confunda con uno que está pero nadie leyó.
 */

import { describe, expect, it } from 'vitest';

import type { Parameter, ParameterIndex, Revision } from '../../api/regulatory';
import {
  ACTION_LABEL,
  authorshipLabel,
  canVerify,
  ecuadorDate,
  gaps,
  indexHeadline,
  isInForce,
  periodLabel,
  plainValue,
  revisionLine,
  verificationLabel,
} from './regulatory';

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

describe('plainValue', () => {
  it('quita el envoltorio de almacenamiento', () => {
    expect(plainValue({ v: 24 })).toBe('24');
  });

  it('los miles llevan punto', () => {
    expect(plainValue({ v: 1825 })).toBe('1.825');
  });

  it('un booleano se lee en español', () => {
    expect(plainValue({ v: true })).toBe('Sí');
  });

  it('una tabla por nivel de tensión se muestra tal cual y no se aplana', () => {
    // Aplanarla sería inventar un solo límite donde la norma pone varios.
    expect(plainValue({ mv: 24, bv: 12 })).toBe('{"mv":24,"bv":12}');
  });

  it('un objeto dentro de v no se muestra como [object Object]', () => {
    expect(plainValue({ v: { a: 1 } })).toBe('{"a":1}');
  });
});

describe('fechas y períodos', () => {
  it('la fecha se escribe como en Ecuador', () => {
    expect(ecuadorDate('2026-06-30')).toBe('30/06/2026');
  });

  it('una fecha ausente no se inventa', () => {
    expect(ecuadorDate(null)).toBe('—');
  });

  it('un período abierto dice «vigente» y no «hasta null»', () => {
    expect(periodLabel(parameter())).toContain('vigente');
  });

  it('un período cerrado muestra las dos fechas', () => {
    expect(periodLabel(parameter({ effective_to: '2026-06-30' }))).toBe(
      '01/01/2026 a 30/06/2026',
    );
  });

  it('solo el período abierto está vigente', () => {
    expect(isInForce(parameter())).toBe(true);
    expect(isInForce(parameter({ effective_to: '2026-06-30' }))).toBe(false);
  });
});

describe('verificación', () => {
  it('sin verificar se explica, no se marca con un símbolo', () => {
    expect(verificationLabel(parameter())).toContain('las reglas lo evalúan');
  });

  it('un estricto sin verificar dice que las reglas se niegan a evaluarlo', () => {
    expect(verificationLabel(parameter({ strict: true }))).toContain('se niegan a evaluarlo');
  });

  it('verificado nombra a la persona y la fecha', () => {
    const row = parameter({
      verified: true,
      verified_by: 'jose.vera',
      verified_at: '2026-02-01T10:00:00+00:00',
    });
    expect(verificationLabel(row)).toBe('Verificado por jose.vera el 01/02/2026');
  });

  it('solo se puede verificar lo no verificado, y solo con permiso', () => {
    expect(canVerify(parameter(), true)).toBe(true);
    expect(canVerify(parameter(), false)).toBe(false);
    expect(canVerify(parameter({ verified: true }), true)).toBe(false);
  });
});

describe('autoría', () => {
  it('quien cargó y quien editó se distinguen', () => {
    const row = parameter({ created_by: 'maria.perez', updated_by: 'jose.vera' });
    expect(authorshipLabel(row)).toBe('Cargado por maria.perez; última edición de jose.vera');
  });

  it('no repite a la misma persona dos veces', () => {
    expect(authorshipLabel(parameter())).toBe('Cargado por maria.perez');
  });

  it('una fila antigua sin autor lo dice en vez de quedar en blanco', () => {
    const row = parameter({ created_by: null, updated_by: null });
    expect(authorshipLabel(row)).toBe('Cargado por sin registrar');
  });
});

describe('los huecos', () => {
  function index(overrides: Partial<ParameterIndex> = {}): ParameterIndex {
    return {
      loaded: ['a', 'b'],
      required_by_rules: ['a', 'b', 'c'],
      missing: [],
      unverified: [],
      ...overrides,
    };
  }

  it('lo que falta va antes de lo que no está verificado', () => {
    // Un código que falta hace que la regla calle, y callar se parece a cumplir.
    const found = gaps(index({ missing: ['c'], unverified: ['a'] }));
    expect(found.map((gap) => gap.kind)).toEqual(['missing', 'unverified']);
  });

  it('cada hueco dice qué implica, no solo que existe', () => {
    expect(gaps(index({ missing: ['c'] }))[0]?.advice).toContain('Ninguna regla puede juzgar');
    expect(gaps(index({ unverified: ['a'] }))[0]?.advice).toContain('texto oficial');
  });

  it('el encabezado solo dice que está todo cuando las dos listas están vacías', () => {
    expect(indexHeadline(index())).toContain('todos verificados');
    expect(indexHeadline(index({ unverified: ['a'] }))).toContain('1 sin verificar');
    expect(indexHeadline(index({ missing: ['c'] }))).toContain('1 sin cargar');
  });

  it('aguanta no haber cargado todavía', () => {
    expect(gaps(null)).toEqual([]);
    expect(indexHeadline(null)).toBe('Cargando…');
  });
});

describe('las revisiones', () => {
  function revision(overrides: Partial<Revision> = {}): Revision {
    return { at: '2026-01-02T10:00:00+00:00', action: 'creado', actor: 'maria.perez', changed: {}, note: null, ...overrides };
  }

  it('una creación se dice sin inventar un cambio', () => {
    expect(revisionLine(revision())).toBe('Creado por maria.perez');
  });

  it('una corrección dice desde qué valor', () => {
    const line = revisionLine(
      revision({ action: 'corregido', actor: 'jose.vera', changed: { value: { from: 24, to: 30 } } }),
    );
    expect(line).toContain('value: 24 → 30');
  });

  it('un campo que estaba vacío se dice, no se muestra como null', () => {
    const line = revisionLine(
      revision({ action: 'cerrado', changed: { effective_to: { from: null, to: '2026-06-30' } } }),
    );
    expect(line).toContain('(vacío) → 2026-06-30');
  });

  it('cada acción tiene su palabra en español', () => {
    expect(Object.keys(ACTION_LABEL).sort()).toEqual([
      'cerrado',
      'corregido',
      'creado',
      'verificado',
    ]);
  });

  it('una acción que el servidor añada después se muestra tal cual', () => {
    expect(revisionLine(revision({ action: 'algo_nuevo' }))).toContain('algo_nuevo');
  });
});
