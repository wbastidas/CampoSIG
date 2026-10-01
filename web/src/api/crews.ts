/**
 * Crew administration client (RF-005).
 *
 * Create and edit share one call (`saveCrew`, a PUT): the form that fills it in cannot tell which
 * case it is in without asking the server first, and asking first just to ask again is the
 * request this collapses into one.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export interface Crew {
  id: string;
  code: string;
  name: string;
  leader_name: string | null;
  vehicle: string | null;
  competencies: string[];
  members: string[];
  zone: string | null;
  active: boolean;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface CrewPayload {
  code: string;
  name: string;
  leader_name: string | null;
  vehicle: string | null;
  competencies: string[];
  members: string[];
  zone: string | null;
}

export interface CrewHistoryEntry {
  sequence: number;
  kind: string;
  actor: string;
  occurred_at: string | null;
  payload: Record<string, unknown>;
  reason: string | null;
}

const BASE = '/api/v1/crews';

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

export function fetchCrews(
  businessUnit: string,
  options: { includeInactive?: boolean } = {},
  signal?: AbortSignal,
): Promise<Crew[]> {
  const query = options.includeInactive ? '?include_inactive=true' : '';
  return call<Crew[]>(`${BASE}/units/${encodeURIComponent(businessUnit)}${query}`, { signal });
}

export function saveCrew(businessUnit: string, payload: CrewPayload): Promise<Crew> {
  return call<Crew>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(payload.code)}`,
    { method: 'PUT', body: JSON.stringify(payload) },
  );
}

export function setCrewActive(businessUnit: string, code: string, active: boolean): Promise<Crew> {
  return call<Crew>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(code)}/active`,
    { method: 'POST', body: JSON.stringify({ active }) },
  );
}

export function fetchCrewHistory(
  businessUnit: string,
  code: string,
  signal?: AbortSignal,
): Promise<CrewHistoryEntry[]> {
  return call<CrewHistoryEntry[]>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(code)}/history`,
    { signal },
  );
}
