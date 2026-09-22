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
  /** State of the last pre-review run, or null when none ran (RF-170). */
  pre_review_state: string | null;
  /** Risk the pre-review assigned, or null when there is no report. Null is not 'low'. */
  risk_level: 'low' | 'medium' | 'high' | null;
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

/** One finding of the pre-review report (Annex D, RF-175). */
export interface AgentObservation {
  id: string;
  category: 'coherence' | 'regulatory' | 'catalog' | 'evidence' | 'anomaly' | 'safety';
  severity: 'low' | 'medium' | 'high';
  message: string;
  evidence: {
    type: 'transcript' | 'field' | 'photo' | 'computed';
    span: [number, number] | null;
    json_path: string | null;
    evidence_id: string | null;
    detail: string | null;
  }[];
  source: { document: string; version: string | null; section: string | null; verified: boolean } | null;
  suggested_action: string | null;
  confidence: number | null;
  node: string | null;
}

export interface AgentReport {
  work_order_id: string;
  graph_version: string;
  hardware_profile: string;
  risk_level: 'low' | 'medium' | 'high';
  status: 'complete' | 'partial' | 'failed';
  summary: string;
  observations: AgentObservation[];
  models: Record<string, string>;
  budget: { llm_calls: number; tokens: number; duration_s: number };
  /** Nodes that did not run, with the reason (RF-204). */
  skipped: string[];
  /** Observations the guardrail refused. Zero is the expected value. */
  discarded: number;
}

/**
 * The report and the state of the run that produced it.
 *
 * The run state travels because "there is no report" has two very different meanings — it failed, or
 * it has not run — and a supervisor deciding without one should know which.
 */
export interface AgentReportEnvelope {
  run_state: string | null;
  error: string | null;
  report: AgentReport | null;
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
  /** Null when no run exists at all (RF-170, RF-204). */
  agent_report: AgentReportEnvelope | null;
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

/** What a batch approval did, and what it deliberately did not do (RF-176). */
export interface BatchOutcome {
  approved: string[];
  /** Held back for one-by-one verification. Not approved — that is the point. */
  sampled: string[];
  refused: { work_order_id: string; code: string | null; reason: string }[];
  sample_note: string;
}

/**
 * How many of a batch of this size would be held back (RF-176).
 *
 * Asked of the server rather than computed here on purpose: the rounding rule is a policy, and a
 * second copy of it in the browser is a copy free to drift from the one that actually decides.
 */
export function fetchBatchPreview(
  businessUnit: string,
  size: number,
  signal?: AbortSignal,
): Promise<{ batch_size: number; sampled: number; would_approve: number }> {
  return request(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/batch-approval/preview?size=${size}`,
    { signal },
  );
}

/** Approve the selected low-risk orders, sample included (RF-176). */
export function approveBatch(
  businessUnit: string,
  workOrderIds: string[],
  note?: string,
): Promise<BatchOutcome> {
  return request<BatchOutcome>(`${BASE}/units/${encodeURIComponent(businessUnit)}/batch-approval`, {
    method: 'POST',
    body: JSON.stringify({ work_order_ids: workOrderIds, note: note || undefined }),
  });
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
