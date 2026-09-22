/**
 * La lógica de decisión del importador (RF-301).
 *
 * Dos de estos casos son la razón por la que el módulo existe aparte del componente: cambiar de
 * clase tiene que **borrar** los campos elegidos para la anterior, y un tipo de activo que nadie
 * mapeó no es lo mismo que uno mapeado a medias.
 */

import { describe, expect, it } from 'vitest';

import type {
  AssetProposal,
  FieldCandidate,
  ProfileDecisions,
} from '../../api/modelProfile';
import {
  ambiguous,
  candidatesFor,
  chooseField,
  chooseLayer,
  chosenField,
  chosenLayer,
  clearAsset,
  confidence,
  leadingLayer,
  progressOf,
  rankedEvidence,
  refusals,
  statusOf,
  valueMapGaps,
} from './decisions';

function candidate(field: string, score: number, extra: Partial<FieldCandidate> = {}): FieldCandidate {
  return {
    field,
    label: field,
    score,
    evidence: [],
    domain: null,
    volatile_by_business_unit: false,
    value_map: null,
    ...extra,
  };
}

function asset(overrides: Partial<AssetProposal> = {}): AssetProposal {
  return {
    asset_type_key: 'support_structure',
    geometry: 'point',
    candidates: [
      { layer: 'ClaseA', score: 0.9, evidence: [] },
      { layer: 'ClaseB', score: 0.4, evidence: [] },
    ],
    attributes: [
      { attribute_key: 'code', attribute_type: 'string', required: true, candidates: [candidate('COD', 0.9)], refused: [] },
      { attribute_key: 'material', attribute_type: 'enum', required: false, candidates: [candidate('MAT', 0.8)], refused: [] },
    ],
    related: [],
    participates_in_geometric_network: false,
    ...overrides,
  };
}

function decisions(assets: ProfileDecisions['assets'] = {}): ProfileDecisions {
  return {
    header: {
      id: 'importado',
      label: null,
      provider: 'arcpy-agent',
      arcgis_version: null,
      spatial_reference: 32717,
      geometric_network: null,
      feature_dataset: null,
    },
    assets,
  };
}

describe('confianza', () => {
  it('se dice en palabras, no en un porcentaje', () => {
    expect(confidence(0.95)).toBe('alta');
    expect(confidence(0.6)).toBe('media');
    expect(confidence(0.31)).toBe('baja');
  });
});

describe('ambigüedad', () => {
  it('un solo candidato nunca es ambiguo', () => {
    expect(ambiguous([{ score: 0.9 }])).toBe(false);
  });

  it('dos candidatos separados por menos del margen sí lo son', () => {
    expect(ambiguous([{ score: 0.9 }, { score: 0.85 }])).toBe(true);
    expect(ambiguous([{ score: 0.9 }, { score: 0.4 }])).toBe(false);
  });
});

describe('evidencia', () => {
  it('se lee de la señal más fuerte a la más débil, con las penalizaciones contando', () => {
    const ordered = rankedEvidence([
      { signal: 'tipo', detail: '', weight: -0.2 },
      { signal: 'nombre', detail: '', weight: 0.5 },
      { signal: 'geometría', detail: '', weight: 0.15 },
    ]);
    expect(ordered.map((e) => e.signal)).toEqual(['nombre', 'tipo', 'geometría']);
  });
});

describe('elegir una clase', () => {
  it('prellena los atributos que la propuesta resuelve sola', () => {
    const next = chooseLayer(decisions(), 'support_structure', asset(), 'ClaseA');
    expect(chosenLayer(next, 'support_structure')).toBe('ClaseA');
    expect(chosenField(next, 'support_structure', 'code')).toBe('COD');
  });

  it('no prellena un atributo ambiguo', () => {
    const ambiguousAsset = asset({
      attributes: [
        {
          attribute_key: 'code',
          attribute_type: 'string',
          required: true,
          candidates: [candidate('COD', 0.8), candidate('NUM', 0.78)],
          refused: [],
        },
      ],
    });
    const next = chooseLayer(decisions(), 'support_structure', ambiguousAsset, 'ClaseA');
    expect(chosenField(next, 'support_structure', 'code')).toBeNull();
  });

  it('borra los campos elegidos para la clase anterior', () => {
    // El defecto que esto impide: `CODIGO` existe en casi todas las clases, así que un campo
    // elegido para la clase rechazada sobreviviría al cambio y parecería decidido, apuntando a
    // una columna de una clase que nadie eligió.
    const before = decisions({
      support_structure: {
        layer: 'ClaseB',
        attributes: { code: 'COD_VIEJO', material: 'MAT_VIEJO' },
        related: [],
        participates_in_geometric_network: false,
      },
    });
    const after = chooseLayer(before, 'support_structure', asset(), 'ClaseA');
    expect(chosenField(after, 'support_structure', 'code')).toBe('COD');
    expect(chosenField(after, 'support_structure', 'material')).toBe('MAT');
    expect(Object.values(after.assets.support_structure?.attributes ?? {})).not.toContain(
      'COD_VIEJO',
    );
  });

  it('no muta el objeto anterior', () => {
    const before = decisions();
    chooseLayer(before, 'support_structure', asset(), 'ClaseA');
    expect(before.assets).toEqual({});
  });
});

