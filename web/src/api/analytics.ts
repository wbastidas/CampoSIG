/**
 * AI dashboard client (RF-134, RF-111a).
 *
 * One call for five panels plus the agreement, for the same reason the review detail is one call:
 * a screen that makes six would be a screen where one failure silently removes a panel, and the
 * panel that vanishes is the one nobody notices was supposed to be there.
 */

import type { AgentAgreement } from './review';
import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

/**
 * Every rate is nullable, and that is the contract, not an omission: below the server's
 * `min_for_a_rate` the count travels and the rate does not. «100 % de aceptación» over two
 * proposals is noise with a percent sign.
 */
export interface FieldAcceptance {
  field_key: string;
  proposals: number;
  accepted: number;
  corrected: number;
  acceptance: number | null;
  mean_confidence: number | null;
}

export interface ClassCorrections {
  proposed_class: string;
  proposals: number;
  corrected: number;
  correction_rate: number | null;
  /** What people changed it to, most frequent first. */
  became: { value: string; times: number }[];
}

export interface WordErrors {
  reference_words: number;
  errors: number;
  measured_fields: number;
  /** Values that are not text — a number, a code, a list — so no word distance applies. */
  unmeasurable_fields: number;
  error_rate: number | null;
  /** What the number measures, in the server's own words. Shown, not paraphrased. */
  measures: string;
}

export interface VoiceAdoption {
  user: string;
  responses: number;
  responses_with_voice: number;
  voice_fields: number;
  adoption: number | null;
}

export interface ModelInFleet {
  model_name: string;
  model_version: string;
  origin: string;
  proposals: number;
  accepted: number;
  acceptance: number | null;
  first_seen: string | null;
  last_seen: string | null;
}

export interface AiDashboard {
  since: string | null;
  until: string | null;
  min_for_a_rate: number;
  fields: FieldAcceptance[];
  visual_classes: ClassCorrections[];
  word_errors: WordErrors | null;
  voice_adoption: VoiceAdoption[];
  fleet: ModelInFleet[];
  /** RF-111a's acceptance criterion: the kappa shows on this dashboard. */
  agreement: AgentAgreement;
}

const BASE = '/api/v1/analytics';

/**
 * A board, or the server's reason for not giving one.
 *
 * Shared by the two boards rather than written twice: they differ in their query and in nothing
 * else, and two copies of the error handling would be two chances for one of them to swallow a
 * detail the screen needs to show.
 */
async function read<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { headers: authHeaders(), signal });
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

