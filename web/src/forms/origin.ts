/**
 * How an AI-proposed value is described beside it (rule 8).
 *
 * In its own module because the form view is a component and this is not — and because the
 * difference between "a model proposed this and a technician accepted it unchanged" and "a
 * technician corrected it" is the whole audit, so it deserves its own tests.
 *
 * The acta prints the same sentence on paper (`app/reports/acta.py: ai_note`). Both exist because
 * rule 8 asks for origin, model version and confidence wherever an AI value is shown, and a value
 * shown without them reads exactly like one a person wrote.
 */

/** Just enough of a provenance row to mark a field. The review API's shape, narrowed. */
export interface FieldOrigin {
  field_key: string;
  origin: string;
  confidence: number | null;
  model_name: string | null;
  model_version: string | null;
  confirmed_by: string | null;
  accepted_unchanged: boolean;
  is_ai: boolean;
}

/** How an AI-proposed value is described beside it (rule 8). */
export function originNote(entry: FieldOrigin): string {
  const source = entry.origin === 'voz' ? 'dictado' : entry.origin === 'vision' ? 'visión' : 'IA';
  const model = entry.model_name ?? 'modelo sin identificar';
  const version = entry.model_version ?? 'sin versión';
  const confidence =
    entry.confidence === null ? 'sin confianza' : `confianza ${Math.round(entry.confidence * 100)} %`;
  if (!entry.confirmed_by) return `propuesto por ${source} · ${model} ${version} · ${confidence} · sin confirmar`;
  const verb = entry.accepted_unchanged ? 'aceptado sin cambios por' : 'corregido por';
  return `propuesto por ${source} · ${model} ${version} · ${confidence} · ${verb} ${entry.confirmed_by}`;
}

