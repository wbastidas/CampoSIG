/**
 * The office attachments of one work order, in the planner's panel (RF-017).
 *
 * Mounted where the planner already has one work order in hand, which is the map's selection: an
 * attachment belongs to an order, and a screen of its own would need a work-order picker the
 * platform does not have.
 *
 * Uploading is three calls in sequence, none of which touch our API with the file's bytes: the
 * server only ever signs a URL. The browser hashes the file, asks for the signature, `PUT`s
 * straight to object storage with it, and only then registers the result through the endpoint
 * that already existed — the same three steps a phone would run.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  type AttachmentList,
  fetchAttachments,
  registerAttachment,
  withdrawAttachment,
} from '../../api/attachments';
import { ApiError } from '../../api/planning';
import { presignUpload, uploadFile } from '../../api/storage';
import {
  type AttachmentRow,
  budgetHeadline,
  budgetWarning,
  EMPTY_UPLOAD,
  kindLabel,
  megabytes,
  rows,
  sha256Hex,
  TRAVEL_LABEL,
  UPLOAD_KINDS,
  type UploadDraft,
  uploadProblems,
  withdrawAdvice,
  withdrawProblems,
} from './attachments';

export interface AttachmentsPanelProps {
  businessUnit: string;
  /** The one selected work order. The panel is not rendered without one. */
  workOrderId: string;
  /** False for anybody who cannot write. The server refuses it regardless (ADR-013). */
  mayWithdraw?: boolean;
  /** False for anybody who cannot attach. The server refuses it regardless (ADR-013). */
  mayUpload?: boolean;
}

