/**
 * Reading a crew suggestion (RF-021).
 *
 * The judgements this file makes are about honesty, not about layout:
 *
 * * **A score is never shown alone.** «72» tells a planner nothing; «72 — cae en su zona (+40),
 *   trabajo abierto a 1,2 km (+28)» is something they can disagree with, which is the point.
 * * **A zero-point factor is still shown.** Dropping it would make a crew that scored 40 out of
 *   four factors look like one that scored 40 out of one.
 * * **An exclusion is not a low score.** The two are rendered apart because they mean different
 *   things: one crew is a worse fit, the other must not do this work.
 */

import type { CrewSuggestion, ExcludedCrew, SuggestedCrew } from '../../api/planning';

/** Points with their sign, es-EC. A zero reads as «0» and not as «+0». */
export function signedPoints(points: number): string {
  if (points === 0) return '0';
  return points > 0 ? `+${points}` : String(points);
}

export interface ReasonLine {
  factor: string;
  points: string;
  detail: string;
  /** True when this factor contributed nothing — shown differently, never hidden. */
  empty: boolean;
}

export function reasonLines(candidate: SuggestedCrew): ReasonLine[] {
  return candidate.reasons.map((reason) => ({
    factor: reason.factor,
    points: signedPoints(reason.points),
    detail: reason.detail,
    empty: reason.points === 0,
  }));
}

/** The headline of one candidate: its place, its code and its score. */
export function candidateHeadline(candidate: SuggestedCrew, position: number): string {
  return `${position}. ${candidate.code} · ${candidate.name} — ${candidate.score} puntos`;
}

/**
 * Whether the suggestion is worth showing at all.
 *
 * False when no crew qualified. The caveats then say why, and the planner still has the manual
 * assignment they always had — a suggestion panel that showed an empty list with no explanation
 * would read as a broken screen.
 */
export function hasCandidates(suggestion: CrewSuggestion | null): boolean {
  return (suggestion?.candidates.length ?? 0) > 0;
}

/** What the competency requirement says, when there is one. */
export function requirementLine(suggestion: CrewSuggestion | null): string | null {
  if (!suggestion || suggestion.required_competencies.length === 0) return null;
  return `Este formulario exige: ${suggestion.required_competencies.join(', ')}.`;
}

/** The excluded crews, worst-explained first? No — by code, so the list is stable to read. */
export function exclusionLines(suggestion: CrewSuggestion | null): ExcludedCrew[] {
  if (!suggestion) return [];
  return [...suggestion.excluded].sort((a, b) => a.code.localeCompare(b.code));
}

/**
 * Whether the top candidate is clearly ahead.
 *
 * Used to decide whether the screen says «la primera destaca» or «están parejas». A margin of a
 * couple of points is noise from rounding, and presenting it as a recommendation would be lending
 * the number authority it does not have.
 */
export const CLEAR_MARGIN = 10;

export function marginAdvice(suggestion: CrewSuggestion | null): string | null {
  const candidates = suggestion?.candidates ?? [];
  if (candidates.length < 2) return null;
  const first = candidates[0];
  const second = candidates[1];
  if (!first || !second) return null;
  const margin = first.score - second.score;
  if (margin >= CLEAR_MARGIN) {
    return `${first.code} va ${margin} puntos por delante de ${second.code}.`;
  }
  return `${first.code} y ${second.code} están parejas (${margin} punto(s) de diferencia): decida por lo que sepa del terreno.`;
}
