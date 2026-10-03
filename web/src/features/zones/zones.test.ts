/**
 * The judgements of the zones screen (RF-152).
 *
 * What is worth testing here is what would mislead an administrator: a coverage line that reads
 * fine while eleven work orders are unplaceable, an import preview that does not warn it is about
 * to replace eleven boundaries, and a «100 %» over nothing.
 */

import { describe, expect, it } from 'vitest';

import type {
  BackfillReport,
  CoverageReport,
  ImportReport,
  ZoneCollection,
} from '../../api/zones';
import {
  backfillLines,
  codesIn,
  coverageCaveats,
  coverageHeadline,
  importFailed,
  importHeadline,
  integer,
  overlapLines,
  parseDocument,
  percent,
  zoneRows,
} from './zones';

function coverage(overrides: Partial<CoverageReport['coverage']> = {}): CoverageReport {
  return {
    coverage: {
      open_orders: 0,
      inside_one: 0,
      ambiguous: 0,
      outside: 0,
      without_location: 0,
      covered_share: null,
      ...overrides,
    },
    overlaps: [],
  };
}

const POLYGON = {
  type: 'Polygon',
  coordinates: [
    [
      [-80, -2],
      [-79.9, -2],
      [-79.9, -2.1],
      [-80, -2.1],
      [-80, -2],
    ],
  ],
};

function feature(properties: Record<string, unknown>) {
  return { type: 'Feature', geometry: POLYGON, properties };
}

describe('formato es-EC', () => {
  it('usa coma decimal en los porcentajes', () => {
    expect(percent(0.945, 1)).toBe('94,5 %');
  });

  it('usa punto de miles en los enteros', () => {
    expect(integer(11480)).toBe('11.480');
  });
});

describe('parseDocument', () => {
  it('acepta un FeatureCollection y cuenta sus rasgos', () => {
    const parsed = parseDocument(
      JSON.stringify({ type: 'FeatureCollection', features: [feature({ code: 'N' })] }),
    );
    expect(parsed.problem).toBeNull();
    expect(parsed.features).toBe(1);
  });

  it('acepta un Feature suelto, que es lo que exporta un SIG de escritorio', () => {
    const parsed = parseDocument(JSON.stringify(feature({ code: 'N' })));
    expect(parsed.problem).toBeNull();
    expect(parsed.features).toBe(1);
  });

  it('dice que no es JSON en vez de mandarlo al servidor', () => {
    expect(parseDocument('{no json').problem).toBe('El texto no es JSON válido.');
  });

  it('nombra el type que llegó cuando no es GeoJSON', () => {
    const parsed = parseDocument(JSON.stringify({ type: 'Topology' }));
    expect(parsed.problem).toContain('Topology');
    expect(parsed.document).toBeNull();
  });

  it('rechaza una colección vacía, que de otro modo se reportaría como éxito', () => {
    const parsed = parseDocument(JSON.stringify({ type: 'FeatureCollection', features: [] }));
    expect(parsed.problem).toContain('ningún rasgo');
  });

  it('no dice nada cuando no hay nada pegado todavía', () => {
    expect(parseDocument('   ').problem).toBe('No hay nada que importar.');
  });
});

describe('codesIn', () => {
  it('lee el código de cualquiera de los nombres habituales', () => {
    const document = {
      type: 'FeatureCollection',
      features: [feature({ ZONA: 'ESTE' }), feature({ codigo: 'OESTE' })],
    };
    expect(codesIn(document)).toEqual(['ESTE', 'OESTE']);
  });

  it('respeta la propiedad que el usuario nombró', () => {
    const document = { type: 'FeatureCollection', features: [feature({ code: 'NO', sec: 'SI' })] };
    expect(codesIn(document, 'sec')).toEqual(['SI']);
  });

  it('devuelve null para el rasgo sin código, para poder avisar antes de enviar', () => {
    const document = { type: 'FeatureCollection', features: [feature({ otra: 'cosa' })] };
    expect(codesIn(document)).toEqual([null]);
  });

  it('no toma un objeto anidado como código', () => {
    // Si lo tomara, la vista previa mostraría «[object Object]» como el código de una zona.
    const document = { type: 'FeatureCollection', features: [feature({ code: { a: 1 } })] };
    expect(codesIn(document)).toEqual([null]);
  });
});

describe('coverageHeadline', () => {
  it('dice que no hay trabajo abierto cuando no lo hay', () => {
    expect(coverageHeadline(coverage())).toContain('No hay trabajo abierto');
  });

  it('nombra las que no caen en ninguna zona, que es lo que hay que corregir', () => {
    const report = coverage({ open_orders: 200, inside_one: 189, outside: 11, covered_share: 0.945 });
    expect(coverageHeadline(report)).toContain('11 no cae(n) en ninguna zona');
  });

  it('separa las ambiguas de las descubiertas', () => {
    const report = coverage({ open_orders: 10, inside_one: 7, outside: 2, ambiguous: 1 });
    const headline = coverageHeadline(report);
    expect(headline).toContain('2 no cae(n)');
    expect(headline).toContain('1 cae(n) en más de una');
  });

  it('lo dice sin adornos cuando todo cae en una zona', () => {
    const report = coverage({ open_orders: 5, inside_one: 5, covered_share: 1 });
    expect(coverageHeadline(report)).toContain('caen en una zona');
  });
});

