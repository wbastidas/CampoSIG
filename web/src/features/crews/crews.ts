/**
 * Validating and shaping the crew roster form before it reaches the server (RF-005).
 *
 * The pure half of the screen. Competencies and members arrive as comma-separated text — the
 * same shape `catalogs.ts` already uses for synonyms — because a form field asking an
 * administrator to add N rows for N people is slower than one they type into and the server
 * validates the same either way.
 */

import type { Crew, CrewHistoryEntry } from '../../api/crews';

export interface CrewDraft {
  code: string;
  name: string;
  leaderName: string;
  vehicle: string;
  competencies: string;
  members: string;
  zone: string;
}

export const EMPTY_DRAFT: CrewDraft = {
  code: '',
  name: '',
  leaderName: '',
  vehicle: '',
  competencies: '',
  members: '',
  zone: '',
};

export function draftFromCrew(crew: Crew): CrewDraft {
  return {
    code: crew.code,
    name: crew.name,
    leaderName: crew.leader_name ?? '',
    vehicle: crew.vehicle ?? '',
    competencies: crew.competencies.join(', '),
    members: crew.members.join(', '),
    zone: crew.zone ?? '',
  };
}

/** A comma-separated list, trimmed and without repeats or blanks — same rule as `parseSynonyms`. */
export function parseList(text: string): string[] {
  const seen: string[] = [];
  for (const part of text.split(',')) {
    const cleaned = part.trim();
    if (cleaned && !seen.includes(cleaned)) seen.push(cleaned);
  }
  return seen;
}

/** What the server would refuse anyway, told here so a round trip is not how the administrator
 * finds out. */
export function draftProblems(draft: CrewDraft): string[] {
  const problems: string[] = [];
  if (!draft.code.trim()) problems.push('El código es obligatorio.');
  if (!draft.name.trim()) problems.push('El nombre es obligatorio.');
  return problems;
}

export interface CrewRow {
  code: string;
  name: string;
  leaderName: string;
  memberCount: number;
  zone: string;
  active: boolean;
  updatedBy: string;
  updatedAt: string;
}

/** The table, active first and then by code — the same order `zoneRows` already settled on. */
export function crewRows(crews: Crew[]): CrewRow[] {
  const rows = crews.map((crew) => ({
    code: crew.code,
    name: crew.name,
    leaderName: crew.leader_name ?? '—',
    memberCount: crew.members.length,
    zone: crew.zone ?? '—',
    active: crew.active,
    updatedBy: crew.updated_by ?? '—',
    updatedAt: crew.updated_at,
  }));
  return rows.sort((a, b) => {
    if (a.active !== b.active) return a.active ? -1 : 1;
    return a.code.localeCompare(b.code);
  });
}

const KIND_LABEL: Record<string, string> = {
  creacion: 'Creada',
  cambio_campo: 'Editada',
};

/** One line per change, oldest first — the «historial de cambios» RF-005 asks for. */
export function historyLines(entries: CrewHistoryEntry[]): string[] {
  return entries.map((entry) => {
    const when = entry.occurred_at ? new Date(entry.occurred_at).toLocaleString('es-EC') : '—';
    const label = KIND_LABEL[entry.kind] ?? entry.kind;
    return `${when} · ${label} por ${entry.actor}`;
  });
}
