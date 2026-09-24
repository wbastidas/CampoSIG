/**
 * Las decisiones de la pantalla de política (RF-151).
 *
 * Lo que se prueba es lo que convertiría un guardado en un borrado: que «no toqué esto» no viaje
 * como «pon esto en nulo», y que un valor heredado no se vea igual que uno decidido.
 */

import { describe, expect, it } from 'vitest';

import type { EffectivePolicy, PolicyList, PolicyValues } from '../../api/policy';
import {
  changesOf,
  configuredZones,
  displayValue,
  effectiveRows,
  hasChanges,
  isBoolean,
  labelOf,
  problemsIn,
  rowFor,
  scopeHeadline,
} from './policy';

function list(): PolicyList {
  return {
    fields: ['store_audio', 'min_photos'],
    defaults: { store_audio: false, min_photos: 1 },
    rows: [
      {
        zone_code: null,
        values: { store_audio: true, min_photos: 3 },
        note: null,
        updated_by: 'admin',
        updated_at: '2026-09-20T10:00:00+00:00',
      },
      {
        zone_code: 'NORTE',
        values: { store_audio: null, min_photos: 5 },
        note: null,
        updated_by: 'admin',
        updated_at: '2026-09-21T10:00:00+00:00',
      },
    ],
  };
}

function effective(overrides: Record<string, { value: unknown; source: string }> = {}) {
  const base: EffectivePolicy = {
    business_unit: 'GYE',
    zone_code: null,
    values: {
      store_audio: { value: false, source: 'por omisión de la plataforma' },
      require_audio_consent: { value: true, source: 'por omisión de la plataforma' },
      audio_retention_days: { value: 90, source: 'por omisión de la plataforma' },
      min_photos: { value: 3, source: 'unidad' },
      photo_max_edge_px: { value: 1600, source: 'por omisión de la plataforma' },
      photo_quality: { value: 80, source: 'por omisión de la plataforma' },
      evidence_retention_days: { value: 1825, source: 'por omisión de la plataforma' },
      upload_on_metered: { value: false, source: 'por omisión de la plataforma' },
      metered_upload_limit_mb: { value: null, source: 'por omisión de la plataforma' },
      downscale_on_metered: { value: true, source: 'por omisión de la plataforma' },
    },
  };
  return { ...base, values: { ...base.values, ...overrides } } as EffectivePolicy;
}

describe('changesOf', () => {
  const loaded: PolicyValues = { store_audio: true, min_photos: 3 };

  it('solo manda lo que cambió', () => {
    expect(changesOf(loaded, { min_photos: 6 })).toEqual({ min_photos: 6 });
  });

  it('no manda un campo que volvió a su valor original', () => {
    expect(changesOf(loaded, { min_photos: 3 })).toEqual({});
  });

  it('un nulo explícito sí viaja, porque es lo que hace que se herede otra vez', () => {
    expect(changesOf(loaded, { min_photos: null })).toEqual({ min_photos: null });
  });

  it('false no es una ausencia', () => {
    // Si se comparara por truthiness, apagar el audio no llegaría nunca al servidor.
    expect(changesOf(loaded, { store_audio: false })).toEqual({ store_audio: false });
  });

  it('un campo que ya era nulo y sigue nulo no viaja', () => {
    expect(changesOf({ min_photos: null }, { min_photos: null })).toEqual({});
  });

  it('hasChanges dice si hay algo que guardar', () => {
    expect(hasChanges(loaded, {})).toBe(false);
    expect(hasChanges(loaded, { min_photos: 4 })).toBe(true);
  });
});

describe('rowFor y configuredZones', () => {
  it('encuentra la fila de la unidad con el ámbito nulo', () => {
    expect(rowFor(list(), null)?.min_photos).toBe(3);
  });

  it('encuentra la fila de una zona', () => {
    expect(rowFor(list(), 'NORTE')?.min_photos).toBe(5);
  });

  it('devuelve null para una zona sin fila propia, que es distinto de una fila vacía', () => {
    expect(rowFor(list(), 'SUR')).toBeNull();
  });

  it('enumera solo las zonas configuradas', () => {
    expect(configuredZones(list())).toEqual(['NORTE']);
  });

  it('aguanta no haber cargado todavía', () => {
    expect(rowFor(null, null)).toBeNull();
    expect(configuredZones(null)).toEqual([]);
  });
});

describe('effectiveRows', () => {
  it('marca como heredado lo que decidió la plataforma y no una persona', () => {
    const rows = effectiveRows(effective());
    const audio = rows.find((row) => row.field === 'store_audio');
    const photos = rows.find((row) => row.field === 'min_photos');
    expect(audio?.inherited).toBe(true);
    expect(photos?.inherited).toBe(false);
  });

  it('muestra el origen con las palabras del servidor', () => {
    const rows = effectiveRows(effective({ min_photos: { value: 5, source: 'zona' } }));
    expect(rows.find((row) => row.field === 'min_photos')?.source).toBe('zona');
  });

  it('trae una fila por campo, en el orden de la pantalla', () => {
    expect(effectiveRows(effective())).toHaveLength(10);
    expect(effectiveRows(effective())[0]?.field).toBe('store_audio');
  });

  it('no revienta antes de cargar', () => {
    expect(effectiveRows(null)).toEqual([]);
  });
});

describe('displayValue', () => {
  it('un booleano se lee en español', () => {
    expect(displayValue(true)).toBe('Sí');
    expect(displayValue(false)).toBe('No');
  });

  it('un número sin definir lo dice, en vez de mostrar 0', () => {
    expect(displayValue(null)).toBe('sin definir');
  });

  it('los miles llevan punto, como en Ecuador', () => {
    expect(displayValue(1825)).toBe('1.825');
  });
});

describe('problemsIn', () => {
  it('una retención de cero días es un error de tipeo', () => {
    expect(problemsIn({ audio_retention_days: 0 })).toHaveLength(1);
  });

  it('la calidad va de 1 a 100', () => {
    expect(problemsIn({ photo_quality: 140 })[0]).toContain('1 a 100');
  });

  it('las fotos mínimas pueden ser cero, que es «ninguna obligatoria»', () => {
    expect(problemsIn({ min_photos: 0 })).toEqual([]);
  });

  it('un nulo no es un problema: es heredar', () => {
    expect(problemsIn({ audio_retention_days: null, photo_quality: null })).toEqual([]);
  });
});

describe('etiquetas y ámbito', () => {
  it('cada campo booleano se sabe booleano, para pintar un selector y no un número', () => {
    expect(isBoolean('store_audio')).toBe(true);
    expect(isBoolean('min_photos')).toBe(false);
  });

  it('una etiqueta desconocida se muestra tal cual en vez de quedar en blanco', () => {
    expect(labelOf('campo_nuevo')).toBe('campo_nuevo');
  });

  it('el encabezado dice dónde va a caer el guardado', () => {
    expect(scopeHeadline(null)).toContain('toda la unidad');
    expect(scopeHeadline('NORTE')).toContain('hereda de la unidad');
  });
});
