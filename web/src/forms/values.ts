/**
 * Rendering a JSONB answer for a person to read.
 *
 * Moved out of the review screen because the acta, the form view and the audit table all need it,
 * and three copies of "how do we show a repeatable table row" is three chances to show
 * `[object Object]` to somebody auditing an AI proposal — which is the defect this function was
 * written for in the first place.
 *
 * Booleans read as **Sí / No**, not `true` / `false`. The UI is in Ecuadorian Spanish (rule 11) and
 * a supervisor reading `true` under "¿Quedó señalizado?" is being shown the storage format instead
 * of the answer. The acta prints the same words, so paper and screen agree.
 */

export function displayValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  if (typeof value === 'string') return value.trim() ? value : '—';
  if (typeof value === 'number') return String(value);
  if (Array.isArray(value)) {
    return value.length === 0 ? '—' : value.map(displayValue).join(', ');
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return '—';
    return entries.map(([key, inner]) => `${key}: ${displayValue(inner)}`).join('; ');
  }
  // Only a symbol or a function reaches here, and neither can come from JSONB. The type is named
  // rather than converted: `String(Symbol())` throws, and a value with no honest representation
  // must not fake one.
  return `(${typeof value})`;
}
