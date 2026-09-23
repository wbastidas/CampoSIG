/**
 * Cómo se leen los números del tablero (RF-134).
 *
 * Todo lo que se prueba aquí es el mismo fallo visto de cinco lados: un número que se lee como
 * medición cuando no lo es. Un tablero es una herramienta de decisión —alguien mira una tasa y
 * decide publicar un modelo, pedir un lote de etiquetado o no hacer nada— y la forma más barata de
 * provocar la decisión equivocada es pintar una tasa suprimida como «0 %».
 */

import { describe, expect, it } from 'vitest';

import type {
  ClassCorrections,
  FieldAcceptance,
  ModelInFleet,
  VoiceAdoption,
  WordErrors,
} from '../../api/analytics';
import {
  byModel,
  confusionLabel,
  coverageLabel,
  fieldAdvice,
  isMeasured,
  percent,
  rateLabel,
  regressed,
  sortAdoption,
  wordErrorLabel,
} from './metrics';

function fleetRow(overrides: Partial<ModelInFleet> = {}): ModelInFleet {
  return {
    model_name: 'mobilenetv3-pole',
    model_version: '2026.08',
    origin: 'vision',
    proposals: 20,
    accepted: 18,
    acceptance: 0.9,
    first_seen: '2026-09-01T00:00:00Z',
    last_seen: '2026-09-10T00:00:00Z',
    ...overrides,
  };
}

describe('los porcentajes se escriben como en Ecuador', () => {
  it('con coma decimal', () => {
    // La misma familia del «6,480 m» de las distancias: un punto decimal se lee como miles aquí.
    expect(percent(0.6)).toBe('60,0 %');
    expect(percent(0.905, 1)).toBe('90,5 %');
    expect(percent(0.9, 0)).toBe('90 %');
  });

  it('nunca con punto', () => {
    expect(percent(0.123)).not.toContain('.');
  });
});

describe('una tasa que falta dice por qué falta', () => {
  it('con muestra suficiente muestra la tasa y su denominador', () => {
    expect(rateLabel(0.6, 6, 10, 5)).toBe('60,0 % (6 de 10)');
  });

  it('sin muestra suficiente dice cuántas faltan, y no un cero', () => {
    const said = rateLabel(null, 2, 2, 5);
    expect(said).toContain('sin muestra suficiente');
    expect(said).toContain('2 de 5');
    expect(said).not.toContain('0 %');
  });

  it('sin propuestas dice eso, que no es lo mismo', () => {
    // «Sin propuestas» y «con pocas propuestas» llevan a decisiones distintas: la primera es que
    // el modelo no se está usando, la segunda que todavía no se sabe.
    expect(rateLabel(null, 0, 0, 5)).toContain('sin propuestas');
  });

  it('isMeasured distingue las dos para que la pantalla pueda atenuar la fila', () => {
    expect(isMeasured(0)).toBe(true);
    expect(isMeasured(null)).toBe(false);
  });
});

describe('qué hacer con un campo', () => {
  function row(overrides: Partial<FieldAcceptance> = {}): FieldAcceptance {
    return {
      field_key: 'material',
      proposals: 40,
      accepted: 36,
      corrected: 4,
      acceptance: 0.9,
      mean_confidence: 0.88,
      ...overrides,
    };
  }

  it('aceptación alta: el modelo acierta', () => {
    expect(fieldAdvice(row(), 5)).toContain('acierta');
  });

  it('aceptación media: más ejemplos en el próximo lote', () => {
    expect(fieldAdvice(row({ acceptance: 0.75 }), 5)).toContain('etiquetado');
  });

  it('equivocado y seguro se nombra distinto de equivocado y dudoso', () => {
    // Es el peor de los dos: la confianza alta es justo lo que hace que una persona acepte sin
    // mirar, así que el consejo es revisar el umbral antes que el modelo.
    const confident = fieldAdvice(row({ acceptance: 0.4, mean_confidence: 0.95 }), 5);
    const unsure = fieldAdvice(row({ acceptance: 0.4, mean_confidence: 0.3 }), 5);
    expect(confident).toContain('umbral');
    expect(unsure).toContain('datos de entrenamiento');
    expect(confident).not.toBe(unsure);
  });

  it('sin muestra no da consejo: dice qué falta', () => {
    const said = fieldAdvice(row({ acceptance: null, proposals: 3 }), 5);
    expect(said).toContain('3 propuesta');
    expect(said).toContain('5');
  });

  it('el consejo no acusa a nadie', () => {
    // La regla de RF-174 para los agentes, por la misma razón: un panel que suena a veredicto se
    // discute en vez de accionarse.
    const words = ['error del técnico', 'culpa', 'mal trabajo', 'incumple'];
    for (const acceptance of [0.95, 0.75, 0.4]) {
      const said = fieldAdvice(row({ acceptance }), 5).toLowerCase();
      for (const word of words) expect(said).not.toContain(word);
    }
  });
});

