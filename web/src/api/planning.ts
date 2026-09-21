/**
 * Planner API client.
 *
 * Every call carries the business unit: one platform instance serves the holding company
 * and all of its business units, and nothing crosses between them (ADR-009). A call without
 * a unit would be a bug, so the unit is a required argument rather than ambient state.
 */

export type WorkOrderState =
  | 'borrador' | 'planificada' | 'asignada' | 'descargada' | 'en_camino' | 'en_sitio'
  | 'en_ejecucion' | 'suspendida' | 'cerrada_campo' | 'sincronizada' | 'en_revision'
  | 'devuelta' | 'aprobada' | 'cerrada' | 'anulada';

export type Priority = 'baja' | 'media' | 'alta' | 'critica';

export interface WorkOrderProperties {
  code: string | null;
  work_type: string;
  form_code: string;
  state: WorkOrderState;
  priority: Priority;
  assigned: boolean;
  crew_id: string | null;
  asset_code: string | null;
  feeder_code: string | null;
  sla_due_at: string | null;
  /** Optimistic-lock version, sent back on assignment so concurrent planners collide
   *  loudly instead of silently overwriting each other (RF-311). */
  version: number;
}

export interface WorkOrderFeature {
  type: 'Feature';
  id: string;
  geometry: { type: 'Point'; coordinates: [number, number] };
  properties: WorkOrderProperties;
}

export interface WorkOrderCollection {
  type: 'FeatureCollection';
  features: WorkOrderFeature[];
  /** True when the server capped the result. Surfaced so the planner knows the map is
   *  incomplete rather than believing they see everything. */
  truncated: boolean;
}

export interface Crew {
  crew_id: string;
  code: string;
  name: string;
  open_work_orders: number;
}

export interface BoundingBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface AssignSelectionResult {
  assigned: string[];
  /** Partial success is normal: one refused pin must not lose the planner the others. */
  failures: { work_order_id: string; message: string }[];
}

const BASE = '/api/v1/planning';

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    // Prefer the server's message: it is written for the planner, in Spanish, and says
    // what to do — "recargue antes de reasignar" is more useful than "409 Conflict".
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Response had no JSON body; the status line stands.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export function fetchWorkOrders(
  businessUnit: string,
  bounds: BoundingBox,
  options: { unassignedOnly?: boolean; states?: WorkOrderState[] } = {},
  signal?: AbortSignal,
): Promise<WorkOrderCollection> {
  const params = new URLSearchParams({
    business_unit: businessUnit,
    west: String(bounds.west),
    south: String(bounds.south),
    east: String(bounds.east),
    north: String(bounds.north),
  });
  if (options.unassignedOnly) params.set('unassigned_only', 'true');
  for (const state of options.states ?? []) params.append('states', state);
  return request<WorkOrderCollection>(`${BASE}/work-orders.geojson?${params}`, { signal });
}

export function fetchCrews(businessUnit: string, signal?: AbortSignal): Promise<Crew[]> {
  const params = new URLSearchParams({ business_unit: businessUnit });
  return request<Crew[]>(`${BASE}/crews?${params}`, { signal });
}

export function assignSelection(
  businessUnit: string,
  workOrderIds: string[],
  crewId: string,
  reason?: string,
): Promise<AssignSelectionResult> {
  const params = new URLSearchParams({ business_unit: businessUnit });
  return request<AssignSelectionResult>(`${BASE}/assign-selection?${params}`, {
    method: 'POST',
    body: JSON.stringify({ work_order_ids: workOrderIds, crew_id: crewId, reason }),
  });
}
