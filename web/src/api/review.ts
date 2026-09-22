/**
 * Review API client (M11, RF-110 to RF-112, RF-342).
 *
 * The detail comes back assembled in one call, deliberately. A screen that had to make six
 * calls and combine them is a screen where one failed call silently removes a blocker from
 * view — and the blockers are the whole point of this screen.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export type DecisionKind = 'aprobada' | 'devuelta' | 'anulada';

export interface QueueItem {
  work_order_id: string;
  code: string | null;
  work_type: string;
  form_code: string;
  state: string;
  priority: string;
  asset_code: string | null;
  crew_id: string | null;
  sla_due_at: string | null;
  updated_at: string | null;
}

export interface Provenance {
  field_key: string;
  origin: string;
  proposed_value: unknown;
  final_value: unknown;
  confidence: number | null;
  model_name: string | null;
  model_version: string | null;
  accepted_unchanged: boolean;
  confirmed_by: string | null;
  /** The transcript span, or the evidence and crop, the proposal came from. */
  source: string | null;
  is_ai: boolean;
}

export interface Evidence {
  evidence_id: string;
  kind: string;
  stage: string;
  storage_key: string;
  content_hash: string;
  integrity_verified: boolean;
  vision_result: Record<string, unknown> | null;
}

export interface ComplianceFinding {
  rule: string;
  outcome: 'cumple' | 'incumple' | 'no_aplica' | 'no_determinable';
  message: string;
  severity: 'low' | 'medium' | 'high';
  measured: number | null;
  limit: unknown;
  unit: string | null;
  norm_ref: string | null;
  article_ref: string | null;
  /** False when the limit has not been checked against the official text (ADR-007). */
  limit_verified: boolean;
  parameter_code: string | null;
  evaluated_on: string | null;
  blocking: boolean;
}

/**
 * Something the AI layer will not do on this deployment, and why (RF-204).
 *
 * Shown rather than left as a missing section: a report with a gap looks complete, which is worse
 * than no report. `placement` distinguishes the two answers that matter to a supervisor — work
 * that waits for tonight from work that is not coming at all.
 */
export interface Degradation {
  alias: string;
  purpose: string;
  placement: 'night_batch' | 'unavailable' | 'interactive';
  reason: string;
}

export interface ReviewDetail {
  work_order: {
    work_order_id: string;
    code: string | null;
    work_type: string;
    state: string;
    priority: string;
    asset_type_key: string | null;
    asset_code: string | null;
    feeder_code: string | null;
    zone: string | null;
    external_ref: string | null;
  };
  form: {
    code: string;
    version: string;
    title: string;
    schema: Record<string, unknown>;
    ui_schema: Record<string, unknown>;
    /** Conditional rules, so the form view can mark what the answers still owe (I5). */
    rules: unknown[];
    warnings: string[];
  };
  response: {
    response_id: string;
    state: string;
    answers: Record<string, unknown>;
    captured_by: string | null;
    captured_at: string | null;
    submitted_at: string | null;
  } | null;
  provenance: Provenance[];
  evidence: Evidence[];
  photo_counts: Record<string, number>;
  missing_photos: string[];
  compliance: ComplianceFinding[];
  blockers: string[];
  degradations: Degradation[];
  observations: { field_key: string; message: string; suggested_value: unknown }[];
  history: {
    decision: string;
    reviewer_sub: string;
    note: string | null;
    decided_at: string | null;
    blind_sample: boolean | null;
  }[];
}

export interface GisTray {
  proposals: {
    proposal_id: string;
    work_order_id: string | null;
    asset_type_key: string;
    action: string;
    status: string;
    requires_arcfm: boolean;
    created_at: string | null;
  }[];
  batches: {
    batch_id: string;
    status: string;
    created_at: string | null;
    completed_at: string | null;
    results: number;
  }[];
}

/** Thrown on 422: approval refused, with the reasons the server listed. */
export class ApprovalBlocked extends Error {
  constructor(readonly blockers: string[]) {
    super(blockers.join('; '));
    this.name = 'ApprovalBlocked';
  }
}

const BASE = '/api/v1/review';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: authHeaders(init?.headers ?? {}),
  });
  if (!response.ok) {
    // Un 401 significa que el token dejó de servir; la sesión se entera en un solo sitio.
    if (response.status === 401) notifyExpired();
    let detail: unknown = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (body.detail) detail = body.detail;
    } catch {
      // No JSON body; the status line stands.
    }
    // The blocker list travels as structured detail, so the screen can render it as a list
    // rather than as one long sentence a supervisor has to parse.
    if (
      response.status === 422 &&
      typeof detail === 'object' &&
      detail !== null &&
      Array.isArray((detail as { blockers?: unknown }).blockers)
    ) {
      throw new ApprovalBlocked((detail as { blockers: string[] }).blockers);
    }
    throw new ApiError(response.status, typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return (await response.json()) as T;
}

export function fetchQueue(
  businessUnit: string,
  options: { area?: string; crewId?: string; limit?: number; offset?: number } = {},
  signal?: AbortSignal,
): Promise<{ total: number; items: QueueItem[] }> {
  const params = new URLSearchParams();
  if (options.area) params.set('area', options.area);
  if (options.crewId) params.set('crew_id', options.crewId);
  if (options.limit) params.set('limit', String(options.limit));
  if (options.offset) params.set('offset', String(options.offset));
  const query = params.toString();
  return request(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/queue${query ? `?${query}` : ''}`,
    { signal },
  );
}

export function fetchDetail(
  businessUnit: string,
  workOrderId: string,
  signal?: AbortSignal,
): Promise<ReviewDetail> {
  return request<ReviewDetail>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/work-orders/${workOrderId}`,
    { signal },
  );
}

export function submitDecision(
  businessUnit: string,
  workOrderId: string,
  body: {
    decision: DecisionKind;
    // No `reviewer_sub`: quien decide sale del token, y el servidor lo descarta si viaja aquí
    // (ADR-013). Mandarlo igual sería un campo que parece autoritativo y no lo es.
    note?: string;
    observations?: { field_key: string; message: string; suggested_value?: unknown }[];
    blind_sample?: boolean;
  },
): Promise<{ decision: string; decided_at: string | null; work_order_state: string }> {
  return request(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/work-orders/${workOrderId}/decision`,
    { method: 'POST', body: JSON.stringify(body) },
  );
}

export function fetchGisTray(businessUnit: string, signal?: AbortSignal): Promise<GisTray> {
  return request<GisTray>(`${BASE}/units/${encodeURIComponent(businessUnit)}/gis-tray`, {
    signal,
  });
}

/**
 * Issue the acta of a work order and hand back the PDF with its verification code (RF-115).
 *
 * Returned as a blob rather than a URL to navigate to: the request carries the bearer token, and
 * a plain `<a href>` would not. The code and hash come back in headers so the screen can name
 * the document it just produced without parsing the PDF.
 */
export async function issueActa(
  businessUnit: string,
  workOrderId: string,
): Promise<{ blob: Blob; verificationCode: string; contentHash: string }> {
  const response = await fetch(
    `/api/v1/reports/units/${encodeURIComponent(businessUnit)}/work-orders/${workOrderId}/acta`,
    { method: 'POST', headers: authHeaders() },
  );
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
  return {
    blob: await response.blob(),
    verificationCode: response.headers.get('X-SIGEC-Verification-Code') ?? '',
    contentHash: response.headers.get('X-SIGEC-Document-Hash') ?? '',
  };
}
