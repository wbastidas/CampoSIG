/**
 * Reading the maintenance board (RF-133).
 *
 * The number this board is planned with is a backlog, and a backlog whose definition nobody can see
 * is one that gets argued about instead of worked. So the definition travels from the server and is
 * shown, not paraphrased — and the two things that are *not* the backlog (findings already attended,
 * findings with no asset to follow) are shown beside it rather than folded in.
 */

import type { AssetRecurrence, FeederHeat, MaintenanceBoard } from '../../api/analytics';

/** Worst first, which is the order a planner reads in. */
export const CRITICALITY_ORDER = ['critica', 'alta', 'media', 'baja'];

export const CRITICALITY_LABEL: Record<string, string> = {
  critica: 'Crítica',
  alta: 'Alta',
  media: 'Media',
  baja: 'Baja',
};

export function criticalityLabel(key: string): string {
  return CRITICALITY_LABEL[key] ?? key;
}

/** A share as a percentage, es-EC. */
export function percent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits).replace('.', ',')} %`;
}

/**
 * The backlog by criticality, worst first, including the levels with none.
 *
 * Including the empty ones on purpose: «crítica: 0» is the sentence a planner wants to read, and a
 * row that simply disappears leaves them wondering whether it is zero or whether the board broke.
 */
export function backlogRows(board: MaintenanceBoard): { criticality: string; open: number }[] {
  return CRITICALITY_ORDER.map((criticality) => ({
    criticality,
    open: board.backlog.open_by_criticality[criticality] ?? 0,
  }));
}

/** What the backlog headline says. */
export function backlogHeadline(board: MaintenanceBoard): string {
  if (board.findings === 0) return 'Sin hallazgos registrados en el periodo.';
  return `${board.backlog.open} hallazgo(s) abierto(s) de ${board.findings} registrado(s).`;
}

/** What the headline does not cover, and the two are different things. */
export function backlogCaveats(board: MaintenanceBoard): string[] {
  const lines: string[] = [];
  if (board.backlog.attended > 0) {
    lines.push(`${board.backlog.attended} con trabajo posterior sobre el mismo activo.`);
  }
  if (board.backlog.untrackable > 0) {
    // No hay con qué seguirlos: llamarlos abiertos o atendidos serían afirmaciones sin dato.
    lines.push(
      `${board.backlog.untrackable} sin código de activo: no se pueden seguir, y no se cuentan ` +
        'ni como abiertos ni como atendidos.',
    );
  }
  if (board.backlog.wants_order > 0) {
    lines.push(`${board.backlog.wants_order} con petición de la cuadrilla de generar trabajo.`);
  }
  return lines;
}

/** What a feeder's heat says in one line. */
export function feederLine(row: FeederHeat): string {
  const top = row.top_defect
    ? `, sobre todo «${row.top_defect.defect_code}» (${row.top_defect.times})`
    : '';
  return `${row.defects} defecto(s), ${percent(row.share)} del periodo${top}.`;
}

/**
 * What a recurring asset is telling the planner.
 *
 * The distinction is the whole value of the panel: one defect repeated is a repair that did not
 * hold, several different ones is an asset at the end of its life, and those are different
 * decisions — a revisit versus a replacement.
 */
export function recurrenceAdvice(row: AssetRecurrence): string {
  const distinct = Object.keys(row.defects).length;
  if (distinct === 1) {
    const [defect, times] = Object.entries(row.defects)[0] ?? ['', 0];
    return `«${defect}» ${times} veces: la reparación no aguantó.`;
  }
  return `${distinct} defectos distintos: revisar si el activo está al final de su vida.`;
}

/** Defect types seen in the period, most frequent first, for the filter to offer. */
export function defectOptions(board: MaintenanceBoard): { code: string; count: number }[] {
  return Object.entries(board.by_defect)
    .map(([code, count]) => ({ code, count }))
    .sort((a, b) => b.count - a.count || a.code.localeCompare(b.code, 'es'));
}
