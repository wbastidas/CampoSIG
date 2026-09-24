/**
 * The AI dashboard (RF-134), with the blind-sample agreement of RF-111a.
 *
 * Five panels, and each one answers a question somebody actually asks: which field needs more
 * training data, which visual class the detector confuses, how much the voice pipeline gets wrong,
 * whether the crews use dictation at all, and which model versions are out there.
 *
 * Every judgement lives in `metrics.ts` and is tested there. This file renders and calls.
 *
 * The one thing it renders with care is the *absence* of a number. A suppressed rate is shown as
 * "sin muestra suficiente", never as 0 %, and an empty panel says there was nothing to measure
 * rather than nothing to fix — the two readings lead to opposite decisions.
 */

import { useCallback, useEffect, useState } from 'react';

import { type AiDashboard, fetchAiDashboard } from '../../api/analytics';
import { disagreementLines, kappaVerdict } from '../review/decision';
import {
  byModel,
  confusionLabel,
  coverageLabel,
  fieldAdvice,
  isMeasured,
  percent,
  rateLabel,
  regressed,
  sortAdoption,
  wordErrorLabel,
} from './metrics';

export interface AiDashboardScreenProps {
  /** Required: nothing crosses between business units (ADR-009). */
  businessUnit: string;
}

/** Periods an analyst actually asks for. Open-ended is the default: a pilot has little data. */
const PERIODS: { key: string; label: string; days: number | null }[] = [
  { key: 'todo', label: 'Todo', days: null },
  { key: '7', label: 'Últimos 7 días', days: 7 },
  { key: '30', label: 'Últimos 30 días', days: 30 },
  { key: '90', label: 'Últimos 90 días', days: 90 },
];

