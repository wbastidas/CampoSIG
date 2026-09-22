/**
 * Review screen logic, as pure functions (M11, RF-110 to RF-112, ADR-007).
 *
 * Three judgements live here, and each one is a way a supervisor gets misled by a screen:
 *
 * 1. **What to read first.** A capture with an unconfirmed AI value and one with a regulatory
 *    breach need different attention, and the queue order decides which one gets looked at
 *    before lunch.
 * 2. **Which AI values still need a person.** The supervisor's main job on an assisted capture
 *    is auditing that list, so it has to be derivable and not buried in a table.
 * 3. **What a compliance finding actually says.** "No applicable" and "complies" look the same
 *    in green and mean completely different things; a provisional verdict from an unverified
 *    limit must never be shown as if it cited the official text.
 */

import type {
  AgentObservation,
  AgentReport,
  BatchOutcome,
  ComplianceFinding,
  Degradation,
  Provenance,
  QueueItem,
  ReviewDetail,
} from '../../api/review';
// Re-exportado: la pantalla lo usaba de aquí, y el valor de una respuesta se muestra igual en
// la revisión, en la vista de formulario y en el acta.
export { displayValue } from '../../forms/values';

export type Attention = 'bloqueado' | 'revisar' | 'listo';

export const ATTENTION_ORDER: Attention[] = ['bloqueado', 'revisar', 'listo'];

export const ATTENTION_LABEL: Record<Attention, string> = {
  bloqueado: 'No se puede aprobar',
  revisar: 'Requiere lectura',
  listo: 'Aprobable',
};

/** Same colour-blind-safe ramp as every other screen. */
export const ATTENTION_COLOR: Record<Attention, string> = {
  bloqueado: '#7f1d1d',
  revisar: '#a16207',
  listo: '#3f6212',
};

export const OUTCOME_LABEL: Record<ComplianceFinding['outcome'], string> = {
  cumple: 'Cumple',
  incumple: 'Incumple',
  no_aplica: 'Sin medición',
  no_determinable: 'Sin límite cargado',
};

/**
 * How much attention a capture needs.
 *
 * A blocker means the approve button will be refused, so saying so before the supervisor
 * presses it is the difference between a screen and a form that argues back.
 */
export function attentionFor(detail: ReviewDetail): Attention {
  if (detail.blockers.length > 0) return 'bloqueado';
  if (unconfirmedAiValues(detail.provenance).length > 0) return 'revisar';
  if (detail.compliance.some((finding) => finding.outcome === 'incumple')) return 'revisar';
  return 'listo';
}

/** AI proposals nobody has confirmed. The audit the supervisor is actually there to do. */
export function unconfirmedAiValues(provenance: Provenance[]): Provenance[] {
  return provenance.filter((entry) => entry.is_ai && entry.confirmed_by === null);
}

/** AI values a person corrected rather than accepted — the training signal, and a smell. */
export function correctedAiValues(provenance: Provenance[]): Provenance[] {
  return provenance.filter(
    (entry) => entry.is_ai && entry.confirmed_by !== null && !entry.accepted_unchanged,
  );
}

/**
 * Acceptance rate of the AI proposals on this capture, or null when there were none.
 *
 * Null and not zero: a capture with no AI values has no acceptance rate, and showing 0 %
 * would read as "the model got everything wrong".
 */
export function acceptanceRate(provenance: Provenance[]): number | null {
  const confirmed = provenance.filter((entry) => entry.is_ai && entry.confirmed_by !== null);
  if (confirmed.length === 0) return null;
  return confirmed.filter((entry) => entry.accepted_unchanged).length / confirmed.length;
}

/**
 * Compliance findings worth showing, worst first.
 *
 * Breaches, then undetermined, then the rest. "No measurement" is kept — seeing that the
 * platform looked at the earth resistance and found nothing recorded is different from it not
 * having looked — but it goes last.
 */
export function sortFindings(findings: ComplianceFinding[]): ComplianceFinding[] {
  const rank: Record<ComplianceFinding['outcome'], number> = {
    incumple: 0,
    no_determinable: 1,
    cumple: 2,
    no_aplica: 3,
  };
  return [...findings].sort((a, b) => {
    const byOutcome = rank[a.outcome] - rank[b.outcome];
    if (byOutcome !== 0) return byOutcome;
    return a.rule.localeCompare(b.rule, 'es');
  });
}

/**
 * How a finding should be cited on screen.
 *
 * An unverified limit gets the comparison and **not** the citation, because the citation is
 * the claim that this number comes from the official text — and nobody has checked that yet
 * (ADR-007).
 */
