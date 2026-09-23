/**
 * Regulatory parameters (RF-150, ADR-007).
 *
 * The screen a deployment checklist reads. Two lists have to be empty, and they are deliberately not
 * merged: a code no rule can find makes that rule report it cannot judge — which on a dashboard
 * looks exactly like compliance — while a loaded but unverified code makes it judge against a number
 * somebody typed. One is silence, the other is a plausible answer, and they need different work.
 *
 * Under them, one code at a time: its periods, because «24 horas» is a fact about a date and not
 * about the platform, and its revisions, because «usuario que modificó» is only useful next to what
 * they modified it from.
 *
 * Every judgement lives in `regulatory.ts` and is tested there.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  fetchHistory,
  fetchIndex,
  fetchRevisions,
  type Parameter,
  type ParameterIndex,
  type Revision,
  verifyParameter,
} from '../../api/regulatory';
import {
  authorshipLabel,
  canVerify,
  ecuadorDate,
  gaps,
  indexHeadline,
  isInForce,
  periodLabel,
  plainValue,
  revisionLine,
  verificationLabel,
} from './regulatory';

export interface RegulatoryScreenProps {
  /** False for anybody who is not functional administration. The server enforces it too. */
  mayEdit?: boolean;
}

export function RegulatoryScreen({ mayEdit = true }: RegulatoryScreenProps) {
  const [index, setIndex] = useState<ParameterIndex | null>(null);
  const [code, setCode] = useState<string>('');
  const [periods, setPeriods] = useState<Parameter[]>([]);
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadIndex = useCallback(async (signal?: AbortSignal) => {
    try {
      setIndex(await fetchIndex(signal));
      setError(null);
    } catch (cause) {
      if ((cause as Error).name === 'AbortError') return;
      setError((cause as Error).message);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // El setState ocurre tras el await dentro del callback, no en el cuerpo del efecto.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadIndex(controller.signal);
    return () => controller.abort();
  }, [loadIndex]);

  const loadCode = useCallback(async (wanted: string, signal?: AbortSignal) => {
    if (!wanted) {
      setPeriods([]);
      setRevisions([]);
      return;
    }
    try {
      const [rows, log] = await Promise.all([
        fetchHistory(wanted, signal),
        fetchRevisions(wanted, signal),
      ]);
      setPeriods(rows);
      setRevisions(log);
      setError(null);
    } catch (cause) {
      if ((cause as Error).name === 'AbortError') return;
      setError((cause as Error).message);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadCode(code, controller.signal);
    return () => controller.abort();
  }, [code, loadCode]);

  const verify = async (row: Parameter) => {
    setBusy(true);
    try {
      await verifyParameter(row.code, row.effective_from);
      setStatus(
        `Queda registrado que usted leyó el texto oficial de ${row.norm_ref} y el valor coincide.`,
      );
      await Promise.all([loadIndex(), loadCode(row.code)]);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const problems = gaps(index);

  return (
    <section className="reg-screen">
      <header>
        <h1>Parámetros regulatorios</h1>
        <p>
          Los límites son nacionales, no de una unidad de negocio. Ninguno está codificado: cada uno
          vive con su vigencia y su referencia a la norma.
        </p>
      </header>

      {error && <p role="alert">{error}</p>}
      {status && <p className="reg-status">{status}</p>}

      <section className="reg-gaps" aria-label="Pendientes antes del piloto">
        <h2>Pendientes antes del piloto</h2>
        <p className="reg-headline">{indexHeadline(index)}</p>
        {problems.length === 0 ? (
          <p>Sin huecos: todo lo que las reglas necesitan está cargado y verificado.</p>
        ) : (
          <ul>
            {problems.map((gap) => (
              <li key={`${gap.kind}-${gap.code}`} className={`reg-${gap.kind}`}>
                <strong>{gap.code}</strong> — {gap.advice}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="reg-detail" aria-label="Historia de un código">
        <h2>Historia de un código</h2>
        <label htmlFor="reg-code">Código</label>
        <select id="reg-code" value={code} onChange={(event) => setCode(event.target.value)}>
          <option value="">Elija un código</option>
          {(index?.loaded ?? []).map((entry) => (
            <option key={entry} value={entry}>
              {entry}
            </option>
          ))}
        </select>

        {code === '' ? (
          <p>Elija un código para ver sus períodos y quién los modificó.</p>
        ) : (
          <>
            <h3>Períodos</h3>
            <table>
              <thead>
                <tr>
                  <th scope="col">Vigencia</th>
                  <th scope="col">Valor</th>
                  <th scope="col">Norma</th>
                  <th scope="col">Verificación</th>
                  <th scope="col">Autoría</th>
                  {mayEdit && <th scope="col">Acción</th>}
                </tr>
              </thead>
              <tbody>
                {periods.map((row) => (
                  <tr
                    key={row.effective_from}
                    className={isInForce(row) ? 'reg-in-force' : undefined}
                  >
                    <th scope="row">{periodLabel(row)}</th>
                    <td>
                      {plainValue(row.value)}
                      {row.unit ? ` ${row.unit}` : ''}
                    </td>
                    <td>
                      {row.norm_ref}
                      {row.article_ref ? ` · ${row.article_ref}` : ''}
                    </td>
                    <td className={row.verified ? undefined : 'reg-unverified'}>
                      {verificationLabel(row)}
                    </td>
                    <td>{authorshipLabel(row)}</td>
                    {mayEdit && (
                      <td>
                        {canVerify(row, mayEdit) ? (
                          <button type="button" disabled={busy} onClick={() => void verify(row)}>
                            Declaro haber leído el texto oficial
                          </button>
                        ) : (
                          <span className="reg-help">—</span>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>

            <h3>Quién modificó qué</h3>
            {revisions.length === 0 ? (
              <p>Sin ediciones registradas.</p>
            ) : (
              <ol className="reg-revisions">
                {revisions.map((revision, position) => (
                  <li key={`${revision.at}-${position}`}>
                    <span className="reg-when">{ecuadorDate(revision.at)}</span>{' '}
                    {revisionLine(revision)}
                    {revision.note && <span className="reg-help"> · {revision.note}</span>}
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </section>
    </section>
  );
}
