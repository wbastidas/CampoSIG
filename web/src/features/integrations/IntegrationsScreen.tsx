/**
 * The integrations screen (RF-125).
 *
 * What a person needs in order to fix an integration: which connector is unhappy, exactly what
 * failed, and a button that retries it. The retry button is the reason this screen exists —
 * a ledger you can read but not act on just tells you about the problem twice a day.
 *
 * Every judgement lives in `ledger.ts` and is tested there. This file renders and calls.
 */

import { Fragment, useCallback, useEffect, useState } from 'react';

import {
  type ConnectorHealth,
  fetchConnectors,
  fetchEvents,
  type IntegrationEvent,
  retryEvent,
} from '../../api/integrations';
import {
  canRetry,
  connectorHealth,
  HEALTH_COLOR,
  HEALTH_LABEL,
  nextAttemptIn,
  shortError,
  sortConnectors,
  sortEvents,
  STATUS_LABEL,
  summarise,
} from './ledger';

/** A broken connector should not need a page reload to stop being broken on screen. */
const REFRESH_MS = 30_000;

export interface IntegrationsScreenProps {
  /** Required: nothing crosses between business units (ADR-009). */
  businessUnit: string;
  /** Who is pressing retry. Recorded on the event, so the ledger says who intervened. */
  operator: string;
  now?: () => Date;
}

export function IntegrationsScreen({
  businessUnit,
  operator,
  now = () => new Date(),
}: IntegrationsScreenProps) {
  const [connectors, setConnectors] = useState<ConnectorHealth[]>([]);
  const [events, setEvents] = useState<IntegrationEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const [health, ledger] = await Promise.all([
          fetchConnectors(businessUnit, signal),
          fetchEvents(businessUnit, { limit: 200 }, signal),
        ]);
        setConnectors(health);
        setEvents(ledger);
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        // The stale ledger stays on screen beside the error: blanking it would leave the
        // operator with less than they had a second ago.
        setError((cause as Error).message);
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
    void load(controller.signal);
    const timer = setInterval(() => void load(), REFRESH_MS);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [load]);

  const onRetry = useCallback(
    async (event: IntegrationEvent) => {
      setBusy(event.id);
      try {
        await retryEvent(businessUnit, event.id, operator);
        await load();
      } catch (cause) {
        setError((cause as Error).message);
      } finally {
        setBusy(null);
      }
    },
    [businessUnit, operator, load],
  );

  const clock = now();
  const summary = summarise(connectors, events);

  return (
    <section className="integrations">
      <header>
        <h1>Integraciones</h1>
        {error && <p role="alert" className="board-error">{error}</p>}
      </header>

      <dl className="integrations-summary">
        <div className={summary.waitingForAPerson > 0 ? 'alarming' : undefined}>
          <dt>Esperando a una persona</dt>
          <dd>{summary.waitingForAPerson}</dd>
        </div>
        <div>
          <dt>En cola</dt>
          <dd>{summary.pending}</dd>
        </div>
        <div>
          <dt>Entregados</dt>
          <dd>{summary.delivered}</dd>
        </div>
        <div>
          <dt>Descartados</dt>
          <dd>{summary.abandoned}</dd>
        </div>
      </dl>

      <h2>Conectores</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Estado</th>
            <th scope="col">Conector</th>
            <th scope="col">En cola</th>
            <th scope="col">Esperando a una persona</th>
            <th scope="col">Entregados</th>
            <th scope="col">Último error</th>
          </tr>
        </thead>
        <tbody>
          {sortConnectors(connectors).map((row) => {
            const health = connectorHealth(row);
            return (
              <tr key={row.connector}>
                <td>
                  <span
                    className="severity-chip"
                    style={{ backgroundColor: HEALTH_COLOR[health] }}
                    aria-label={HEALTH_LABEL[health]}
                  >
                    {HEALTH_LABEL[health]}
                  </span>
                </td>
                <td>{row.connector}</td>
                <td>{row.pending}</td>
                <td className={row.waiting_for_a_person > 0 ? 'alarming' : undefined}>
                  {row.waiting_for_a_person}
                </td>
                <td>{row.delivered}</td>
                <td>{row.last_error ?? '—'}</td>
              </tr>
            );
          })}
          {connectors.length === 0 && (
            <tr>
              <td colSpan={6}>Todavía no hay intercambios registrados en esta unidad.</td>
            </tr>
          )}
        </tbody>
      </table>

      <h2>Bitácora de intercambios</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Estado</th>
            <th scope="col">Conector</th>
            <th scope="col">Tipo</th>
            <th scope="col">Referencia</th>
            <th scope="col">Intentos</th>
            <th scope="col">Próximo intento</th>
            <th scope="col">Error</th>
            <th scope="col">Acción</th>
          </tr>
        </thead>
        <tbody>
          {sortEvents(events).map((row) => (
            // La key va en el Fragment, no en las filas: dos <tr> por evento y React
            // necesita identificar el par, no cada mitad.
            <Fragment key={row.id}>
              <tr className={row.needs_attention ? 'alarming-row' : undefined}>
                <td>{STATUS_LABEL[row.status]}</td>
                <td>{row.connector}</td>
                <td>{row.kind}</td>
                <td>{row.external_ref ?? '—'}</td>
                <td>{row.attempts}</td>
                <td>{nextAttemptIn(row, clock) ?? '—'}</td>
                <td>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => setExpanded(expanded === row.id ? null : row.id)}
                    disabled={!row.last_error}
                  >
                    {shortError(row) ?? '—'}
                  </button>
                </td>
                <td>
                  <button
                    type="button"
                    onClick={() => void onRetry(row)}
                    disabled={!canRetry(row) || busy === row.id}
                  >
                    {busy === row.id ? 'Reintentando…' : 'Reintentar'}
                  </button>
                </td>
              </tr>
              {expanded === row.id && (
                <tr>
                  <td colSpan={8}>
                    <pre>{row.last_error}</pre>
                    <details>
                      <summary>Payload enviado</summary>
                      <pre>{JSON.stringify(row.payload, null, 2)}</pre>
                    </details>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
          {events.length === 0 && (
            <tr>
              <td colSpan={8}>Sin intercambios. Nada que reintentar.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
