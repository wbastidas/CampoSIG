/**
 * The proposal tray (RF-013, RF-114).
 *
 * «La propuesta aparece en la bandeja del supervisor; al aprobarla pasa a Planificada; al rechazarla
 * guarda el motivo.» Three actions, and each one says what it is about to do before it does it.
 *
 * The screen's one insistence: a priority the platform **estimated** never looks like one it
 * computed. The badge, the arithmetic and the caveats in the server's own words are all there for
 * that, because the first supervisor who checks a number and finds it was a default stops trusting
 * the whole tray.
 *
 * Every judgement lives in `proposals.ts` and is tested there.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  approveProposal,
  fetchTray,
  mergeProposal,
  type Proposal,
  rejectProposal,
  type Tray,
} from '../../api/proposals';
import {
  canDecide,
  confidenceLabel,
  countRows,
  deadlineLabel,
  type DecisionDraft,
  decisionAdvice,
  decisionProblems,
  EMPTY_DECISION,
  originLabel,
  PRIORITY_LABEL,
  priorityLabel,
  reasonOptions,
  reasonsAdvice,
  signalLabel,
  signalOf,
  stateLabel,
  trayHeadline,
  trayRows,
} from './proposals';

export interface ProposalsScreenProps {
  businessUnit: string;
  /** False for anybody who is not a supervisor or planner. The server enforces it too. */
  mayDecide?: boolean;
}

const STATES = ['propuesta', 'aprobada', 'fusionada', 'rechazada'];

