/**
 * The preventive-plan screen (RF-012).
 *
 * Three things the screen refuses to let a planner miss, because each one is a way a plan looks
 * healthy while failing: that issued is not done, that an expanded scope is a subset of the real
 * feeder, and that a period which issued nothing is «atrasado» and not «al día».
 *
 * Firing is a button and never a consequence of opening the page. Every judgement lives in
 * `plans.ts` and is tested there.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  fetchPlan,
  fetchPlans,
  type PlanDetail,
  type PlanRow,
  runPlan,
  savePlan,
} from '../../api/plans';
import {
  CADENCE_LABEL,
  cadenceLabel,
  canSubmit,
  caveatsOf,
  completionLabel,
  coverageLabel,
  draftAdvice,
  draftProblems,
  EMPTY_PLAN,
  headline,
  HEALTH_LABEL,
  historyRows,
  isExpanded,
  MAX_DAY_OF_MONTH,
  outcomeLabel,
  parseAssets,
  type PlanDraft,
  planRows,
  runSummary,
  SCOPE_LABEL,
  scopeLabel,
} from './plans';

export interface PlansScreenProps {
  businessUnit: string;
  /** False for anybody who is not a planner or an administrator. The server enforces it too. */
  mayEdit?: boolean;
}

export function PlansScreen({ businessUnit, mayEdit = true }: PlansScreenProps) {
  const [plans, setPlans] = useState<PlanRow[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<PlanDetail | null>(null);
  const [draft, setDraft] = useState<PlanDraft>(EMPTY_PLAN);
  const [writing, setWriting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setPlans((await fetchPlans(businessUnit, signal)).plans);
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

  const open = useCallback(
    async (code: string | null, signal?: AbortSignal) => {
      if (!code) {
        setDetail(null);
        return;
      }
      try {
        setDetail(await fetchPlan(businessUnit, code, signal));
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
    void open(selected, controller.signal);
    return () => controller.abort();
  }, [selected, open]);

  const fire = async (code: string) => {
    setBusy(true);
    try {
      setStatus(runSummary(await runPlan(businessUnit, code)));
      await Promise.all([load(), open(code)]);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    setBusy(true);
    try {
      await savePlan(businessUnit, draft.code.trim(), {
        name: draft.name.trim(),
        work_type: draft.workType.trim(),
        form_code: draft.formCode.trim(),
        cadence: draft.cadence,
        scope: draft.scope,
        ...(draft.cadence === 'dias' ? { cadence_days: Number(draft.cadenceDays) } : {}),
        ...(draft.cadence !== 'dias' ? { day_of_month: Number(draft.dayOfMonth) } : {}),
        ...(draft.scope === 'activos'
          ? {
              targets: parseAssets(draft.assets).map((asset_code, sort_order) => ({
                asset_code,
                sort_order,
              })),
            }
          : { scope_value: draft.scopeValue.trim() }),
        ...(draft.skipDays ? { skip_if_attended_within_days: Number(draft.skipDays) } : {}),
        ...(draft.startsOn ? { starts_on: draft.startsOn } : {}),
      });
      setStatus(`El plan «${draft.code.trim()}» quedó guardado.`);
      setDraft(EMPTY_PLAN);
      setWriting(false);
      await load();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const rows = planRows(plans ?? []);

  return (
    <section aria-label="Planes de mantenimiento preventivo">
      <h2>Planes preventivos</h2>
      <p>{headline(plans)}</p>

      {error && <p role="alert">{error}</p>}
      {status && <p role="status">{status}</p>}

      <table>
        <caption>Planes de la unidad</caption>
        <thead>
          <tr>
            <th scope="col">Plan</th>
            <th scope="col">Frecuencia</th>
            <th scope="col">Alcance</th>
            <th scope="col">Estado</th>
            <th scope="col">Emisión</th>
            <th scope="col">Cumplimiento</th>
            <th scope="col" />
          </tr>
        </thead>
        <tbody>
          {rows.map((plan) => (
            <tr key={plan.code}>
              <th scope="row">{plan.code}</th>
              <td>{cadenceLabel(plan.cadence, plan.cadence_days)}</td>
              <td>{scopeLabel(plan.scope, plan.scope_value)}</td>
              <td>{HEALTH_LABEL[plan.health]}</td>
              <td>{coverageLabel(plan.coverage)}</td>
              {/* Emitido no es hecho: los dos números juntos, nunca uno en vez del otro. */}
              <td>{completionLabel(plan.completion)}</td>
              <td>
                <button type="button" onClick={() => setSelected(plan.code)} disabled={busy}>
                  Ver
                </button>
                {mayEdit && (
                  <button type="button" onClick={() => void fire(plan.code)} disabled={busy}>
                    Generar ahora
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {detail && (
        <article aria-label={`Detalle de ${detail.code}`}>
          <h3>
            {detail.code} — {detail.name}
          </h3>
          <p>{scopeLabel(detail.scope, detail.scope_value)}</p>
          <p>{coverageLabel(detail.coverage)}</p>
          <p>{completionLabel(detail.completion)}</p>
          {isExpanded(detail) && (
            <p>
              El alcance expande a {detail.expanded.length} activo(s) con lo que la plataforma sabe
              hoy.
            </p>
          )}
          {caveatsOf(detail).length > 0 && (
            <ul aria-label="Lo que el alcance no puede saber">
              {caveatsOf(detail).map((caveat) => (
                <li key={caveat}>{caveat}</li>
              ))}
            </ul>
          )}
          {detail.note && <p role="note">{detail.note}</p>}

          <table>
            <caption>Historial</caption>
            <thead>
              <tr>
                <th scope="col">Periodo</th>
                <th scope="col">Activo</th>
                <th scope="col">Resultado</th>
                <th scope="col">Motivo</th>
              </tr>
            </thead>
            <tbody>
              {historyRows(detail).map((issue) => (
                <tr key={`${issue.period}-${issue.asset_code ?? 'alcance'}-${issue.issued_at}`}>
                  <td>{issue.period}</td>
                  <td>{issue.asset_code ?? 'todo el alcance'}</td>
                  <td>{outcomeLabel(issue.outcome)}</td>
                  <td>{issue.reason ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      )}

      {mayEdit && (
        <div>
          <button type="button" onClick={() => setWriting(!writing)} disabled={busy}>
            {writing ? 'Cancelar' : 'Nuevo plan'}
          </button>
        </div>
      )}

      {mayEdit && writing && (
        <form
          aria-label="Nuevo plan preventivo"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <label>
            Código
            <input
              value={draft.code}
              onChange={(event) => setDraft({ ...draft, code: event.target.value })}
            />
          </label>
          <label>
            Nombre
            <input
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          </label>
          <label>
            Tipo de trabajo
            <input
              value={draft.workType}
              onChange={(event) => setDraft({ ...draft, workType: event.target.value })}
            />
          </label>
          <label>
            Formulario
            <input
              value={draft.formCode}
              onChange={(event) => setDraft({ ...draft, formCode: event.target.value })}
            />
          </label>
          <label>
            Frecuencia
            <select
              value={draft.cadence}
              onChange={(event) => setDraft({ ...draft, cadence: event.target.value })}
            >
              {Object.entries(CADENCE_LABEL).map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          {draft.cadence === 'dias' ? (
            <label>
              Cada cuántos días
              <input
                value={draft.cadenceDays}
                onChange={(event) => setDraft({ ...draft, cadenceDays: event.target.value })}
              />
            </label>
          ) : (
            <label>
              Día del mes (1 a {MAX_DAY_OF_MONTH})
              <input
                value={draft.dayOfMonth}
                onChange={(event) => setDraft({ ...draft, dayOfMonth: event.target.value })}
              />
            </label>
          )}
          <label>
            Alcance
            <select
              value={draft.scope}
              onChange={(event) => setDraft({ ...draft, scope: event.target.value })}
            >
              {Object.entries(SCOPE_LABEL).map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          {draft.scope === 'activos' ? (
            <label>
              Activos, uno por línea (el orden es la ruta)
              <textarea
                value={draft.assets}
                onChange={(event) => setDraft({ ...draft, assets: event.target.value })}
              />
            </label>
          ) : (
            <label>
              Código del alimentador o de la zona
              <input
                value={draft.scopeValue}
                onChange={(event) => setDraft({ ...draft, scopeValue: event.target.value })}
              />
            </label>
          )}
          <label>
            No emitir si se atendió en los últimos N días (opcional)
            <input
              value={draft.skipDays}
              onChange={(event) => setDraft({ ...draft, skipDays: event.target.value })}
            />
          </label>
          <label>
            Fecha de inicio
            <input
              type="date"
              value={draft.startsOn}
              onChange={(event) => setDraft({ ...draft, startsOn: event.target.value })}
            />
          </label>

          <p>{draftAdvice(draft)}</p>
          {draftProblems(draft).map((problem) => (
            <p role="alert" key={problem}>
              {problem}
            </p>
          ))}
          <button type="submit" disabled={busy || !canSubmit(draft)}>
            Guardar el plan
          </button>
        </form>
      )}
    </section>
  );
}
