/**
 * Cómo se lee el tablero de mantenimiento (RF-133).
 *
 * El número con el que se planifica es una lista de pendientes, y una lista cuya definición nadie
 * puede ver se discute en vez de trabajarse. Así que lo que se prueba es que la definición del
 * servidor llegue intacta, que lo que **no** es pendiente se muestre al lado en vez de plegarse
 * dentro, y que la reincidencia distinga los dos casos que llevan a decisiones distintas.
 */

import { describe, expect, it } from 'vitest';

import type { AssetRecurrence, FeederHeat, MaintenanceBoard } from '../../api/analytics';
import {
  backlogCaveats,
  backlogHeadline,
  backlogRows,
  CRITICALITY_ORDER,
  criticalityLabel,
  defectOptions,
  feederLine,
  percent,
  recurrenceAdvice,
} from './maintenance';

function board(overrides: Partial<MaintenanceBoard> = {}): MaintenanceBoard {
  return {
    since: '2026-08-21T12:00:00+00:00',
    until: '2026-09-20T12:00:00+00:00',
    defect_filter: null,
    findings: 30,
    heat: { by_feeder: [], without_feeder: 0 },
    recurrence: [],
    backlog: {
      open_by_criticality: { critica: 2, alta: 5 },
      open: 7,
      attended: 20,
      untrackable: 3,
      wants_order: 4,
      definition: 'abierto significa que no hay ninguna OT posterior cerrada sobre el mismo activo',
    },
    by_defect: { cruceta_podrida: 18, aislador_roto: 12 },
    open_findings: [],
    ...overrides,
  };
}

describe('la lista de pendientes', () => {
  it('dice cuántos de cuántos', () => {
    expect(backlogHeadline(board())).toBe('7 hallazgo(s) abierto(s) de 30 registrado(s).');
  });

  it('sin hallazgos lo dice en vez de mostrar un cero', () => {
    expect(backlogHeadline(board({ findings: 0 }))).toContain('Sin hallazgos registrados');
  });

  it('las criticidades van de peor a mejor e incluyen las vacías', () => {
    // «crítica: 0» es la frase que un planificador quiere leer; una fila que desaparece deja la duda
    // de si es cero o de si el tablero se rompió.
    const rows = backlogRows(board());
    expect(rows.map((row) => row.criticality)).toEqual(CRITICALITY_ORDER);
    expect(rows.find((row) => row.criticality === 'media')?.open).toBe(0);
  });

  it('lo atendido y lo que no se puede seguir se muestran aparte, no plegados', () => {
    const lines = backlogCaveats(board());
    expect(lines.some((line) => line.includes('20 con trabajo posterior'))).toBe(true);
    const untrackable = lines.find((line) => line.includes('3 sin código de activo'));
    expect(untrackable).toContain('ni como abiertos ni como atendidos');
  });

  it('lo que la cuadrilla pidió convertir se dice', () => {
    expect(backlogCaveats(board()).some((line) => line.includes('4 con petición'))).toBe(true);
  });

  it('sin salvedades no inventa ninguna', () => {
    const clean = board({
      backlog: { ...board().backlog, attended: 0, untrackable: 0, wants_order: 0 },
    });
    expect(backlogCaveats(clean)).toEqual([]);
  });
});

describe('el calor de un alimentador', () => {
  function heat(overrides: Partial<FeederHeat> = {}): FeederHeat {
    return {
      feeder_code: 'ALIM-NORTE',
      defects: 18,
      share: 0.6,
      top_defect: { defect_code: 'cruceta_podrida', times: 12 },
      ...overrides,
    };
  }

  it('dice cuántos, qué parte del periodo y cuál domina', () => {
    const said = feederLine(heat());
    expect(said).toContain('18 defecto(s)');
    expect(said).toContain('60 %');
    expect(said).toContain('cruceta_podrida');
  });

  it('sin defecto dominante no inventa uno', () => {
    expect(feederLine(heat({ top_defect: null }))).not.toContain('sobre todo');
  });

  it('los porcentajes se escriben con coma', () => {
    expect(percent(0.125, 1)).toBe('12,5 %');
  });
});

describe('la reincidencia de un activo', () => {
  function asset(overrides: Partial<AssetRecurrence> = {}): AssetRecurrence {
    return {
      asset_code: 'P-000452',
      findings: 3,
      defects: { cruceta_podrida: 3 },
      worst_criticality: 'alta',
      ...overrides,
    };
  }

  it('un defecto repetido es una reparación que no aguantó', () => {
    expect(recurrenceAdvice(asset())).toContain('no aguantó');
  });

  it('varios defectos distintos apuntan al final de la vida del activo', () => {
    // Son decisiones distintas: una revisita contra un reemplazo.
    const said = recurrenceAdvice(
      asset({ defects: { cruceta_podrida: 1, aislador_roto: 1, poste_fisurado: 1 } }),
    );
    expect(said).toContain('3 defectos distintos');
    expect(said).toContain('final de su vida');
  });
});

describe('el filtro de defectos', () => {
  it('ofrece los tipos del periodo, el más frecuente primero', () => {
    const options = defectOptions(board());
    expect(options.map((option) => option.code)).toEqual(['cruceta_podrida', 'aislador_roto']);
  });

  it('sin defectos no ofrece nada en vez de un catálogo inventado', () => {
    expect(defectOptions(board({ by_defect: {} }))).toEqual([]);
  });
});

describe('las etiquetas', () => {
  it('las criticidades se traducen y una desconocida muestra su clave', () => {
    expect(criticalityLabel('critica')).toBe('Crítica');
    expect(criticalityLabel('urgentisima')).toBe('urgentisima');
  });
});