export function AttachmentsPanel({
  businessUnit,
  workOrderId,
  mayWithdraw = true,
  mayUpload = true,
}: AttachmentsPanelProps) {
  const [list, setList] = useState<AttachmentList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [uploading, setUploading] = useState(false);
  const [draft, setDraft] = useState<UploadDraft>(EMPTY_UPLOAD);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const fresh = await fetchAttachments(businessUnit, workOrderId, {}, signal);
        setList(fresh);
        setError(null);
      } catch (cause) {
        if (signal?.aborted) return;
        setList(null);
        setError(cause instanceof ApiError ? cause.message : 'No se pudieron leer los adjuntos');
      }
    },
    [businessUnit, workOrderId],
  );

  useEffect(() => {
    const controller = new AbortController();
    // El setState ocurre tras el await dentro del callback, no en el cuerpo del efecto.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const onWithdraw = useCallback(
    async (row: AttachmentRow) => {
      if (withdrawProblems(reason).length > 0) return;
      setBusy(true);
      setStatus(null);
      try {
        await withdrawAttachment(businessUnit, row.attachment.id, reason);
        await load();
        setStatus(`«${row.attachment.title}» ya no viaja en los paquetes nuevos.`);
        setOpenId(null);
        setReason('');
      } catch (cause) {
        setStatus(cause instanceof ApiError ? cause.message : 'No se pudo retirar el adjunto');
      } finally {
        setBusy(false);
      }
    },
    [businessUnit, load, reason],
  );

  const onUpload = useCallback(async () => {
    const problems = uploadProblems(draft);
    if (problems.length > 0 || !draft.file) return;
    const file = draft.file;
    setUploading(true);
    setUploadStatus(null);
    try {
      const contentHash = await sha256Hex(file);
      const presigned = await presignUpload(businessUnit, {
        purpose: 'adjunto',
        kind: draft.kind,
        filename: file.name,
        content_type: file.type,
        size_bytes: file.size,
      });
      await uploadFile(presigned, file);
      await registerAttachment(businessUnit, workOrderId, {
        title: draft.title.trim(),
        filename: file.name,
        storage_key: presigned.storage_key,
        content_hash: contentHash,
        size_bytes: file.size,
        mime_type: file.type,
        kind: draft.kind,
      });
      await load();
      setDraft(EMPTY_UPLOAD);
      setUploadStatus(`«${draft.title.trim()}» se adjuntó.`);
    } catch (cause) {
      setUploadStatus(cause instanceof ApiError ? cause.message : 'No se pudo subir el adjunto');
    } finally {
      setUploading(false);
    }
  }, [businessUnit, draft, load, workOrderId]);

  const visible = rows(list);
  const warning = budgetWarning(list);

  return (
    <section className="planner__attachments" aria-label="Adjuntos de oficina">
      <h3>Adjuntos de oficina</h3>

      {error && (
        <p role="status" className="planner__warning">
          {error}
        </p>
      )}

      <dl className="planner__summary">
        <dt>Descarga de la cuadrilla</dt>
        <dd>{budgetHeadline(list)}</dd>
      </dl>

      {warning && (
        <p role="status" className="planner__warning">
          {warning}
        </p>
      )}

      {list && visible.length === 0 && !error && (
        <p className="planner__hint">Esta OT no tiene adjuntos de oficina.</p>
      )}

      <ul className="planner__attachment-list">
        {visible.map((row) => (
          <li key={row.attachment.id}>
            <strong>{row.attachment.title}</strong>
            <span>
              {kindLabel(row.attachment.kind)} · {megabytes(row.attachment.size_bytes)} MB ·{' '}
              {TRAVEL_LABEL[row.travel]}
            </span>
            {row.fromWork && <span className="planner__hint">De la obra, compartido</span>}
            {row.attachment.note && <p>{row.attachment.note}</p>}
            {row.travel === 'viaja' && mayWithdraw && (
              <button
                type="button"
                onClick={() => {
                  setOpenId(row.attachment.id === openId ? null : row.attachment.id);
                  setReason('');
                }}
              >
                Retirar
              </button>
            )}
            {openId === row.attachment.id && (
              <div className="planner__withdraw">
                <p>{withdrawAdvice(row)}</p>
                <label htmlFor={`motivo-${row.attachment.id}`}>Motivo</label>
                <input
                  id={`motivo-${row.attachment.id}`}
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                />
                {withdrawProblems(reason).map((problem) => (
                  <p key={problem} role="status" className="planner__warning">
                    {problem}
                  </p>
                ))}
                <button
                  type="button"
                  disabled={busy || withdrawProblems(reason).length > 0}
                  onClick={() => void onWithdraw(row)}
                >
                  {busy ? 'Retirando…' : 'Confirmar retiro'}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>

      {mayUpload && (
        <div className="planner__upload">
          <label htmlFor="adjunto-titulo">Título</label>
          <input
            id="adjunto-titulo"
            value={draft.title}
            onChange={(event) => setDraft({ ...draft, title: event.target.value })}
          />

          <label htmlFor="adjunto-tipo">Tipo</label>
          <select
            id="adjunto-tipo"
            value={draft.kind}
            onChange={(event) => setDraft({ ...draft, kind: event.target.value })}
          >
            {UPLOAD_KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {kindLabel(kind)}
              </option>
            ))}
          </select>

          <label htmlFor="adjunto-archivo">Archivo</label>
          <input
            id="adjunto-archivo"
            type="file"
            onChange={(event) => setDraft({ ...draft, file: event.target.files?.[0] ?? null })}
          />

          {uploadProblems(draft).map((problem) => (
            <p key={problem} role="status" className="planner__warning">
              {problem}
            </p>
          ))}

          <button
            type="button"
            disabled={uploading || uploadProblems(draft).length > 0}
            onClick={() => void onUpload()}
          >
            {uploading ? 'Subiendo…' : 'Adjuntar'}
          </button>

          {uploadStatus && (
            <p role="status" className="planner__status">
              {uploadStatus}
            </p>
          )}
        </div>
      )}

      {status && (
        <p role="status" className="planner__status">
          {status}
        </p>
      )}
    </section>
  );
}
