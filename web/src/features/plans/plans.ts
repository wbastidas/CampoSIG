/**
 * Reading preventive plans (RF-012).
 *
 * The screen exists to make three things impossible to miss, because each one is a way a plan looks
 * healthy while failing:
 *
 * 1. **Issued is not done.** «Emitió 11 de 11» and «se ejecutaron 2 de 11» are both true at once,
 *    and only the second answers «¿cumplimos el plan?». So compliance is shown next to issuance and
 *    never instead of it.
 * 2. **An expanded scope is a subset.** «Todos los postes del alimentador» is a question the GIS
 *    answers, not this platform; what a plan expands to is the assets the platform has already
 *    worked on. The caveat is shown in the server's words, never paraphrased.
 * 3. **A period skipped is not a period done.** A plan whose orders nobody executes stops issuing —
 *    by design, so twelve orders do not pile up on one pole — and the screen has to say «atrasado»
 *    rather than «al día» when that happens, because the counts alone look identical.
 */

import type {
  PlanCompletion,
  PlanCoverage,
  PlanDetail,
  PlanIssueView,
  PlanRow,
} from '../../api/plans';

export const CADENCE_LABEL: Record<string, string> = {
  mensual: 'Mensual',
  trimestral: 'Trimestral',
  semestral: 'Semestral',
  anual: 'Anual',
  dias: 'Cada N días',
};

export const SCOPE_LABEL: Record<string, string> = {
  activos: 'Lista de activos (o ruta)',
  alimentador: 'Por alimentador',
  zona: 'Por zona',
};

export const OUTCOME_LABEL: Record<string, string> = {
  emitida: 'OT emitida',
  trabajo_pendiente: 'Ya había trabajo pendiente',
  atendida_hace_poco: 'Atendido hace poco',
};

export function cadenceLabel(cadence: string, days: number | null): string {
  if (cadence === 'dias') return days ? `Cada ${days} días` : 'Cada N días';
  return CADENCE_LABEL[cadence] ?? cadence;
}

export function scopeLabel(scope: string, value: string | null): string {
  const base = SCOPE_LABEL[scope] ?? scope;
  return value ? `${base}: ${value}` : base;
}

export function outcomeLabel(outcome: string): string {
  return OUTCOME_LABEL[outcome] ?? outcome;
}

/** Whether this plan's scope is an approximation rather than a list somebody wrote. */
export function isExpanded(plan: { scope: string }): boolean {
  return plan.scope !== 'activos';
}

export type Health = 'al-dia' | 'atrasado' | 'sin-alcance' | 'inactivo';

/**
 * How a plan is doing, in one word.
 *
 * `atrasado` is the one worth having: a plan whose current period issued nothing because every asset
 * already had pending work is *not* on schedule, and its issue count — zero — looks the same as a
 * plan that has nothing to do.
 */
export function healthOf(plan: PlanRow): Health {
  if (!plan.active) return 'inactivo';
  if (plan.coverage.targets === 0) return 'sin-alcance';
  const skipped = plan.coverage.skipped_pending + plan.coverage.skipped_recent;
  if (plan.coverage.issued === 0 && skipped > 0) return 'atrasado';
  return 'al-dia';
}

export const HEALTH_LABEL: Record<Health, string> = {
  'al-dia': 'Al día',
  atrasado: 'Atrasado: el periodo no emitió nada',
  'sin-alcance': 'Sin alcance: no hay activos que cubrir',
  inactivo: 'Inactivo',
};

const HEALTH_RANK: Record<Health, number> = {
  atrasado: 0,
  'sin-alcance': 1,
  'al-dia': 2,
  inactivo: 3,
};

/** Worst first, then by code, so the list reads the same way every time. */
export function planRows(plans: PlanRow[]): (PlanRow & { health: Health })[] {
  return plans
    .map((plan) => ({ ...plan, health: healthOf(plan) }))
    .sort((a, b) => {
      const byHealth = HEALTH_RANK[a.health] - HEALTH_RANK[b.health];
      return byHealth !== 0 ? byHealth : a.code.localeCompare(b.code);
    });
}

/** The issuance of the current period, with its denominator. */
export function coverageLabel(coverage: PlanCoverage): string {
  if (coverage.targets === 0) return 'Sin activos en el alcance';
  return `${coverage.issued} de ${coverage.targets} emitidas en ${coverage.period}`;
}

/**
 * Compliance, with its denominator and never as a lone percentage.
 *
 * Suppressed when nothing was issued: «0 de 0» is not 0 % compliance, it is no data, and a zero on a
 * screen is read as a failure.
 */
export function completionLabel(completion: PlanCompletion): string {
  if (completion.issued === 0) return 'Nada emitido todavía en este periodo';
  return `${completion.submitted} de ${completion.issued} ejecutadas`;
}

/** The headline over the list. Names how many plans are behind, which is the actionable number. */
export function headline(plans: PlanRow[] | null): string {
  if (!plans) return 'Cargando…';
  if (plans.length === 0) return 'No hay ningún plan preventivo cargado.';
  const behind = plans.filter((plan) => healthOf(plan) === 'atrasado').length;
  const active = plans.filter((plan) => plan.active).length;
  const base = `${plans.length} plan(es), ${active} activo(s)`;
  return behind > 0 ? `${base}; ${behind} atrasado(s).` : `${base}.`;
}

