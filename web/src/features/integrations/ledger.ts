/**
 * Integrations screen logic, as pure functions (RF-125).
 *
 * The judgements live here for the same reason as on the dispatch board: what counts as
 * needing a person, and what order the rows go in, is the substance of the screen, and it
 * deserves tests that run without a browser.
 *
 * One rule is worth stating because it is easy to get backwards: **a pending event is not a
 * problem.** It retries itself. A failed one has given up, and nothing will happen to it
 * until somebody presses retry. So "failed" outranks "lots of pending" every time.
 */

import type { ConnectorHealth, EventStatus, IntegrationEvent } from '../../api/integrations';

export type Health = 'roto' | 'atencion' | 'sano';

export const HEALTH_ORDER: Health[] = ['roto', 'atencion', 'sano'];

export const HEALTH_LABEL: Record<Health, string> = {
  roto: 'Requiere intervención',
  atencion: 'Con reintentos en curso',
  sano: 'Al día',
};

/** Same colour-blind-safe ramp as the planner map and the dispatch board. */
export const HEALTH_COLOR: Record<Health, string> = {
  roto: '#7f1d1d',
  atencion: '#a16207',
  sano: '#3f6212',
};

export const STATUS_LABEL: Record<EventStatus, string> = {
  pendiente: 'Pendiente',
  entregado: 'Entregado',
  fallido: 'Fallido',
  descartado: 'Descartado',
};

/**
 * How a connector is doing.
 *
 * Anything waiting on a person is broken, however small the number: one unclosed claim is a
 * customer whose complaint is still open. Pending events are the system working.
 */
export function connectorHealth(row: ConnectorHealth): Health {
  if (row.waiting_for_a_person > 0) return 'roto';
  if (row.pending > 0) return 'atencion';
  return 'sano';
}

export function sortConnectors(rows: ConnectorHealth[]): ConnectorHealth[] {
  return [...rows].sort((a, b) => {
    const rank =
      HEALTH_ORDER.indexOf(connectorHealth(a)) - HEALTH_ORDER.indexOf(connectorHealth(b));
    return rank !== 0 ? rank : a.connector.localeCompare(b.connector, 'es');
  });
}

/** Whether the retry button should do anything for this row. */
export function canRetry(event: IntegrationEvent): boolean {
  return event.status === 'fallido' || event.status === 'descartado';
}

/**
 * Failed first, then pending, then everything else; newest first inside each group.
 *
 * Newest-first inside a group and not oldest-first on purpose: when a connector breaks, forty
 * rows fail within a minute and the most recent one carries the error worth reading.
 */
export function sortEvents(rows: IntegrationEvent[]): IntegrationEvent[] {
  const rank: Record<EventStatus, number> = {
    fallido: 0,
    pendiente: 1,
    descartado: 2,
    entregado: 3,
  };
  return [...rows].sort((a, b) => {
    const byStatus = rank[a.status] - rank[b.status];
    if (byStatus !== 0) return byStatus;
    return (b.created_at ?? '').localeCompare(a.created_at ?? '');
  });
}

export interface LedgerSummary {
  total: number;
  waitingForAPerson: number;
  pending: number;
  delivered: number;
  abandoned: number;
  connectorsBroken: number;
}

export function summarise(
  connectors: ConnectorHealth[],
  events: IntegrationEvent[],
): LedgerSummary {
  return {
    total: events.length,
    waitingForAPerson: events.filter((event) => event.status === 'fallido').length,
    pending: events.filter((event) => event.status === 'pendiente').length,
    delivered: events.filter((event) => event.status === 'entregado').length,
    abandoned: events.filter((event) => event.status === 'descartado').length,
    connectorsBroken: connectors.filter((row) => connectorHealth(row) === 'roto').length,
  };
}

/**
 * The error, trimmed for a table cell without hiding which error it was.
 *
 * The first line, because a stack trace's first line is the part that identifies it, and the
 * full text stays available on the row's detail.
 */
export function shortError(event: IntegrationEvent, max = 120): string | null {
  if (!event.last_error) return null;
  const firstLine = (event.last_error.split('\n')[0] ?? event.last_error).trim();
  return firstLine.length <= max ? firstLine : `${firstLine.slice(0, max - 1)}…`;
}

/** "en 4 min", "ahora", or null when nothing is scheduled. */
export function nextAttemptIn(event: IntegrationEvent, now: Date): string | null {
  if (!event.next_attempt_at) return null;
  const due = new Date(event.next_attempt_at).getTime();
  if (Number.isNaN(due)) return null;
  const minutes = Math.round((due - now.getTime()) / 60000);
  if (minutes <= 0) return 'ahora';
  if (minutes < 60) return `en ${minutes} min`;
  return `en ${Math.round(minutes / 60)} h`;
}
