/**
 * Reading the regulatory parameters (RF-150, ADR-007).
 *
 * This screen exists for two lists that have to be empty before a pilot, and they are not the same
 * list: codes a rule needs and nobody loaded, and codes loaded that nobody has checked against the
 * official text. The first makes a rule report that it cannot judge; the second makes it judge
 * against a number somebody typed. Showing them together as «problemas» would hide that.
 *
 * And one framing decision: a value is shown with the period it was in force, never on its own.
 * «24 horas» is not a fact about the platform, it is a fact about a date — an approval from March
 * has to stay explicable against March's limit.
 */

import type { Parameter, ParameterIndex, Revision } from '../../api/regulatory';

/** The storage wrapper off: `{v: 24}` reads as «24». */
export function plainValue(value: Record<string, unknown>): string {
  const keys = Object.keys(value);
  if (keys.length === 1 && keys[0] === 'v') {
    const inner = value.v;
    if (inner === null || inner === undefined) return 'sin valor';
    if (typeof inner === 'number') return inner.toLocaleString('es-EC').replace(/,/g, '.');
    if (typeof inner === 'boolean') return inner ? 'Sí' : 'No';
    if (typeof inner === 'string') return inner;
    // Un objeto o un arreglo dentro de `v`: se muestra como JSON, no como «[object Object]».
    return JSON.stringify(inner);
  }
  // A table keyed by voltage level, a range — shown as it is rather than flattened into a lie.
  return JSON.stringify(value);
}

/** A date as Ecuador writes it, from the ISO the server sends. */
export function ecuadorDate(iso: string | null): string {
  if (!iso) return '—';
  const [date] = iso.split('T');
  const parts = (date ?? '').split('-');
  if (parts.length !== 3) return iso;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

/** How a period reads. An open period says «vigente», not «hasta null». */
export function periodLabel(row: Parameter): string {
  const from = ecuadorDate(row.effective_from);
  if (!row.effective_to) return `desde ${from} · vigente`;
  return `${from} a ${ecuadorDate(row.effective_to)}`;
}

export function isInForce(row: Parameter): boolean {
  return row.effective_to === null;
}

/**
 * What the verification state means for whoever reads it.
 *
 * Spelled out rather than shown as a tick, because «no verificado» is not a formatting detail: it
 * is the difference between a limit read from the official text and a plausible-looking number.
 */
export function verificationLabel(row: Parameter): string {
  if (row.verified) return `Verificado por ${row.verified_by} el ${ecuadorDate(row.verified_at)}`;
  if (row.strict) {
    return 'Sin verificar, y es estricto: las reglas se niegan a evaluarlo hasta que alguien lo lea';
  }
  return 'Sin verificar: las reglas lo evalúan y reportan el resultado como no verificado';
}

/** RF-150's «usuario que modificó», next to who loaded it. */
export function authorshipLabel(row: Parameter): string {
  const loaded = row.created_by ?? 'sin registrar';
  if (!row.updated_by || row.updated_by === row.created_by) return `Cargado por ${loaded}`;
  return `Cargado por ${loaded}; última edición de ${row.updated_by}`;
}

export interface Gap {
  kind: 'missing' | 'unverified';
  code: string;
  advice: string;
}

/**
 * The two lists, kept apart, worst first.
 *
 * A missing code is worse than an unverified one: the rule cannot judge at all, so nothing is
 * reported about that limit — which looks exactly like compliance.
 */
export function gaps(index: ParameterIndex | null): Gap[] {
  if (!index) return [];
  const missing: Gap[] = index.missing.map((code) => ({
    kind: 'missing' as const,
    code,
    advice: 'Ninguna regla puede juzgar este límite: no hay parámetro cargado.',
  }));
  const unverified: Gap[] = index.unverified.map((code) => ({
    kind: 'unverified' as const,
    code,
    advice: 'Cargado, pero nadie lo comparó con el texto oficial.',
  }));
  return [...missing, ...unverified];
}

/** The headline. Says «listo» only when both lists are empty. */
export function indexHeadline(index: ParameterIndex | null): string {
  if (!index) return 'Cargando…';
  if (index.missing.length === 0 && index.unverified.length === 0) {
    return `${index.loaded.length} parámetro(s) cargado(s), todos verificados.`;
  }
  const parts: string[] = [];
  if (index.missing.length > 0) parts.push(`${index.missing.length} sin cargar`);
  if (index.unverified.length > 0) parts.push(`${index.unverified.length} sin verificar`);
  return `${index.loaded.length} parámetro(s) cargado(s); ${parts.join(' y ')}.`;
}

export const ACTION_LABEL: Record<string, string> = {
  creado: 'Creado',
  corregido: 'Corregido',
  cerrado: 'Cerrado',
  verificado: 'Verificado',
};

/** One revision as a sentence: who, what and — when it moved a value — from what. */
export function revisionLine(revision: Revision): string {
  const action = ACTION_LABEL[revision.action] ?? revision.action;
  const fields = Object.keys(revision.changed);
  if (fields.length === 0) return `${action} por ${revision.actor}`;
  const moved = fields
    .map((field) => {
      const change = revision.changed[field];
      return `${field}: ${describe(change?.from)} → ${describe(change?.to)}`;
    })
    .join('; ');
  return `${action} por ${revision.actor} — ${moved}`;
}

function describe(value: unknown): string {
  if (value === null || value === undefined) return '(vacío)';
  if (typeof value === 'object') return JSON.stringify(value);
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return JSON.stringify(value);
}

/** Whether a period can still be verified: only an unverified one, and only by an editor. */
export function canVerify(row: Parameter, mayEdit: boolean): boolean {
  return mayEdit && !row.verified;
}