export function ProposalsScreen({ businessUnit, mayDecide = true }: ProposalsScreenProps) {
  const [state, setState] = useState('propuesta');
  const [tray, setTray] = useState<Tray | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [draft, setDraft] = useState<DecisionDraft>(EMPTY_DECISION);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setTray(await fetchTray(businessUnit, state, signal));
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        setError((cause as Error).message);
      }
    },
    [businessUnit, state],
  );

  useEffect(() => {
    const controller = new AbortController();
    // El setState ocurre tras el await dentro del callback, no en el cuerpo del efecto.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const start = (proposal: Proposal) => {
    setOpenId(proposal.id === openId ? null : proposal.id);
    setDraft(EMPTY_DECISION);
    setStatus(null);
  };

  const decide = async (proposal: Proposal) => {
    setBusy(true);
    try {
      if (draft.decision === 'aprobar') {
        const result = await approveProposal(businessUnit, proposal.id, {
          ...(draft.priority ? { priority: draft.priority } : {}),
          ...(draft.note ? { note: draft.note } : {}),
        });
        setStatus(
          `Aprobada: la OT queda ${stateLabel(result.state)} con prioridad ` +
            `${priorityLabel(result.proposal.priority)}.`,
        );
      } else if (draft.decision === 'fusionar') {
        await mergeProposal(businessUnit, proposal.id, {
          work_order_id: draft.workOrderId.trim(),
          ...(draft.note ? { note: draft.note } : {}),
        });
        setStatus('Fusionada: los hallazgos quedan en la descripción de la OT de destino.');
      } else {
        await rejectProposal(businessUnit, proposal.id, {
          reason_code: draft.reasonCode,
          ...(draft.note ? { note: draft.note } : {}),
        });
        setStatus('Rechazada: el motivo queda guardado como señal de entrenamiento.');
      }
      setOpenId(null);
      setDraft(EMPTY_DECISION);
      await load();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const rows = trayRows(tray);
  const reasons = reasonOptions(tray);
  const reasonsProblem = reasonsAdvice(tray);

  return (
    <section aria-label="Bandeja de OT propuestas">
      <h2>OT propuestas</h2>
      <p>{trayHeadline(tray)}</p>

      <label>
        Estado
        <select value={state} onChange={(event) => setState(event.target.value)}>
          {STATES.map((code) => (
            <option key={code} value={code}>
              {stateLabel(code)}
            </option>
          ))}
        </select>
      </label>

      <ul aria-label="Conteo por estado">
        {countRows(tray).map((row) => (
          <li key={row.state}>
            {row.label}: {row.total}
          </li>
        ))}
      </ul>

      {error && <p role="alert">{error}</p>}
      {status && <p role="status">{status}</p>}
      {reasonsProblem && <p role="alert">{reasonsProblem}</p>}

      <ul aria-label="Propuestas">
        {rows.map((proposal) => (
          <li key={proposal.id}>
            <article>
              <h3>
                {proposal.defect_code} en {proposal.asset_code ?? 'activo sin código'}
              </h3>
              <p>
                <strong>
                  {proposal.criticality.annex_band} {priorityLabel(proposal.priority)}
                </strong>{' '}
                — {confidenceLabel(proposal.criticality)}
              </p>
              <p>{proposal.criticality.explanation}</p>
              <p>Plazo sugerido: {deadlineLabel(proposal.suggested_deadline_hours)}</p>
              <p>{originLabel(proposal.origin)}</p>
              {proposal.criticality.estimated && (
                <ul aria-label={`Lo que no se pudo saber de ${proposal.id}`}>
                  {proposal.criticality.caveats.map((caveat) => (
                    <li key={caveat}>{caveat}</li>
                  ))}
                </ul>
              )}
              <p>{proposal.justification}</p>
              {proposal.model_name && (
                <p>
                  {proposal.model_name} {proposal.model_version ?? ''}
                  {proposal.confidence !== null
                    ? ` — confianza ${Math.round(proposal.confidence * 100)} %`
                    : ''}
                </p>
              )}
              {proposal.reject_reason_code && (
                <p>Rechazada por «{proposal.reject_reason_code}»</p>
              )}
              {proposal.decided_by && <p>Decidió {proposal.decided_by}</p>}

              {mayDecide && proposal.state === 'propuesta' && (
                <button type="button" onClick={() => start(proposal)} disabled={busy}>
                  {openId === proposal.id ? 'Cerrar' : 'Decidir'}
                </button>
              )}

              {openId === proposal.id && (
                <div>
                  <fieldset>
                    <legend>Decisión</legend>
                    {(['aprobar', 'fusionar', 'rechazar'] as const).map((option) => (
                      <label key={option}>
                        <input
                          type="radio"
                          name={`decision-${proposal.id}`}
                          value={option}
                          checked={draft.decision === option}
                          onChange={() => setDraft({ ...EMPTY_DECISION, decision: option })}
                        />
                        {option}
                      </label>
                    ))}
                  </fieldset>

                  {draft.decision === 'aprobar' && (
                    <label>
                      Prioridad
                      <select
                        value={draft.priority}
                        onChange={(event) => setDraft({ ...draft, priority: event.target.value })}
                      >
                        <option value="">
                          La que calculó el anexo C ({priorityLabel(proposal.priority)})
                        </option>
                        {Object.entries(PRIORITY_LABEL).map(([code, label]) => (
                          <option key={code} value={code}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}

                  {draft.decision === 'fusionar' && (
                    <label>
                      OT de destino
                      <input
                        value={draft.workOrderId}
                        onChange={(event) =>
                          setDraft({ ...draft, workOrderId: event.target.value })
                        }
                      />
                    </label>
                  )}

                  {draft.decision === 'rechazar' && (
                    <label>
                      Motivo
                      <select
                        value={draft.reasonCode}
                        onChange={(event) => setDraft({ ...draft, reasonCode: event.target.value })}
                      >
                        <option value="">Elija un motivo</option>
                        {reasons.map((reason) => (
                          <option key={reason.code} value={reason.code}>
                            {reason.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}

                  {draft.decision === 'rechazar' && signalLabel(signalOf(tray, draft.reasonCode)) && (
                    <p>{signalLabel(signalOf(tray, draft.reasonCode))}</p>
                  )}

                  <label>
                    Nota
                    <textarea
                      value={draft.note}
                      onChange={(event) => setDraft({ ...draft, note: event.target.value })}
                    />
                  </label>

                  <p>{decisionAdvice(draft, proposal)}</p>
                  {decisionProblems(draft).map((problem) => (
                    <p role="alert" key={problem}>
                      {problem}
                    </p>
                  ))}

                  <button
                    type="button"
                    onClick={() => void decide(proposal)}
                    disabled={busy || !canDecide(draft)}
                  >
                    Confirmar
                  </button>
                </div>
              )}
            </article>
          </li>
        ))}
      </ul>
    </section>
  );
}
