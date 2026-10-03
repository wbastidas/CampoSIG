/**
 * Audit trail client (RF-160, RF-161).
 *
 * Read-only, and that is the contract rather than an omission: the trail has no endpoint that
 * edits or deletes it, so there is nothing here that could call one.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export interface AuditEvent {
  sequence: number;
  kind: string;
  subject_type: string;
  subject_id: string;
  work_order_id: string | null;
  asset_code: string | null;
  actor_kind: string;
  actor: string;
  device_key: string | null;
  payload: Record<string, unknown>;
  reason: string | null;
  occurred_at: string | null;
  hash: string;
  prev_hash: string;
}

/** What the chain verification found. `intact: false` is an answer, not an error. */
export interface ChainCheck {
  events: number;
  intact: boolean;
  broken_at: number | null;
  problem: string | null;
}

export interface TrailFilters {
  workOrderId?: string;
  assetCode?: string;
  actor?: string;
  deviceKey?: string;
  limit?: number;
  offset?: number;
}

const BASE = '/api/v1/audit';

async function read<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { headers: authHeaders(), signal });
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

export function fetchTrail(
  businessUnit: string,
  filters: TrailFilters = {},
  signal?: AbortSignal,
): Promise<{ total: number; events: AuditEvent[] }> {
  const params = new URLSearchParams();
  if (filters.workOrderId) params.set('work_order_id', filters.workOrderId);
  if (filters.assetCode) params.set('asset_code', filters.assetCode);
  if (filters.actor) params.set('actor', filters.actor);
  if (filters.deviceKey) params.set('device_key', filters.deviceKey);
  if (filters.limit) params.set('limit', String(filters.limit));
  if (filters.offset) params.set('offset', String(filters.offset));
  const query = params.toString();
  return read(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/trail${query ? `?${query}` : ''}`,
    signal,
  );
}

export function verifyChain(businessUnit: string, signal?: AbortSignal): Promise<ChainCheck> {
  return read(`${BASE}/units/${encodeURIComponent(businessUnit)}/verify`, signal);
}
