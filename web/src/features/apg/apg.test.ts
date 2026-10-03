/**
 * Cómo se lee el tablero de alumbrado (RF-131, ADR-007).
 *
 * El número de este tablero va a un informe al regulador, así que todo lo que se prueba aquí es lo
 * que evita que eso pase con un número que no lo sostiene: que un porcentaje medido contra un plazo
 * sin verificar se marque como provisional, que las atenciones no medibles se cuenten al lado, y que
 * la tasa de falla diga por qué está dividida.
 */

import { describe, expect, it } from 'vitest';

import type { ApgBoard, ApgBreach } from '../../api/analytics';
import {
  breachCitation,
  causeLabel,
  complianceCaveats,
  complianceHeadline,
  hours,
  ledShare,
  percent,
  shares,
  technologyLabel,
} from './apg';

function board(overrides: Partial<ApgBoard> = {}): ApgBoard {
  return {
    computed_at: '2026-09-20T12:00:00+00:00',
    since: '2026-08-21T12:00:00+00:00',
    until: '2026-09-20T12:00:00+00:00',
    attentions: 30,
    restoration: {
      within: 24,
      breached: 6,
      judged: 30,
      not_measurable: 0,
      against_unverified_limit: 0,
      compliance: 0.8,
      median_hours: 10,
      p90_hours: 40,
      worst_hours: 90,
      min_sample: 5,
    },
    fleet: { by_technology: { led: 18, sodium_hp: 12 }, without_technology: 0 },
    failures: {
      by_cause: { fotocontrol: 12, lampara_o_modulo: 18 },
      distinct_luminaires: 20,
      failures_per_luminaire: 1.5,
      denominator: 'luminarias con al menos una falla en el periodo, no el total instalado',
      repeat_offenders: [{ asset_code: 'LUM-A', failures: 3 }],
    },
    breaches: [],
    ...overrides,
  };
}

function breach(overrides: Partial<ApgBreach> = {}): ApgBreach {
  return {
    work_order_id: 'wo-1',
    order_code: 'OT-1',
    asset_code: 'LUM-A',
    hours: 60,
    limit_hours: 48,
    within_limit: false,
    limit_verified: true,
    norm_ref: 'ARCERNNR 007/23',
    article_ref: 'Art. 21',
    message: 'la reposición tomó 60.0 h por encima del plazo de 48 h',
    ...overrides,
  };
}

describe('los números se escriben como en Ecuador', () => {
  it('porcentajes con coma decimal', () => {
    expect(percent(0.8)).toBe('80,0 %');
    expect(percent(0.8)).not.toContain('.');
  });

  it('horas, y días cuando pasa de un día', () => {
    expect(hours(10)).toBe('10,0 h');
    expect(hours(36)).toBe('1,5 d');
    expect(hours(null)).toBe('—');
  });
});

describe('el titular del cumplimiento', () => {
  it('da el porcentaje con las atenciones que lo sostienen', () => {
    expect(complianceHeadline(board())).toContain('80,0 % dentro del plazo (24 de 30)');
  });

  it('con muestra pequeña dice cuántas faltan', () => {
    const said = complianceHeadline(
      board({
        restoration: { ...board().restoration, judged: 2, compliance: null },
      }),
    );
    expect(said).toContain('2 de 5');
  });

  it('sin nada medible lo dice, que no es «100 %»', () => {
    const said = complianceHeadline(
      board({ restoration: { ...board().restoration, judged: 0, compliance: null } }),
    );
    expect(said).toContain('Ninguna atención');
    expect(said).not.toContain('%');
  });
});

describe('lo que tiene que viajar con el porcentaje', () => {
  it('un plazo sin verificar lo vuelve provisional y no citable', () => {
    // ADR-007: un número con aspecto oficial invita al lector a dejar de comprobar.
    const lines = complianceCaveats(
      board({ restoration: { ...board().restoration, against_unverified_limit: 6 } }),
    );
    expect(lines[0]).toContain('sin verificar');
    expect(lines[0]).toContain('no citable');
  });

  it('las atenciones no medibles se dicen con el motivo posible', () => {
    const lines = complianceCaveats(
      board({ restoration: { ...board().restoration, not_measurable: 7 } }),
    );
    expect(lines[0]).toContain('7 atención(es) sin plazo medible');
    expect(lines[0]).toContain('parámetro regulatorio');
  });

  it('si se pudo medir menos de la mitad, se avisa aparte', () => {
    // Un 100 % sobre cinco medibles de doscientas capturadas no es una tasa de cumplimiento.
    const lines = complianceCaveats(
      board({ restoration: { ...board().restoration, judged: 5, not_measurable: 195 } }),
    );
    expect(lines.some((line) => line.includes('menos de la mitad'))).toBe(true);
  });

  it('sin salvedades no inventa ninguna', () => {
    expect(complianceCaveats(board())).toEqual([]);
  });
});

describe('la cita de un incumplimiento', () => {
  it('con límite verificado cita la norma y el artículo', () => {
    expect(breachCitation(breach())).toBe('ARCERNNR 007/23 · Art. 21');
  });

  it('sin verificar NO se presenta como cita del texto oficial', () => {
    const said = breachCitation(breach({ limit_verified: false }));
    expect(said).toContain('provisional');
    expect(said).not.toContain('ARCERNNR');
  });

  it('sin referencia ninguna lo dice en vez de dejar un hueco', () => {
    expect(breachCitation(breach({ norm_ref: null, article_ref: null }))).toBe('Sin referencia');
  });
});

describe('la flota', () => {
  it('la cuota de LED es el número de la modernización', () => {
    expect(ledShare(board())).toContain('60,0 % de las atendidas son LED (18 de 30)');
  });

  it('sin tecnologías registradas no hay cuota', () => {
    expect(ledShare(board({ fleet: { by_technology: {}, without_technology: 4 } }))).toBeNull();
  });

  it('una tecnología desconocida muestra su clave y no se pliega en «Otra»', () => {
    // Plegarla esconderia una clase entera de la flota que el perfil sí conoce.
    expect(technologyLabel('induccion_magnetica')).toBe('induccion_magnetica');
    expect(technologyLabel('led')).toBe('LED');
  });

  it('las cuotas se ordenan de mayor a menor', () => {
    const rows = shares({ led: 3, sodium_hp: 10 });
    expect(rows.map((row) => row.key)).toEqual(['sodium_hp', 'led']);
    expect(rows[0]!.share).toBeCloseTo(10 / 13);
  });

  it('sin datos no hay cuotas y no se divide por cero', () => {
    expect(shares({})).toEqual([]);
  });
});

describe('las causas', () => {
  it('se traducen, y una desconocida muestra su clave', () => {
    expect(causeLabel('fotocontrol')).toBe('Fotocontrol');
    expect(causeLabel('causa_nueva')).toBe('causa_nueva');
  });
});
