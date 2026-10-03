/**
 * Consignaciones: what is de-energised, when, and by whose authority (RF-024).
 *
 * Two roles and two calls, on purpose: the planner asks, the Centro de Control grants. Neither the
 * requester nor the decider can be named in a payload — both come from the token, because a descargo
 * somebody gave themselves is what the procedure exists to prevent.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export type OutageStateValue = 'solicitada' | 'aprobada' | 'rechazada' | 'vencida' | 'devuelta';

export interface OutageRequestRow {
  id: string;
  /** The authority. Null until the Centro de Control grants it. */
  number: string | null;
  state: OutageStateValue;
  equipment: string;
  feeder_code: string | null;
  substation_code: string | null;
  window_start: string;
  window_end: string;
  requested_by: string;
  decided_by: string | null;
  decided_at: string | null;
  returned_at: string | null;
  returned_by: string | null;
  note: string | null;
  /** Whether the permit form F-TR-02 opens. Needs the state *and* the number. */
  grants_permit: boolean;
  orders?: number;
  /** Granted with no work order under it: a line de-energised for nothing. */
  unused?: boolean;
}

export interface OutageWorkOrder {
  work_order_id: string;
  code: string | null;
  work_type: string;
  state: string;
  form_code: string;
}

export interface OutageDetail extends OutageRequestRow {
  work_orders: OutageWorkOrder[];
}

export interface OutageList {
  /** State → how many. What is waiting on the Centro de Control, said out loud. */
  counts: Record<string, number>;
  requests: OutageRequestRow[];
}

export interface OutagePayload {
  equipment: string;
  window_start: string;
  window_end: string;
  feeder_code?: string | null;
  substation_code?: string | null;
  note?: string | null;
}

const BASE = '/api/v1/outages';

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...authHeaders(),
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    if (response.status === 401) notifyExpired();
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      // No JSON body; the status line stands.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export function fetchOutages(
  businessUnit: string,
  state?: OutageStateValue,
  signal?: AbortSignal,
): Promise<OutageList> {
  const params = state ? `?state=${encodeURIComponent(state)}` : '';
  return call(`${BASE}/units/${encodeURIComponent(businessUnit)}${params}`, { signal });
}

export function fetchOutage(
  businessUnit: string,
  requestId: string,
  signal?: AbortSignal,
): Promise<OutageDetail> {
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(requestId)}`,
    { signal },
  );
}

/** The requester is the token's subject; the payload cannot name one. */
export function requestOutage(
  businessUnit: string,
  payload: OutagePayload,
): Promise<OutageRequestRow> {
  return call(`${BASE}/units/${encodeURIComponent(businessUnit)}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/** The number is required by the server: a granted row without one opens nothing. */
export function approveOutage(
  businessUnit: string,
  requestId: string,
  number: string,
  note?: string,
): Promise<OutageRequestRow> {
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(requestId)}/approve`,
    { method: 'POST', body: JSON.stringify({ number, note }) },
  );
}

/** The reason is required: «no» without one sends the planner to the phone. */
export function rejectOutage(
  businessUnit: string,
  requestId: string,
  note: string,
): Promise<OutageRequestRow> {
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(requestId)}/reject`,
    { method: 'POST', body: JSON.stringify({ note }) },
  );
}

/** Handed back by whoever received it, so the equipment can be re-energised. */
export function handBackOutage(businessUnit: string, requestId: string): Promise<OutageRequestRow> {
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(requestId)}/return`,
    { method: 'POST', body: '{}' },
  );
}
