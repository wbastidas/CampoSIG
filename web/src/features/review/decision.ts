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
  ComplianceFinding,
  Provenance,
  QueueItem,
  ReviewDetail,
} from '../../api/review';

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
