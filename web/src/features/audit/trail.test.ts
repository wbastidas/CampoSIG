/**
 * Cómo se lee la bitácora (RF-160, RF-161).
 *
 * Una bitácora sirve para que alguien reconstruya qué pasó y lo pueda defender. Lo que se prueba
 * aquí es lo que se interpone entre las filas y esa reconstrucción: que cada evento diga en una
 * línea qué ocurrió, que el origen de un valor propuesto por un modelo se lea junto a la persona
 * que respondió por él, y —lo que más importa— que una cadena rota nunca se pinte como íntegra.
 */

import { describe, expect, it } from 'vitest';

import type { AuditEvent, ChainCheck } from '../../api/audit';
import { chainVerdict, kindLabel, modelBehind, mostRecentFirst, summarise } from './trail';

function event(overrides: Partial<AuditEvent> = {}): AuditEvent {
  return {
    sequence: 1,
    kind: 'transicion',
    subject_type: 'orden_trabajo',
    subject_id: 'wo-1',
    work_order_id: 'wo-1',
    asset_code: 'P-000452',
    actor_kind: 'persona',
    actor: 'kc|sup.1',
    device_key: null,
    payload: {},
    reason: null,
    occurred_at: '2026-09-20T12:00:00+00:00',
    hash: 'a'.repeat(64),
    prev_hash: '',
    ...overrides,
  };
}

describe('qué dice cada evento', () => {
  it('una transición muestra de dónde a dónde', () => {
    // Sin el estado de origen solo se sabe dónde acabó, que no es una historia.
    const said = summarise(event({ payload: { from: 'planificada', to: 'asignada' } }));
    expect(said).toBe('planificada → asignada');
  });

  it('un cambio de campo muestra el antes y el después', () => {
    const said = summarise(
      event({ kind: 'cambio_campo', payload: { field_key: 'material', before: null, after: 'wood' } }),
    );
    expect(said).toContain('material');
    expect(said).toContain('— → wood');
  });

  it('un valor ausente se muestra como raya y no como «null»', () => {
    expect(summarise(event({ kind: 'cambio_campo', payload: { field_key: 'x' } }))).toContain('—');
  });

  it('un booleano se lee en español', () => {
    const said = summarise(
      event({ kind: 'cambio_campo', payload: { field_key: 'ok', before: false, after: true } }),
    );
    expect(said).toContain('No → Sí');
  });

  it('un objeto no sale como [object Object]', () => {
    // Es la forma de decirle al auditor que no se le va a mostrar el dato.
    const said = summarise(
      event({ kind: 'cambio_campo', payload: { field_key: 'gps', after: { lat: -2.1 } } }),
    );
    expect(said).not.toContain('[object Object]');
    expect(said).toContain('lat');
  });

  it('un acceso a evidencia dice cuántas', () => {
    expect(summarise(event({ kind: 'acceso_evidencia', payload: { count: 3 } }))).toContain('3');
  });

  it('una exportación dice qué salió', () => {
    expect(summarise(event({ kind: 'exportacion', payload: { kind: 'acta' } }))).toContain('acta');
  });

  it('un tipo de evento desconocido muestra su nombre y no «Otro»', () => {
    // Una bitácora que esconde lo que no reconoce tiene un punto ciego justo donde pasó algo nuevo.
    expect(kindLabel('algo_nuevo')).toBe('algo_nuevo');
    expect(kindLabel('transicion')).toBe('Cambio de estado');
  });
});

describe('el origen de un valor', () => {
  it('el modelo se lee junto a la persona que respondió por el valor', () => {
    const said = modelBehind(
      event({
        kind: 'cambio_campo',
        payload: { model: { name: 'mobilenetv3-pole', version: '2026.09', confidence: 0.91 } },
      }),
    );
    expect(said).toContain('mobilenetv3-pole');
    expect(said).toContain('91 %');
  });

  it('un valor manual no inventa un modelo', () => {
    expect(modelBehind(event({ kind: 'cambio_campo', payload: { field_key: 'x' } }))).toBeNull();
  });
});

describe('la verificación de la cadena', () => {
  function check(overrides: Partial<ChainCheck> = {}): ChainCheck {
    return { events: 10, intact: true, broken_at: null, problem: null, ...overrides };
  }

  it('una cadena íntegra lo dice con cuántos eventos cubre', () => {
    expect(chainVerdict(check())).toContain('íntegra sobre 10');
  });

  it('una bitácora vacía no es una cadena rota', () => {
    expect(chainVerdict(check({ events: 0 }))).toContain('todavía no tiene eventos');
  });

  it('una cadena rota dice en qué evento y por qué', () => {
    // «La cadena está rota» sin número es un hallazgo sobre el que nadie puede actuar: el paso
    // siguiente del auditor es ir a mirar ese evento.
    const said = chainVerdict(
      check({ intact: false, broken_at: 42, problem: 'el evento 42 fue alterado' }),
    );
    expect(said).toContain('42');
    expect(said).toContain('alterado');
    expect(said).not.toContain('íntegra');
  });

  it('una cadena rota sin motivo tampoco se pinta como buena', () => {
    const said = chainVerdict(check({ intact: false, broken_at: 7, problem: null }));
    expect(said).toContain('rota');
  });
});

describe('el orden de lectura', () => {
  it('lo más reciente primero, que es por donde empieza un auditor', () => {
    const ordered = mostRecentFirst([event({ sequence: 1 }), event({ sequence: 9 })]);
    expect(ordered.map((entry) => entry.sequence)).toEqual([9, 1]);
  });
});
