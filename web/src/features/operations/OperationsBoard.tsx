/**
 * The operational board (RF-130).
 *
 * What is where, what is late, who is getting work done, and how long the work takes. The first
 * three come from the work orders; the fourth comes from the audit trail, and could not be shown at
 * all until the trail existed.
 *
 * It refreshes itself every five minutes, which is the requirement's acceptance criterion, and says
 * when it last managed to: a board that refreshes silently looks equally fresh when the refresh has
 * been failing for an hour.
 *
 * Every judgement lives in `board.ts` and is tested there. This file renders and calls.
 */

import { useCallback, useEffect, useState } from 'react';

import { fetchOperationalBoard, type Leg, type OperationalBoard } from '../../api/analytics';
import {
  freshness,
  legCaveats,
  legHeadline,
  legTail,
  openTotal,
  orderedStates,
  REFRESH_MS,
  stateLabel,
} from './board';

export interface OperationsBoardProps {
  /** Required: nothing crosses between business units (ADR-009). */
  businessUnit: string;
  /** Injected so a test can control the clock rather than wait five minutes. */
  refreshMs?: number;
  now?: () => Date;
}

export function OperationsBoard({
  businessUnit,
  refreshMs = REFRESH_MS,
  now = () => new Date(),
}: OperationsBoardProps) {
  const [board, setBoard] = useState<OperationalBoard | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setBoard(await fetchOperationalBoard(businessUnit, signal));
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        // El tablero anterior se queda en pantalla con el aviso encima: borrarlo dejaría al
        // supervisor sin nada, y unos datos de hace cinco minutos con su advertencia valen más que
        // una pantalla vacía.
        setError((cause as Error).message);
      }
    },
    [businessUnit],
  );

  useEffect(() => {
    const controller = new AbortController();
    // El setState ocurre tras el await dentro del callback, no en el cuerpo del efecto.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    const timer = setInterval(() => void load(), refreshMs);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [load, refreshMs]);

  return (
    <section className="ops-board">
      <header>
        <h1>Tablero operativo</h1>
        {board && (
          <p className="review-hint">
            {openTotal(board)} OT abiertas. {freshness(board.computed_at, now())} Se actualiza solo
            cada {Math.round(refreshMs / 60000)} minutos.
          </p>
        )}
        {error && (
          <p role="alert" className="board-error">
            {error}
          </p>
        )}
      </header>

      {board === null ? (
        error === null && <p>Cargando el tablero…</p>
      ) : (
        <div className="ai-board-panels">
          <SlaPanel board={board} />
          <StatesPanel board={board} />
          <TimesPanel board={board} />
          <CrewsPanel board={board} />
        </div>
      )}
    </section>
  );
}

function SlaPanel({ board }: { board: OperationalBoard }) {
  const { overdue, due_soon, due_soon_hours, without_sla } = board.sla;
  return (
    <section aria-label="Compromisos de tiempo">
      <h2>SLA</h2>
      <p role={overdue > 0 ? 'alert' : 'status'} className={overdue > 0 ? 'ops-late' : undefined}>
        {overdue} OT vencida(s) y abierta(s).
      </p>
      <p>
        {due_soon} vence(n) en las próximas {due_soon_hours} horas.
      </p>
      {without_sla > 0 && (
        /* «0 vencidas» sobre cien OT que nunca tuvieron fecha no informa de nada. */
        <p className="ai-board-note">{without_sla} OT abiertas sin compromiso de tiempo cargado.</p>
      )}
    </section>
  );
}

function StatesPanel({ board }: { board: OperationalBoard }) {
  const rows = orderedStates(board.by_state);
  return (
    <section aria-label="OT por estado">
      <h2>Dónde está el trabajo</h2>
      {rows.length === 0 ? (
        <p>Sin OT en el periodo.</p>
      ) : (
        <table>
          <tbody>
            {rows.map((row) => (
              <tr key={row.state}>
                <td>{stateLabel(row.state)}</td>
                <td>{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function TimesPanel({ board }: { board: OperationalBoard }) {
  return (
    <section aria-label="Tiempos">
      <h2>Cuánto tarda el trabajo</h2>
      {board.legs.map((leg: Leg) => (
        <div key={leg.key} className="ops-leg">
          <h3>{leg.label}</h3>
          <p role="status">{legHeadline(leg)}</p>
          {legTail(leg) && <p className="ai-board-note">{legTail(leg)}</p>}
          {legCaveats(leg).map((line) => (
            <p key={line} className="ai-board-note">
              {line}
            </p>
          ))}
        </div>
      ))}
    </section>
  );
}

function CrewsPanel({ board }: { board: OperationalBoard }) {
  return (
    <section aria-label="Productividad por cuadrilla">
      <h2>Cuadrillas</h2>
      <p className="ai-board-note">
        Lo cerrado en campo es el trabajo de la cuadrilla; lo que pase después en revisión es de la
        oficina.
      </p>
      {board.crews.length === 0 ? (
        <p>Sin cuadrillas registradas en esta unidad.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Cuadrilla</th>
              <th>Cerradas en campo</th>
              <th>Aprobadas</th>
              <th>Abiertas ahora</th>
            </tr>
          </thead>
          <tbody>
            {board.crews.map((crew) => (
              <tr key={crew.crew_id}>
                <td>{crew.crew_name}</td>
                <td>{crew.closed_in_field}</td>
                <td>{crew.approved}</td>
                <td>{crew.open_now}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