describe('elegir un campo', () => {
  it('desmapear un atributo es una respuesta legítima y se guarda como tal', () => {
    const start = chooseLayer(decisions(), 'support_structure', asset(), 'ClaseA');
    const next = chooseField(start, 'support_structure', 'material', null);
    expect(chosenField(next, 'support_structure', 'material')).toBeNull();
    expect(chosenField(next, 'support_structure', 'code')).toBe('COD');
  });

  it('elegir un campo sin haber elegido clase no hace nada', () => {
    const next = chooseField(decisions(), 'support_structure', 'code', 'COD');
    expect(next.assets).toEqual({});
  });
});

describe('estado por tipo de activo', () => {
  it('sin clase elegida no está listo', () => {
    expect(statusOf(asset(), undefined).ready).toBe(false);
  });

  it('un obligatorio sin campo bloquea; un opcional sin campo no', () => {
    const status = statusOf(asset(), {
      layer: 'ClaseA',
      attributes: { material: 'MAT' },
      related: [],
      participates_in_geometric_network: false,
    });
    expect(status.missingRequired).toEqual(['code']);
    expect(status.unmapped).toEqual([]);
    expect(status.ready).toBe(false);
  });

  it('con todos los obligatorios mapeados está listo, aunque falte un opcional', () => {
    const status = statusOf(asset(), {
      layer: 'ClaseA',
      attributes: { code: 'COD' },
      related: [],
      participates_in_geometric_network: false,
    });
    expect(status.missingRequired).toEqual([]);
    expect(status.unmapped).toEqual(['material']);
    expect(status.ready).toBe(true);
  });
});

describe('avance', () => {
  it('un tipo que nadie mapeó no bloquea; uno mapeado a medias sí', () => {
    // Una instalación sin alumbrado público es una instalación real. Una clase elegida con un
    // atributo obligatorio colgando es trabajo a medio hacer.
    const assets = [asset(), asset({ asset_type_key: 'street_light' })];
    const half = progressOf(
      assets,
      decisions({
        support_structure: {
          layer: 'ClaseA',
          attributes: {},
          related: [],
          participates_in_geometric_network: false,
        },
      }),
    );
    expect(half).toEqual({ total: 2, decided: 0, blocked: 1 });

    const none = progressOf(assets, decisions());
    expect(none).toEqual({ total: 2, decided: 0, blocked: 0 });
  });
});

describe('huecos del mapa de valores', () => {
  it('se listan los valores canónicos que el dominio no cubre', () => {
    const withDomain = asset({
      attributes: [
        {
          attribute_key: 'material',
          attribute_type: 'enum',
          required: false,
          candidates: [
            candidate('MAT', 0.8, {
              domain: 'DomMaterial',
              value_map: {
                value_map_name: 'material.support',
                domain: 'DomMaterial',
                mapping: { concrete: '1' },
                unmapped: ['fiberglass'],
                unclaimed: [],
              },
            }),
          ],
          refused: [],
        },
      ],
    });
    const gaps = valueMapGaps(withDomain, {
      layer: 'ClaseA',
      attributes: { material: 'MAT' },
      related: [],
      participates_in_geometric_network: false,
    });
    expect(gaps).toEqual([
      { attributeKey: 'material', domain: 'DomMaterial', unmapped: ['fiberglass'] },
    ]);
  });

  it('un atributo sin campo elegido no reporta huecos de dominio', () => {
    expect(valueMapGaps(asset(), undefined)).toEqual([]);
  });
});

describe('rechazos', () => {
  it('se muestran, porque «¿por qué no aparece este campo?» se pregunta una vez por instalación', () => {
    const withRefusals = asset({
      attributes: [
        {
          attribute_key: 'code',
          attribute_type: 'string',
          required: true,
          candidates: [candidate('COD', 0.9)],
          refused: ['OBJECTID: es una columna de control de la geodatabase'],
        },
      ],
    });
    expect(refusals(withRefusals)).toEqual([
      {
        attributeKey: 'code',
        reasons: ['OBJECTID: es una columna de control de la geodatabase'],
      },
    ]);
  });
});

describe('utilidades', () => {
  it('la clase líder es la primera candidata, o ninguna', () => {
    expect(leadingLayer(asset().candidates)).toBe('ClaseA');
    expect(leadingLayer([])).toBeNull();
  });

  it('los candidatos de un atributo inexistente son una lista vacía, no un error', () => {
    expect(candidatesFor(asset(), 'no_existe')).toEqual([]);
  });

  it('olvidar un tipo de activo lo quita de las decisiones', () => {
    const start = chooseLayer(decisions(), 'support_structure', asset(), 'ClaseA');
    expect(clearAsset(start, 'support_structure').assets).toEqual({});
  });
});
