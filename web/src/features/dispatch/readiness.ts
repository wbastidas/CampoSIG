/**
 * Dispatch board logic, as pure functions.
 *
 * Kept out of the component for the same reason the mobile sync engine is kept out of
 * Android (ADR-010): this is where the judgements live — what counts as blocked, what a
 * supervisor should look at first — and judgements deserve tests that run in milliseconds.
 *
 * The ordering rule is the substance of the screen. A dispatch board sorted alphabetically
 * is a list; sorted by how wrong things are, it is a work queue.
 */

import type { CrewDispatch, DeviceReadiness } from '../../api/dispatch';

export type Severity = 'bloqueado' | 'atencion' | 'listo';

export const SEVERITY_ORDER: Severity[] = ['bloqueado', 'atencion', 'listo'];

export const SEVERITY_LABEL: Record<Severity, string> = {
  bloqueado: 'Bloqueado',
  atencion: 'Requiere atención',
  listo: 'Listo',
};

/**
 * Same colour-blind-safe ramp as the planner map, so a supervisor moving between the two
 * screens reads the same colours as the same thing.
 */
export const SEVERITY_COLOR: Record<Severity, string> = {
  bloqueado: '#7f1d1d',
  atencion: '#a16207',
  listo: '#3f6212',
};

/**
 * How wrong a crew's dispatch is.
 *
 * Undelivered work outranks everything: a crew that never received an order will not do it
 * today, and no amount of other things being fine changes that. Stale copies and overdue
 * SLAs need attention but the work is at least on a phone.
 */
export function crewSeverity(row: CrewDispatch): Severity {
  if (row.undelivered > 0) return 'bloqueado';
  if (row.stale_on_device > 0 || row.overdue > 0) return 'atencion';
  return 'listo';
}

/** A device with any blocker is blocked; the server decides what a blocker is. */
export function deviceSeverity(row: DeviceReadiness): Severity {
  if (row.blockers.length === 0) return 'listo';
  if (row.status !== 'activo' || row.last_sync_at === null) return 'bloqueado';
  return 'atencion';
}

function bySeverityThen<T>(severity: (row: T) => Severity, key: (row: T) => string) {
  return (a: T, b: T): number => {
    const rank = SEVERITY_ORDER.indexOf(severity(a)) - SEVERITY_ORDER.indexOf(severity(b));
    return rank !== 0 ? rank : key(a).localeCompare(key(b), 'es');
  };
}

/** Worst first, then by crew code. A stable order so the screen does not jump on refresh. */
export function sortCrews(rows: CrewDispatch[]): CrewDispatch[] {
  return [...rows].sort(bySeverityThen(crewSeverity, (row) => row.code));
}

export function sortDevices(rows: DeviceReadiness[]): DeviceReadiness[] {
  return [...rows].sort(bySeverityThen(deviceSeverity, (row) => row.device_key));
}

export interface DispatchSummary {
  crews: number;
  assigned: number;
  delivered: number;
  undelivered: number;
  staleOnDevice: number;
  overdue: number;
  crewsBlocked: number;
  /** The headline: what share of assigned work is actually on a phone. */
  deliveryRate: number;
}

export function summarise(rows: CrewDispatch[]): DispatchSummary {
  const assigned = rows.reduce((total, row) => total + row.assigned, 0);
  const delivered = rows.reduce((total, row) => total + row.delivered, 0);
  return {
    crews: rows.length,
    assigned,
    delivered,
    undelivered: rows.reduce((total, row) => total + row.undelivered, 0),
    staleOnDevice: rows.reduce((total, row) => total + row.stale_on_device, 0),
    overdue: rows.reduce((total, row) => total + row.overdue, 0),
    crewsBlocked: rows.filter((row) => crewSeverity(row) === 'bloqueado').length,
    // Nothing assigned is not a failure to deliver: a unit with no work for a crew is at
    // 100 %, not at 0 %. Reporting 0 there would make the number useless on a quiet day.
    deliveryRate: assigned === 0 ? 1 : delivered / assigned,
  };
}

/**
 * How stale the board itself is, in minutes, or null when a crew has never synced.
 *
 * Shown next to every row because the whole board is a photograph of the last time each
 * phone spoke to the server, and a supervisor reading it as live would trust it too much.
 */
export function minutesSinceSync(row: { last_sync_at: string | null }, now: Date): number | null {
  if (!row.last_sync_at) return null;
  const then = new Date(row.last_sync_at).getTime();
  if (Number.isNaN(then)) return null;
  return Math.max(0, Math.floor((now.getTime() - then) / 60000));
}

/** "hace 4 min", "hace 2 h", "hace 3 d" — or that it never synced. */
export function formatSync(row: { last_sync_at: string | null }, now: Date): string {
  const minutes = minutesSinceSync(row, now);
  if (minutes === null) return 'nunca';
  if (minutes < 1) return 'recién';
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return `hace ${Math.floor(hours / 24)} d`;
}