describe('coverageCaveats', () => {
  it('no cuenta contra las zonas las OT sin punto, y lo dice', () => {
    const report = coverage({ open_orders: 10, inside_one: 7, without_location: 3, covered_share: 1 });
    const lines = coverageCaveats(report);
    expect(lines[0]).toContain('no tienen punto');
    expect(lines[0]).toContain('No cuentan contra la cobertura');
  });

  it('explica que no se puede calcular el porcentaje en vez de mostrar 0 %', () => {
    const report = coverage({ open_orders: 4, without_location: 4, covered_share: null });
    expect(coverageCaveats(report).join(' ')).toContain('no se puede calcular el porcentaje');
  });

  it('avisa de que una OT en dos zonas no tiene respuesta', () => {
    const report = coverage({ open_orders: 3, ambiguous: 1, inside_one: 2, covered_share: 0.66 });
    expect(coverageCaveats(report).join(' ')).toContain('no tiene respuesta');
  });
});

describe('overlapLines', () => {
  it('muestra la frase del servidor sin parafrasear', () => {
    const report: CoverageReport = {
      ...coverage(),
      overlaps: [{ left: 'A', right: 'B', area_m2: 3.2e7, text: 'A y B se solapan en 32.000.000 m²' }],
    };
    expect(overlapLines(report)).toEqual(['A y B se solapan en 32.000.000 m²']);
  });

  it('devuelve nada cuando no hay solapamientos, que es el estado esperado', () => {
    expect(overlapLines(coverage())).toEqual([]);
  });
});

describe('zoneRows', () => {
  const collection: ZoneCollection = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: { type: 'MultiPolygon', coordinates: [] },
        properties: {
          code: 'SUR',
          name: 'Sur',
          description: null,
          origin: 'importada',
          active: false,
          updated_by: 'admin',
          updated_at: '2026-09-01T10:00:00Z',
        },
      },
      {
        type: 'Feature',
        geometry: { type: 'MultiPolygon', coordinates: [] },
        properties: {
          code: 'NORTE',
          name: 'Norte',
          description: null,
          origin: 'dibujada',
          active: true,
          updated_by: null,
          updated_at: null,
        },
      },
    ],
  };

  it('pone las activas primero y luego ordena por código', () => {
    expect(zoneRows(collection).map((row) => row.code)).toEqual(['NORTE', 'SUR']);
  });

  it('no inventa un autor cuando no hay', () => {
    expect(zoneRows(collection)[0]?.updatedBy).toBe('—');
  });

  it('devuelve una lista vacía mientras no ha cargado', () => {
    expect(zoneRows(null)).toEqual([]);
  });
});

describe('importHeadline', () => {
  function report(overrides: Partial<ImportReport> = {}): ImportReport {
    return { created: [], updated: [], accepted: 0, rejected: [], ...overrides };
  }

  it('cuenta las creadas y las reemplazadas por separado', () => {
    const line = importHeadline(report({ created: ['A'], updated: ['B', 'C'], accepted: 3 }));
    expect(line).toBe('1 creada(s) y 2 reemplazada(s); sin rechazos.');
  });

  it('nombra los rechazos, porque un silencio ahí es lo que esconde un archivo a medias', () => {
    const line = importHeadline(
      report({
        created: ['A'],
        accepted: 1,
        rejected: [{ index: 1, code: 'B', reason: 'geometría inválida' }],
      }),
    );
    expect(line).toContain('1 rechazada(s)');
  });

  it('un archivo del que no entró nada es un fallo; uno del que entró casi todo no', () => {
    expect(importFailed(report({ rejected: [{ index: 0, code: null, reason: 'x' }] }))).toBe(true);
    expect(
      importFailed(
        report({
          created: ['A'],
          accepted: 1,
          rejected: [{ index: 1, code: 'B', reason: 'x' }],
        }),
      ),
    ).toBe(false);
  });
});

describe('backfillLines', () => {
  function report(overrides: Partial<BackfillReport> = {}): BackfillReport {
    return { dry_run: false, filled: {}, ambiguous: {}, outside: [], ...overrides };
  }

  it('dice en condicional cuando es una simulación', () => {
    const lines = backfillLines(report({ dry_run: true, filled: { a: 'N' } }));
    expect(lines[0]).toContain('se llenaría(n)');
    expect(lines.at(-1)).toContain('todavía no se escribió nada');
  });

  it('explica por qué no tocó las ambiguas en vez de solo contarlas', () => {
    const lines = backfillLines(report({ ambiguous: { a: ['N', 'S'] } }));
    expect(lines.join(' ')).toContain('nadie podría revisar');
  });

  it('cuenta aparte las que no caen en ninguna zona', () => {
    expect(backfillLines(report({ outside: ['a', 'b'] })).join(' ')).toContain('2 OT no caen');
  });
});
