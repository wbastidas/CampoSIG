/**
 * Cómo se describe un valor propuesto por un modelo (regla 8).
 *
 * La diferencia entre «un modelo lo propuso y un técnico lo aceptó sin cambios» y «un técnico lo
 * corrigió» es toda la auditoría: sin ella, el supervisor no puede saber si alguien miró el valor.
 */

import { describe, expect, it } from 'vitest';

import { type FieldOrigin, originNote } from './origin';

function entry(overrides: Partial<FieldOrigin> = {}): FieldOrigin {
  return {
    field_key: 'material',
    origin: 'vision',
    confidence: 0.91,
    model_name: 'mobilenetv3-pole',
    model_version: '2026.09',
    confirmed_by: 'tecnico.7',
    accepted_unchanged: true,
    is_ai: true,
    ...overrides,
  };
}

describe('la nota de procedencia', () => {
  it('nombra el origen, el modelo, la versión y la confianza', () => {
    const note = originNote(entry());
    expect(note).toContain('visión');
    expect(note).toContain('mobilenetv3-pole 2026.09');
    expect(note).toContain('confianza 91 %');
  });

  it('distingue aceptado sin cambios de corregido', () => {
    expect(originNote(entry({ accepted_unchanged: true }))).toContain('aceptado sin cambios por');
    expect(originNote(entry({ accepted_unchanged: false }))).toContain('corregido por');
  });

  it('un valor que nadie confirmó lo dice', () => {
    // Sin esto, un valor que nadie miró se lee igual que uno confirmado.
    expect(originNote(entry({ confirmed_by: null }))).toContain('sin confirmar');
  });

  it('una confianza ausente no se inventa como cero', () => {
    const note = originNote(entry({ confidence: null }));
    expect(note).toContain('sin confianza');
    expect(note).not.toContain('0 %');
  });

  it('un dictado se nombra dictado', () => {
    expect(originNote(entry({ origin: 'voz' }))).toContain('dictado');
  });

  it('un origen que no se reconoce no se presenta como humano', () => {
    expect(originNote(entry({ origin: 'otro' }))).toContain('IA');
  });
});
