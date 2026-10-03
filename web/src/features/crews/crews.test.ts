/**
 * The judgements of the crew administration screen (RF-005).
 */

import { describe, expect, it } from 'vitest';

import type { Crew, CrewHistoryEntry } from '../../api/crews';
import {
  crewRows,
  draftFromCrew,
  draftProblems,
  EMPTY_DRAFT,
  historyLines,
  parseList,
} from './crews';

function crew(overrides: Partial<Crew> = {}): Crew {
  return {
    id: 'c1',
    code: 'C-01',
    name: 'Cuadrilla 1',
    leader_name: null,
    vehicle: null,
    competencies: [],
    members: [],
    zone: null,
    active: true,
    created_by: 'admin',
    updated_by: 'admin',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('parseList', () => {
  it('trims, drops blanks and dedupes', () => {
    expect(parseList('Ana Pérez,  Luis Toro , ,Ana Pérez')).toEqual(['Ana Pérez', 'Luis Toro']);
  });

  it('an empty string is an empty list', () => {
    expect(parseList('')).toEqual([]);
  });
});

describe('draftProblems', () => {
  it('a code and a name are both required', () => {
    expect(draftProblems(EMPTY_DRAFT)).toHaveLength(2);
  });

  it('nothing is wrong once both are filled', () => {
    expect(draftProblems({ ...EMPTY_DRAFT, code: 'C-01', name: 'Cuadrilla 1' })).toEqual([]);
  });

  it('whitespace alone does not count as filled in', () => {
    expect(draftProblems({ ...EMPTY_DRAFT, code: '  ', name: '  ' })).toHaveLength(2);
  });
});

describe('draftFromCrew', () => {
  it('joins lists back into comma text for the form fields', () => {
    const draft = draftFromCrew(
      crew({ competencies: ['MV', 'altura'], members: ['Ana Pérez', 'Luis Toro'] }),
    );
    expect(draft.competencies).toBe('MV, altura');
    expect(draft.members).toBe('Ana Pérez, Luis Toro');
  });

  it('a null leader, vehicle or zone becomes an empty field, not «null»', () => {
    const draft = draftFromCrew(crew());
    expect(draft.leaderName).toBe('');
    expect(draft.vehicle).toBe('');
    expect(draft.zone).toBe('');
  });
});

describe('crewRows', () => {
  it('active crews come before inactive ones', () => {
    const rows = crewRows([crew({ code: 'B', active: false }), crew({ code: 'A', active: true })]);
    expect(rows.map((row) => row.code)).toEqual(['A', 'B']);
  });

  it('within the same state, rows sort by code', () => {
    const rows = crewRows([crew({ code: 'C-02' }), crew({ code: 'C-01' })]);
    expect(rows.map((row) => row.code)).toEqual(['C-01', 'C-02']);
  });

  it('member count comes from the roster, not a guess', () => {
    const rows = crewRows([crew({ members: ['Ana Pérez', 'Luis Toro', 'Eva Ríos'] })]);
    expect(rows[0]!.memberCount).toBe(3);
  });
});

describe('historyLines', () => {
  function entry(overrides: Partial<CrewHistoryEntry> = {}): CrewHistoryEntry {
    return {
      sequence: 1,
      kind: 'creacion',
      actor: 'admin.funcional',
      occurred_at: '2026-01-01T12:00:00Z',
      payload: {},
      reason: null,
      ...overrides,
    };
  }

  it('one line per entry, with who and what', () => {
    const lines = historyLines([
      entry({ kind: 'creacion' }),
      entry({ kind: 'cambio_campo', actor: 'otra.persona' }),
    ]);
    expect(lines).toHaveLength(2);
    expect(lines[0]).toContain('Creada');
    expect(lines[0]).toContain('admin.funcional');
    expect(lines[1]).toContain('Editada');
    expect(lines[1]).toContain('otra.persona');
  });

  it('an unrecognised kind still shows, by its own name', () => {
    expect(historyLines([entry({ kind: 'algo_nuevo' })])[0]).toContain('algo_nuevo');
  });
});
