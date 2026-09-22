/**
 * Dispatch API client: what the crews were sent, and whether they have it.
 *
 * Like the planner client, every call carries the business unit (ADR-009). The dispatch
 * board is the screen a supervisor watches before the crews leave, so it answers the one
 * question the planning board cannot: assignment is an intention, delivery is a fact.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export interface CrewDispatch {
  crew_id: string;
  code: string;
  name: string;
  zone: string | null;
  assigned: number;
  delivered: number;
  /** Assigned work no device has received. The number that ruins a morning. */
  undelivered: number;
  /** Delivered, but the planner edited the order since: the crew holds an old copy. */
  stale_on_device: number;
  in_progress: number;
  returned: number;
  overdue: number;
  devices: string[];
  last_sync_at: string | null;
}

export interface DeviceReadiness {
  device_key: string;
  user_sub: string | null;
  status: string;
  app_version: string | null;
  model_package_version: string | null;
  last_sync_at: string | null;
  held_orders: number;
  stale_orders: number;
  pending_uploads: number;
  package_zone: string | null;
  package_version: number | null;
  package_current: boolean;
  /** Written by the server, in Spanish, for the dispatcher. Rendered verbatim. */
  blockers: string[];
}

export interface OfflinePackage {
  zone: string;
  version: number;
  content_hash: string;
  built_at: string;
  manifest: Record<string, unknown>;
}

const BASE = '/api/v1/dispatch';

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

export function fetchDispatchBoard(
  businessUnit: string,
  signal?: AbortSignal,
): Promise<CrewDispatch[]> {
  return request<CrewDispatch[]>(`${BASE}/units/${encodeURIComponent(businessUnit)}/board`, {
    signal,
  });
}

export function fetchDeviceReadiness(
  businessUnit: string,
  signal?: AbortSignal,
): Promise<DeviceReadiness[]> {
  return request<DeviceReadiness[]>(`${BASE}/units/${encodeURIComponent(businessUnit)}/devices`, {
    signal,
  });
}

export function publishPackage(
  businessUnit: string,
  zone: string,
  tileUrl: string,
  assetCount: number,
  modelPackageVersion?: string,
): Promise<OfflinePackage> {
  return request<OfflinePackage>(`${BASE}/units/${encodeURIComponent(businessUnit)}/packages`, {
    method: 'POST',
    body: JSON.stringify({
      zone,
      tile_url: tileUrl,
      asset_count: assetCount,
      model_package_version: modelPackageVersion,
    }),
  });
}
