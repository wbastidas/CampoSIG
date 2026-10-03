/**
 * Capture policy client (RF-151).
 *
 * Two shapes, because the screen asks two different questions. `rows` is what somebody set; the
 * effective view is what a phone will actually obey. Only the second answers «why is the north
 * still taking one photograph», and it answers it by naming the origin of every value.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

/** Field → value, as stored. Null means «no opinion», which is inherited, not false. */
export type PolicyValues = Record<string, string | number | boolean | null>;

export interface PolicyRow {
  /** Null for the unit's own row. */
  zone_code: string | null;
  values: PolicyValues;
  note: string | null;
  updated_by: string | null;
  updated_at: string | null;
}

export interface PolicyList {
  fields: string[];
  defaults: PolicyValues;
  rows: PolicyRow[];
}

export interface EffectiveValue {
  value: string | number | boolean | null;
  /** «zona», «unidad» or «por omisión de la plataforma», in the server's words. */
  source: string;
}

export interface EffectivePolicy {
  business_unit: string;
  zone_code: string | null;
  values: Record<string, EffectiveValue>;
}

const BASE = '/api/v1/policies';

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

export function fetchPolicies(businessUnit: string, signal?: AbortSignal): Promise<PolicyList> {
  return call<PolicyList>(`${BASE}/units/${encodeURIComponent(businessUnit)}`, { signal });
}

export function fetchEffective(
  businessUnit: string,
  zone?: string,
  signal?: AbortSignal,
): Promise<EffectivePolicy> {
  const query = zone ? `?zone=${encodeURIComponent(zone)}` : '';
  return call<EffectivePolicy>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/effective${query}`,
    { signal },
  );
}

/**
 * Save only what changed.
 *
 * `changes` is sent verbatim: a key with `null` clears that field, and a key that is absent leaves
 * it alone. Sending the whole form would turn «I did not touch this» into «set this to null».
 */
export function savePolicy(
  businessUnit: string,
  changes: PolicyValues,
  zone?: string,
): Promise<PolicyRow> {
  const scope = zone
    ? `${BASE}/units/${encodeURIComponent(businessUnit)}/zones/${encodeURIComponent(zone)}`
    : `${BASE}/units/${encodeURIComponent(businessUnit)}`;
  return call<PolicyRow>(scope, { method: 'PUT', body: JSON.stringify(changes) });
}

export function clearZonePolicy(
  businessUnit: string,
  zone: string,
): Promise<{ zone_code: string; removed: boolean }> {
  return call<{ zone_code: string; removed: boolean }>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/zones/${encodeURIComponent(zone)}`,
    { method: 'DELETE' },
  );
}
