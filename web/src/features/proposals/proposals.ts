/**
 * Reading the proposal tray (RF-013, RF-114).
 *
 * The screen's whole job is to make one distinction visible: **a priority the platform computed
 * from declared data, and one it estimated.** They are the same number on the screen and completely
 * different things to a supervisor. A tray that presented both as a computation is a tray that gets
 * ignored wholesale the first time somebody checks one and finds it was a default.
 *
 * So `estimated` is a badge, the caveats are shown in the server's own words and never paraphrased
 * — they are the words the area agreed on, and a shorter version would be the platform's opinion —
 * and the arithmetic is printed so anybody can redo it.
 *
 * The reject reason is a picker over the catalogue and never a text box: RF-114 says the reason is a
 * training signal, and free text cannot be a label. The signal each reason carries is shown, because
 * a supervisor choosing between «no es un defecto» and «ya está resuelto» is choosing what a model
 * learns, and they should be able to see that.
 */

import type { Criticality, Proposal, RejectReason, Tray } from '../../api/proposals';

/** Worst first. The same order the server uses; stated here because the screen re-sorts on filter. */
const PRIORITY_RANK: Record<string, number> = { critica: 0, alta: 1, media: 2, baja: 3 };

export const PRIORITY_LABEL: Record<string, string> = {
  critica: 'Crítica',
  alta: 'Alta',
  media: 'Media',
  baja: 'Baja',
};

export const STATE_LABEL: Record<string, string> = {
  propuesta: 'En la bandeja',
  aprobada: 'Aprobada',
  fusionada: 'Fusionada',
  rechazada: 'Rechazada',
};

export const ORIGIN_LABEL: Record<string, string> = {
  hallazgo_campo: 'Hallazgo de la cuadrilla',
  deteccion_visual: 'Detección visual',
};

export function priorityLabel(priority: string): string {
  return PRIORITY_LABEL[priority] ?? priority;
}

export function stateLabel(state: string): string {
  return STATE_LABEL[state] ?? state;
}

export function originLabel(origin: string): string {
  return ORIGIN_LABEL[origin] ?? origin;
}

/** Worst first, then oldest first, so nothing starves inside a priority. */
export function trayRows(tray: Tray | null): Proposal[] {
  if (!tray) return [];
  return [...tray.proposals].sort((a, b) => {
    const byPriority = (PRIORITY_RANK[a.priority] ?? 9) - (PRIORITY_RANK[b.priority] ?? 9);
    if (byPriority !== 0) return byPriority;
    return (a.created_at ?? '').localeCompare(b.created_at ?? '');
  });
}

/**
 * How the priority should be read: as a computation, or as an estimate.
 *
 * Two words rather than a boolean in the markup, because this is the label a supervisor scans for.
 */
export function confidenceLabel(criticality: Criticality): string {
  return criticality.estimated ? 'Estimada' : 'Calculada';
}

/** The deadline in words. P4 has none, and «sin plazo» is the honest answer, not «0 h». */
export function deadlineLabel(hours: number | null): string {
  if (hours === null) return 'Sin plazo: entra al plan de mantenimiento';
  if (hours === 0) return 'Inmediato';
  if (hours < 24) return `${hours} h`;
  const days = Math.round(hours / 24);
  return `${days} día(s)`;
}

/** The headline. Says how many of the open ones carry an estimate, because that is the caveat. */
export function trayHeadline(tray: Tray | null): string {
  if (!tray) return 'Cargando…';
  const rows = tray.proposals;
  if (rows.length === 0) return 'No hay propuestas en este estado.';
  const estimated = rows.filter((row) => row.criticality.estimated).length;
  const worst = rows.filter((row) => row.priority === 'critica').length;
  const parts = [`${rows.length} propuesta(s)`];
  if (worst > 0) parts.push(`${worst} crítica(s)`);
  if (estimated > 0) parts.push(`${estimated} con prioridad estimada`);
  return `${parts.join(', ')}.`;
}

