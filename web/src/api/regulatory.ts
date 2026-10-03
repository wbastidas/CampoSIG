/**
 * Regulatory parameter client (RF-150, ADR-007).
 *
 * The endpoints are not scoped to a business unit: the limits a regulator publishes are national
 * (ADR-009 keeps nothing corporate inside a unit's data). So nothing here takes a unit, which is
 * itself the thing worth noticing when reading this file next to the others.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export interface Parameter {
  code: string;
  /** Stored as an object so JSONB querying is uniform; `{v: 24}` for a scalar. */
  value: Record<string, unknown>;
  unit: string | null;
  description: string | null;
  norm_ref: string;
  article_ref: string | null;
  source_url: string | null;
  effective_from: string;
  effective_to: string | null;
  /** True only when a person stated they read the official text (ADR-007). */
  verified: boolean;
  verified_by: string | null;
  verified_at: string | null;
  strict: boolean;
  created_by: string | null;
  updated_by: string | null;
  updated_at: string | null;
}

export interface ParameterIndex {
  loaded: string[];
  required_by_rules: string[];
  /** Codes a rule needs and nobody loaded. The list a deployment checklist has to empty. */
  missing: string[];
  /** In force but unverified against the official text. The other list to empty. */
  unverified: string[];
}

export interface Revision {
  at: string;
  action: string;
  actor: string;
  /** {field: {from, to}}. Empty for a creation, where everything is new. */
  changed: Record<string, { from: unknown; to: unknown }>;
  note: string | null;
}

const BASE = '/api/v1/regulatory';

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

export function fetchIndex(signal?: AbortSignal): Promise<ParameterIndex> {
  return call<ParameterIndex>(`${BASE}/parameters`, { signal });
}

export function fetchHistory(code: string, signal?: AbortSignal): Promise<Parameter[]> {
  return call<Parameter[]>(`${BASE}/parameters/${encodeURIComponent(code)}`, { signal });
}

export function fetchRevisions(code: string, signal?: AbortSignal): Promise<Revision[]> {
  return call<Revision[]>(`${BASE}/parameters/${encodeURIComponent(code)}/revisions`, { signal });
}

/**
 * Record that a person read the official text and the value matches.
 *
 * No author parameter: the server signs it with the token's subject. A verification the browser
 * could fill in would be a verification nobody made.
 */
export function verifyParameter(
  code: string,
  effectiveFrom: string,
  note?: string,
): Promise<Parameter> {
  return call<Parameter>(`${BASE}/parameters/${encodeURIComponent(code)}/verify`, {
    method: 'POST',
    body: JSON.stringify({ effective_from: effectiveFrom, note: note ?? null }),
  });
}
