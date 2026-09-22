/**
 * Integrations API client (RF-125).
 *
 * The screen this serves answers one question: which corporate exchange is stuck, and why.
 * The retry is a real call and not a hint — a ledger you can read but not act on just tells
 * you about the problem twice a day.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export type Connector = 'sistema_ot' | 'call_center' | 'arcgis';
export type Direction = 'entrada' | 'salida';
export type EventStatus = 'pendiente' | 'entregado' | 'fallido' | 'descartado';

export interface IntegrationEvent {
  id: string;
  connector: Connector;
  direction: Direction;
  kind: string;
  status: EventStatus;
  idempotency_key: string;
  external_ref: string | null;
  work_order_id: string | null;
  attempts: number;
  last_error: string | null;
  next_attempt_at: string | null;
  created_at: string | null;
  delivered_at: string | null;
  /** True when retries are exhausted and it is waiting on a person. */
  needs_attention: boolean;
  payload: Record<string, unknown>;
  response: Record<string, unknown> | null;
}

export interface ConnectorHealth {
  connector: Connector;
  pending: number;
  delivered: number;
  /** The number that matters: pending events retry themselves, failed ones do not. */
  waiting_for_a_person: number;
  abandoned: number;
  last_error: string | null;
  last_exchange_at: string | null;
}

const BASE = '/api/v1/integrations';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: authHeaders(init?.headers ?? {}),
  });
  if (!response.ok) {
    // Un 401 significa que el token dejó de servir; la sesión se entera en un solo sitio.
    if (response.status === 401) notifyExpired();
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // No JSON body; the status line stands.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export function fetchConnectors(
  businessUnit: string,
  signal?: AbortSignal,
): Promise<ConnectorHealth[]> {
  return request<ConnectorHealth[]>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/connectors`,
    { signal },
  );
}

export function fetchEvents(
  businessUnit: string,
  options: { connector?: Connector; status?: EventStatus; limit?: number } = {},
  signal?: AbortSignal,
): Promise<IntegrationEvent[]> {
  const params = new URLSearchParams();
  if (options.connector) params.set('connector', options.connector);
  if (options.status) params.set('status', options.status);
  if (options.limit) params.set('limit', String(options.limit));
  const query = params.toString();
  return request<IntegrationEvent[]>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/events${query ? `?${query}` : ''}`,
    { signal },
  );
}

export function retryEvent(
  businessUnit: string,
  eventId: string,
  requestedBy: string,
): Promise<IntegrationEvent> {
  return request<IntegrationEvent>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/events/${eventId}/retry`,
    { method: 'POST', body: JSON.stringify({ requested_by: requestedBy }) },
  );
}

export function abandonEvent(
  businessUnit: string,
  eventId: string,
  requestedBy: string,
  reason: string,
): Promise<IntegrationEvent> {
  return request<IntegrationEvent>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/events/${eventId}/abandon`,
    { method: 'POST', body: JSON.stringify({ requested_by: requestedBy, reason }) },
  );
}
