/**
 * El panel de ruta sugerida, dentro del panel del planificador (RF-025).
 *
 * Aparece cuando hay dos o más OT seleccionadas en el mapa — con una sola no hay nada que
 * ordenar, y es justo el caso que `AttachmentsPanel` ya cubre. No asigna ni cambia ninguna OT:
 * solo pide el orden y lo muestra, con la comparación contra el orden en que se pidieron.
 */

import { useState } from 'react';

import { type RouteSuggestion, suggestRoute } from '../../api/routing';
import { ApiError } from '../../api/planning';
import { requestProblems, savingsHeadline } from './route';

export interface RouteSuggestionPanelProps {
  businessUnit: string;
  /** Las OT seleccionadas, en el orden en que el planificador las fue marcando. */
  workOrderIds: string[];
}

export function RouteSuggestionPanel({ businessUnit, workOrderIds }: RouteSuggestionPanelProps) {
  const [suggestion, setSuggestion] = useState<RouteSuggestion | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const problems = requestProblems(workOrderIds.length);

  const onSuggest = async () => {
    if (problems.length > 0) return;
    setBusy(true);
    setStatus(null);
    try {
      setSuggestion(await suggestRoute(businessUnit, { work_order_ids: workOrderIds }));
    } catch (error) {
      setSuggestion(null);
      setStatus(error instanceof ApiError ? error.message : 'No se pudo calcular la ruta');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="planner__route" aria-label="Ruta sugerida">
      <h3>Ruta sugerida</h3>

      <button type="button" onClick={() => void onSuggest()} disabled={busy || problems.length > 0}>
        {busy ? 'Calculando…' : 'Sugerir ruta'}
      </button>
      {problems.map((problem) => (
        <p key={problem} className="planner__hint">
          {problem}
        </p>
      ))}

      {status && (
        <p role="status" className="planner__warning">
          {status}
        </p>
      )}

      {suggestion && (
        <>
          <p>{savingsHeadline(suggestion)}</p>
          {suggestion.caveats.map((caveat) => (
            <p key={caveat} role="status" className="planner__warning">
              {caveat}
            </p>
          ))}
          <ol className="planner__route-stops">
            {suggestion.stops.map((stop, position) => (
              <li key={stop.work_order_id}>
                {position + 1}. {stop.code ?? stop.work_order_id}
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}