export function citationFor(finding: ComplianceFinding): string | null {
  if (!finding.norm_ref) return null;
  const reference = finding.article_ref
    ? `${finding.norm_ref}, ${finding.article_ref}`
    : finding.norm_ref;
  return finding.limit_verified ? reference : `${reference} — valor sin verificar`;
}

/** Evidence split by stage, for the before/after comparison. */
export function evidenceByStage(detail: ReviewDetail): {
  before: ReviewDetail['evidence'];
  after: ReviewDetail['evidence'];
  other: ReviewDetail['evidence'];
} {
  return {
    before: detail.evidence.filter((item) => item.stage === 'antes'),
    after: detail.evidence.filter((item) => item.stage === 'despues'),
    other: detail.evidence.filter((item) => item.stage !== 'antes' && item.stage !== 'despues'),
  };
}

/**
 * Whether the same file was submitted as both the before and the after photograph.
 *
 * Caught by content hash, not by a model: an identical file is identical, and it is the one
 * thing a hurried closing photograph is most likely to be.
 */
export function reusedEvidence(detail: ReviewDetail): string[] {
  const { before, after } = evidenceByStage(detail);
  const beforeHashes = new Set(before.map((item) => item.content_hash));
  return after.filter((item) => beforeHashes.has(item.content_hash)).map((item) => item.storage_key);
}

/** Evidence whose hash did not match what the device recorded. Never a rounding error. */
export function tamperedEvidence(detail: ReviewDetail): ReviewDetail['evidence'] {
  return detail.evidence.filter((item) => !item.integrity_verified);
}

const PRIORITY_RANK: Record<string, number> = {
  critica: 0,
  alta: 1,
  media: 2,
  baja: 3,
};

/**
 * Queue order: overdue SLA first, then by priority, then oldest update.
 *
 * Deliberately not "newest first": the queue is a backlog, and the item that has been waiting
 * longest is the one closest to breaching something.
 */
export function sortQueue(items: QueueItem[], now: Date): QueueItem[] {
  const overdue = (item: QueueItem) =>
    item.sla_due_at !== null && new Date(item.sla_due_at).getTime() < now.getTime() ? 0 : 1;
  return [...items].sort((a, b) => {
    const byOverdue = overdue(a) - overdue(b);
    if (byOverdue !== 0) return byOverdue;
    const byPriority = (PRIORITY_RANK[a.priority] ?? 9) - (PRIORITY_RANK[b.priority] ?? 9);
    if (byPriority !== 0) return byPriority;
    return (a.updated_at ?? '').localeCompare(b.updated_at ?? '');
  });
}

/** Proposals the GIS editor has to apply by hand in ArcFM (ADR-001). */
export function needsArcFm(tray: { proposals: { requires_arcfm: boolean }[] }): number {
  return tray.proposals.filter((proposal) => proposal.requires_arcfm).length;
}



/**
 * What the AI layer will not do here, worth showing and worth ordering (RF-204).
 *
 * `unavailable` first, because it is the one a supervisor has to absorb: that report is not
 * coming, so the decision is theirs on the deterministic evidence alone. A `night_batch` notice is
 * information about a wait, which is a smaller thing to know.
 */
export function sortDegradations(entries: Degradation[]): Degradation[] {
  const weight = (entry: Degradation): number =>
    entry.placement === 'unavailable' ? 0 : entry.placement === 'night_batch' ? 1 : 2;
  return [...entries].sort((a, b) => weight(a) - weight(b) || a.alias.localeCompare(b.alias));
}

/** Whether anything is missing at all, which is what decides if the section shows. */
export function hasDegradations(detail: ReviewDetail): boolean {
  return detail.degradations.some((entry) => entry.placement !== 'interactive');
}

export const PLACEMENT_LABEL: Record<Degradation['placement'], string> = {
  unavailable: 'No se va a ejecutar',
  night_batch: 'Queda para el lote nocturno',
  interactive: 'En línea',
};

/**
 * Reading the pre-review report (RF-111, RF-175).
 *
 * The risk level is what a supervisor sorts by, so the label has to be unambiguous in a glance and
 * not depend on colour: these actas get read on office monitors of every vintage, and a colour-only
 * signal is one a colour-blind supervisor does not receive at all.
 */
export const RISK_LABEL: Record<AgentReport['risk_level'], string> = {
  high: 'Riesgo alto',
  medium: 'Riesgo medio',
  low: 'Riesgo bajo',
};

