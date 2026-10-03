/**
 * Proposal-tray client (RF-013, RF-114).
 *
 * Four calls and no more: the tray, and the three decisions. Generation is deliberately absent —
 * raising proposals is not a decision, it belongs to a planner or a batch, and a button on the
 * supervisor's own tray that filled it would be an odd thing to put in front of them.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

/** The Annex C arithmetic, as the server computed it on the day of the proposal. */
export interface Criticality {
  severity: number;
  consequence: number;
  score: number;
  priority: string;
  /** «P1»..«P4»: the areas speak in P-numbers. */
  annex_band: string;
  /** True when the zone's exposure raised the consequence by one level. */
  exposed: boolean;
  /** True when any input was a default or a declared approximation. */
  estimated: boolean;
  /** What the computation could not know, in the server's own words. Never paraphrased. */
  caveats: string[];
  explanation: string;
}

export interface FindingView {
  work_order_id: string;
  order_code: string | null;
  asset_code: string | null;
  defect_code: string;
  criticality: string;
  feeder_code: string | null;
  recorded_at: string | null;
  wants_order: boolean;
}

export interface Proposal {
  id: string;
  state: string;
  origin: string;
  asset_code: string | null;
  asset_type_key: string | null;
  feeder_code: string | null;
  zone: string | null;
  defect_code: string;
  work_type: string;
  form_code: string | null;
  priority: string;
  criticality: Criticality;
  /** The annex's suggested deadline in hours, or null for P4 — which is a plan, not a clock. */
  suggested_deadline_hours: number | null;
  justification: string;
  findings: FindingView[];
  source_work_order_id: string | null;
  work_order_id: string | null;
  merged_into_id: string | null;
  reject_reason_code: string | null;
  reject_note: string | null;
  decided_by: string | null;
  decided_at: string | null;
  created_at: string | null;
  /** Rule 8: an AI value travels with its origin, model version and confidence. */
  model_name: string | null;
  model_version: string | null;
  confidence: number | null;
}

export interface RejectReason {
  code: string;
  label: string;
  /** What this reason teaches a training set. Not all rejections teach the same thing (RF-114). */
  signal: string | null;
}

export interface Tray {
  state: string;
  counts: Record<string, number>;
  reject_reasons: RejectReason[];
  proposals: Proposal[];
}

const BASE = '/api/v1/proposals';

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

export function fetchTray(businessUnit: string, state?: string, signal?: AbortSignal): Promise<Tray> {
  const query = state ? `?state=${encodeURIComponent(state)}` : '';
  return call<Tray>(`${BASE}/units/${encodeURIComponent(businessUnit)}${query}`, { signal });
}

/** Approve: the proposal becomes a planned work order. `priority` is the supervisor's own call. */
export function approveProposal(
  businessUnit: string,
  id: string,
  body: { priority?: string; note?: string } = {},
): Promise<{ work_order_id: string; state: string; proposal: Proposal }> {
  return call(`${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(id)}/approve`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/** Merge: the findings are attached to a work order that already exists. */
export function mergeProposal(
  businessUnit: string,
  id: string,
  body: { work_order_id: string; note?: string },
): Promise<Proposal> {
  return call(`${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(id)}/merge`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/** Reject with a catalogued reason. The code is the training label; the note never is. */
export function rejectProposal(
  businessUnit: string,
  id: string,
  body: { reason_code: string; note?: string },
): Promise<Proposal> {
  return call(`${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(id)}/reject`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function fetchTrainingSignals(
  businessUnit: string,
  signal?: AbortSignal,
): Promise<Record<string, number>> {
  return call<Record<string, number>>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/training-signals`,
    { signal },
  );
}
