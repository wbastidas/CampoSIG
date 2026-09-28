/**
 * Rutas sugeridas para un conjunto de OT (RF-025).
 *
 * Una sugerencia, no una asignación: el planificador selecciona OT en el mapa, pide el orden y
 * decide si lo sigue. Nada aquí escribe en ninguna OT.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export interface RouteStop {
  work_order_id: string;
  code: string | null;
  longitude: number;
  latitude: number;
  /** Metros desde la parada anterior, o desde el punto de partida si lo hay. */
  leg_distance_m: number;
}

export interface RouteSuggestion {
  stops: RouteStop[];
  total_distance_m: number;
  /** La distancia del orden en que se pidieron las OT: el punto de comparación del criterio. */
  naive_distance_m: number;
  start: { longitude: number; latitude: number } | null;
  caveats: string[];
}

export interface RouteRequest {
  work_order_ids: string[];
  start_latitude?: number;
  start_longitude?: number;
  /** Toma la última posición reportada por este dispositivo como inicio (RF-020). */
  start_device_key?: string;
}

const BASE = '/api/v1/routing';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: authHeaders({ 'Content-Type': 'application/json', ...(init?.headers ?? {}) }),
  });
  if (!response.ok) {
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

export function suggestRoute(
  businessUnit: string,
  payload: RouteRequest,
  signal?: AbortSignal,
): Promise<RouteSuggestion> {
  return request(`${BASE}/units/${encodeURIComponent(businessUnit)}/suggest`, {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  });
}