describe('la confusión de una clase visual', () => {
  function row(overrides: Partial<ClassCorrections> = {}): ClassCorrections {
    return {
      proposed_class: 'concrete',
      proposals: 20,
      corrected: 8,
      correction_rate: 0.4,
      became: [{ value: 'wood', times: 8 }],
      ...overrides,
    };
  }

  it('una sola clase de destino es una confusión de dos', () => {
    expect(confusionLabel(row())).toContain('confusión de dos clases');
  });

  it('varias destinos es un detector dudando', () => {
    const said = confusionLabel(
      row({
        became: [
          { value: 'wood', times: 5 },
          { value: 'metal', times: 3 },
        ],
      }),
    );
    expect(said).toContain('dudando');
    expect(said).toContain('«wood» (5)');
  });

  it('sin correcciones no inventa una confusión', () => {
    expect(confusionLabel(row({ corrected: 0, became: [] }))).toBeNull();
  });
});

describe('el error de palabras', () => {
  function rows(overrides: Partial<WordErrors> = {}): WordErrors {
    return {
      reference_words: 120,
      errors: 12,
      measured_fields: 20,
      unmeasurable_fields: 4,
      error_rate: 0.1,
      measures: 'no es un WER contra una transcripción de referencia',
      ...overrides,
    };
  }

  it('se reporta con las palabras y los campos que lo sostienen', () => {
    const said = wordErrorLabel(rows(), 5);
    expect(said).toContain('10,0 %');
    expect(said).toContain('120 palabras');
    expect(said).toContain('20 campo');
  });

  it('sin campos medibles lo dice, y no reporta cero por ciento', () => {
    const said = wordErrorLabel(rows({ measured_fields: 0, error_rate: null }), 5);
    expect(said).toContain('Sin campos dictados');
    expect(said).not.toContain('0,0 %');
  });

  it('con muestra pequeña dice cuántos campos faltan', () => {
    expect(wordErrorLabel(rows({ measured_fields: 3, error_rate: null }), 5)).toContain('3 de 5');
  });

  it('la cobertura dice cuánto quedó fuera de la estimación', () => {
    // Una tasa sobre tres campos de cuatrocientos no es la tasa de nada.
    const said = coverageLabel(rows({ measured_fields: 3, unmeasurable_fields: 397 }));
    expect(said).toContain('397 de 400');
  });

  it('sin nada fuera no molesta con una advertencia', () => {
    expect(coverageLabel(rows({ unmeasurable_fields: 0 }))).toBeNull();
  });

  it('sin datos no se muestra nada del panel', () => {
    expect(wordErrorLabel(null, 5)).toContain('Sin campos dictados');
  });
});

describe('la adopción de la voz', () => {
  function row(overrides: Partial<VoiceAdoption> = {}): VoiceAdoption {
    return {
      user: 'tecnico.1',
      responses: 10,
      responses_with_voice: 8,
      voice_fields: 30,
      adoption: 0.8,
      ...overrides,
    };
  }

  it('se ordena por campos dictados y luego por nombre', () => {
    const ordered = sortAdoption([
      row({ user: 'b', voice_fields: 5 }),
      row({ user: 'a', voice_fields: 5 }),
      row({ user: 'c', voice_fields: 50 }),
    ]);
    expect(ordered.map((entry) => entry.user)).toEqual(['c', 'a', 'b']);
  });

  it('quien no dicta no se cae de la lista', () => {
    const ordered = sortAdoption([row({ user: 'z', voice_fields: 0, adoption: 0 })]);
    expect(ordered).toHaveLength(1);
  });
});

describe('las versiones en la flota', () => {
  it('se agrupan por modelo y se ordenan por última actividad', () => {
    const groups = byModel([
      fleetRow({ model_version: '2026.09', last_seen: '2026-09-20T00:00:00Z' }),
      fleetRow({ model_version: '2026.08', last_seen: '2026-09-10T00:00:00Z' }),
      fleetRow({ model_name: 'whisper-small-ec', origin: 'voz' }),
    ]);
    expect(groups.map((group) => group.model)).toEqual(['mobilenetv3-pole', 'whisper-small-ec']);
    expect(groups[0]!.versions.map((row) => row.model_version)).toEqual(['2026.08', '2026.09']);
  });

  it('una versión nueva que acepta peor se marca como candidata a reversión', () => {
    // «Nunca regresar» es la primera compuerta de calidad de la guía (8.4).
    const drop = regressed([
      fleetRow({ model_version: '2026.08', acceptance: 0.9, last_seen: '2026-09-01T00:00:00Z' }),
      fleetRow({ model_version: '2026.09', acceptance: 0.6, last_seen: '2026-09-20T00:00:00Z' }),
    ]);
    expect(drop).not.toBeNull();
    expect(drop!.to.model_version).toBe('2026.09');
  });

  it('una que acepta mejor no se marca', () => {
    expect(
      regressed([
        fleetRow({ model_version: '2026.08', acceptance: 0.6 }),
        fleetRow({ model_version: '2026.09', acceptance: 0.9 }),
      ]),
    ).toBeNull();
  });

  it('una caída contra una tasa que no se reportó no es una caída', () => {
    // Comparar contra un número que el servidor se negó a dar sería inventar la comparación.
    expect(
      regressed([
        fleetRow({ model_version: '2026.08', acceptance: null, proposals: 2 }),
        fleetRow({ model_version: '2026.09', acceptance: 0.5 }),
      ]),
    ).toBeNull();
  });

  it('con una sola versión no hay nada que comparar', () => {
    expect(regressed([fleetRow()])).toBeNull();
  });
});
