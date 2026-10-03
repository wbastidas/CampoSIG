/**
 * Reading the audit trail (RF-160, RF-161).
 *
 * The screen's whole job is to turn rows into a story an auditor can put in a report, so the
 * judgements here are about wording: what each event says in one line, and — the one that matters —
 * what a broken chain says. A verification result rendered as a green tick when it is not green is
 * the single worst thing this screen could do.
 */

import type { AuditEvent, ChainCheck } from '../../api/audit';

export const KIND_LABEL: Record<string, string> = {
  creacion: 'Creación',
  cambio_campo: 'Cambio de campo',
  transicion: 'Cambio de estado',
  acceso_evidencia: 'Acceso a evidencia',
  exportacion: 'Exportación',
  decision: 'Decisión',
};

export function kindLabel(kind: string): string {
  // An unknown kind shows its raw name rather than «Otro»: a trail that hides what it does not
  // recognise is a trail with a blind spot exactly where something new happened.
  return KIND_LABEL[kind] ?? kind;
}

export const ACTOR_LABEL: Record<string, string> = {
  persona: 'Persona',
  sistema: 'Sistema',
  modelo: 'Modelo',
};

/** One line describing what happened, from the event's own payload. */
export function summarise(event: AuditEvent): string {
  const payload = event.payload ?? {};
  switch (event.kind) {
    case 'transicion':
      return `${describe(payload.from)} → ${describe(payload.to)}`;
    case 'cambio_campo': {
      if (typeof payload.field_key === 'string') {
        return `${payload.field_key}: ${describe(payload.before)} → ${describe(payload.after)}`;
      }
      const after = payload.after as Record<string, unknown> | undefined;
      return after ? `asignada a ${describe(after.user_sub)}` : 'cambio registrado';
    }
    case 'acceso_evidencia':
      return `${describe(payload.count)} evidencia(s) consultada(s)`;
    case 'exportacion':
      return `${describe(payload.kind)} emitido`;
    case 'decision':
      return describe(payload.decision);
    case 'creacion':
      return `${describe(payload.work_type)} (${describe(payload.state)})`;
    default:
      return '';
  }
}

/**
 * Un valor del payload, legible.
 *
 * Todo lo que llega en el payload es `unknown` —viene de un JSONB— así que pasa por aquí y no por
 * `String()`: un objeto interpolado sale como «[object Object]», que es la forma de decirle al
 * auditor que no se le va a mostrar el dato.
 */
function describe(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'bigint') return String(value);
  // Un objeto, una lista, o algo que JSON no sabe serializar. Nunca `String()`: un payload que
  // llegara con una forma inesperada saldría como «[object Object]», que es la manera de decirle
  // al auditor que no se le va a mostrar el dato.
  return JSON.stringify(value) ?? '—';
}

/**
 * Whether a field change came from a model, and which one.
 *
 * RF-160 asks for the origin by name. A value a model proposed and a person confirmed has a person
 * as its actor — that is who answered for it — and the model belongs beside it, not instead of it.
 */
export function modelBehind(event: AuditEvent): string | null {
  const model = (event.payload ?? {}).model as
    | { name?: string; version?: string; confidence?: number }
    | null
    | undefined;
  if (!model?.name) return null;
  const confidence =
    typeof model.confidence === 'number'
      ? ` · ${(model.confidence * 100).toFixed(0).replace('.', ',')} %`
      : '';
  return `${model.name} ${model.version ?? ''}${confidence}`.trim();
}

/**
 * What the chain verification says, in words for a report.
 *
 * An intact chain gets one sentence. A broken one gets the sequence number and the reason, because
 * the auditor's next step is to go and look at that event — and «la cadena está rota» without a
 * number is a finding nobody can act on.
 */
export function chainVerdict(check: ChainCheck): string {
  if (check.intact) {
    return check.events === 0
      ? 'La bitácora de esta unidad todavía no tiene eventos.'
      : `Cadena íntegra sobre ${check.events} evento(s).`;
  }
  return `Cadena rota en el evento ${check.broken_at}: ${check.problem ?? 'motivo desconocido'}.`;
}

/** Newest first for the screen's default view: an auditor starts from what just happened. */
export function mostRecentFirst(events: AuditEvent[]): AuditEvent[] {
  return [...events].sort((a, b) => b.sequence - a.sequence);
}
