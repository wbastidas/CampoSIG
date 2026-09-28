/**
 * Firmar una subida al almacenamiento de objetos (RF-005, RF-017).
 *
 * El backend nunca transporta el archivo: firma una URL de `PUT` y el cliente sube directo a
 * SeaweedFS con ella. Con la URL y el `storage_key` en mano, el llamante hace el `PUT` con
 * `uploadFile` y luego registra el resultado donde corresponda —`registerAttachment`,
 * la sincronización de evidencias— con ese mismo `storage_key` y el hash que calculó.
 */

import { ApiError } from './planning';
import { authHeaders, notifyExpired } from './session';

export type UploadPurpose = 'adjunto' | 'evidencia';

export interface PresignedUpload {
  url: string;
  storage_key: string;
  method: 'PUT';
  expires_in: number;
  /** Cabeceras que hay que mandar exactamente así en el `PUT`, o la firma no valida. */
  headers: Record<string, string>;
}

export interface PresignRequest {
  purpose: UploadPurpose;
  /** Para `evidencia`, un `EvidenceKind` (`foto`, `audio`, `firma`, `croquis`, `documento`);
   *  para `adjunto`, un `AttachmentKind`. */
  kind: string;
  filename: string;
  content_type: string;
  size_bytes: number;
}

const BASE = '/api/v1/storage';

export function presignUpload(
  businessUnit: string,
  payload: PresignRequest,
): Promise<PresignedUpload> {
  return call(`${BASE}/units/${encodeURIComponent(businessUnit)}/presign`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/** Sube el archivo con la URL firmada. No pasa por nuestra API: va directo al almacenamiento. */
export async function uploadFile(upload: PresignedUpload, file: Blob): Promise<void> {
  const response = await fetch(upload.url, {
    method: upload.method,
    headers: upload.headers,
    body: file,
  });
  if (!response.ok) {
    throw new ApiError(response.status, `no se pudo subir el archivo (${response.status})`);
  }
}

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
