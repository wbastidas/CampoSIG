/**
 * Crew administration: create, edit, deactivate, members and change history (RF-005).
 *
 * Create and edit share one form, the way `ZonesScreen` already does for zones: filling in a
 * code that already exists edits that row instead of asking the operator to pick a mode first.
 *
 * The history is fetched on demand, one crew at a time, rather than joined into the list: a unit
 * with forty crews does not need forty audit queries to render a table.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  type Crew,
  fetchCrewHistory,
  fetchCrews,
  type CrewHistoryEntry,
  saveCrew,
  setCrewActive,
} from '../../api/crews';
import {
  type CrewDraft,
  draftFromCrew,
  draftProblems,
  EMPTY_DRAFT,
  crewRows,
  historyLines,
  parseList,
} from './crews';

export interface CrewsScreenProps {
  businessUnit: string;
  /** False for anybody who may only look. The server refuses a write regardless (ADR-013). */
  mayEdit?: boolean;
}

export function CrewsScreen({ businessUnit, mayEdit = true }: CrewsScreenProps) {
  const [crews, setCrews] = useState<Crew[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState<CrewDraft>(EMPTY_DRAFT);
  const [editing, setEditing] = useState(false);
  // Separate from `editing`: once a code names a crew that already exists, changing it would
  // create a second row rather than rename the first, so the field locks the moment we know.
  const [codeIsFixed, setCodeIsFixed] = useState(false);
  const [openHistory, setOpenHistory] = useState<string | null>(null);
  const [history, setHistory] = useState<CrewHistoryEntry[] | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const rows = await fetchCrews(businessUnit, { includeInactive: true }, signal);
        setCrews(rows);
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

  const edit = (crew: Crew) => {
    setDraft(draftFromCrew(crew));
    setEditing(true);
    setCodeIsFixed(true);
    setStatus(null);
  };

  const startNew = () => {
    setDraft(EMPTY_DRAFT);
    setEditing(true);
    setCodeIsFixed(false);
    setStatus(null);
  };

  const save = async () => {
    const problems = draftProblems(draft);
    if (problems.length > 0) return;
    setBusy(true);
    try {
      await saveCrew(businessUnit, {
        code: draft.code,
        name: draft.name,
        leader_name: draft.leaderName || null,
        vehicle: draft.vehicle || null,
        competencies: parseList(draft.competencies),
        members: parseList(draft.members),
        zone: draft.zone || null,
      });
      await load();
      setStatus(`«${draft.name}» se guardó.`);
      setEditing(false);
      setDraft(EMPTY_DRAFT);
    } catch (cause) {
      setStatus((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (code: string, active: boolean) => {
    setBusy(true);
    try {
      await setCrewActive(businessUnit, code, active);
      await load();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const toggleHistory = async (code: string) => {
    if (openHistory === code) {
      setOpenHistory(null);
      setHistory(null);
      return;
    }
    setOpenHistory(code);
    try {
      setHistory(await fetchCrewHistory(businessUnit, code));
    } catch (cause) {
      setError((cause as Error).message);
    }
  };

  const rows = crewRows(crews ?? []);
  const problems = draftProblems(draft);

  return (
    <section className="crew-screen">
      <header>
        <h1>Cuadrillas</h1>
      </header>

      {error && <p role="alert">{error}</p>}

      <section className="crew-list" aria-label="Cuadrillas de la unidad">
        <h2>Cuadrillas ({rows.length})</h2>
        {rows.length === 0 ? (
          <p>Esta unidad todavía no tiene cuadrillas registradas.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th scope="col">Código</th>
                <th scope="col">Nombre</th>
                <th scope="col">Jefe</th>
                <th scope="col">Integrantes</th>
                <th scope="col">Zona</th>
                <th scope="col">Estado</th>
                <th scope="col">Última edición</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.code} className={row.active ? undefined : 'crew-inactive'}>
                  <th scope="row">{row.code}</th>
                  <td>{row.name}</td>
                  <td>{row.leaderName}</td>
                  <td>{row.memberCount}</td>
                  <td>{row.zone}</td>
                  <td>{row.active ? 'Activa' : 'Inactiva'}</td>
                  <td>
                    {row.updatedBy} · {row.updatedAt}
                  </td>
                  <td>
                    {mayEdit && (
                      <button
                        type="button"
                        onClick={() => {
                          const crew = (crews ?? []).find((c) => c.code === row.code);
                          if (crew) edit(crew);
                        }}
                      >
                        Editar
                      </button>
                    )}
                    {mayEdit && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void toggle(row.code, !row.active)}
                      >
                        {row.active ? 'Desactivar' : 'Reactivar'}
                      </button>
                    )}
                    <button type="button" onClick={() => void toggleHistory(row.code)}>
                      Historial
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {openHistory && (
          <div aria-label={`Historial de ${openHistory}`}>
            <h3>Historial de {openHistory}</h3>
            {history === null ? (
              <p>Cargando…</p>
            ) : history.length === 0 ? (
              <p>Sin cambios registrados.</p>
            ) : (
              <ul>
                {historyLines(history).map((line, index) => (
                  <li key={index}>{line}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      {mayEdit && (
        <section className="crew-form" aria-label="Crear o editar cuadrilla">
          <h2>{editing ? 'Editar cuadrilla' : 'Nueva cuadrilla'}</h2>
          {!editing && (
            <button type="button" onClick={startNew}>
              Nueva cuadrilla
            </button>
          )}
          {editing && (
            <>
              <label htmlFor="crew-code">Código</label>
              <input
                id="crew-code"
                value={draft.code}
                disabled={codeIsFixed}
                onChange={(event) => setDraft({ ...draft, code: event.target.value })}
              />

              <label htmlFor="crew-name">Nombre</label>
              <input
                id="crew-name"
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
              />

              <label htmlFor="crew-leader">Jefe de cuadrilla</label>
              <input
                id="crew-leader"
                value={draft.leaderName}
                onChange={(event) => setDraft({ ...draft, leaderName: event.target.value })}
              />

              <label htmlFor="crew-vehicle">Vehículo</label>
              <input
                id="crew-vehicle"
                value={draft.vehicle}
                onChange={(event) => setDraft({ ...draft, vehicle: event.target.value })}
              />

              <label htmlFor="crew-competencies">Competencias (separadas por comas)</label>
              <input
                id="crew-competencies"
                value={draft.competencies}
                onChange={(event) => setDraft({ ...draft, competencies: event.target.value })}
              />

              <label htmlFor="crew-members">Integrantes (separados por comas)</label>
              <input
                id="crew-members"
                value={draft.members}
                onChange={(event) => setDraft({ ...draft, members: event.target.value })}
              />

              <label htmlFor="crew-zone">Zona</label>
              <input
                id="crew-zone"
                value={draft.zone}
                onChange={(event) => setDraft({ ...draft, zone: event.target.value })}
              />

              {problems.map((problem) => (
                <p key={problem} role="alert">
                  {problem}
                </p>
              ))}

              <button
                type="button"
                disabled={busy || problems.length > 0}
                onClick={() => void save()}
              >
                {busy ? 'Guardando…' : 'Guardar'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setEditing(false);
                  setDraft(EMPTY_DRAFT);
                }}
              >
                Cancelar
              </button>
            </>
          )}
          {status && <p role="status">{status}</p>}
        </section>
      )}
    </section>
  );
}