/** The counts by state, ordered the way the tray is worked, and only the ones that exist. */
export function countRows(tray: Tray | null): { state: string; label: string; total: number }[] {
  if (!tray) return [];
  const order = ['propuesta', 'aprobada', 'fusionada', 'rechazada'];
  return order
    .filter((state) => (tray.counts[state] ?? 0) > 0)
    .map((state) => ({ state, label: stateLabel(state), total: tray.counts[state] ?? 0 }));
}

/** The reasons a rejection may name. Empty means the catalogue is not loaded, which is worth saying. */
export function reasonOptions(tray: Tray | null): RejectReason[] {
  return tray?.reject_reasons ?? [];
}

/**
 * What to tell a supervisor who has no reasons to choose from.
 *
 * Null when there are reasons. A rejection without a catalogued reason is not offered at all: the
 * alternative would be a free-text box, and RF-114's training signal cannot come from free text.
 */
export function reasonsAdvice(tray: Tray | null): string | null {
  if (!tray) return null;
  if (tray.reject_reasons.length > 0) return null;
  return (
    'El catálogo «proposal_reject_reason» no tiene valores, así que no se puede rechazar: el motivo ' +
    'es una etiqueta de entrenamiento y no un texto libre. Cárguelo desde Catálogos.'
  );
}

export type Decision = 'aprobar' | 'fusionar' | 'rechazar';

export interface DecisionDraft {
  decision: Decision;
  /** The supervisor's own priority, empty to keep the computed one. */
  priority: string;
  /** The target work order for a merge. */
  workOrderId: string;
  reasonCode: string;
  note: string;
}

export const EMPTY_DECISION: DecisionDraft = {
  decision: 'aprobar',
  priority: '',
  workOrderId: '',
  reasonCode: '',
  note: '',
};

/** Everything wrong with a decision before it is sent, in Spanish. */
export function decisionProblems(draft: DecisionDraft): string[] {
  const problems: string[] = [];
  if (draft.decision === 'fusionar' && !draft.workOrderId.trim()) {
    problems.push('Indique la OT en la que se fusiona.');
  }
  if (draft.decision === 'rechazar' && !draft.reasonCode) {
    problems.push('Elija un motivo de rechazo del catálogo.');
  }
  return problems;
}

export function canDecide(draft: DecisionDraft): boolean {
  return decisionProblems(draft).length === 0;
}

/**
 * What the platform will do, said before the supervisor presses the button.
 *
 * The override is named explicitly: changing the priority is a decision a supervisor takes with
 * knowledge the platform does not have, and it should be obvious that it is being taken.
 */
export function decisionAdvice(draft: DecisionDraft, proposal: Proposal): string {
  if (draft.decision === 'aprobar') {
    const chosen = draft.priority || proposal.priority;
    const overridden = draft.priority && draft.priority !== proposal.priority;
    return overridden
      ? `Se crea una OT planificada con prioridad ${priorityLabel(chosen)}, en lugar de la ` +
          `${priorityLabel(proposal.priority)} que calculó el anexo C. Queda en la bitácora.`
      : `Se crea una OT planificada con prioridad ${priorityLabel(chosen)}.`;
  }
  if (draft.decision === 'fusionar') {
    return 'Los hallazgos se adjuntan a la descripción de esa OT. No se crea ninguna OT nueva.';
  }
  return 'No se crea ninguna OT. El motivo se guarda como señal para el entrenamiento.';
}

/** The signal a chosen reason carries, for the line under the picker. */
export function signalOf(tray: Tray | null, reasonCode: string): string | null {
  const found = reasonOptions(tray).find((reason) => reason.code === reasonCode);
  return found?.signal ?? null;
}

export const SIGNAL_LABEL: Record<string, string> = {
  falso_positivo: 'Enseña que la detección se equivocó',
  clase_equivocada: 'Enseña que el defecto era otro',
  ninguna: 'No enseña nada: la detección acertó y el mundo cambió',
  fuera_de_alcance: 'Enseña que el activo no es de la distribuidora',
  prioridad: 'Enseña que la prioridad estaba mal, no el defecto',
  activo: 'Enseña que el activo identificado era otro',
};

export function signalLabel(signal: string | null): string | null {
  if (!signal) return null;
  return SIGNAL_LABEL[signal] ?? signal;
}
