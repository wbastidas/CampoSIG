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

export async function fetchAiDashboard(
  businessUnit: string,
  options: { since?: string; until?: string } = {},
  signal?: AbortSignal,
): Promise<AiDashboard> {
  const params = new URLSearchParams();
  if (options.since) params.set('since', options.since);
  if (options.until) params.set('until', options.until);
  const query = params.toString();
  const response = await fetch(
    `/api/v1/analytics/units/${encodeURIComponent(businessUnit)}/ai-dashboard${
      query ? `?${query}` : ''
    }`,
    { headers: authHeaders(), signal },
  );
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
  return (await response.json()) as AiDashboard;
}
