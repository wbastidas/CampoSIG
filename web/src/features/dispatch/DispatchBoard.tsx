/**
 * The dispatch board: what the crews were sent, and whether they actually have it.
 *
 * This is the screen a supervisor watches at six in the morning, before the trucks leave.
 * It is deliberately a table and not a map: the question here is not *where* the work is —
 * the planner already answered that — but whether it reached a phone, and there is nothing
 * spatial about that.
 *
 * Every judgement (what counts as blocked, what order the rows go in) lives in
 * `readiness.ts` and is tested there. This file renders.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  type CrewDispatch,
  type DeviceReadiness,
  fetchDeviceReadiness,
  fetchDispatchBoard,
} from '../../api/dispatch';
import {
  crewSeverity,
  deviceSeverity,
  formatSync,
  SEVERITY_COLOR,
  SEVERITY_LABEL,
  type Severity,
  sortCrews,
  sortDevices,
  summarise,
} from './readiness';

/** How often the board refreshes itself. A minute: crews sync on the move, and a supervisor
 *  who has to press a button to see the truth will eventually stop pressing it. */
const REFRESH_MS = 60_000;

export interface DispatchBoardProps {
  /** Required: nothing crosses between business units (ADR-009). */
  businessUnit: string;
  /** Injectable so the clock is not ambient state in tests. */
  now?: () => Date;
}

function SeverityChip({ severity }: { severity: Severity }) {
  return (
    <span
      className="severity-chip"
      style={{ backgroundColor: SEVERITY_COLOR[severity] }}
      // The colour is reinforced with text, never used alone: a supervisor with a colour
      // vision deficiency reads the same board as everyone else.
      aria-label={SEVERITY_LABEL[severity]}
    >
      {SEVERITY_LABEL[severity]}
    </span>
  );
}

export function DispatchBoard({ businessUnit, now = () => new Date() }: DispatchBoardProps) {
  const [crews, setCrews] = useState<CrewDispatch[]>([]);
  const [devices, setDevices] = useState<DeviceReadiness[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const [board, readiness] = await Promise.all([
          fetchDispatchBoard(businessUnit, signal),
          fetchDeviceReadiness(businessUnit, signal),
        ]);
        setCrews(board);
        setDevices(readiness);
        setLoadedAt(new Date());
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        // The stale board stays on screen with the error beside it. Blanking it would
        // leave the supervisor with less than they had a second ago.
        setError((cause as Error).message);
      }
    },
    [businessUnit],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    const timer = setInterval(() => void load(), REFRESH_MS);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [load]);

  const clock = now();
  const summary = summarise(crews);
  const orderedCrews = sortCrews(crews);
  const orderedDevices = sortDevices(devices);

  return (
    <section className="dispatch-board">
      <header>
        <h1>Despliegue a cuadrillas</h1>
        {loadedAt && (
          <p className="board-age">
            Datos al {loadedAt.toLocaleTimeString('es-EC')}. Cada fila muestra la última vez
            que ese teléfono habló con el servidor: el tablero es una fotografía, no un
            estado en vivo.
          </p>
        )}
        {error && <p role="alert" className="board-error">{error}</p>}
      </header>

      <dl className="dispatch-summary">
        <div>
          <dt>Cuadrillas</dt>
          <dd>{summary.crews}</dd>
        </div>
        <div>
          <dt>Asignado</dt>
          <dd>{summary.assigned}</dd>
        </div>
        <div>
          <dt>En los teléfonos</dt>
          <dd>
            {summary.delivered} ({Math.round(summary.deliveryRate * 100)} %)
          </dd>
        </div>
        <div className={summary.undelivered > 0 ? 'alarming' : undefined}>
          <dt>Sin entregar</dt>
          <dd>{summary.undelivered}</dd>
        </div>
        <div className={summary.staleOnDevice > 0 ? 'alarming' : undefined}>
          <dt>Copia desactualizada</dt>
          <dd>{summary.staleOnDevice}</dd>
        </div>
        <div>
          <dt>Fuera de plazo</dt>
          <dd>{summary.overdue}</dd>
        </div>
      </dl>

      <h2>Por cuadrilla</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Estado</th>
            <th scope="col">Cuadrilla</th>
            <th scope="col">Zona</th>
            <th scope="col">Asignado</th>
            <th scope="col">Entregado</th>
            <th scope="col">Sin entregar</th>
            <th scope="col">Copia vieja</th>
            <th scope="col">En ejecución</th>
            <th scope="col">Devuelto</th>
            <th scope="col">Dispositivos</th>
            <th scope="col">Última sincronización</th>
          </tr>
        </thead>
        <tbody>
          {orderedCrews.map((row) => (
            <tr key={row.crew_id}>
              <td><SeverityChip severity={crewSeverity(row)} /></td>
              <td>
                {row.code} — {row.name}
              </td>
              <td>{row.zone ?? '—'}</td>
              <td>{row.assigned}</td>
              <td>{row.delivered}</td>
              <td className={row.undelivered > 0 ? 'alarming' : undefined}>{row.undelivered}</td>
              <td className={row.stale_on_device > 0 ? 'alarming' : undefined}>
                {row.stale_on_device}
              </td>
              <td>{row.in_progress}</td>
              <td>{row.returned}</td>
              <td>{row.devices.length > 0 ? row.devices.join(', ') : 'ninguno'}</td>
              <td>{formatSync(row, clock)}</td>
            </tr>
          ))}
          {orderedCrews.length === 0 && (
            <tr>
              <td colSpan={11}>No hay cuadrillas activas en esta unidad de negocio.</td>
            </tr>
          )}
        </tbody>
      </table>

      <h2>Por dispositivo</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Estado</th>
            <th scope="col">Dispositivo</th>
            <th scope="col">Técnico</th>
            <th scope="col">App</th>
            <th scope="col">Modelos</th>
            <th scope="col">OT a bordo</th>
            <th scope="col">Paquete de zona</th>
            <th scope="col">Última sincronización</th>
            <th scope="col">Por qué no debería salir</th>
          </tr>
        </thead>
        <tbody>
          {orderedDevices.map((row) => (
            <tr key={row.device_key}>
              <td><SeverityChip severity={deviceSeverity(row)} /></td>
              <td>{row.device_key}</td>
              <td>{row.user_sub ?? '—'}</td>
              <td>{row.app_version ?? '—'}</td>
              <td>{row.model_package_version ?? 'sin paquete'}</td>
              <td>
                {row.held_orders}
                {row.stale_orders > 0 && <span className="alarming"> ({row.stale_orders} viejas)</span>}
              </td>
              <td>
                {row.package_zone
                  ? `${row.package_zone} v${row.package_version ?? '?'}${
                      row.package_current ? '' : ' — desactualizado'
                    }`
                  : '—'}
              </td>
              <td>{formatSync(row, clock)}</td>
              <td>
                {/* The server writes these, in Spanish, for the dispatcher. Rendered
                    verbatim so one wording is maintained in one place. */}
                {row.blockers.length === 0 ? (
                  'nada'
                ) : (
                  <ul>
                    {row.blockers.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                )}
              </td>
            </tr>
          ))}
          {orderedDevices.length === 0 && (
            <tr>
              <td colSpan={9}>No hay dispositivos registrados en esta unidad de negocio.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
