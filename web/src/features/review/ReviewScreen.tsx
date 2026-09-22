/**
 * The supervisor's review screen (M11, RF-110 to RF-112, RF-342).
 *
 * This is where field data becomes authoritative, so the screen's job is to make the four
 * things a decision depends on impossible to miss:
 *
 * 1. the values a model proposed and whether anybody confirmed them (SRS rule 0.5),
 * 2. the before and after photographs, side by side, with the same-file case called out,
 * 3. what the deterministic compliance rules found, with their citations (ADR-007),
 * 4. the reasons approval is blocked — shown *before* the button is pressed, not after.
 *
 * Every judgement lives in `decision.ts` and is tested there. This file renders and calls.
 */

import { Fragment, useCallback, useEffect, useState } from 'react';

import {
  ApprovalBlocked,
  type DecisionKind,
  fetchDetail,
  fetchGisTray,
  fetchQueue,
  type GisTray,
  type QueueItem,
  type ReviewDetail,
  submitDecision,
} from '../../api/review';
import {
  ATTENTION_COLOR,
  ATTENTION_LABEL,
  acceptanceRate,
  attentionFor,
  citationFor,
  evidenceByStage,
  needsArcFm,
  OUTCOME_LABEL,
  reusedEvidence,
  sortFindings,
  sortQueue,
  tamperedEvidence,
  unconfirmedAiValues,
} from './decision';

export interface ReviewScreenProps {
  /** Required: nothing crosses between business units (ADR-009). */
  businessUnit: string;
  /** Who is deciding. Recorded on the decision. */
  reviewer: string;
  now?: () => Date;
}

export function ReviewScreen({ businessUnit, reviewer, now = () => new Date() }: ReviewScreenProps) {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [tray, setTray] = useState<GisTray | null>(null);
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [refused, setRefused] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const loadQueue = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const body = await fetchQueue(businessUnit, { limit: 100 }, signal);
        setQueue(body.items);
        setTotal(body.total);
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        setError((cause as Error).message);
      }
    },
    [businessUnit],
  );

  const loadTray = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setTray(await fetchGisTray(businessUnit, signal));
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        // The tray is secondary; its failure must not hide the queue.
        setTray(null);
      }
    },
    [businessUnit],
  );

  useEffect(() => {
    const controller = new AbortController();
    void loadQueue(controller.signal);
    void loadTray(controller.signal);
    return () => controller.abort();
  }, [loadQueue, loadTray]);

  useEffect(() => {
    if (selected === null) {
      setDetail(null);
      return;
    }
    const controller = new AbortController();
    void (async () => {
      try {
        setDetail(await fetchDetail(businessUnit, selected, controller.signal));
        setRefused([]);
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        setError((cause as Error).message);
      }
    })();
    return () => controller.abort();
  }, [businessUnit, selected]);

  const decide = useCallback(
    async (decision: DecisionKind) => {
      if (selected === null) return;
      setBusy(true);
      setRefused([]);
      try {
        await submitDecision(businessUnit, selected, {
          decision,
          reviewer_sub: reviewer,
          note: note || undefined,
        });
        setNote('');
        setSelected(null);
        await Promise.all([loadQueue(), loadTray()]);
      } catch (cause) {
        if (cause instanceof ApprovalBlocked) {
          // The server refused with reasons. Shown as a list, because a supervisor should not
          // have to parse one long sentence to find the one condition that failed.
          setRefused(cause.blockers);
        } else {
          setError((cause as Error).message);
        }
      } finally {
        setBusy(false);
      }
    },
    [businessUnit, selected, reviewer, note, loadQueue, loadTray],
  );

  const clock = now();
  const ordered = sortQueue(queue, clock);

  return (
    <section className="review">
      <header>
        <h1>Revisión</h1>
        <p>{total} orden(es) esperando decisión.</p>
        {error && <p role="alert" className="board-error">{error}</p>}
      </header>

      <div className="review-layout">
        <nav aria-label="Cola de revisión">
          <ul className="review-queue">
            {ordered.map((item) => (
              <li key={item.work_order_id}>
                <button
                  type="button"
                  onClick={() => setSelected(item.work_order_id)}
                  aria-current={selected === item.work_order_id}
                >
                  <strong>{item.code ?? item.work_order_id.slice(0, 8)}</strong>
                  <span>{item.work_type}</span>
                  <span>{item.priority}</span>
                  {item.sla_due_at && <span className="sla">vence {item.sla_due_at.slice(0, 10)}</span>}
                </button>
              </li>
            ))}
            {ordered.length === 0 && <li>Nada esperando revisión.</li>}
          </ul>
        </nav>

        {detail === null ? (
          <p>Seleccione una orden de la cola.</p>
        ) : (
          <article className="review-detail">
            <ReviewHeader detail={detail} />
            <Blockers detail={detail} refused={refused} />
            <AiAudit detail={detail} />
            <Compliance detail={detail} />
            <BeforeAfter detail={detail} />
            <Observations detail={detail} />

            <fieldset>
              <legend>Decisión</legend>
              <label htmlFor="review-note">Nota</label>
              <textarea
                id="review-note"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Qué corregir, o por qué se aprueba"
              />
              <div className="review-actions">
                <button type="button" disabled={busy} onClick={() => void decide('aprobada')}>
                  Aprobar
                </button>
                <button type="button" disabled={busy} onClick={() => void decide('devuelta')}>
                  Devolver con observaciones
                </button>
                <button type="button" disabled={busy} onClick={() => void decide('anulada')}>
                  Anular
                </button>
              </div>
            </fieldset>
          </article>
        )}
      </div>

      {tray && <GisTrayPanel tray={tray} />}
    </section>
  );
}