export const CATEGORY_LABEL: Record<AgentObservation['category'], string> = {
  safety: 'Seguridad',
  regulatory: 'Normativa',
  evidence: 'Evidencia',
  coherence: 'Coherencia',
  catalog: 'Catálogo',
  anomaly: 'Anomalía',
};

const OBSERVATION_SEVERITY: Record<AgentObservation['severity'], number> = {
  high: 0,
  medium: 1,
  low: 2,
};

/** Worst first, then by id, so two readings of one report agree. */
export function sortObservations(observations: AgentObservation[]): AgentObservation[] {
  return [...observations].sort(
    (a, b) =>
      OBSERVATION_SEVERITY[a.severity] - OBSERVATION_SEVERITY[b.severity] ||
      a.id.localeCompare(b.id),
  );
}

/**
 * The citation of a report observation, or why there is none.
 *
 * An unverified limit is **not** shown as a citation of the official text (ADR-007): handing
 * somebody a verdict with an official-looking reference under it is worse than handing them the
 * verdict alone, because it invites them to stop checking.
 */
export function observationCitation(observation: AgentObservation): string | null {
  const source = observation.source;
  if (!source) return null;
  if (!source.verified) return 'Límite sin verificar contra el texto oficial; resultado provisional';
  return [source.document, source.version ? `v${source.version}` : null, source.section]
    .filter(Boolean)
    .join(' · ');
}

/** Why there is no report, in words. Null when there is one. */
export function missingReportReason(detail: ReviewDetail): string | null {
  const envelope = detail.agent_report;
  if (envelope === null) {
    return 'La pre-revisión de esta OT todavía no se ha ejecutado.';
  }
  if (envelope.report !== null) return null;
  if (envelope.error) {
    // Distinguished on purpose: "it failed" and "it has not run" are different things to a
    // supervisor who is about to decide without it.
    return `La pre-revisión falló (${envelope.run_state ?? 'sin estado'}): ${envelope.error}`;
  }
  return `La pre-revisión está en estado «${envelope.run_state ?? 'desconocido'}» y aún no produjo informe.`;
}

/**
 * Batch approval: what may be selected, and what the screen must say (RF-176).
 *
 * The server decides — it re-checks the risk and runs every approval through the same gate as an
 * individual one. What these do is keep the supervisor from selecting a batch that will come back
 * half refused, and make the sample impossible to overlook: «12 aprobadas» without «1 apartada»
 * reads as a finished batch, and the one held back is the whole point of the requirement.
 */
export type BatchBar = 'apta' | 'sin_informe' | 'riesgo';

/** Why this order cannot go in a batch, or null when it can. */
export function batchBar(item: QueueItem): BatchBar {
  if (item.risk_level === null) return 'sin_informe';
  return item.risk_level === 'low' ? 'apta' : 'riesgo';
}

/** Said in the row, so the supervisor reads why instead of discovering it in the refusals. */
export function batchBarLabel(item: QueueItem): string | null {
  switch (batchBar(item)) {
    case 'apta':
      return null;
    case 'riesgo':
      return `${RISK_LABEL[item.risk_level as AgentReport['risk_level']]}: se revisa una por una`;
    case 'sin_informe':
      // Not the same as low risk, and the distinction matters: an order nobody pre-reviewed is
      // exactly the one a bulk approval should not swallow.
      return 'Sin pre-revisión: se revisa una por una';
  }
}

export function batchable(items: QueueItem[]): QueueItem[] {
  return items.filter((item) => batchBar(item) === 'apta');
}

/**
 * What pressing the button will do, in words, before it is pressed.
 *
 * `sampled` comes from the server's own preview: the rounding rule is policy, and a second copy of
 * it here would be a copy free to drift from the one that decides.
 */
export function batchPlan(selected: number, sampled: number | null): string {
  if (selected === 0) return 'Seleccione OT de riesgo bajo para aprobar en lote.';
  if (sampled === null) return `${selected} seleccionada(s). Calculando la muestra…`;
  const approve = Math.max(selected - sampled, 0);
  return (
    `${selected} seleccionada(s): se aprobarán ${approve} y quedarán ${sampled} apartada(s) ` +
    'para verificación individual obligatoria (RF-176).'
  );
}

/** What the batch actually did. Every part of it, including what it refused and why. */
export function batchOutcomeLines(outcome: BatchOutcome): string[] {
  const lines = [
    `Aprobadas: ${outcome.approved.length}.`,
    `Apartadas para verificación individual: ${outcome.sampled.length}. No están aprobadas.`,
  ];
  if (outcome.refused.length > 0) {
    lines.push(`Rechazadas: ${outcome.refused.length}.`);
  }
  return lines;
}
