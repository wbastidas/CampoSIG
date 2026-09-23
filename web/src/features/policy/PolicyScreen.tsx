/**
 * Capture policy administration (RF-151).
 *
 * Two panels, deliberately in this order. **What a phone will obey** comes first, with the origin of
 * every value; the editor comes second. An administrator's question is almost never «what did I
 * type» — it is «why is the north still asking for one photograph», and only the effective view with
 * its origins answers that.
 *
 * The editor sends only what changed. That is not an optimisation: a `PUT` carrying every field
 * would turn «I did not touch this» into «set this to null», and a null here means «inherit», so a
 * zone would silently stop overriding things nobody meant to change.
 *
 * Every judgement lives in `policy.ts` and is tested there.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  clearZonePolicy,
  type EffectivePolicy,
  fetchEffective,
  fetchPolicies,
  type PolicyList,
  type PolicyValues,
  savePolicy,
} from '../../api/policy';
import {
  changesOf,
  configuredZones,
  displayValue,
  effectiveRows,
  FIELD_LABELS,
  hasChanges,
  isBoolean,
  problemsIn,
  rowFor,
  scopeHeadline,
} from './policy';

export interface PolicyScreenProps {
  /** Required: nothing crosses between business units (ADR-009). */
  businessUnit: string;
  /** False for a supervisor, who may read and may not write. The server enforces it too. */
  mayEdit?: boolean;
}

export function PolicyScreen({ businessUnit, mayEdit = true }: PolicyScreenProps) {
  const [list, setList] = useState<PolicyList | null>(null);
  const [effective, setEffective] = useState<EffectivePolicy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  /** Null means the unit's own policy. */
  const [scope, setScope] = useState<string | null>(null);
  const [zoneDraft, setZoneDraft] = useState('');
  const [edited, setEdited] = useState<PolicyValues>({});

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const [rows, resolved] = await Promise.all([
          fetchPolicies(businessUnit, signal),
          fetchEffective(businessUnit, scope ?? undefined, signal),
        ]);
        setList(rows);
        setEffective(resolved);
        setEdited({});
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        setError((cause as Error).message);
      }
    },
    [businessUnit, scope],
  );

  useEffect(() => {
    const controller = new AbortController();
    // El setState ocurre tras el await dentro del callback, no en el cuerpo del efecto.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const loaded = rowFor(list, scope);
  const problems = problemsIn(edited);
  const dirty = hasChanges(loaded, edited);

  const valueOf = (field: string): string | number | boolean | null => {
    if (field in edited) return edited[field] ?? null;
    return loaded ? (loaded[field] ?? null) : null;
  };

  const save = async () => {
    setBusy(true);
    try {
      await savePolicy(businessUnit, changesOf(loaded, edited), scope ?? undefined);
      setStatus('Guardado. Llega al teléfono en el siguiente sync.');
      await load();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const removeZone = async (zone: string) => {
    setBusy(true);
    try {
      await clearZonePolicy(businessUnit, zone);
      setStatus(`La zona ${zone} vuelve a heredar la política de la unidad.`);
      setScope(null);
      await load();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="pol-screen">
      <header>
        <h1>Política de captura</h1>
      </header>

      {error && <p role="alert">{error}</p>}
      {status && <p className="pol-status">{status}</p>}

      <section className="pol-effective" aria-label="Lo que obedece el teléfono">
        <h2>Lo que obedece el teléfono{scope ? ` en ${scope}` : ''}</h2>
        <p>
          El valor y quién lo decidió. La política viaja dentro del paquete de la zona, así que un
          cambio llega al teléfono en el siguiente sync.
        </p>
        <table>
          <thead>
            <tr>
              <th scope="col">Parámetro</th>
              <th scope="col">Valor</th>
              <th scope="col">Lo decidió</th>
            </tr>
          </thead>
          <tbody>
            {effectiveRows(effective).map((row) => (
              <tr key={row.field} className={row.inherited ? 'pol-inherited' : undefined}>
                <th scope="row">{row.label}</th>
                <td>{displayValue(row.value)}</td>
                <td>{row.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="pol-scope" aria-label="Ámbito">
        <h2>Ámbito</h2>
        <label htmlFor="pol-scope">Editar</label>
        <select
          id="pol-scope"
          value={scope ?? ''}
          onChange={(event) => setScope(event.target.value || null)}
        >
          <option value="">Toda la unidad</option>
          {configuredZones(list).map((zone) => (
            <option key={zone} value={zone}>
              Zona {zone}
            </option>
          ))}
        </select>
        <p>{scopeHeadline(scope)}</p>
        {mayEdit && (
          <>
            <label htmlFor="pol-new-zone">Añadir una zona</label>
            <input
              id="pol-new-zone"
              value={zoneDraft}
              onChange={(event) => setZoneDraft(event.target.value)}
            />
            <button
              type="button"
              disabled={busy || zoneDraft.trim() === ''}
              onClick={() => {
                setScope(zoneDraft.trim());
                setZoneDraft('');
              }}
            >
              Editar esa zona
            </button>
          </>
        )}
        {mayEdit && scope !== null && configuredZones(list).includes(scope) && (
          <button type="button" disabled={busy} onClick={() => void removeZone(scope)}>
            Quitar la política de {scope}
          </button>
        )}
      </section>

      {mayEdit && (
        <section className="pol-editor" aria-label="Editar la política">
          <h2>Editar</h2>
          <p>
            Un campo vacío significa <strong>sin opinión</strong>: se hereda. Solo se envía lo que
            usted cambie.
          </p>
          {FIELD_LABELS.map((entry) => {
            const current = valueOf(entry.field);
            return (
              <div key={entry.field} className="pol-field">
                {isBoolean(entry.field) ? (
                  <>
                    <label htmlFor={`pol-${entry.field}`}>{entry.label}</label>
                    <select
                      id={`pol-${entry.field}`}
                      value={current === null ? '' : current ? 'si' : 'no'}
                      onChange={(event) =>
                        setEdited({
                          ...edited,
                          [entry.field]:
                            event.target.value === '' ? null : event.target.value === 'si',
                        })
                      }
                    >
                      <option value="">Heredar</option>
                      <option value="si">Sí</option>
                      <option value="no">No</option>
                    </select>
                  </>
                ) : (
                  <>
                    <label htmlFor={`pol-${entry.field}`}>{entry.label}</label>
                    <input
                      id={`pol-${entry.field}`}
                      type="number"
                      value={current === null ? '' : String(current)}
                      onChange={(event) =>
                        setEdited({
                          ...edited,
                          [entry.field]:
                            event.target.value === '' ? null : Number(event.target.value),
                        })
                      }
                    />
                  </>
                )}
                {entry.help && <span className="pol-help">{entry.help}</span>}
              </div>
            );
          })}

          {problems.length > 0 && (
            <ul role="alert">
              {problems.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}

          <button
            type="button"
            disabled={busy || !dirty || problems.length > 0}
            onClick={() => void save()}
          >
            Guardar
          </button>
          {!dirty && <span className="pol-help">No hay nada cambiado que guardar.</span>}
        </section>
      )}
    </section>
  );
}
