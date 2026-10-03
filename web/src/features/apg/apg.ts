/**
 * Reading the street-lighting board (RF-131, ADR-007).
 *
 * The number this board exists for is a regulatory compliance percentage, which means somebody will
 * put it in a report to the regulator. So the judgements here are about not letting that happen with
 * a number that does not support it:
 *
 * * a percentage measured against a limit nobody verified is labelled provisional, every time it is
 *   shown — ADR-007's rule, and the reason is that an official-looking figure invites the reader to
 *   stop checking;
 * * attentions the rule could not judge are counted next to the percentage, because a 100 % over
 *   five judged attentions out of two hundred captured is not a compliance rate;
 * * the failure rate says what it is divided by, since the platform does not know the installed
 *   fleet — that lives in the GIS.
 */

import type { ApgBoard, ApgBreach } from '../../api/analytics';

/** A share as a percentage, es-EC. */
export function percent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits).replace('.', ',')} %`;
}

/** Hours, in the unit a person would say them in. */
export function hours(value: number | null): string {
  if (value === null) return '—';
  if (value < 24) return `${value.toFixed(1).replace('.', ',')} h`;
  return `${(value / 24).toFixed(1).replace('.', ',')} d`;
}

/** The compliance headline, or why there is not one. */
export function complianceHeadline(board: ApgBoard): string {
  const { compliance, judged, min_sample, within } = board.restoration;
  if (compliance === null) {
    return judged === 0
      ? 'Ninguna atención con plazo medible en el periodo.'
      : `Sin muestra suficiente: ${judged} de ${min_sample} atenciones medibles.`;
  }
  return `${percent(compliance)} dentro del plazo (${within} de ${judged}).`;
}

/**
 * Warnings that must travel with the percentage.
 *
 * Both are about what the number does not cover, and both change what somebody may do with it: one
 * says the limit is unconfirmed, the other says most of the period was not measurable.
 */
export function complianceCaveats(board: ApgBoard): string[] {
  const lines: string[] = [];
  const { against_unverified_limit, not_measurable, judged } = board.restoration;
  if (against_unverified_limit > 0) {
    lines.push(
      `${against_unverified_limit} juzgada(s) contra un plazo sin verificar contra el texto ` +
        'oficial: resultado provisional, no citable como cumplimiento normativo.',
    );
  }
  if (not_measurable > 0) {
    lines.push(
      `${not_measurable} atención(es) sin plazo medible: falta la hora de reclamo, la de ` +
        'reposición, o el parámetro regulatorio no está cargado.',
    );
  }
  if (judged > 0 && not_measurable > judged) {
    lines.push('Se pudo medir menos de la mitad del periodo: el porcentaje cubre poco.');
  }
  return lines;
}

/** The citation of a breach, or why there is none. Never an official-looking reference to nothing. */
export function breachCitation(breach: ApgBreach): string {
  if (!breach.limit_verified) {
    return 'Plazo sin verificar contra el texto oficial; resultado provisional';
  }
  return [breach.norm_ref, breach.article_ref].filter(Boolean).join(' · ') || 'Sin referencia';
}

export const TECHNOLOGY_LABEL: Record<string, string> = {
  led: 'LED',
  sodium_hp: 'Sodio alta presión',
  mercury: 'Mercurio',
  metal_halide: 'Aditivos metálicos',
  other: 'Otra',
};

export function technologyLabel(key: string): string {
  // An unknown technology shows its raw key rather than «Otra»: a value the screen does not know is
  // one the profile added, and folding it into «Otra» would hide a whole class of the fleet.
  return TECHNOLOGY_LABEL[key] ?? key;
}

export const CAUSE_LABEL: Record<string, string> = {
  lampara_o_modulo: 'Lámpara o módulo',
  driver_o_balasto: 'Driver o balasto',
  fotocontrol: 'Fotocontrol',
  fusible: 'Fusible',
  conexion: 'Conexión',
  brazo: 'Brazo',
  vandalismo: 'Vandalismo',
  alimentacion: 'Alimentación',
};

export function causeLabel(key: string): string {
  return CAUSE_LABEL[key] ?? key;
}

/** Counts as a sorted list with their share, for a bar to be drawn from. */
export function shares(counts: Record<string, number>): { key: string; count: number; share: number }[] {
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
  if (total === 0) return [];
  return Object.entries(counts)
    .map(([key, count]) => ({ key, count, share: count / total }))
    .sort((a, b) => b.count - a.count || a.key.localeCompare(b.key, 'es'));
}

/** How the LED share reads, which is the modernisation number the area is measured on. */
export function ledShare(board: ApgBoard): string | null {
  const counts = board.fleet.by_technology;
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
  if (total === 0) return null;
  const led = counts.led ?? 0;
  return `${percent(led / total)} de las atendidas son LED (${led} de ${total}).`;
}
