/**
 * Catalogue client (RF-034).
 *
 * The device's delta endpoint is not used from here — a browser has nothing to sync — so this
 * covers the two things a screen needs: the index with one version per catalogue, and the resolved
 * list for one business unit.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export interface CatalogSummary {
  code: string;
  title: string;
  /** 'manual' or 'integracion': who owns the values. */
  source: string;
  version: number;
  /** Why it is empty, when it is. The server's words. */
  note: string | null;
  active_entries: number;
  retired_entries: number;
  empty: boolean;
}

export interface CatalogIndex {
  catalogs: CatalogSummary[];
  /** Codes served by the unit's synced GIS metadata, not by this table (RF-304). */
  gis_backed: string[];
}

export interface CatalogEntryView {
  code: string;
  label: string;
  synonyms: string[];
  parent_code: string | null;
  attributes: Record<string, unknown>;
  /** True when the value is this unit's rather than the national list's. */
  local: boolean;
}

export interface ResolvedCatalog {
  code: string;
  title: string;
  source: string;
  version: number;
  note: string | null;
  empty: boolean;
  entries: CatalogEntryView[];
}

const BASE = '/api/v1/catalogs';

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

export function fetchIndex(signal?: AbortSignal): Promise<CatalogIndex> {
  return call<CatalogIndex>(`${BASE}/`, { signal });
}

export function fetchResolved(
  businessUnit: string,
  code: string,
  signal?: AbortSignal,
): Promise<ResolvedCatalog> {
  return call<ResolvedCatalog>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/catalog/${encodeURIComponent(code)}`,
    { signal },
  );
}

export interface EntryPayload {
  code: string;
  label: string;
  synonyms?: string[];
  parent_code?: string | null;
  attributes?: Record<string, unknown>;
  sort_order?: number;
  active?: boolean;
}

/** Write a national value. The author is the token's subject. */
export function saveNationalEntry(code: string, entry: EntryPayload): Promise<unknown> {
  return call(
    `${BASE}/catalog/${encodeURIComponent(code)}/entries/${encodeURIComponent(entry.code)}`,
    { method: 'PUT', body: JSON.stringify(entry) },
  );
}

/** Write a value only this unit sees. A national code it repeats is overridden, not duplicated. */
export function saveLocalEntry(
  businessUnit: string,
  code: string,
  entry: EntryPayload,
): Promise<unknown> {
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/catalog/${encodeURIComponent(code)}/entries/${encodeURIComponent(entry.code)}`,
    { method: 'PUT', body: JSON.stringify(entry) },
  );
}

/** Deactivates; there is no delete. The tombstone has to reach the device. */
export function retireEntry(code: string, entryCode: string): Promise<unknown> {
  return call(
    `${BASE}/catalog/${encodeURIComponent(code)}/entries/${encodeURIComponent(entryCode)}`,
    { method: 'DELETE' },
  );
}
