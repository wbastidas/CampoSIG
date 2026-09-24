/**
 * Profile importer API client (RF-301, RF-302).
 *
 * Mirrors `backend/app/api/model_profile.py`. The shapes carry the *evidence* of each
 * proposal, not just its score: a screen that showed a number an administrator cannot argue
 * with would turn accepting a binding into clicking a button.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

const BASE = '/api/v1/model-profile';

export interface Evidence {
  signal: string;
  detail: string;
  weight: number;
}

export interface ValueMapProposal {
  value_map_name: string;
  domain: string;
  mapping: Record<string, string>;
  /** Canonical values the domain offers no code for. These are what blocks publication. */
  unmapped: string[];
  unclaimed: string[];
}

export interface FieldCandidate {
  field: string;
  label: string;
  score: number;
  evidence: Evidence[];
  domain: string | null;
  volatile_by_business_unit: boolean;
  value_map: ValueMapProposal | null;
}

export interface AttributeProposal {
  attribute_key: string;
  attribute_type: string;
  required: boolean;
  candidates: FieldCandidate[];
  /** Fields that matched by name and were refused anyway, with the reason. */
  refused: string[];
}

export interface RelatedProposal {
  as: string;
  relationship: string;
  target_layer: string;
  cardinality: string;
}

export interface LayerCandidate {
  layer: string;
  score: number;
  evidence: Evidence[];
}

export interface AssetProposal {
  asset_type_key: string;
  geometry: string;
  candidates: LayerCandidate[];
  attributes: AttributeProposal[];
  related: RelatedProposal[];
  participates_in_geometric_network: boolean;
}

export interface ProfileProposal {
  profile_id: string;
  assets: AssetProposal[];
  unclaimed_layer_count: number;
}

export interface ProposalResponse {
  profile_id: string;
  proposal: ProfileProposal;
  gaps: string[];
  layer_names: string[];
}

export interface AssetDecision {
  layer: string;
  attributes: Record<string, string>;
  related: RelatedProposal[];
  participates_in_geometric_network: boolean;
}

export interface ProfileDecisions {
  header: {
    id: string;
    label: string | null;
    provider: string;
    arcgis_version: string | null;
    spatial_reference: number;
    geometric_network: string | null;
    feature_dataset: string | null;
  };
  assets: Record<string, AssetDecision>;
}

export interface Draft {
  draft_id: string;
  business_unit_code: string;
  profile_id: string;
  version: number;
  status: 'draft' | 'published' | 'superseded';
  ready: boolean;
  problems: string[];
  decisions: ProfileDecisions;
  document: Record<string, unknown> | null;
  created_by: string;
  updated_by: string | null;
  published_by: string | null;
  updated_at: string | null;
  published_at: string | null;
}

export interface HistoryEntry {
  draft_id: string;
  version: number;
  status: string;
  problems: string[];
  created_by: string;
  published_by: string | null;
  published_at: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: authHeaders(init?.headers ?? {}) });
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

export function fetchProposal(
  businessUnit: string,
  signal?: AbortSignal,
): Promise<ProposalResponse> {
  const params = new URLSearchParams({ business_unit: businessUnit });
  return request<ProposalResponse>(`${BASE}/proposal?${params}`, { signal });
}

export function fetchAssetProposal(
  businessUnit: string,
  assetTypeKey: string,
  layer: string,
  signal?: AbortSignal,
): Promise<AssetProposal> {
  const params = new URLSearchParams({ business_unit: businessUnit, layer });
  return request<AssetProposal>(
    `${BASE}/proposal/${encodeURIComponent(assetTypeKey)}?${params}`,
    { signal },
  );
}

export function fetchCurrentDraft(
  businessUnit: string,
  profileId: string,
  signal?: AbortSignal,
): Promise<Draft> {
  const params = new URLSearchParams({ business_unit: businessUnit, profile_id: profileId });
  return request<Draft>(`${BASE}/drafts/current?${params}`, { signal });
}

export function createDraft(
  businessUnit: string,
  body: { profile_id: string; label?: string; arcgis_version?: string },
): Promise<Draft> {
  const params = new URLSearchParams({ business_unit: businessUnit });
  return request<Draft>(`${BASE}/drafts?${params}`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function saveDecisions(
  businessUnit: string,
  draftId: string,
  decisions: ProfileDecisions,
): Promise<Draft> {
  const params = new URLSearchParams({ business_unit: businessUnit });
  return request<Draft>(`${BASE}/drafts/${draftId}?${params}`, {
    method: 'PUT',
    body: JSON.stringify({ decisions }),
  });
}

export function publishDraft(businessUnit: string, draftId: string): Promise<Draft> {
  const params = new URLSearchParams({ business_unit: businessUnit });
  return request<Draft>(`${BASE}/drafts/${draftId}/publish?${params}`, { method: 'POST' });
}

export function fetchHistory(
  businessUnit: string,
  profileId: string,
  signal?: AbortSignal,
): Promise<HistoryEntry[]> {
  const params = new URLSearchParams({ business_unit: businessUnit, profile_id: profileId });
  return request<HistoryEntry[]>(`${BASE}/history?${params}`, { signal });
}

/** The URL of the YAML export, for an ordinary download link. */
export function yamlUrl(businessUnit: string, draftId: string): string {
  const params = new URLSearchParams({ business_unit: businessUnit });
  return `${BASE}/drafts/${draftId}/yaml?${params}`;
}