function ReviewHeader({ detail }: { detail: ReviewDetail }) {
  const attention = attentionFor(detail);
  const rate = acceptanceRate(detail.provenance);
  return (
    <header>
      <h2>
        {detail.work_order.code ?? detail.work_order.work_order_id.slice(0, 8)} — {detail.form.title}
      </h2>
      <span
        className="severity-chip"
        style={{ backgroundColor: ATTENTION_COLOR[attention] }}
        aria-label={ATTENTION_LABEL[attention]}
      >
        {ATTENTION_LABEL[attention]}
      </span>
      <dl>
        <div>
          <dt>Activo</dt>
          <dd>{detail.work_order.asset_code ?? '—'}</dd>
        </div>
        <div>
          <dt>Alimentador</dt>
          <dd>{detail.work_order.feeder_code ?? '—'}</dd>
        </div>
        <div>
          <dt>Aceptación de la IA</dt>
          {/* Null y no 0 %: una captura sin propuestas no tiene tasa. */}
          <dd>{rate === null ? 'sin propuestas' : `${Math.round(rate * 100)} %`}</dd>
        </div>
      </dl>
      {detail.form.warnings.map((warning) => (
        <p key={warning} className="form-warning">{warning}</p>
      ))}
    </header>
  );
}

function Blockers({ detail, refused }: { detail: ReviewDetail; refused: string[] }) {
  const reasons = refused.length > 0 ? refused : detail.blockers;
  if (reasons.length === 0) return null;
  return (
    <section className="blockers" role="alert">
      <h3>No se puede aprobar todavía</h3>
      <ul>
        {reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </section>
  );
}

function AiAudit({ detail }: { detail: ReviewDetail }) {
  const ai = detail.provenance.filter((entry) => entry.is_ai);
  if (ai.length === 0) return null;
  const pending = new Set(unconfirmedAiValues(detail.provenance).map((entry) => entry.field_key));
  return (
    <section>
      <h3>Valores propuestos por IA</h3>
      <table>
        <thead>
          <tr>
            <th scope="col">Campo</th>
            <th scope="col">Origen</th>
            <th scope="col">Propuesto</th>
            <th scope="col">Final</th>
            <th scope="col">Confianza</th>
            <th scope="col">Modelo</th>
            <th scope="col">Confirmó</th>
            <th scope="col">De dónde salió</th>
          </tr>
        </thead>
        <tbody>
          {ai.map((entry) => (
            <tr key={entry.field_key} className={pending.has(entry.field_key) ? 'alarming-row' : undefined}>
              <td>{entry.field_key}</td>
              <td>{entry.origin}</td>
              <td>{String(entry.proposed_value ?? '—')}</td>
              <td>{String(entry.final_value ?? '—')}</td>
              <td>{entry.confidence === null ? '—' : `${Math.round(entry.confidence * 100)} %`}</td>
              <td>
                {entry.model_name ?? '—'}
                {entry.model_version ? ` ${entry.model_version}` : ''}
              </td>
              <td>{entry.confirmed_by ?? 'nadie todavía'}</td>
              {/* El fragmento dictado, o la evidencia y el recorte: una propuesta que no se
                  puede mirar no es revisable. */}
              <td><code>{entry.source ?? '—'}</code></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Compliance({ detail }: { detail: ReviewDetail }) {
  if (detail.compliance.length === 0) return null;
  return (
    <section>
      <h3>Cumplimiento normativo</h3>
      <table>
        <thead>
          <tr>
            <th scope="col">Regla</th>
            <th scope="col">Resultado</th>
            <th scope="col">Medido</th>
            <th scope="col">Límite</th>
            <th scope="col">Norma</th>
            <th scope="col">Detalle</th>
          </tr>
        </thead>
        <tbody>
          {sortFindings(detail.compliance).map((row) => (
            <tr key={row.rule} className={row.blocking ? 'alarming-row' : undefined}>
              <td>{row.rule}</td>
              <td>{OUTCOME_LABEL[row.outcome]}</td>
              <td>{row.measured === null ? '—' : `${row.measured} ${row.unit ?? ''}`}</td>
              <td>{row.limit === null ? '—' : `${String(row.limit)} ${row.unit ?? ''}`}</td>
              <td>{citationFor(row) ?? '—'}</td>
              <td>{row.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function BeforeAfter({ detail }: { detail: ReviewDetail }) {
  const { before, after } = evidenceByStage(detail);
  const reused = reusedEvidence(detail);
  const tampered = tamperedEvidence(detail);
  return (
    <section>
      <h3>Antes y después</h3>
      {reused.length > 0 && (
        <p role="alert">
          {/* Por hash, no por un modelo: un archivo idéntico es idéntico. */}
          La misma fotografía se envió como antes y como después: {reused.join(', ')}
        </p>
      )}
      {tampered.length > 0 && (
        <p role="alert">
          Hay evidencia cuyo hash no coincide con lo que registró el dispositivo:{' '}
          {tampered.map((item) => item.storage_key).join(', ')}
        </p>
      )}
      {detail.missing_photos.map((problem) => (
        <p key={problem} role="alert">{problem}</p>
      ))}
      <div className="evidence-pair">
        <figure>
          <figcaption>Antes ({before.length})</figcaption>
          <ul>
            {before.map((item) => (
              <li key={item.evidence_id}><code>{item.storage_key}</code></li>
            ))}
          </ul>
        </figure>
        <figure>
          <figcaption>Después ({after.length})</figcaption>
          <ul>
            {after.map((item) => (
              <li key={item.evidence_id}><code>{item.storage_key}</code></li>
            ))}
          </ul>
        </figure>
      </div>
    </section>
  );
}

function Observations({ detail }: { detail: ReviewDetail }) {
  if (detail.observations.length === 0 && detail.history.length === 0) return null;
  return (
    <section>
      <h3>Historial</h3>
      {detail.observations.length > 0 && (
        <ul>
          {detail.observations.map((observation) => (
            <li key={observation.field_key}>
              <strong>{observation.field_key}</strong>: {observation.message}
            </li>
          ))}
        </ul>
      )}
      <ol>
        {detail.history.map((row, index) => (
          <li key={`${row.decided_at}-${index}`}>
            {row.decision} · {row.reviewer_sub} · {row.decided_at?.slice(0, 16) ?? ''}
            {row.note ? ` — ${row.note}` : ''}
          </li>
        ))}
      </ol>
    </section>
  );
}

function GisTrayPanel({ tray }: { tray: GisTray }) {
  const manual = needsArcFm(tray);
  return (
    <section className="gis-tray">
      <h2>Bandeja hacia el GIS</h2>
      <p>
        {tray.proposals.length} propuesta(s) en espera, {tray.batches.length} lote(s) despachado(s).
        {manual > 0 && (
          <>
            {' '}
            {/* La plataforma nunca escribe conectividad (ADR-001): esto lo aplica un editor. */}
            <strong>{manual}</strong> requieren que un editor las aplique en ArcFM.
          </>
        )}
      </p>
      <table>
        <thead>
          <tr>
            <th scope="col">Tipo de activo</th>
            <th scope="col">Acción</th>
            <th scope="col">Estado</th>
            <th scope="col">ArcFM</th>
            <th scope="col">Creada</th>
          </tr>
        </thead>
        <tbody>
          {tray.proposals.slice(0, 25).map((proposal) => (
            <Fragment key={proposal.proposal_id}>
              <tr>
                <td>{proposal.asset_type_key}</td>
                <td>{proposal.action}</td>
                <td>{proposal.status}</td>
                <td>{proposal.requires_arcfm ? 'sí' : 'no'}</td>
                <td>{proposal.created_at?.slice(0, 16) ?? '—'}</td>
              </tr>
            </Fragment>
          ))}
          {tray.proposals.length === 0 && (
            <tr>
              <td colSpan={5}>Nada en espera de ir al GIS.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
