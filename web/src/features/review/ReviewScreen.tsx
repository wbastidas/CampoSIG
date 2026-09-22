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

import { FormView } from '../../forms/FormView';

import {
  ApprovalBlocked,
  approveBatch,
  type BatchOutcome,
  type DecisionKind,
  fetchBatchPreview,
  fetchDetail,
  fetchGisTray,
  fetchQueue,
  type GisTray,
  issueActa,
  type QueueItem,
  type ReviewDetail,
  submitDecision,
} from '../../api/review';
import {
  ATTENTION_COLOR,
  ATTENTION_LABEL,
  CATEGORY_LABEL,
  acceptanceRate,
  attentionFor,
  batchBarLabel,
  batchOutcomeLines,
  batchPlan,
  batchable,
  citationFor,
  displayValue,
  evidenceByStage,
  hasDegradations,
  missingReportReason,
  needsArcFm,
  observationCitation,
  OUTCOME_LABEL,
  PLACEMENT_LABEL,
  reusedEvidence,
  RISK_LABEL,
  sortDegradations,
  sortFindings,
  sortObservations,
  sortQueue,
  tamperedEvidence,
  unconfirmedAiValues,
} from './decision';

export interface ReviewScreenProps {
  /** Required: nothing crosses between business units (ADR-009). */
  businessUnit: string;
  /**
   * Who is reviewing, for the screen to show. **Not** what signs the decision: that comes from
   * the token on the server (ADR-013), and sending it from here would be a field that looks
   * authoritative and is discarded.
   */
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
  const [acta, setActa] = useState<{ code: string; hash: string } | null>(null);
  // La aprobación en lote (RF-176). `picked` son las que el supervisor marcó; `sampled` es el
  // tamaño de la muestra según el servidor, que es quien tiene la política de redondeo.
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [sampled, setSampled] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [batchOutcome, setBatchOutcome] = useState<BatchOutcome | null>(null);

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
    // El setState ocurre tras el await dentro del callback, no en el cuerpo del efecto. La
    // regla no puede verlo a través de la indirección, y reescribir "cargar al montar" para
    // complacerla lo empeoraría.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadQueue(controller.signal);
    void loadTray(controller.signal);
    return () => controller.abort();
  }, [loadQueue, loadTray]);

  useEffect(() => {
    // Nada que cargar: el detalle ya se limpió al cambiar la selección, no hace falta un
    // setState aquí que provoque un render en cascada.
    if (selected === null) return;
    const controller = new AbortController();
    void (async () => {
      try {
        setDetail(await fetchDetail(businessUnit, selected, controller.signal));
        setRefused([]);
        setError(null);
        // El aviso del acta pertenecía a la OT anterior; dejarlo en pantalla haría creer que se
        // emitió el acta de esta.
        setActa(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        setError((cause as Error).message);
      }
    })();
    return () => controller.abort();
  }, [businessUnit, selected]);

  /**
   * How many of the current selection the server would hold back (RF-176).
   *
   * Asked of the server on every change instead of computed here: the rounding rule is policy, and
   * a copy of it in the browser is a copy free to drift from the one that actually decides. The
   * call is a bare GET with a number.
   */
  useEffect(() => {
    if (picked.size === 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSampled(null);
      return;
    }
    const controller = new AbortController();
    void (async () => {
      try {
        const preview = await fetchBatchPreview(businessUnit, picked.size, controller.signal);
        setSampled(preview.sampled);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        // Sin muestra conocida no se promete un número: el plan dirá que está calculando, y el
        // botón queda deshabilitado. Inventarla aquí sería inventar la política.
        setSampled(null);
      }
    })();
    return () => controller.abort();
  }, [businessUnit, picked]);

  const togglePicked = useCallback((workOrderId: string) => {
    setBatchOutcome(null);
    setConfirming(false);
    setPicked((current) => {
      const next = new Set(current);
      if (next.has(workOrderId)) next.delete(workOrderId);
      else next.add(workOrderId);
      return next;
    });
  }, []);

  /**
   * Approve the selected batch (RF-176).
   *
   * Two presses, not one: the first asks, the second does it. A bulk approval releases as-built
   * proposals towards the corporate GIS for every order in it, and that is not a thing to do on a
   * mis-click. The sample is drawn by the server, so nothing here decides what is held back.
   */
  const runBatch = useCallback(async () => {
    if (picked.size === 0) return;
    setBusy(true);
    try {
      const outcome = await approveBatch(businessUnit, [...picked], note || undefined);
      setBatchOutcome(outcome);
      setPicked(new Set());
      setConfirming(false);
      setNote('');
      setError(null);
      await Promise.all([loadQueue(), loadTray()]);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }, [businessUnit, picked, note, loadQueue, loadTray]);

  /**
   * Emit the acta and hand the browser the file (RF-115).
   *
   * Through `fetch` rather than a link, because the request needs the bearer token. The
   * verification code is shown afterwards so the supervisor can read it back to whoever holds
   * the paper — a QR that will not focus is a common enough problem in the field.
   */
  const printActa = useCallback(async () => {
    if (selected === null) return;
    setBusy(true);
    try {
      const issued = await issueActa(businessUnit, selected);
      const url = URL.createObjectURL(issued.blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `acta-${selected}.pdf`;
      link.click();
      // Revoked right after: an object URL that is never released keeps the whole PDF in memory
      // for as long as the tab lives, and a supervisor prints dozens in a morning.
      URL.revokeObjectURL(url);
      setActa({ code: issued.verificationCode, hash: issued.contentHash });
      setError(null);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }, [businessUnit, selected]);

  const decide = useCallback(
    async (decision: DecisionKind) => {
      if (selected === null) return;
      setBusy(true);
      setRefused([]);
      try {
        await submitDecision(businessUnit, selected, {
          decision,
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
    [businessUnit, selected, note, loadQueue, loadTray],
  );

  const clock = now();
  const ordered = sortQueue(queue, clock);

  return (
    <section className="review">
      <header>
        <h1>Revisión</h1>
        <p>
          {total} orden(es) esperando decisión. Revisa {reviewer}.
        </p>
        {error && <p role="alert" className="board-error">{error}</p>}
      </header>

      <div className="review-layout">
        <nav aria-label="Cola de revisión">
          <BatchApproval
            batchable={batchable(ordered).length}
            picked={picked.size}
            sampled={sampled}
            confirming={confirming}
            busy={busy}
            outcome={batchOutcome}
            onAsk={() => setConfirming(true)}
            onCancel={() => setConfirming(false)}
            onConfirm={() => void runBatch()}
          />
          <ul className="review-queue">
            {ordered.map((item) => {
              const bar = batchBarLabel(item);
              const label = item.code ?? item.work_order_id.slice(0, 8);
              return (
                <li key={item.work_order_id}>
                  {bar === null ? (
                    <input
                      type="checkbox"
                      aria-label={`Incluir ${label} en el lote`}
                      checked={picked.has(item.work_order_id)}
                      onChange={() => togglePicked(item.work_order_id)}
                    />
                  ) : (
                    /* Dicho en la fila, no descubierto en los rechazos: así el supervisor ve por
                       qué esta OT no entra en el lote antes de intentarlo (RF-176). */
                    <span className="review-nobatch">{bar}</span>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setDetail(null);
                      setSelected(item.work_order_id);
                    }}
                    aria-current={selected === item.work_order_id}
                  >
                    <strong>{label}</strong>
                    <span>{item.work_type}</span>
                    <span>{item.priority}</span>
                    {item.sla_due_at && <span className="sla">vence {item.sla_due_at.slice(0, 10)}</span>}
                  </button>
                </li>
              );
            })}
            {ordered.length === 0 && <li>Nada esperando revisión.</li>}
          </ul>
        </nav>

        {detail === null ? (
          <p>Seleccione una orden de la cola.</p>
        ) : (
          <article className="review-detail">
            <ReviewHeader detail={detail} />
            <Blockers detail={detail} refused={refused} />
            <PreReview detail={detail} />
            <Degradations detail={detail} />
            {/* La captura misma, antes de la auditoría: se revisa lo que la cuadrilla escribió,
                no solo lo que la plataforma opina de ello (I6, vista de formulario). */}
            <FormView
              schema={detail.form.schema}
              uiSchema={detail.form.ui_schema}
              answers={detail.response?.answers ?? {}}
              rules={detail.form.rules}
              provenance={detail.provenance}
              warnings={detail.form.warnings}
            />
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

            <fieldset>
              <legend>Acta</legend>
              <p className="review-hint">
                {detail.work_order.state === 'aprobada'
                  ? 'El acta lleva las fotos, los hallazgos, la procedencia de cada valor de IA y un QR de verificación.'
                  : 'Esta OT todavía no está aprobada, así que el acta saldrá marcada como borrador.'}
              </p>
              <button type="button" disabled={busy} onClick={() => void printActa()}>
                Emitir acta en PDF
              </button>
              {acta && (
                <p role="status" className="review-acta">
                  Acta emitida. Código de verificación <code>{acta.code}</code>. Huella{' '}
                  <code>{acta.hash.slice(0, 16)}…</code>
                </p>
              )}
            </fieldset>
          </article>
        )}
      </div>

      {tray && <GisTrayPanel tray={tray} />}
    </section>
  );
}

/**
 * Batch approval of low-risk work orders (RF-176).
 *
 * The requirement grants the bulk action and charges two things for it, and this panel is where both
 * are visible: the approval happens because a person pressed something — twice, since it releases
 * as-built proposals for every order in the batch — and a mandatory sample is held back for
 * one-by-one verification, said in the plan *before* the press and again in the result after it.
 *
 * "12 aprobadas" without "1 apartada" reads as a finished batch. The one held back is the point.
 */
function BatchApproval({
  batchable,
  picked,
  sampled,
  confirming,
  busy,
  outcome,
  onAsk,
  onCancel,
  onConfirm,
}: {
  batchable: number;
  picked: number;
  sampled: number | null;
  confirming: boolean;
  busy: boolean;
  outcome: BatchOutcome | null;
  onAsk: () => void;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <section className="review-batch" aria-label="Aprobación en lote">
      <h2>Aprobación en lote</h2>
      <p className="review-hint">
        {batchable} de riesgo bajo en esta página. Las demás se revisan una por una.
      </p>
      <p role="status">{batchPlan(picked, sampled)}</p>
      {!confirming ? (
        <button type="button" disabled={picked === 0 || sampled === null || busy} onClick={onAsk}>
          Aprobar {picked} en lote
        </button>
      ) : (
        <div className="review-batch-confirm" role="group" aria-label="Confirmar el lote">
          <p>
            Se aprobarán {Math.max(picked - (sampled ?? 0), 0)} OT y se liberarán sus propuestas
            as-built hacia el SIG. No se puede deshacer en bloque.
          </p>
          <button type="button" disabled={busy} onClick={onConfirm}>
            Confirmar aprobación en lote
          </button>
          <button type="button" disabled={busy} onClick={onCancel}>
            Cancelar
          </button>
        </div>
      )}
      {outcome && (
        <div className="review-batch-outcome" role="status">
          <ul>
            {batchOutcomeLines(outcome).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          {outcome.refused.length > 0 && (
            <ul aria-label="OT rechazadas del lote">
              {outcome.refused.map((item) => (
                <li key={item.work_order_id}>
                  <strong>{item.code ?? item.work_order_id.slice(0, 8)}</strong>: {item.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

/**
 * The pre-review report (RF-111, RF-175).
 *
 * Above the evidence and below the blockers: it is context for reading the capture, not a verdict on
 * it. The heading states the risk level in words — these screens get read on office monitors of every
 * vintage, and a colour-only signal is one a colour-blind supervisor does not receive at all.
 *
 * When there is no report, the reason is shown instead of nothing. "It failed" and "it has not run
 * yet" are different things to somebody about to decide without it, and neither of them is a reason
 * to wait: the deterministic findings above are complete either way (RF-204).
 */
function PreReview({ detail }: { detail: ReviewDetail }) {
  const missing = missingReportReason(detail);
  if (missing !== null) {
    return (
      <section aria-label="Informe de pre-revisión">
        <h3>Informe de pre-revisión</h3>
        <p role="status">{missing}</p>
      </section>
    );
  }

  const report = detail.agent_report?.report;
  if (!report) return null;

  return (
    <section aria-label="Informe de pre-revisión">
      <h3>
        Informe de pre-revisión — {RISK_LABEL[report.risk_level]}{' '}
        <span className="prereview__meta">{report.graph_version}</span>
      </h3>
      <p>{report.summary}</p>

      {report.discarded > 0 && (
        <p role="status">
          {/* Un nodo que empieza a producir observaciones sin apoyo tiene que notarse en la
              ejecución siguiente y no en seis meses. */}
          El guardrail descartó {report.discarded} observación(es) por no señalar evidencia.
        </p>
      )}

      {report.observations.length === 0 ? (
        <p>Sin observaciones: las reglas deterministas no encontraron nada que revisar.</p>
      ) : (
        <ul className="prereview__observations">
          {sortObservations(report.observations).map((observation) => {
            const citation = observationCitation(observation);
            return (
              <li key={observation.id}>
                <strong>{CATEGORY_LABEL[observation.category]}</strong>{' '}
                <span className="severity-chip">{observation.severity}</span>
                <div>{observation.message}</div>
                {observation.suggested_action && (
                  <div className="prereview__action">{observation.suggested_action}</div>
                )}
                {citation && <div className="prereview__citation">{citation}</div>}
                {/* La evidencia que la observación señala: sin esto el supervisor tendría que ir a
                    buscarla, que es el trabajo que el informe existe para ahorrar. */}
                <ul className="prereview__evidence">
                  {observation.evidence.map((ref, index) => (
                    <li key={`${ref.type}-${index}`}>
                      {ref.detail ?? ref.json_path ?? ref.evidence_id ?? ref.type}
                    </li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

/**
 * What the AI layer will not do on this deployment (RF-204).
 *
 * Shown above the evidence, not tucked at the bottom: a supervisor deciding without the agent's
 * report should know that before reading, not after. And it only renders when something is
 * actually missing — a permanent notice becomes part of the furniture, and then nobody reads it on
 * the day it means something.
 */
function Degradations({ detail }: { detail: ReviewDetail }) {
  if (!hasDegradations(detail)) return null;
  return (
    <section aria-label="Ayuda de IA no disponible">
      <h3>Lo que la IA no va a aportar en esta revisión</h3>
      <ul>
        {sortDegradations(detail.degradations).map((entry) => (
          <li key={entry.alias}>
            <strong>{PLACEMENT_LABEL[entry.placement]}</strong>: {entry.purpose} — {entry.reason}
          </li>
        ))}
      </ul>
      <p className="review-hint">
        La decisión no depende de esto: los hallazgos normativos y los impedimentos de arriba son
        deterministas y están completos.
      </p>
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
              <td>{displayValue(entry.proposed_value)}</td>
              <td>{displayValue(entry.final_value)}</td>
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
              <td>{row.limit === null ? '—' : `${displayValue(row.limit)} ${row.unit ?? ''}`}</td>
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
