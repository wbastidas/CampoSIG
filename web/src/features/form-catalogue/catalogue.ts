/**
 * Reading the form catalogue (RF-032).
 *
 * The screen exists for one sentence a person needs to be able to say out loud: «este formulario
 * cambió y nadie lo publicó». A form edited three weeks ago that was never published is a form
 * nobody in the field has ever filled in, and nothing else on the platform makes that visible.
 *
 * So the states are named rather than coloured, and the two that are *not* the same thing — never
 * published, and published but since edited — are kept apart.
 */

import type { CatalogueRow, FormVersion } from '../../api/forms';

export type Situation = 'nunca' | 'borrador' | 'al-dia';

export function situationOf(row: CatalogueRow): Situation {
  if (row.never_published) return 'nunca';
  if (row.has_unpublished_draft) return 'borrador';
  return 'al-dia';
}

export const SITUATION_LABEL: Record<Situation, string> = {
  nunca: 'Nunca publicado',
  borrador: 'Borrador sin publicar',
  'al-dia': 'Al día',
};

export const SITUATION_ADVICE: Record<Situation, string> = {
  nunca:
    'Ninguna OT tiene una forma congelada de este formulario: se compone contra el archivo, que ' +
    'puede cambiar bajo una OT ya asignada.',
  borrador:
    'El archivo cambió y nadie publicó la nueva versión, así que las OT siguen recibiendo la ' +
    'anterior. Nadie en campo ha visto este cambio.',
  'al-dia': 'Lo publicado coincide con el archivo.',
};

/** Worst first: what is never published, then the drafts, then the rest by code. */
const SITUATION_RANK: Record<Situation, number> = { nunca: 0, borrador: 1, 'al-dia': 2 };

export function catalogueRows(rows: CatalogueRow[]): (CatalogueRow & { situation: Situation })[] {
  return rows
    .map((row) => ({ ...row, situation: situationOf(row) }))
    .sort((a, b) => {
      const byRank = SITUATION_RANK[a.situation] - SITUATION_RANK[b.situation];
      return byRank !== 0 ? byRank : a.code.localeCompare(b.code);
    });
}

/** The headline. Only says «al día» when every form is. */
export function catalogueHeadline(rows: CatalogueRow[]): string {
  if (rows.length === 0) return 'No hay formularios en el catálogo.';
  const never = rows.filter((row) => row.never_published).length;
  const drafts = rows.filter((row) => row.has_unpublished_draft).length;
  if (never === 0 && drafts === 0) {
    return `${rows.length} formulario(s), todos publicados y al día.`;
  }
  const parts: string[] = [];
  if (never > 0) parts.push(`${never} nunca publicado(s)`);
  if (drafts > 0) parts.push(`${drafts} con borrador sin publicar`);
  return `${rows.length} formulario(s): ${parts.join(' y ')}.`;
}

/** Whether publishing this row would do anything. */
export function canPublish(row: CatalogueRow): boolean {
  return row.never_published || row.has_unpublished_draft;
}

/** A date as Ecuador writes it. */
export function ecuadorDate(iso: string | null): string {
  if (!iso) return '—';
  const [date] = iso.split('T');
  const parts = (date ?? '').split('-');
  if (parts.length !== 3) return iso;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

export const STATE_LABEL: Record<string, string> = {
  publicado: 'Publicada',
  obsoleto: 'Obsoleta',
};

/** One published version as a sentence, with who froze it and what it was made of. */
export function versionLine(version: FormVersion): string {
  const state = STATE_LABEL[version.state] ?? version.state;
  const who = version.published_by ?? 'sin registrar';
  return `v${version.version} · ${state} · publicada por ${who} el ${ecuadorDate(version.published_at)}`;
}

/** The blocks a version froze, so a reader sees what the form was made of. */
export function blocksLine(version: FormVersion): string {
  if (version.blocks.length === 0) return 'Sin bloques registrados.';
  return `Bloques: ${version.blocks.join(', ')}.`;
}

/** Only a published version can be withdrawn; an obsolete one already is. */
export function canObsolete(version: FormVersion): boolean {
  return version.state === 'publicado';
}
