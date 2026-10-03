/**
 * Consignaciones: el tablero del Centro de Control y del planificador (RF-024).
 *
 * Dos roles en una pantalla y no en dos, porque los dos miran la misma cola: el planificador pide y
 * ve en qué va lo que pidió; el Centro de Control otorga con número o niega con motivo. Lo que la
 * pantalla no hace es esconder botones para explicar permisos — el servidor rechaza igual, y aquí se
 * dice por qué antes del clic, incluida la única negativa que sorprende: quien pidió no otorga.
 *
 * Todo juicio vive en `outages.ts` y se prueba ahí.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  approveOutage,
  fetchOutages,
  handBackOutage,
  type OutageList,
  type OutageStateValue,
  rejectOutage,
  requestOutage,
} from '../../api/outages';
import {
  authorityLine,
  canDecide,
  canHandBack,
  type DecisionDraft,
  decisionAdvice,
  decisionProblems,
  EMPTY_DECISION,
  isOwnRequest,
  type OutageRow,
  overdueWarning,
  requestProblems,
  rows,
  stateLabel,
  STATES,
  unusedWarning,
  windowLabel,
} from './outages';

export interface OutagesScreenProps {
  businessUnit: string;
  /** The token's subject, so the screen can say «usted la pidió» before the server's 403. */
  subject?: string | null;
  /** False for anybody who is not the Centro de Control. The server enforces it too (ADR-013). */
  mayDecide?: boolean;
  /** False for anybody who cannot ask for one. */
  mayRequest?: boolean;
  now?: () => Date;
}

const EMPTY_REQUEST = {
  equipment: '',
  windowStart: '',
  windowEnd: '',
  feeder: '',
  substation: '',
  note: '',
};

