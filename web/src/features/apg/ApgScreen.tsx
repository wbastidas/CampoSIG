/**
 * The street-lighting board (RF-131).
 *
 * The number this screen exists for goes into a report to the regulator, so what it renders with
 * most care is the qualification of that number: the deadline it was measured against, whether
 * anybody verified it, and how much of the period could not be measured at all.
 *
 * Every judgement lives in `apg.ts` and is tested there. This file renders, calls, and hands the
 * browser the export.
 */

import { useCallback, useEffect, useState } from 'react';

import { type ApgBoard, downloadApgCsv, fetchApgBoard } from '../../api/analytics';
import {
  breachCitation,
  causeLabel,
  complianceCaveats,
  complianceHeadline,
  hours,
  ledShare,
  percent,
  shares,
  technologyLabel,
} from './apg';

export interface ApgScreenProps {
  /** Required: nothing crosses between business units (ADR-009). */
  businessUnit: string;
}

export function ApgScreen({ businessUnit }: ApgScreenProps) {
  const [board, setBoard] = useState<ApgBoard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setBoard(await fetchApgBoard(businessUnit, signal));
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
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
    return () => controller.abort();
  }, [load]);

  const exportCsv = useCallback(async () => {
    setBusy(true);
    try {
      const blob = await downloadApgCsv(businessUnit);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `apg-incumplimientos-${businessUnit}.csv`;
      link.click();
      // Liberado enseguida: un object URL que nadie revoca se queda con el archivo en memoria
      // mientras viva la pestaña.
      URL.revokeObjectURL(url);
      setError(null);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }, [businessUnit]);

  return (
    <section className="apg-board">
      <header>
        <h1>Alumbrado público</h1>
        <p className="review-hint">
          El plazo máximo de reposición sale de los parámetros regulatorios cargados, con su vigencia
          y su referencia a la norma: no está escrito en el código (ADR-007).
        </p>
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
          <section aria-label="Cumplimiento del plazo">
            <h2>Plazo de reposición</h2>
            <p role="status">{complianceHeadline(board)}</p>
            {complianceCaveats(board).map((line) => (
              <p key={line} className="ai-board-note">
                {line}
              </p>
            ))}
            <ul>
              <li>Mediana: {hours(board.restoration.median_hours)}</li>
              <li>9 de cada 10 por debajo de: {hours(board.restoration.p90_hours)}</li>
              <li>La peor: {hours(board.restoration.worst_hours)}</li>
            </ul>
          </section>

          <section aria-label="Flota por tecnología">
            <h2>Tecnología de las luminarias atendidas</h2>
            {ledShare(board) === null ? (
              <p>Sin tecnología registrada en el periodo.</p>
            ) : (
              <>
                <p role="status">{ledShare(board)}</p>
                <table>
                  <tbody>
                    {shares(board.fleet.by_technology).map((row) => (
                      <tr key={row.key}>
                        <td>{technologyLabel(row.key)}</td>
                        <td>{row.count}</td>
                        <td>{percent(row.share, 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
            {board.fleet.without_technology > 0 && (
              <p className="ai-board-note">
                {board.fleet.without_technology} atención(es) sin tecnología registrada, de antes de
                que el formulario la pidiera.
              </p>
            )}
          </section>

          <section aria-label="Fallas">
            <h2>Fallas</h2>
            <p role="status">
              {board.failures.failures_per_luminaire === null
                ? 'Sin luminarias con falla en el periodo.'
                : `${board.failures.failures_per_luminaire
                    .toFixed(2)
                    .replace('.', ',')} fallas por luminaria afectada (${
                    board.failures.distinct_luminaires
                  } luminarias, ${board.attentions} atenciones).`}
            </p>
            {/* Lo que el servidor dice del denominador, sin parafrasear: no es la tasa de la flota,
                porque el inventario vive en el SIG. */}
            <p className="ai-board-note">{board.failures.denominator}</p>
            {board.failures.repeat_offenders.length > 0 && (
              <>
                <h3>Reincidentes</h3>
                <ul>
                  {board.failures.repeat_offenders.map((row) => (
                    <li key={row.asset_code}>
                      <code>{row.asset_code}</code>: {row.failures} fallas
                    </li>
                  ))}
                </ul>
              </>
            )}
            {shares(board.failures.by_cause).length > 0 && (
              <>
                <h3>Causas</h3>
                <table>
                  <tbody>
                    {shares(board.failures.by_cause).map((row) => (
                      <tr key={row.key}>
                        <td>{causeLabel(row.key)}</td>
                        <td>{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </section>

          <section aria-label="Incumplimientos">
            <h2>Fuera de plazo</h2>
            <button type="button" disabled={busy} onClick={() => void exportCsv()}>
              Exportar a CSV
            </button>
            {board.breaches.length === 0 ? (
              <p>Ninguna atención por encima del plazo en el periodo.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>OT</th>
                    <th>Luminaria</th>
                    <th>Tomó</th>
                    <th>Plazo</th>
                    <th>Norma</th>
                  </tr>
                </thead>
                <tbody>
                  {board.breaches.map((breach) => (
                    <tr key={breach.work_order_id}>
                      <td>{breach.order_code ?? breach.work_order_id.slice(0, 8)}</td>
                      <td>{breach.asset_code ?? '—'}</td>
                      <td>{hours(breach.hours)}</td>
                      <td>{hours(breach.limit_hours)}</td>
                      <td className={breach.limit_verified ? undefined : 'apg-provisional'}>
                        {breachCitation(breach)}
                      </td>
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
