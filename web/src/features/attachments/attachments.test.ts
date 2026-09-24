/**
 * Los juicios de la lista de adjuntos (RF-017).
 *
 * Lo que se prueba es lo que decide si la cuadrilla tiene el archivo: cuánto pesa la descarga
 * frente a su techo, qué no está viajando, y de quién es el plano cuando la OT es un frente.
 */

import { describe, expect, it } from 'vitest';

import type { Attachment, AttachmentList } from '../../api/attachments';
import {
  budgetHeadline,
  budgetWarning,
  kindLabel,
  megabytes,
  rows,
  withdrawAdvice,
  withdrawProblems,
} from './attachments';

const MB = 1024 * 1024;

function attachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: 'a1',
    work_order_id: 'ot-1',
    kind: 'plano',
    title: 'Plano estructural del poste 4471',
    note: null,
    filename: 'plano.pdf',
    content_hash: 'a'.repeat(64),
    size_bytes: 2 * MB,
    mime_type: 'application/pdf',
    offline: true,
    uploaded_by: 'kc|planificador.demo',
    uploaded_at: '2026-09-24T14:00:00Z',
    withdrawn_at: null,
    withdrawn_by: null,
    withdrawn_reason: null,
    is_active: true,
    ...overrides,
  };
}

function list(overrides: Partial<AttachmentList> = {}): AttachmentList {
  return {
    work_order_id: 'ot-1',
    offline_bytes: 2 * MB,
    max_offline_bytes: 60 * MB,
    attachments: [attachment()],
    ...overrides,
  };
}

describe('megabytes', () => {
  it('usa coma decimal, que es la de Ecuador (regla 11)', () => {
    expect(megabytes(2.5 * MB)).toBe('2,5');
    expect(megabytes(60 * MB)).toBe('60,0');
  });
});

describe('budgetHeadline', () => {
  it('dice el peso con su techo y nunca un porcentaje a secas', () => {
    expect(budgetHeadline(list())).toBe('2,0 de 60,0 MB');
  });
});

describe('budgetWarning', () => {
  it('calla mientras sobra espacio', () => {
    expect(budgetWarning(list())).toBeNull();
  });

  it('avisa a las cuatro quintas partes, antes de que el servidor rechace la subida', () => {
    const warning = budgetWarning(list({ offline_bytes: 50 * MB }));

    expect(warning).toContain('50,0 MB');
    expect(warning).toContain('60,0 MB');
    expect(warning).toContain('no baja al teléfono');
  });
});

describe('rows', () => {
  it('distingue lo que viaja, lo que no baja y lo retirado', () => {
    const view = rows(
      list({
        attachments: [
          attachment({ id: 'a1' }),
          attachment({ id: 'a2', offline: false }),
          attachment({
            id: 'a3',
            is_active: false,
            withdrawn_at: '2026-09-24T15:00:00Z',
            withdrawn_reason: 'lo reemplaza el diseño final',
          }),
        ],
      }),
    );

    expect(view.map((row) => row.travel)).toEqual(['viaja', 'no_viaja', 'retirado']);
  });

  it('marca el adjunto que es de la obra y no del frente (RF-015)', () => {
    const view = rows(
      list({
        work_order_id: 'frente-3',
        attachments: [
          attachment({ work_order_id: 'obra-1' }),
          attachment({ id: 'a2', work_order_id: 'frente-3' }),
        ],
      }),
    );

    expect(view[0]?.fromWork).toBe(true);
    expect(view[1]?.fromWork).toBe(false);
  });

  it('sin datos no inventa filas', () => {
    expect(rows(null)).toEqual([]);
  });
});

describe('withdrawProblems', () => {
  it('exige el motivo: la cuadrilla pudo haber trabajado con ese plano', () => {
    expect(withdrawProblems('   ')).toHaveLength(1);
    expect(withdrawProblems('lo reemplaza el diseño final')).toEqual([]);
  });
});

describe('withdrawAdvice', () => {
  it('dice que no se borra, porque eso es lo que la gente teme al pulsar', () => {
    const advice = withdrawAdvice({ attachment: attachment(), fromWork: false, travel: 'viaja' });

    expect(advice).toContain('No se borra');
  });

  it('avisa cuando el plano es de la obra y afecta a todos los frentes', () => {
    const advice = withdrawAdvice({
      attachment: attachment({ work_order_id: 'obra-1' }),
      fromWork: true,
      travel: 'viaja',
    });

    expect(advice).toContain('todos sus frentes');
  });
});

describe('kindLabel', () => {
  it('traduce los tipos y deja pasar uno desconocido sin romperse', () => {
    expect(kindLabel('diseno')).toBe('Diseño');
    expect(kindLabel('otro_tipo')).toBe('otro_tipo');
  });
});
