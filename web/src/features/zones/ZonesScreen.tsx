/**
 * Zone administration (RF-152).
 *
 * Three things on one screen because they are one job: the zones that exist, whether they cover the
 * work, and importing a corrected file. The coverage sits *above* the table on purpose — a list of
 * twelve well-named zones looks finished, and the number that says otherwise is the count of open
 * work orders none of them contains.
 *
 * Importing is two steps. The paste is parsed and summarised locally first — how many features,
 * which codes, which of them already exist — and only then sent. A file that replaces eleven
 * boundaries should say so before it does it, not after.
 *
 * Every judgement lives in `zones.ts` and is tested there.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  backfillZones,
  type BackfillReport,
  type CoverageReport,
  fetchCoverage,
  fetchZones,
  type ImportReport,
  importZones,
  setZoneActive,
  type ZoneCollection,
} from '../../api/zones';
import {
  backfillLines,
  codesIn,
  coverageCaveats,
  coverageHeadline,
  importFailed,
  importHeadline,
  integer,
  overlapLines,
  parseDocument,
  zoneRows,
} from './zones';

export interface ZonesScreenProps {
  /** Required: nothing crosses between business units (ADR-009). */
  businessUnit: string;
  /** False for a planner, who may look and may not move a boundary. The server enforces it too. */
  mayEdit?: boolean;
}

export function ZonesScreen({ businessUnit, mayEdit = true }: ZonesScreenProps) {
  const [collection, setCollection] = useState<ZoneCollection | null>(null);
  const [report, setReport] = useState<CoverageReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [text, setText] = useState('');
  const [codeProperty, setCodeProperty] = useState('');
  const [replaceExisting, setReplaceExisting] = useState(true);
  const [imported, setImported] = useState<ImportReport | null>(null);
  const [backfill, setBackfill] = useState<BackfillReport | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const [zones, coverage] = await Promise.all([
          fetchZones(businessUnit, { includeInactive: true }, signal),
          fetchCoverage(businessUnit, signal),
        ]);
        setCollection(zones);
        setReport(coverage);
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

  const parsed = parseDocument(text);
  const existing = new Set(zoneRows(collection).map((row) => row.code));
  const codes = parsed.document ? codesIn(parsed.document, codeProperty || undefined) : [];
  const willReplace = codes.filter((code) => code !== null && existing.has(code));

  const runImport = async () => {
    if (!parsed.document) return;
    setBusy(true);
    try {
      const result = await importZones(businessUnit, parsed.document, {
        codeProperty: codeProperty || undefined,
        replaceExisting,
      });
      setImported(result);
      setError(null);
      await load();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const runBackfill = async (dryRun: boolean) => {
    setBusy(true);
    try {
      setBackfill(await backfillZones(businessUnit, { dryRun }));
      setError(null);
      if (!dryRun) await load();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (code: string, active: boolean) => {
    setBusy(true);
    try {
      await setZoneActive(businessUnit, code, active);
      await load();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const rows = zoneRows(collection);
  const overlaps = report ? overlapLines(report) : [];

  return (
    <section className="zon-screen">
      <header>
        <h1>Zonas</h1>
      </header>

      {error && <p role="alert">{error}</p>}

      <section className="zon-coverage" aria-label="Cobertura">
        <h2>Cobertura</h2>
        {report ? (
          <>
            <p className="zon-headline">{coverageHeadline(report)}</p>
            <ul>
              {coverageCaveats(report).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            {overlaps.length > 0 ? (
              <>
                <h3>Solapamientos</h3>
                <ul>
                  {overlaps.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p>Ninguna zona se solapa con otra.</p>
            )}
          </>
        ) : (
          <p>Cargando…</p>
        )}
      </section>

      <section className="zon-list" aria-label="Zonas de la unidad">
        <h2>Zonas ({integer(rows.length)})</h2>
        {rows.length === 0 ? (
          <p>
            Esta unidad todavía no tiene zonas dibujadas. Hasta que las tenga, la zona de una OT es
            el texto que traiga, y la asignación por zona no se puede verificar.
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th scope="col">Código</th>
                <th scope="col">Nombre</th>
                <th scope="col">Origen</th>
                <th scope="col">Estado</th>
                <th scope="col">Última edición</th>
                {mayEdit && <th scope="col">Acción</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.code} className={row.active ? undefined : 'zon-inactive'}>
                  <th scope="row">{row.code}</th>
                  <td>{row.name}</td>
                  <td>{row.origin}</td>
                  <td>{row.active ? 'Activa' : 'Inactiva'}</td>
                  <td>
                    {row.updatedBy} · {row.updatedAt}
                  </td>
                  {mayEdit && (
                    <td>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void toggle(row.code, !row.active)}
                      >
                        {row.active ? 'Desactivar' : 'Reactivar'}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {mayEdit && (
        <section className="zon-import" aria-label="Importar GeoJSON">
          <h2>Importar GeoJSON</h2>
          <label htmlFor="zon-text">Pegue aquí el FeatureCollection</label>
          <textarea
            id="zon-text"
            rows={6}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <label htmlFor="zon-code-prop">Propiedad con el código (opcional)</label>
          <input
            id="zon-code-prop"
            value={codeProperty}
            onChange={(event) => setCodeProperty(event.target.value)}
          />
          <label>
            <input
              type="checkbox"
              checked={replaceExisting}
              onChange={(event) => setReplaceExisting(event.target.checked)}
            />
            Reemplazar el polígono de las zonas que ya existen
          </label>

          {parsed.problem && text.trim() !== '' && <p role="alert">{parsed.problem}</p>}
          {parsed.document && (
            <p className="zon-preview">
              {integer(parsed.features)} rasgo(s).{' '}
              {willReplace.length > 0
                ? `${integer(willReplace.length)} reemplazaría(n) una zona existente: ${willReplace.join(', ')}.`
                : 'Ninguna zona existente se reemplazaría.'}
            </p>
          )}
          {codes.some((code) => code === null) && (
            <p role="alert">
              Hay rasgos sin código; el servidor los rechazará uno por uno y aceptará los demás.
            </p>
          )}

          <button type="button" disabled={busy || !parsed.document} onClick={() => void runImport()}>
            Importar
          </button>

          {imported && (
            <div aria-label="Resultado de la importación">
              <p role={importFailed(imported) ? 'alert' : undefined}>{importHeadline(imported)}</p>
              {imported.rejected.length > 0 && (
                <ul>
                  {imported.rejected.map((item) => (
                    <li key={`${item.index}-${item.code ?? ''}`}>
                      Rasgo {item.index}
                      {item.code ? ` («${item.code}»)` : ''}: {item.reason}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>
      )}

      {mayEdit && (
        <section className="zon-backfill" aria-label="Asignar zona a las OT abiertas">
          <h2>Asignar zona desde el polígono</h2>
          <p>
            Solo a las OT abiertas que no tienen zona. La que ya trae una la conserva: pudo venir del
            sistema corporativo o de un planificador que sabe algo que el polígono no.
          </p>
          <button type="button" disabled={busy} onClick={() => void runBackfill(true)}>
            Simular
          </button>
          <button type="button" disabled={busy} onClick={() => void runBackfill(false)}>
            Aplicar
          </button>
          {backfill && (
            <ul aria-label="Resultado de la asignación">
              {backfillLines(backfill).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
        </section>
      )}
    </section>
  );
}