export function OutagesScreen({
  businessUnit,
  subject = null,
  mayDecide = true,
  mayRequest = true,
  now = () => new Date(),
}: OutagesScreenProps) {
  const [state, setState] = useState<OutageStateValue | ''>('');
  const [list, setList] = useState<OutageList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [draft, setDraft] = useState<DecisionDraft>(EMPTY_DECISION);
  const [asking, setAsking] = useState(false);
  const [form, setForm] = useState(EMPTY_REQUEST);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setList(await fetchOutages(businessUnit, state || undefined, signal));
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

  const start = (row: OutageRow) => {
    setOpenId(row.request.id === openId ? null : row.request.id);
    setDraft(EMPTY_DECISION);
    setStatus(null);
  };

  const decide = async (row: OutageRow) => {
    if (decisionProblems(draft).length > 0) return;
    setBusy(true);
    try {
      if (draft.decision === 'otorgar') {
        const result = await approveOutage(
          businessUnit,
          row.request.id,
          draft.number.trim(),
          draft.note.trim() || undefined,
        );
        setStatus(`Otorgada con el N.º ${result.number ?? draft.number.trim()}.`);
      } else {
        await rejectOutage(businessUnit, row.request.id, draft.note.trim());
        setStatus('Negada: el permiso de trabajo no se habilita y el motivo queda con su autor.');
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

  const giveBack = async (row: OutageRow) => {
    setBusy(true);
    try {
      await handBackOutage(businessUnit, row.request.id);
      setStatus('Devuelta al Centro de Control: el equipo puede reenergizarse.');
      await load();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const ask = async () => {
    if (requestProblems(form).length > 0) return;
    setBusy(true);
    try {
      await requestOutage(businessUnit, {
        equipment: form.equipment.trim(),
        window_start: new Date(form.windowStart).toISOString(),
        window_end: new Date(form.windowEnd).toISOString(),
        feeder_code: form.feeder.trim() || null,
        substation_code: form.substation.trim() || null,
        note: form.note.trim() || null,
      });
      setStatus('Solicitada: espera la decisión del Centro de Control.');
      setForm(EMPTY_REQUEST);
      setAsking(false);
      await load();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const view = rows(list, now());
  const unused = unusedWarning(view);
  const overdue = overdueWarning(view);
  const formProblems = requestProblems(form);

  return (
    <section aria-label="Consignaciones">
      <h2>Consignaciones</h2>
      <p>
        {view.filter((row) => row.awaiting).length} esperan decisión del Centro de Control, de{' '}
        {view.length} en la lista.
      </p>

      {error && (
        <p role="alert" className="out-error">
          {error}
        </p>
      )}

      {unused && (
        <p role="status" className="out-warning">
          {unused}
        </p>
      )}
      {overdue && (
        <p role="status" className="out-warning">
          {overdue}
        </p>
      )}

      <label>
        Estado
        <select
          value={state}
          onChange={(event) => setState(event.target.value as OutageStateValue | '')}
        >
          {STATES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      {mayRequest && (
        <>
          <button type="button" onClick={() => setAsking(!asking)}>
            {asking ? 'Cancelar' : 'Solicitar consignación'}
          </button>
          {asking && (
            <form className="out-form" onSubmit={(event) => event.preventDefault()}>
              <label htmlFor="out-equipment">Equipo o tramo</label>
              <input
                id="out-equipment"
                value={form.equipment}
                onChange={(event) => setForm({ ...form, equipment: event.target.value })}
              />
              <label htmlFor="out-start">Desde</label>
              <input
                id="out-start"
                type="datetime-local"
                value={form.windowStart}
                onChange={(event) => setForm({ ...form, windowStart: event.target.value })}
              />
              <label htmlFor="out-end">Hasta</label>
              <input
                id="out-end"
                type="datetime-local"
                value={form.windowEnd}
                onChange={(event) => setForm({ ...form, windowEnd: event.target.value })}
              />
              <label htmlFor="out-feeder">Alimentador</label>
              <input
                id="out-feeder"
                value={form.feeder}
                onChange={(event) => setForm({ ...form, feeder: event.target.value })}
              />
              <label htmlFor="out-note">Observación</label>
              <input
                id="out-note"
                value={form.note}
                onChange={(event) => setForm({ ...form, note: event.target.value })}
              />
              {formProblems.map((problem) => (
                <p key={problem} role="status" className="out-warning">
                  {problem}
                </p>
              ))}
              <button
                type="button"
                disabled={busy || formProblems.length > 0}
                onClick={() => void ask()}
              >
                Enviar la solicitud
              </button>
            </form>
          )}
        </>
      )}

      {view.length === 0 && !error && <p>No hay consignaciones con este filtro.</p>}

      <ul className="out-list">
        {view.map((row) => (
          <li key={row.request.id} className={row.awaiting ? 'out-awaiting' : undefined}>
            <h3>
              {row.request.equipment} — {stateLabel(row.request.state)}
            </h3>
            <p>{windowLabel(row.request)}</p>
            <p>{authorityLine(row.request)}</p>
            <p className="out-meta">
              Solicitó {row.request.requested_by}
              {row.request.decided_by ? `; decidió ${row.request.decided_by}` : ''}
              {typeof row.request.orders === 'number' ? `; ${row.request.orders} OT` : ''}
            </p>
            {row.request.note && <p className="out-meta">{row.request.note}</p>}

            {row.unused && (
              <p role="status" className="out-warning">
                Otorgada y sin ninguna OT vinculada.
              </p>
            )}
            {row.overdue && (
              <p role="status" className="out-warning">
                La ventana ya cerró y la consignación sigue vigente.
              </p>
            )}

            {canHandBack(row) && (
              <button type="button" disabled={busy} onClick={() => void giveBack(row)}>
                Devolver al Centro de Control
              </button>
            )}

            {canDecide(row) && mayDecide && (
              <>
                {isOwnRequest(row, subject) ? (
                  <p role="status" className="out-warning">
                    Usted solicitó esta consignación: la otorga otra persona del Centro de Control.
                  </p>
                ) : (
                  <button type="button" onClick={() => start(row)}>
                    Decidir
                  </button>
                )}
              </>
            )}

            {openId === row.request.id && (
              <div className="out-decision">
                <label htmlFor={`dec-${row.request.id}`}>Decisión</label>
                <select
                  id={`dec-${row.request.id}`}
                  value={draft.decision}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      decision: event.target.value as DecisionDraft['decision'],
                    })
                  }
                >
                  <option value="">Elija</option>
                  <option value="otorgar">Otorgar</option>
                  <option value="negar">Negar</option>
                </select>

                {draft.decision === 'otorgar' && (
                  <>
                    <label htmlFor={`num-${row.request.id}`}>N.º de consignación</label>
                    <input
                      id={`num-${row.request.id}`}
                      value={draft.number}
                      onChange={(event) => setDraft({ ...draft, number: event.target.value })}
                    />
                  </>
                )}

                <label htmlFor={`nota-${row.request.id}`}>
                  {draft.decision === 'negar' ? 'Motivo' : 'Observación'}
                </label>
                <input
                  id={`nota-${row.request.id}`}
                  value={draft.note}
                  onChange={(event) => setDraft({ ...draft, note: event.target.value })}
                />

                {decisionAdvice(row, draft) && <p>{decisionAdvice(row, draft)}</p>}
                {decisionProblems(draft).map((problem) => (
                  <p key={problem} role="status" className="out-warning">
                    {problem}
                  </p>
                ))}

                <button
                  type="button"
                  disabled={busy || decisionProblems(draft).length > 0}
                  onClick={() => void decide(row)}
                >
                  {busy ? 'Enviando…' : 'Confirmar la decisión'}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>

      {status && (
        <p role="status" className="out-status">
          {status}
        </p>
      )}
    </section>
  );
}
