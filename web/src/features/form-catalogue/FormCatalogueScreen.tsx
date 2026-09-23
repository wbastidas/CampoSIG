/**
 * The form catalogue and its publication (RF-032).
 *
 * This screen exists so somebody can say «este formulario cambió y nadie lo publicó». Nothing else
 * on the platform makes that visible, and the consequence is invisible too: the orders in the field
 * keep receiving the previous version, which is correct behaviour and not at all what the person
 * who edited the file believes is happening.
 *
 * So the list is ordered worst first, the two situations that are not the same thing — never
 * published, and published but since edited — are named apart, and each one says what it implies
 * rather than being a colour.
 *
 * Every judgement lives in `catalogue.ts` and is tested there.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  type CatalogueRow,
  fetchCatalogue,
  fetchVersions,
  type FormVersion,
  obsoleteVersion,
  publishForm,
} from '../../api/forms';
import {
  blocksLine,
  canObsolete,
  canPublish,
  catalogueHeadline,
  catalogueRows,
  SITUATION_ADVICE,
  SITUATION_LABEL,
  versionLine,
} from './catalogue';

export interface FormCatalogueScreenProps {
  /** False for anybody who is not functional administration or IT. The server enforces it too. */
  mayPublish?: boolean;
}

export function FormCatalogueScreen({ mayPublish = true }: FormCatalogueScreenProps) {
  const [rows, setRows] = useState<CatalogueRow[]>([]);
  const [code, setCode] = useState('');
  const [versions, setVersions] = useState<FormVersion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadCatalogue = useCallback(async (signal?: AbortSignal) => {
    try {
      setRows((await fetchCatalogue(signal)).forms);
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
    void loadCatalogue(controller.signal);
    return () => controller.abort();
  }, [loadCatalogue]);

  const loadVersions = useCallback(async (wanted: string, signal?: AbortSignal) => {
    if (!wanted) {
      setVersions([]);
      return;
    }
    try {
      setVersions(await fetchVersions(wanted, signal));
      setError(null);
    } catch (cause) {
      if ((cause as Error).name === 'AbortError') return;
      setError((cause as Error).message);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadVersions(code, controller.signal);
    return () => controller.abort();
  }, [code, loadVersions]);

  const publish = async (row: CatalogueRow) => {
    setBusy(true);
    try {
      const published = await publishForm(row.code);
      setStatus(
        `${row.code} v${published.version} queda congelado. Las OT que se asignen desde ahora lo ` +
          'llevarán; las que ya existen conservan la suya.',
      );
      await Promise.all([loadCatalogue(), loadVersions(code)]);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const withdraw = async (version: FormVersion) => {
    setBusy(true);
    try {
      await obsoleteVersion(version.code, version.version);
      setStatus(
        `v${version.version} queda obsoleta: ninguna OT nueva la usará, y las que ya la llevan ` +
          'siguen componiéndose contra ella.',
      );
      await Promise.all([loadCatalogue(), loadVersions(code)]);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const ordered = catalogueRows(rows);

  return (
    <section className="frm-screen">
      <header>
        <h1>Formularios</h1>
        <p>
          Los archivos son el borrador. Publicar congela la forma, y desde ese momento cada OT
          conserva la versión con la que se asignó.
        </p>
      </header>

      {error && <p role="alert">{error}</p>}
      {status && <p className="frm-status">{status}</p>}

      <section className="frm-catalogue" aria-label="Catálogo">
        <h2>Catálogo</h2>
        <p className="frm-headline">{catalogueHeadline(rows)}</p>
        <table>
          <thead>
            <tr>
              <th scope="col">Código</th>
              <th scope="col">Título</th>
              <th scope="col">Archivo</th>
              <th scope="col">Publicado</th>
              <th scope="col">Situación</th>
              {mayPublish && <th scope="col">Acción</th>}
            </tr>
          </thead>
          <tbody>
            {ordered.map((row) => (
              <tr key={row.code} className={`frm-${row.situation}`}>
                <th scope="row">{row.code}</th>
                <td>{row.title}</td>
                <td>v{row.file_version}</td>
                <td>{row.published_version ? `v${row.published_version}` : '—'}</td>
                <td>
                  {SITUATION_LABEL[row.situation]}
                  <span className="frm-help"> — {SITUATION_ADVICE[row.situation]}</span>
                </td>
                {mayPublish && (
                  <td>
                    {canPublish(row) ? (
                      <button type="button" disabled={busy} onClick={() => void publish(row)}>
                        Publicar v{row.file_version}
                      </button>
                    ) : (
                      <span className="frm-help">—</span>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="frm-versions" aria-label="Versiones de un formulario">
        <h2>Versiones de un formulario</h2>
        <label htmlFor="frm-code">Formulario</label>
        <select id="frm-code" value={code} onChange={(event) => setCode(event.target.value)}>
          <option value="">Elija un formulario</option>
          {ordered.map((row) => (
            <option key={row.code} value={row.code}>
              {row.code} — {row.title}
            </option>
          ))}
        </select>

        {code === '' ? (
          <p>Elija un formulario para ver sus versiones publicadas.</p>
        ) : versions.length === 0 ? (
          <p>
            Este formulario no tiene ninguna versión publicada, así que las OT se componen contra el
            archivo actual.
          </p>
        ) : (
          <ul className="frm-version-list">
            {versions.map((version) => (
              <li key={version.version}>
                <strong>{versionLine(version)}</strong>
                <span className="frm-help"> {blocksLine(version)}</span>
                {version.note && <span className="frm-help"> · {version.note}</span>}
                {mayPublish && canObsolete(version) && (
                  <button type="button" disabled={busy} onClick={() => void withdraw(version)}>
                    Retirar
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
