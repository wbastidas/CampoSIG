/**
 * Form publication client (RF-032).
 *
 * No business unit anywhere: a form is national, like the data model it is generated from
 * (ADR-009). What differs per unit are the catalogue values injected when a form is composed, and
 * those are not frozen by publication.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export interface CatalogueRow {
  code: string;
  title: string;
  area: string;
  /** What the file on disk says. The draft. */
  file_version: string;
  /** What is frozen and in force, or null when nothing was ever published. */
  published_version: string | null;
  /** The file moved and nobody published it: a form nobody in the field has seen. */
  has_unpublished_draft: boolean;
  never_published: boolean;
}

export interface FormVersion {
  code: string;
  version: string;
  state: string;
  content_hash: string;
  published_by: string | null;
  published_at: string | null;
  obsoleted_at: string | null;
  obsoleted_by: string | null;
  note: string | null;
  /** The block codes the version froze. */
  blocks: string[];
}

const BASE = '/api/v1/forms';

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

export function fetchCatalogue(signal?: AbortSignal): Promise<{ forms: CatalogueRow[] }> {
  return call<{ forms: CatalogueRow[] }>(`${BASE}/catalogue`, { signal });
}

export function fetchVersions(code: string, signal?: AbortSignal): Promise<FormVersion[]> {
  return call<FormVersion[]>(`${BASE}/${encodeURIComponent(code)}/versions`, { signal });
}

/** Publish the file's version. The author is the token's subject, never a field. */
export function publishForm(code: string, note?: string): Promise<FormVersion> {
  return call<FormVersion>(`${BASE}/${encodeURIComponent(code)}/publish`, {
    method: 'POST',
    body: JSON.stringify({ note: note ?? null }),
  });
}

export function obsoleteVersion(code: string, version: string): Promise<FormVersion> {
  return call<FormVersion>(
    `${BASE}/${encodeURIComponent(code)}/versions/${encodeURIComponent(version)}/obsolete`,
    { method: 'POST' },
  );
}
