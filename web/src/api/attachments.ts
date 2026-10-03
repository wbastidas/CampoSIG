/**
 * Office attachments of a work order (RF-017).
 *
 * The bytes are not here. This client reads what is attached, says how heavy the crew's download
 * is, and withdraws what should stop travelling. Uploading the file itself waits on the platform's
 * write path to object storage, which does not exist yet for evidence either — the server's
 * registration endpoint is what this client would call once it does.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export interface Attachment {
  id: string;
  work_order_id: string;
  kind: string;
  title: string;
  note: string | null;
  filename: string;
  content_hash: string;
  size_bytes: number;
  mime_type: string;
  /** Whether the file travels in the offline package. False for what nobody opens on site. */
  offline: boolean;
  uploaded_by: string;
  uploaded_at: string | null;
  withdrawn_at: string | null;
  withdrawn_by: string | null;
  withdrawn_reason: string | null;
  is_active: boolean;
}

export interface AttachmentList {
  work_order_id: string;
  /** What the crew downloads for this order, and the ceiling it is measured against. */
  offline_bytes: number;
  max_offline_bytes: number;
  attachments: Attachment[];
}

export interface AttachmentPayload {
  title: string;
  filename: string;
  storage_key: string;
  content_hash: string;
  size_bytes: number;
  mime_type: string;
  kind?: string;
  note?: string | null;
  offline?: boolean;
}

const BASE = '/api/v1/attachments';

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

/** A front's list includes its work's attachments: one set of drawings, six fronts (RF-015). */
export function fetchAttachments(
  businessUnit: string,
  workOrderId: string,
  options: { includeWithdrawn?: boolean } = {},
  signal?: AbortSignal,
): Promise<AttachmentList> {
  const params = options.includeWithdrawn ? '?include_withdrawn=true' : '';
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/work-orders/${encodeURIComponent(
      workOrderId,
    )}${params}`,
    { signal },
  );
}

/** The author is the token's subject; the payload cannot name one. */
export function registerAttachment(
  businessUnit: string,
  workOrderId: string,
  payload: AttachmentPayload,
): Promise<Attachment> {
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/work-orders/${encodeURIComponent(
      workOrderId,
    )}`,
    { method: 'POST', body: JSON.stringify(payload) },
  );
}

/** Withdrawn, never deleted: the crew may have executed the work with this drawing. */
export function withdrawAttachment(
  businessUnit: string,
  attachmentId: string,
  reason: string,
): Promise<Attachment> {
  return call(
    `${BASE}/units/${encodeURIComponent(businessUnit)}/${encodeURIComponent(
      attachmentId,
    )}/withdraw`,
    { method: 'POST', body: JSON.stringify({ reason }) },
  );
}
