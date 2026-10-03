/**
 * Preventive-plan client (RF-012).
 *
 * Firing a plan is a POST and never a consequence of opening the screen: a GET that issued work
 * orders would issue them again on every refresh, and the person refreshing would have no idea.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export interface PlanTarget {
  asset_code: string;
  asset_type_key: string | null;
  feeder_code: string | null;
  zone: string | null;
  /** The visit order. A route is this list sorted by it. */
  sort_order: number;
}

/** How the current period is going. A fraction with its denominator, never a bare percentage. */
export interface PlanCoverage {
  period: string;
  targets: number;
  issued: number;
  skipped_pending: number;
  skipped_recent: number;
  /** What an expanded scope could not know, in the server's words. */
  caveats: string[];
  note: string | null;
}

/** Issued is not done: a plan whose orders nobody executed has 0 % compliance. */
export interface PlanCompletion {
  period: string;
  issued: number;
  submitted: number;
}

export interface Plan {
  code: string;
  name: string;
  description: string | null;
  work_type: string;
  form_code: string;
  priority: string;
  asset_type_key: string | null;
  cadence: string;
  cadence_days: number | null;
  day_of_month: number;
  scope: string;
  scope_value: string | null;
  skip_if_attended_within_days: number | null;
  starts_on: string;
  ends_on: string | null;
  active: boolean;
  created_by: string | null;
  updated_by: string | null;
}

export interface PlanRow extends Plan {
  targets: number;
  coverage: PlanCoverage;
  completion: PlanCompletion;
}

export interface PlanIssueView {
  period: string;
  asset_code: string | null;
  outcome: string;
  /** Why no order was issued, in Spanish. Null when one was. */
  reason: string | null;
  work_order_id: string | null;
  caveats: string[];
  issued_at: string | null;
}

export interface PlanDetail extends Plan {
  coverage: PlanCoverage;
  completion: PlanCompletion;
  targets: PlanTarget[];
  /** What the scope expands to today. Equal to `targets` for an explicit list. */
  expanded: {
    asset_code: string;
    asset_type_key: string | null;
    feeder_code: string | null;
  }[];
  caveats: string[];
  note: string | null;
  history: PlanIssueView[];
}

export interface PlanRun {
  plan_code: string;
  period: string;
  targets: number;
  issued: string[];
  skipped_pending: string[];
  skipped_recent: string[];
  already_issued: string[];
  caveats: string[];
  note: string | null;
}

export interface PlanPayload {
  name: string;
  work_type: string;
  form_code: string;
  cadence: string;
  scope: string;
  priority?: string;
  description?: string | null;
  asset_type_key?: string | null;
  cadence_days?: number | null;
  day_of_month?: number;
  scope_value?: string | null;
  skip_if_attended_within_days?: number | null;
  starts_on?: string | null;
  ends_on?: string | null;
  active?: boolean;
  targets?: { asset_code: string; sort_order?: number }[] | null;
}

const BASE = '/api/v1/plans';

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

export function fetchPlans(
  businessUnit: string,
  signal?: AbortSignal,
): Promise<{ plans: PlanRow[] }> {
  return call(`${BASE}/units/${encodeURIComponent(businessUnit)}`, { signal });
}

export function fetchPlan(
  businessUnit: string,
  code: string,
  signal?: AbortSignal,
): Promise<PlanDetail> {
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/plan/${encodeURIComponent(code)}`,
    { signal },
  );
}

/** The author is the token's subject; the payload cannot name one. */
export function savePlan(businessUnit: string, code: string, payload: PlanPayload): Promise<Plan> {
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/plan/${encodeURIComponent(code)}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    },
  );
}

/** Idempotent per period: firing twice reports what was already issued and creates nothing. */
export function runPlan(businessUnit: string, code: string, on?: string): Promise<PlanRun> {
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/plan/${encodeURIComponent(code)}/run`,
    { method: 'POST', body: JSON.stringify(on ? { on } : {}) },
  );
}
