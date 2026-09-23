/**
 * The catalogue screen (RF-034).
 *
 * The gap this closes was a dangling reference: the form blocks said `x-catalog-ref: defect` and
 * nothing served the list, so a phone had a code field and nothing to choose from. This screen makes
 * that state visible — a catalogue with no values, and whether that is a decision or a fault.
 *
 * Three distinctions the screen has to keep, because they look alike: empty-and-waiting versus
 * empty-with-no-reason, ours versus the ERP's, and national versus this unit's.
 *
 * Every judgement lives in `catalogs.ts` and is tested there.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  type CatalogIndex,
  fetchIndex,
  fetchResolved,
  type ResolvedCatalog,
  retireEntry,
} from '../../api/catalogs';
import {
  emptyAdvice,
  entryRows,
  gisNote,
  HEALTH_LABEL,
  indexHeadline,
  indexRows,
  isEditable,
  sourceLabel,
} from './catalogs';

export interface CatalogsScreenProps {
  /** Required: a catalogue resolves differently per unit, because a unit may add its own values. */
  businessUnit: string;
  /** False for anybody who is not functional administration or IT. The server enforces it too. */
  mayEdit?: boolean;
}

export function CatalogsScreen({ businessUnit, mayEdit = true }: CatalogsScreenProps) {
  const [index, setIndex] = useState<CatalogIndex | null>(null);
  const [code, setCode] = useState('');
  const [catalog, setCatalog] = useState<ResolvedCatalog | null>(null);
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

  const loadCatalog = useCallback(
    async (wanted: string, signal?: AbortSignal) => {
      if (!wanted) {
        setCatalog(null);
        return;
      }
      try {
        setCatalog(await fetchResolved(businessUnit, wanted, signal));
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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadCatalog(code, controller.signal);
    return () => controller.abort();
  }, [code, loadCatalog]);

  const retire = async (entryCode: string) => {
    setBusy(true);
    try {
      await retireEntry(code, entryCode);
      setStatus(
        `«${entryCode}» queda retirado. Viaja al teléfono como lápida en el siguiente sync, para ` +
          'que deje de ofrecerlo.',
      );
      await Promise.all([loadIndex(), loadCatalog(code)]);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const rows = indexRows(index);
  const advice = emptyAdvice(catalog);
  const editable = catalog !== null && mayEdit && isEditable(catalog);

  return (
    <section className="cat-screen">
      <header>
        <h1>Catálogos</h1>
        <p>
          Los formularios los referencian por código. Un catálogo vacío es un selector sin valores, y
          el técnico termina escribiendo en observaciones.
        </p>
      </header>

      {error && <p role="alert">{error}</p>}
      {status && <p className="cat-status">{status}</p>}

      <section className="cat-index" aria-label="Catálogos de la plataforma">
        <h2>Catálogos</h2>
        <p className="cat-headline">{indexHeadline(index)}</p>
        {gisNote(index) && <p className="cat-help">{gisNote(index)}</p>}
        <table>
          <thead>
            <tr>
              <th scope="col">Código</th>
              <th scope="col">Título</th>
              <th scope="col">Valores</th>
              <th scope="col">Versión</th>
              <th scope="col">Situación</th>
              <th scope="col">Quién lo mantiene</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.code} className={`cat-${row.health}`}>
                <th scope="row">{row.code}</th>
                <td>{row.title}</td>
                <td>
                  {row.active_entries}
                  {row.retired_entries > 0 && (
                    <span className="cat-help"> (+{row.retired_entries} retirados)</span>
                  )}
                </td>
                <td>{row.version}</td>
                <td>
                  {HEALTH_LABEL[row.health]}
                  {row.note && <span className="cat-help"> — {row.note}</span>}
                </td>
                <td>{sourceLabel(row.source)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="cat-detail" aria-label="Valores de un catálogo">
        <h2>Valores de un catálogo</h2>
        <label htmlFor="cat-code">Catálogo</label>
        <select id="cat-code" value={code} onChange={(event) => setCode(event.target.value)}>
          <option value="">Elija un catálogo</option>
          {rows.map((row) => (
            <option key={row.code} value={row.code}>
              {row.code} — {row.title}
            </option>
          ))}
        </select>

        {code === '' ? (
          <p>Elija un catálogo para ver lo que puede elegir un técnico de {businessUnit}.</p>
        ) : advice ? (
          <p role="status" className="cat-warning">
            {advice}
          </p>
        ) : (
          <>
            {catalog !== null && !isEditable(catalog) && (
              <p className="cat-help">
                {sourceLabel(catalog.source)}: no se edita desde aquí, porque el siguiente envío
                sobreescribiría lo que se teclee.
              </p>
            )}
            <table>
              <thead>
                <tr>
                  <th scope="col">Código</th>
                  <th scope="col">Etiqueta</th>
                  <th scope="col">Sinónimos</th>
                  <th scope="col">Origen</th>
                  <th scope="col">Atributos</th>
                  {editable && <th scope="col">Acción</th>}
                </tr>
              </thead>
              <tbody>
                {entryRows(catalog).map((row) => (
                  <tr key={row.code}>
                    <th scope="row">{row.code}</th>
                    <td>{row.label}</td>
                    <td>{row.synonyms}</td>
                    <td>{row.origin}</td>
                    <td>{row.extras}</td>
                    {editable && (
                      <td>
                        <button type="button" disabled={busy} onClick={() => void retire(row.code)}>
                          Retirar
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </section>
    </section>
  );
}