/** Every caveat the detail carries, de-duplicated: the same sentence twice is noise. */
export function caveatsOf(detail: PlanDetail | null): string[] {
  if (!detail) return [];
  return [...new Set([...detail.caveats, ...detail.history.flatMap((issue) => issue.caveats)])];
}

/** The history newest first, which is how a planner reads it. */
export function historyRows(detail: PlanDetail | null): PlanIssueView[] {
  if (!detail) return [];
  return [...detail.history].sort((a, b) => (b.issued_at ?? '').localeCompare(a.issued_at ?? ''));
}

/** What a run did, in one sentence, including what it refused to do. */
export function runSummary(run: {
  period: string;
  issued: string[];
  skipped_pending: string[];
  skipped_recent: string[];
  already_issued: string[];
  note: string | null;
}): string {
  if (run.note) return run.note;
  const parts = [`${run.issued.length} OT emitida(s) en ${run.period}`];
  if (run.already_issued.length > 0) {
    parts.push(`${run.already_issued.length} ya estaban emitidas en este periodo`);
  }
  if (run.skipped_pending.length > 0) {
    parts.push(`${run.skipped_pending.length} con trabajo pendiente`);
  }
  if (run.skipped_recent.length > 0) {
    parts.push(`${run.skipped_recent.length} atendidas hace poco`);
  }
  return `${parts.join('; ')}.`;
}

export interface PlanDraft {
  name: string;
  code: string;
  workType: string;
  formCode: string;
  cadence: string;
  cadenceDays: string;
  dayOfMonth: string;
  scope: string;
  scopeValue: string;
  assets: string;
  skipDays: string;
  startsOn: string;
}

export const EMPTY_PLAN: PlanDraft = {
  name: '',
  code: '',
  workType: 'inspeccion_preventiva',
  formCode: '',
  cadence: 'mensual',
  cadenceDays: '',
  dayOfMonth: '1',
  scope: 'activos',
  scopeValue: '',
  assets: '',
  skipDays: '',
  startsOn: '',
};

/** The greatest day of the month a calendar plan may fire on. Mirrors the server's own limit. */
export const MAX_DAY_OF_MONTH = 28;

/** One asset code per line, blanks and repeats dropped, order preserved: the order is the route. */
export function parseAssets(text: string): string[] {
  const seen = new Set<string>();
  const assets: string[] = [];
  for (const line of text.split(/[\n,;]/)) {
    const code = line.trim();
    if (!code || seen.has(code)) continue;
    seen.add(code);
    assets.push(code);
  }
  return assets;
}

/** Everything wrong with a draft, in Spanish, before it is sent. */
export function draftProblems(draft: PlanDraft): string[] {
  const problems: string[] = [];
  if (!draft.code.trim()) problems.push('El plan necesita un código.');
  if (!draft.name.trim()) problems.push('El plan necesita un nombre.');
  if (!draft.formCode.trim()) problems.push('Elija el formulario con el que se ejecuta.');
  if (draft.cadence === 'dias' && !(Number(draft.cadenceDays) > 0)) {
    problems.push('Una frecuencia en días necesita cuántos días, y al menos uno.');
  }
  if (draft.cadence !== 'dias') {
    const day = Number(draft.dayOfMonth);
    if (!Number.isInteger(day) || day < 1 || day > MAX_DAY_OF_MONTH) {
      problems.push(
        `El día del mes tiene que estar entre 1 y ${MAX_DAY_OF_MONTH}: el 29, 30 y 31 no existen ` +
          'todos los meses, y un plan que se saltara febrero emitiría once veces al año.',
      );
    }
  }
  if (draft.scope === 'activos' && parseAssets(draft.assets).length === 0) {
    problems.push('Un plan por activos necesita al menos un activo: la lista es el alcance.');
  }
  if (draft.scope !== 'activos' && !draft.scopeValue.trim()) {
    problems.push('Indique el alimentador o la zona del alcance.');
  }
  return problems;
}

export function canSubmit(draft: PlanDraft): boolean {
  return draftProblems(draft).length === 0;
}

/**
 * What the plan will do, said before it is saved.
 *
 * Including the caveat for an expanded scope: a planner choosing «por alimentador» should learn what
 * that means here before the first run, not from a count that came out lower than they expected.
 */
export function draftAdvice(draft: PlanDraft): string {
  const when =
    draft.cadence === 'dias'
      ? `cada ${draft.cadenceDays || 'N'} días desde su fecha de inicio`
      : `${(CADENCE_LABEL[draft.cadence] ?? draft.cadence).toLowerCase()}, el día ${draft.dayOfMonth} del mes`;
  if (draft.scope === 'activos') {
    const total = parseAssets(draft.assets).length;
    return `Emitirá hasta ${total} OT ${when}, en el orden de la lista.`;
  }
  return (
    `Emitirá una OT ${when} por cada activo de «${draft.scopeValue || '—'}» en el que la ` +
    'plataforma ya haya registrado trabajo. El inventario completo vive en el SIG, así que la ' +
    'expansión puede ser menor que el alimentador real.'
  );
}
