/**
 * The office attachments of one work order, in the planner's panel (RF-017).
 *
 * Mounted where the planner already has one work order in hand, which is the map's selection: an
 * attachment belongs to an order, and a screen of its own would need a work-order picker the
 * platform does not have.
 *
 * There is no upload button. The platform has no write path to object storage yet — evidence has
 * the same gap — so a button here would open a file dialog and register a row pointing at bytes
 * that are nowhere, which is worse than not having it. The panel does what is real today: it says
 * what is attached, what the crew's download weighs against its ceiling, what is *not* travelling,
 * and it withdraws what should stop travelling.
 */

import { useCallback, useEffect, useState } from 'react';

import { type AttachmentList, fetchAttachments, withdrawAttachment } from '../../api/attachments';
import { ApiError } from '../../api/planning';
import {
  type AttachmentRow,
  budgetHeadline,
  budgetWarning,
  kindLabel,
  megabytes,
  rows,
  TRAVEL_LABEL,
  withdrawAdvice,
  withdrawProblems,
} from './attachments';

export interface AttachmentsPanelProps {
  businessUnit: string;
  /** The one selected work order. The panel is not rendered without one. */
  workOrderId: string;
  /** False for anybody who cannot write. The server refuses it regardless (ADR-013). */
  mayWithdraw?: boolean;
}

export function AttachmentsPanel({
  businessUnit,
  workOrderId,
  mayWithdraw = true,
}: AttachmentsPanelProps) {
  const [list, setList] = useState<AttachmentList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [reason, setReason] = useState('');

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

      {status && (
        <p role="status" className="planner__status">
          {status}
        </p>
      )}
    </section>
  );
}
