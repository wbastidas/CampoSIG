/**
 * La disposición de un formulario compuesto (I5, I6).
 *
 * La regla que se prueba es una: **la disposición es la del formulario, no la del renderizador**.
 * Una lista de campos escrita en el código deja de mencionar el que un administrador funcional
 * añade mañana, y la pantalla sigue pareciendo completa — el mismo fallo que el acta evita en papel.
 */

import { describe, expect, it } from 'vitest';

import { annotationsOf, fieldLabel, formSections, orphanFields } from './layout';

const SCHEMA = {
  properties: {
    final_state: { type: 'string', title: 'Estado final' },
    unresolved_reason: { type: 'string', title: 'Causa de no resolución' },
    measured_ohms: { type: 'number', title: 'Resistencia medida', 'x-regulatory-parameter': 'PAT' },
    found: { type: 'string', title: 'Encontrado', 'x-ai-generated': true },
    sin_titulo: { type: 'string' },
    huerfano: { type: 'string', title: 'Campo sin bloque' },
  },
  required: ['final_state', 'measured_ohms'],
};

const UI = {
  'ui:groups': [
    { block: 'B13', title: 'Mediciones', fields: ['measured_ohms'] },
    { block: 'B10', title: 'Resumen', fields: ['found'] },
    { block: 'B12', title: 'Cierre', fields: ['final_state', 'unresolved_reason', 'sin_titulo'] },
  ],
};

describe('las secciones', () => {
  it('salen de los bloques del formulario y en su orden', () => {
    expect(formSections(SCHEMA, UI).map((s) => s.title)).toEqual([
      'Mediciones',
      'Resumen',
      'Cierre',
    ]);
  });

  it('cada campo lleva su etiqueta y si es obligatorio', () => {
    const cierre = formSections(SCHEMA, UI)[1];
    expect(cierre?.title).toBe('Resumen');
    const mediciones = formSections(SCHEMA, UI)[0];
    expect(mediciones?.fields[0]).toMatchObject({
      key: 'measured_ohms',
      label: 'Resistencia medida',
      required: true,
    });
  });

  it('un grupo que nombra campos que el esquema no tiene no produce una sección vacía', () => {
    // El bloque se compuso fuera para este tipo de trabajo; un encabezado vacío se lee como datos
    // que faltan, no como un bloque que no aplica.
    const sections = formSections(SCHEMA, {
      'ui:groups': [{ block: 'B99', title: 'Inexistente', fields: ['no_esta'] }],
    });
    expect(sections).toEqual([]);
  });

  it('un campo del grupo que el esquema no declara se salta sin arrastrar el resto', () => {
    const sections = formSections(SCHEMA, {
      'ui:groups': [{ block: 'B12', title: 'Cierre', fields: ['no_esta', 'final_state'] }],
    });
    expect(sections[0]?.fields.map((f) => f.key)).toEqual(['final_state']);
  });

  it('sin ui:groups no hay secciones, y no una excepción', () => {
    // El esquema llega por la red; un payload sin grupos no puede dejar la pantalla en blanco.
    expect(formSections(SCHEMA, {})).toEqual([]);
    expect(formSections({}, UI)).toEqual([]);
  });
});

describe('las etiquetas', () => {
  it('son el título del formulario', () => {
    expect(fieldLabel({ title: 'Estado final' }, 'final_state')).toBe('Estado final');
  });

  it('caen a la clave cuando el título falta o está vacío', () => {
    expect(fieldLabel({}, 'final_state')).toBe('final_state');
    expect(fieldLabel({ title: '   ' }, 'final_state')).toBe('final_state');
  });

  it('un título que no es una cadena no se imprime como un objeto', () => {
    // El mismo defecto que costó la pantalla de revisión: `String(valor)` sobre un objeto.
    expect(fieldLabel({ title: { es: 'Estado' } }, 'final_state')).toBe('final_state');
  });
});

describe('las anotaciones', () => {
  it('son las claves x- del campo, que es donde vive la semántica de la plataforma', () => {
    expect(annotationsOf(SCHEMA.properties.measured_ohms)).toEqual({
      'x-regulatory-parameter': 'PAT',
    });
    expect(annotationsOf({ type: 'string' })).toEqual({});
  });
});

describe('los campos huérfanos', () => {
  it('se identifican, porque es la única forma de perder datos en silencio', () => {
    // Un campo que existe, se respondió y no aparece en ningún bloque no puede quedar invisible.
    expect(orphanFields(SCHEMA, UI).map((f) => f.key)).toEqual(['huerfano']);
  });

  it('sin grupos, todo es huérfano y nada se pierde', () => {
    expect(orphanFields(SCHEMA, {}).map((f) => f.key)).toEqual(Object.keys(SCHEMA.properties));
  });
});