export function fetchAiDashboard(
  businessUnit: string,
  options: { since?: string; until?: string } = {},
  signal?: AbortSignal,
): Promise<AiDashboard> {
  const params = new URLSearchParams();
  if (options.since) params.set('since', options.since);
  if (options.until) params.set('until', options.until);
  const query = params.toString();
  return read<AiDashboard>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/ai-dashboard${query ? `?${query}` : ''}`,
    signal,
  );
}

/** One stretch of a job's life, timed (RF-130). */
export interface Leg {
  key: string;
  label: string;
  measured: number;
  /** Jobs that started the leg and have not finished it. Not zeros — still running. */
  in_progress: number;
  /** Jobs that finished with no record of one end, usually from before the trail existed. */
  unrecorded: number;
  median_minutes: number | null;
  p90_minutes: number | null;
  worst_minutes: number | null;
  min_sample: number;
}

export interface CrewProductivity {
  crew_id: string;
  crew_name: string;
  closed_in_field: number;
  approved: number;
  open_now: number;
}

export interface OperationalBoard {
  computed_at: string;
  since: string;
  by_state: Record<string, number>;
  sla: {
    overdue: number;
    due_soon: number;
    due_soon_hours: number;
    /** Open orders with no SLA at all. «0 vencidas» over a hundred of these says nothing. */
    without_sla: number;
  };
  legs: Leg[];
  crews: CrewProductivity[];
}

export function fetchOperationalBoard(
  businessUnit: string,
  signal?: AbortSignal,
): Promise<OperationalBoard> {
  return read<OperationalBoard>(`${BASE}/units/${encodeURIComponent(businessUnit)}/operations`, signal);
}

/** One attention that missed the regulator's deadline (RF-131). */
export interface ApgBreach {
  work_order_id: string;
  order_code: string | null;
  asset_code: string | null;
  hours: number | null;
  limit_hours: number | null;
  within_limit: boolean | null;
  /** False when nobody has checked the limit against the official text (ADR-007). */
  limit_verified: boolean;
  norm_ref: string | null;
  article_ref: string | null;
  message: string;
}

export interface ApgBoard {
  computed_at: string;
  since: string;
  until: string;
  attentions: number;
  restoration: {
    within: number;
    breached: number;
    judged: number;
    /** Captured but not judgeable: no times, or no parameter loaded. */
    not_measurable: number;
    /** Judged against a limit nobody verified. */
    against_unverified_limit: number;
    compliance: number | null;
    median_hours: number | null;
    p90_hours: number | null;
    worst_hours: number | null;
    min_sample: number;
  };
  fleet: { by_technology: Record<string, number>; without_technology: number };
  failures: {
    by_cause: Record<string, number>;
    distinct_luminaires: number;
    failures_per_luminaire: number | null;
    /** What the rate is divided by, in the server's own words. Shown, not paraphrased. */
    denominator: string;
    repeat_offenders: { asset_code: string; failures: number }[];
  };
  breaches: ApgBreach[];
}

export function fetchApgBoard(
  businessUnit: string,
  signal?: AbortSignal,
): Promise<ApgBoard> {
  return read<ApgBoard>(`${BASE}/units/${encodeURIComponent(businessUnit)}/apg`, signal);
}

/**
 * The breach export, as a blob the screen hands to the browser (RF-131).
 *
 * Fetched rather than linked, for the same reason the acta is: the request carries the bearer token
 * and a plain `<a href>` would not, so the link would download an HTML login page named `.csv` —
 * which is the kind of bug somebody discovers a week later with the file already circulating.
 */
export async function downloadApgCsv(businessUnit: string): Promise<Blob> {
  const response = await fetch(`${BASE}/units/${encodeURIComponent(businessUnit)}/apg.csv`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    if (response.status === 401) notifyExpired();
    throw new ApiError(response.status, `${response.status} ${response.statusText}`);
  }
  return response.blob();
}

/** The interruption base of a period (RF-132). Never the indices — see `note`. */
export interface InterruptionBase {
  since: string;
  until: string;
  interruptions: number;
  computable: number;
  not_computable: number;
  /** Neither computable nor not: no duration, or no threshold loaded. Never assumed either way. */
  unclassified: number;
  numerators: {
    kva_affected: number;
    kva_hours: number;
    /** Computable interruptions with no kVA recorded. Each leaves both numerators too low. */
    missing_kva: number;
    /** Why the platform does not publish FMIK or TTIK, in the server's own words. */
    note: string;
  };
  /** Export layouts on the server, by the code the export endpoint accepts. */
  formats: string[];
}

/**
 * Whether a payload has the shape the panel needs.
 *
 * Checked and not trusted, for the reason the agreement panel taught: this is a secondary panel
 * beside the board a supervisor uses to chase the SLA, and a web build newer than the API it talks
 * to would otherwise throw during render and blank the whole screen. The fetch's own catch cannot
 * save a render.
 */
export function isInterruptionBase(body: unknown): body is InterruptionBase {
  if (typeof body !== 'object' || body === null) return false;
  const rows = body as Record<string, unknown>;
  const numbers = ['interruptions', 'computable', 'not_computable', 'unclassified'];
  if (!numbers.every((key) => typeof rows[key] === 'number')) return false;
  if (!Array.isArray(rows.formats)) return false;
  const numerators = rows.numerators as Record<string, unknown> | undefined;
  if (typeof numerators !== 'object' || numerators === null) return false;
  return (
    typeof numerators.kva_affected === 'number' &&
    typeof numerators.kva_hours === 'number' &&
    typeof numerators.missing_kva === 'number' &&
    typeof numerators.note === 'string'
  );
}

export async function fetchInterruptionBase(
  businessUnit: string,
  signal?: AbortSignal,
): Promise<InterruptionBase> {
  const body = await read<unknown>(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/interruptions`,
    signal,
  );
  if (!isInterruptionBase(body)) {
    throw new ApiError(200, 'la respuesta de interrupciones no tiene la forma esperada');
  }
  return body;
}

/** The interruption export, in the named layout. Fetched with the token, like every export. */
export async function downloadInterruptions(
  businessUnit: string,
  format: string,
): Promise<Blob> {
  const response = await fetch(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/interruptions.csv?format=${encodeURIComponent(
      format,
    )}`,
    { headers: authHeaders() },
  );
  if (!response.ok) {
    if (response.status === 401) notifyExpired();
    throw new ApiError(response.status, `${response.status} ${response.statusText}`);
  }
  return response.blob();
}
