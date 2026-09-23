/**
 * Reading the operational board (RF-130).
 *
 * Durations are where an operational dashboard misleads most easily, so the judgements here are all
 * about them: a duration written in the wrong unit is unreadable, a suppressed median rendered as a
 * dash looks like zero work, and a leg with jobs still running looks slower than it is unless the
 * screen says how many are still out there.
 */

import type { Leg, OperationalBoard } from '../../api/analytics';

/** RF-130: «los datos se actualizan cada 5 min». */
export const REFRESH_MS = 5 * 60 * 1000;

/**
 * A duration, in the unit a person would use for it, written as Ecuador writes numbers.
 *
 * Minutes under an hour, hours with a comma decimal above — «1,5 h» and not «1.5 h», which reads as
 * fifteen here. The same defect the agents' distances had.
 */
export function duration(minutes: number | null): string {
  if (minutes === null) return '—';
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const hours = minutes / 60;
  if (hours < 24) return `${hours.toFixed(1).replace('.', ',')} h`;
  return `${(hours / 24).toFixed(1).replace('.', ',')} d`;
}

/** What a leg's central number says, or why there is none. */
export function legHeadline(leg: Leg): string {
  if (leg.median_minutes === null) {
    return leg.measured === 0
      ? 'Sin trabajos completos en el periodo.'
      : `Sin muestra suficiente: ${leg.measured} de ${leg.min_sample} trabajos.`;
  }
  return `Mediana ${duration(leg.median_minutes)} sobre ${leg.measured} trabajo(s).`;
}

/**
 * What the headline does not cover.
 *
 * Both numbers matter and they mean opposite things: jobs still running are the operation working,
 * and jobs with no record are the measurement failing.
 */
export function legCaveats(leg: Leg): string[] {
  const lines: string[] = [];
  if (leg.in_progress > 0) {
    lines.push(`${leg.in_progress} en curso, que no cuentan como cero.`);
  }
  if (leg.unrecorded > 0) {
    lines.push(`${leg.unrecorded} sin registro de este tramo en la bitácora.`);
  }
  return lines;
}

/** The tail, when the median hides it. */
export function legTail(leg: Leg): string | null {
  if (leg.p90_minutes === null) return null;
  return `9 de cada 10 por debajo de ${duration(leg.p90_minutes)}; la peor, ${duration(
    leg.worst_minutes,
  )}.`;
}

/** States worth showing first: what is moving, then what is waiting, then what is done. */
const STATE_ORDER = [
  'en_ejecucion',
  'en_sitio',
  'en_camino',
  'descargada',
  'asignada',
  'planificada',
  'suspendida',
  'cerrada_campo',
  'sincronizada',
  'en_revision',
  'devuelta',
  'aprobada',
  'cerrada',
  'anulada',
  'borrador',
];

export const STATE_LABEL: Record<string, string> = {
  borrador: 'Borrador',
  planificada: 'Planificada',
  asignada: 'Asignada',
  descargada: 'Descargada',
  en_camino: 'En camino',
  en_sitio: 'En sitio',
  en_ejecucion: 'En ejecución',
  suspendida: 'Suspendida',
  cerrada_campo: 'Cerrada en campo',
  sincronizada: 'Sincronizada',
  en_revision: 'En revisión',
  devuelta: 'Devuelta',
  aprobada: 'Aprobada',
  cerrada: 'Cerrada',
  anulada: 'Anulada',
};

export function orderedStates(counts: Record<string, number>): { state: string; count: number }[] {
  const known = STATE_ORDER.filter((state) => counts[state] !== undefined).map((state) => ({
    state,
    count: counts[state] ?? 0,
  }));
  // An unknown state shows at the end rather than disappearing: a state the screen does not know
  // about is a state somebody added, and hiding it would hide the work sitting in it.
  const extra = Object.keys(counts)
    .filter((state) => !STATE_ORDER.includes(state))
    .sort()
    .map((state) => ({ state, count: counts[state] ?? 0 }));
  return [...known, ...extra];
}

export function stateLabel(state: string): string {
  return STATE_LABEL[state] ?? state;
}

/** Work that is somebody's to do right now, for the header. */
export function openTotal(board: OperationalBoard): number {
  const done = ['aprobada', 'cerrada', 'anulada'];
  return Object.entries(board.by_state)
    .filter(([state]) => !done.includes(state))
    .reduce((total, [, count]) => total + count, 0);
}

/**
 * How stale the board is, in words.
 *
 * RF-130 asks for data no older than five minutes. The only way somebody can tell whether what they
 * are looking at qualifies is if the screen says when it was computed — a board that refreshes
 * silently is a board that looks equally fresh when the refresh has been failing for an hour.
 */
export function freshness(computedAt: string, now: Date): string {
  const age = (now.getTime() - new Date(computedAt).getTime()) / 1000;
  if (!Number.isFinite(age) || age < 0) return 'Calculado ahora.';
  if (age < 90) return 'Calculado hace menos de un minuto.';
  const minutes = Math.round(age / 60);
  return `Calculado hace ${minutes} minuto(s).`;
}
