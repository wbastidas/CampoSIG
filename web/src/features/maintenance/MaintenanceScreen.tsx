/**
 * The maintenance board (RF-133).
 *
 * Three panels for the three questions the area plans with: which feeder is deteriorating, which
 * asset keeps coming back, and what is still waiting. The filters the requirement asks for — period
 * and defect type — are here, and the defect list is built from what the period actually contains
 * rather than from a hard-coded catalogue that would offer types nobody has ever recorded.
 *
 * Every judgement lives in `maintenance.ts` and is tested there.
 */

import { useCallback, useEffect, useState } from 'react';

import { fetchMaintenanceBoard, type MaintenanceBoard } from '../../api/analytics';
import {
  backlogCaveats,
  backlogHeadline,
  backlogRows,
  criticalityLabel,
  defectOptions,
  feederLine,
  percent,
  recurrenceAdvice,
} from './maintenance';

export interface MaintenanceScreenProps {
  /** Required: nothing crosses between business units (ADR-009). */
  businessUnit: string;
}

export function MaintenanceScreen({ businessUnit }: MaintenanceScreenProps) {
  const [defect, setDefect] = useState('');
  const [board, setBoard] = useState<MaintenanceBoard | null>(null);
  /** The unfiltered board, so the defect list keeps offering every type the period has. */
  const [catalogue, setCatalogue] = useState<MaintenanceBoard | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const body = await fetchMaintenanceBoard(
          businessUnit,
          { defectCode: defect || undefined },
          signal,
        );
        setBoard(body);
        if (!defect) setCatalogue(body);
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        setError((cause as Error).message);
      }
    },
    [businessUnit, defect],
  );

  useEffect(() => {
    const controller = new AbortController();
    // El setState ocurre tras el await dentro del callback, no en el cuerpo del efecto.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const options = defectOptions(catalogue ?? board ?? ({ by_defect: {} } as MaintenanceBoard));

  return (
    <section className="mnt-board">
      <header>
        <h1>Mantenimiento</h1>
        <label htmlFor="mnt-defect">Tipo de defecto</label>
        <select
          id="mnt-defect"
          value={defect}
          onChange={(event) => setDefect(event.target.value)}
        >
          <option value="">Todos</option>
          {options.map((option) => (
            <option key={option.code} value={option.code}>
              {option.code} ({option.count})
            </option>
          ))}
        </select>
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
          <section aria-label="Pendientes">
            <h2>Hallazgos abiertos</h2>
            <p role="status">{backlogHeadline(board)}</p>
            <table>
              <tbody>
                {backlogRows(board).map((row) => (
                  <tr key={row.criticality}>
                    <td>{criticalityLabel(row.criticality)}</td>
                    <td>{row.open}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {backlogCaveats(board).map((line) => (
              <p key={line} className="ai-board-note">
                {line}
              </p>
            ))}
            {/* La definición del servidor, sin parafrasear: «abierto» es una definición, no un
                hecho, y un número de pendientes cuya definición nadie ve se discute en vez de
                trabajarse. */}
            <p className="ai-board-note">{board.backlog.definition}</p>
          </section>

          <section aria-label="Defectos por alimentador">
            <h2>Defectos por alimentador</h2>
            {board.heat.by_feeder.length === 0 ? (
              <p>Sin defectos ubicados en un alimentador en el periodo.</p>
            ) : (
              <ul className="mnt-heat">
                {board.heat.by_feeder.map((row) => (
                  <li key={row.feeder_code}>
                    <strong>{row.feeder_code}</strong>
                    {/* La intensidad como barra: la plataforma no tiene la geometría de los
                        alimentadores —vive en el SIG—, así que lo honesto es mostrar el reparto. */}
                    <span
                      className="mnt-bar"
                      style={{ width: `${Math.max(row.share * 100, 2)}%` }}
                      aria-hidden="true"
                    />
                    <span className="mnt-share">{percent(row.share)}</span>
                    <div className="ai-board-note">{feederLine(row)}</div>
                  </li>
                ))}
              </ul>
            )}
            {board.heat.without_feeder > 0 && (
              <p className="ai-board-note">
                {board.heat.without_feeder} defecto(s) sin alimentador registrado: no se pueden
                ubicar, y descartarlos en silencio subreportaría todos los alimentadores.
              </p>
            )}
          </section>

          <section aria-label="Reincidencia por activo">
            <h2>Activos que vuelven</h2>
            {board.recurrence.length === 0 ? (
              <p>Ningún activo con más de un hallazgo en el periodo.</p>
            ) : (
              <ul>
                {board.recurrence.map((row) => (
                  <li key={row.asset_code}>
                    <code>{row.asset_code}</code>: {row.findings} hallazgos ·{' '}
                    {criticalityLabel(row.worst_criticality)}
                    <div className="ai-board-note">{recurrenceAdvice(row)}</div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-label="Lista de pendientes">
            <h2>Qué hay que atender</h2>
            {board.open_findings.length === 0 ? (
              <p>Nada pendiente en el periodo.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Criticidad</th>
                    <th>Activo</th>
                    <th>Defecto</th>
                    <th>Alimentador</th>
                    <th>Registrado</th>
                  </tr>
                </thead>
                <tbody>
                  {board.open_findings.map((row, index) => (
                    <tr key={`${row.work_order_id}-${row.defect_code}-${index}`}>
                      <td>{criticalityLabel(row.criticality)}</td>
                      <td>{row.asset_code ?? '—'}</td>
                      <td>{row.defect_code}</td>
                      <td>{row.feeder_code ?? '—'}</td>
                      <td>{row.recorded_at?.slice(0, 10) ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>
      )}
    </section>
  );
}