export function AiDashboardScreen({ businessUnit }: AiDashboardScreenProps) {
  const [period, setPeriod] = useState('todo');
  const [board, setBoard] = useState<AiDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      const days = PERIODS.find((entry) => entry.key === period)?.days ?? null;
      const since =
        days === null ? undefined : new Date(Date.now() - days * 86_400_000).toISOString();
      try {
        setBoard(await fetchAiDashboard(businessUnit, { since }, signal));
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        setError((cause as Error).message);
        setBoard(null);
      }
    },
    [businessUnit, period],
  );

  useEffect(() => {
    const controller = new AbortController();
    // El setState ocurre tras el await dentro del callback, no en el cuerpo del efecto.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const minimum = board?.min_for_a_rate ?? 5;

  return (
    <section className="ai-board">
      <header>
        <h1>Tablero de IA</h1>
        <p className="review-hint">
          De qué se fía la plataforma y de qué no. Las tasas traen su denominador: por debajo de{' '}
          {minimum} propuestas no se reporta una tasa, porque un «100 %» sobre dos propuestas no
          dice nada.
        </p>
        <label>
          Periodo
          <select value={period} onChange={(event) => setPeriod(event.target.value)}>
            {PERIODS.map((entry) => (
              <option key={entry.key} value={entry.key}>
                {entry.label}
              </option>
            ))}
          </select>
        </label>
        {error && (
          <p role="alert" className="board-error">
            {error}
          </p>
        )}
      </header>

      {board === null ? (
        // Tras un fallo no se sigue diciendo «cargando»: el aviso de arriba ya explica qué pasó, y
        // un «cargando» perpetuo al lado hace creer que todavía puede aparecer algo.
        error === null && <p>Cargando el tablero…</p>
      ) : (
        <div className="ai-board-panels">
          <FieldsPanel board={board} minimum={minimum} />
          <ClassesPanel board={board} minimum={minimum} />
          <WordsPanel board={board} minimum={minimum} />
          <AdoptionPanel board={board} minimum={minimum} />
          <FleetPanel board={board} />
          <AgreementPanel board={board} />
        </div>
      )}
    </section>
  );
}

function FieldsPanel({ board, minimum }: { board: AiDashboard; minimum: number }) {
  return (
    <section aria-label="Aceptación por campo">
      <h2>Aceptación por campo</h2>
      {board.fields.length === 0 ? (
        <p>Ningún modelo propuso valores en este periodo.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Campo</th>
              <th>Aceptación</th>
              <th>Confianza media</th>
              <th>Qué hacer</th>
            </tr>
          </thead>
          <tbody>
            {board.fields.map((row) => (
              <tr key={row.field_key} className={isMeasured(row.acceptance) ? undefined : 'dim'}>
                <td>
                  <code>{row.field_key}</code>
                </td>
                <td>{rateLabel(row.acceptance, row.accepted, row.proposals, minimum)}</td>
                <td>{row.mean_confidence === null ? '—' : percent(row.mean_confidence, 0)}</td>
                <td>{fieldAdvice(row, minimum)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function ClassesPanel({ board, minimum }: { board: AiDashboard; minimum: number }) {
  return (
    <section aria-label="Correcciones por clase visual">
      <h2>Correcciones por clase visual</h2>
      {board.visual_classes.length === 0 ? (
        <p>Ninguna propuesta de visión en este periodo.</p>
      ) : (
        <ul>
          {board.visual_classes.map((row) => (
            <li key={row.proposed_class}>
              <strong>{row.proposed_class}</strong>:{' '}
              {rateLabel(row.correction_rate, row.corrected, row.proposals, minimum)} corregidas
              {confusionLabel(row) && <div className="ai-board-note">{confusionLabel(row)}</div>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function WordsPanel({ board, minimum }: { board: AiDashboard; minimum: number }) {
  const rows = board.word_errors;
  return (
    <section aria-label="Error de palabras estimado">
      <h2>Error de palabras (estimado)</h2>
      <p role="status">{wordErrorLabel(rows, minimum)}</p>
      {rows && (
        <>
          {/* La advertencia del servidor, mostrada y no parafraseada: quien lea el número lo va a
              citar, y debería citar lo que mide. */}
          <p className="ai-board-note">{rows.measures}</p>
          {coverageLabel(rows) && <p className="ai-board-note">{coverageLabel(rows)}</p>}
        </>
      )}
    </section>
  );
}

function AdoptionPanel({ board, minimum }: { board: AiDashboard; minimum: number }) {
  return (
    <section aria-label="Adopción de la voz">
      <h2>Adopción de la voz</h2>
      <p className="ai-board-note">
        Para saber si la función sirve y dónde hace falta acompañamiento, no para calificar a nadie:
        dictar menos no es trabajar peor.
      </p>
      {board.voice_adoption.length === 0 ? (
        <p>Sin capturas enviadas en este periodo.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Persona</th>
              <th>Capturas con voz</th>
              <th>Campos dictados</th>
            </tr>
          </thead>
          <tbody>
            {sortAdoption(board.voice_adoption).map((row) => (
              <tr key={row.user}>
                <td>{row.user}</td>
                <td>
                  {rateLabel(row.adoption, row.responses_with_voice, row.responses, minimum)}
                </td>
                <td>{row.voice_fields}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function FleetPanel({ board }: { board: AiDashboard }) {
  const groups = byModel(board.fleet);
  return (
    <section aria-label="Versiones en la flota">
      <h2>Versiones en la flota</h2>
      {groups.length === 0 ? (
        <p>Ninguna versión declaró propuestas en este periodo.</p>
      ) : (
        groups.map((group) => {
          const drop = regressed(group.versions);
          return (
            <div key={group.model}>
              <h3>{group.model}</h3>
              <ul>
                {group.versions.map((row) => (
                  <li key={`${row.model_version}-${row.origin}`}>
                    <strong>{row.model_version}</strong> ({row.origin}): {row.proposals} propuesta(s),
                    aceptación{' '}
                    {row.acceptance === null ? 'sin muestra suficiente' : percent(row.acceptance)}
                    {row.last_seen && <span> · última vez {row.last_seen.slice(0, 10)}</span>}
                  </li>
                ))}
              </ul>
              {drop && (
                /* «Nunca regresar» es la primera de las compuertas de calidad de la guía (8.4).
                   Una versión nueva que acepta peor que la anterior es candidata a reversión. */
                <p role="alert" className="ai-board-regression">
                  La versión {drop.to.model_version} acepta peor que {drop.from.model_version} (
                  {percent(drop.to.acceptance ?? 0)} contra {percent(drop.from.acceptance ?? 0)}):
                  candidata a reversión.
                </p>
              )}
            </div>
          );
        })
      )}
    </section>
  );
}

function AgreementPanel({ board }: { board: AiDashboard }) {
  return (
    <section aria-label="Concordancia con el agente">
      <h2>Concordancia con el agente</h2>
      <p role="status">{kappaVerdict(board.agreement)}</p>
      <ul>
        {disagreementLines(board.agreement).map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <p className="ai-board-note">
        Calculado solo sobre la muestra ciega (RF-111a): un kappa medido sobre revisiones que vieron
        el informe primero mide concordancia con una sugerencia, no entre dos juicios.
      </p>
    </section>
  );
}
