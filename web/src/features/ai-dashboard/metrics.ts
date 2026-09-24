/**
 * How the AI dashboard's numbers get read (RF-134).
 *
 * Every judgement here is about the same failure: a number that reads as a measurement when it is
 * not one. A dashboard is a decision tool — somebody looks at a rate and decides to publish a
 * model, order a labelling batch, or leave things alone — and the cheapest way to cause the wrong
 * decision is to render a suppressed rate as «0 %» or an empty panel as «todo bien».
 *
 * So: a missing rate says *why* it is missing and shows its counts; a percentage is written the way
 * Ecuador writes it; an empty panel says there was nothing to measure rather than nothing to fix.
 */

import type {
  ClassCorrections,
  FieldAcceptance,
  ModelInFleet,
  VoiceAdoption,
  WordErrors,
} from '../../api/analytics';

/**
 * A share as a percentage, in es-EC: comma decimal.
 *
 * The same family of defect as the «6,480 m» that the agents' distances had: a point decimal reads
 * as thousands here, and a supervisor reading «0.6 %» where the value is sixty per cent is a
 * supervisor being told the opposite.
 */
export function percent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits).replace('.', ',')} %`;
}

/** A rate, or why it is not being shown. Never a zero standing in for "unknown". */
export function rateLabel(value: number | null, part: number, whole: number, minimum: number): string {
  if (value !== null) return `${percent(value)} (${part} de ${whole})`;
  if (whole === 0) return 'sin propuestas en el periodo';
  return `sin muestra suficiente: ${whole} de ${minimum} necesarias`;
}

/** True when the rate is reportable, for the screen to decide whether to rank or dim a row. */
export function isMeasured(value: number | null): boolean {
  return value !== null;
}

/**
 * What to do about a field, in one line.
 *
 * The wording follows RF-174's rule for the agents — it marks for review, it does not accuse — and
 * for the same reason: a panel that reads as a verdict on the crew gets argued with instead of
 * acted on, and the person it names stops cooperating with the platform.
 */
export function fieldAdvice(row: FieldAcceptance, minimum: number): string {
  if (row.acceptance === null) {
    return `Aún sin muestra: ${row.proposals} propuesta(s), hacen falta ${minimum}.`;
  }
  const confident = row.mean_confidence !== null && row.mean_confidence >= 0.8;
  if (row.acceptance >= 0.9) return 'El modelo acierta en este campo.';
  if (row.acceptance >= 0.7) {
    return 'Aceptación media: candidato a más ejemplos en el próximo lote de etiquetado.';
  }
  return confident
    ? // Equivocado y seguro es el peor de los dos: la confianza alta es justo lo que hace que una
      // persona acepte sin mirar, así que este caso se nombra distinto.
      'Aceptación baja con confianza alta: revisar el umbral antes que el modelo.'
    : 'Aceptación baja y confianza baja: el campo necesita más datos de entrenamiento.';
}

/** The confusion a visual class shows, or null when there is nothing to say. */
export function confusionLabel(row: ClassCorrections): string | null {
  if (row.became.length === 0) return null;
  const [first, ...rest] = row.became;
  if (!first) return null;
  if (rest.length === 0) {
    return `Se corrigió siempre a «${first.value}»: es una confusión de dos clases.`;
  }
  const named = row.became.map((entry) => `«${entry.value}» (${entry.times})`).join(', ');
  return `Se corrigió a ${named}: el detector está dudando entre varias.`;
}

/** The word-error estimate in one sentence, with its caveat attached. */
export function wordErrorLabel(rows: WordErrors | null, minimum: number): string {
  if (rows === null || rows.measured_fields === 0) {
    return 'Sin campos dictados que se puedan comparar en el periodo.';
  }
  if (rows.error_rate === null) {
    return `Sin muestra suficiente: ${rows.measured_fields} de ${minimum} campos medibles.`;
  }
  return (
    `${percent(rows.error_rate)} de palabras con error sobre ${rows.reference_words} ` +
    `palabras en ${rows.measured_fields} campo(s).`
  );
}

/** How much of the dictated material the estimate could not cover. */
export function coverageLabel(rows: WordErrors): string | null {
  const total = rows.measured_fields + rows.unmeasurable_fields;
  if (rows.unmeasurable_fields === 0 || total === 0) return null;
  return (
    `${rows.unmeasurable_fields} de ${total} campos dictados no son texto (números, códigos, ` +
    'listas) y no entran en la estimación.'
  );
}

/** Sorted the way an analyst reads it: most dictated first, then alphabetically. */
export function sortAdoption(rows: VoiceAdoption[]): VoiceAdoption[] {
  return [...rows].sort(
    (a, b) => b.voice_fields - a.voice_fields || a.user.localeCompare(b.user, 'es'),
  );
}

/**
 * Versions grouped by model, newest activity first.
 *
 * The comparison the panel exists for is between two versions of the same model: a new version
 * whose acceptance dropped is a rollback candidate, and that is invisible when the rows are sorted
 * by name.
 */
export function byModel(rows: ModelInFleet[]): { model: string; versions: ModelInFleet[] }[] {
  const grouped = new Map<string, ModelInFleet[]>();
  for (const row of rows) {
    const list = grouped.get(row.model_name) ?? [];
    list.push(row);
    grouped.set(row.model_name, list);
  }
  return [...grouped.entries()]
    .map(([model, versions]) => ({
      model,
      versions: [...versions].sort((a, b) => (a.last_seen ?? '').localeCompare(b.last_seen ?? '')),
    }))
    .sort((a, b) => a.model.localeCompare(b.model, 'es'));
}

/**
 * Whether a newer version of a model accepts worse than an older one.
 *
 * The regression the guide's quality gates exist to catch (sección 8.4: «nunca regresar»). Reported
 * only when both versions have a reportable rate — a drop measured against a rate we refused to
 * report is not a drop.
 */
export function regressed(versions: ModelInFleet[]): { from: ModelInFleet; to: ModelInFleet } | null {
  const measured = versions.filter((row) => row.acceptance !== null);
  if (measured.length < 2) return null;
  const previous = measured[measured.length - 2];
  const latest = measured[measured.length - 1];
  if (!previous || !latest) return null;
  return (latest.acceptance ?? 0) < (previous.acceptance ?? 0)
    ? { from: previous, to: latest }
    : null;
}
