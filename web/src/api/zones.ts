/**
 * Zones client (RF-152).
 *
 * The read endpoints speak GeoJSON, so the types here are GeoJSON types and not a flattened
 * shape of our own. That is what lets the same document round-trip: the operator exports it,
 * corrects it in their desktop GIS and imports it back.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export interface ZoneProperties {
  code: string;
  name: string;
  description: string | null;
  origin: string;
  active: boolean;
  updated_by: string | null;
  updated_at: string | null;
}

export interface ZoneFeature {
  type: 'Feature';
  geometry: { type: string; coordinates: unknown };
  properties: ZoneProperties;
}

export interface ZoneCollection {
  type: 'FeatureCollection';
  features: ZoneFeature[];
}

/** Every count carries its own meaning; see the server's `Coverage`. */
export interface ZoneCoverage {
  open_orders: number;
  inside_one: number;
  ambiguous: number;
  outside: number;
  without_location: number;
  /** Null when nothing is locatable — not zero. */
  covered_share: number | null;
}

export interface ZoneOverlap {
  left: string;
  right: string;
  area_m2: number;
  /** The server's own sentence, shown unparaphrased. */
  text: string;
}

export interface CoverageReport {
  coverage: ZoneCoverage;
  overlaps: ZoneOverlap[];
}

export interface ImportRejection {
  index: number;
  code: string | null;
  reason: string;
}

export interface ImportReport {
  created: string[];
  updated: string[];
  accepted: number;
  rejected: ImportRejection[];
}

export interface BackfillReport {
  dry_run: boolean;
  filled: Record<string, string>;
  ambiguous: Record<string, string[]>;
  outside: string[];
}

const BASE = '/api/v1/zones';

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

export function fetchZones(
  businessUnit: string,
  options: { includeInactive?: boolean } = {},
  signal?: AbortSignal,
): Promise<ZoneCollection> {
  const query = options.includeInactive ? '?include_inactive=true' : '';
  return call<ZoneCollection>(`${BASE}/units/${encodeURIComponent(businessUnit)}${query}`, {
    signal,
  });
}

export function fetchCoverage(businessUnit: string, signal?: AbortSignal): Promise<CoverageReport> {
  return call<CoverageReport>(`${BASE}/units/${encodeURIComponent(businessUnit)}/coverage`, {
    signal,
  });
}

export function importZones(
  businessUnit: string,
  document: unknown,
  options: { codeProperty?: string; replaceExisting?: boolean } = {},
): Promise<ImportReport> {
  return call<ImportReport>(`${BASE}/units/${encodeURIComponent(businessUnit)}/import`, {
    method: 'POST',
    body: JSON.stringify({
      document,
      code_property: options.codeProperty ?? null,
      replace_existing: options.replaceExisting ?? true,
    }),
  });
}

export function setZoneActive(
  businessUnit: string,
  code: string,
  active: boolean,
): Promise<ZoneFeature> {
  return call<ZoneFeature>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(code)}/active`,
    { method: 'POST', body: JSON.stringify({ active }) },
  );
}

export function backfillZones(
  businessUnit: string,
  options: { dryRun?: boolean } = {},
): Promise<BackfillReport> {
  const query = options.dryRun ? '?dry_run=true' : '';
  return call<BackfillReport>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/backfill${query}`,
    { method: 'POST' },
  );
}
