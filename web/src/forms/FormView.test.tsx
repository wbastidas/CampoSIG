/**
 * La vista del formulario capturado, renderizada (I6 «vista de formulario»).
 *
 * La pantalla de revisión mostraba todo *sobre* una captura —la auditoría de IA, los hallazgos, las
 * fotos— y nunca la captura. Un supervisor podía aprobar una OT sin haber visto una sola vez las
 * respuestas como las escribió la cuadrilla, que es la única vista de la que trata la decisión.
 */

import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { FormView } from './FormView';
import type { FieldOrigin } from './origin';

const SCHEMA = {
  properties: {
    final_state: { type: 'string', title: 'Estado final' },
    unresolved_reason: { type: 'string', title: 'Causa de no resolución' },
    measured_ohms: { type: 'number', title: 'Resistencia medida' },
    signposted: { type: 'boolean', title: '¿Quedó señalizado?' },
    material: { type: 'string', title: 'Material' },
    activities: { type: 'array', title: 'Actividades' },
  },
  required: ['final_state', 'measured_ohms'],
};

const UI = {
  'ui:groups': [
    { block: 'B05', title: 'Estado encontrado', fields: ['material'] },
    { block: 'B13', title: 'Mediciones', fields: ['measured_ohms'] },
    { block: 'B12', title: 'Cierre', fields: ['final_state', 'unresolved_reason', 'signposted'] },
  ],
};

const RULES = [
  {
    when: { in: [{ var: 'final_state' }, ['parcial', 'no_resuelto']] },
    require: ['unresolved_reason'],
    message: 'Indique la causa cuando el trabajo no quedó resuelto',
  },
];

function aiEntry(overrides: Partial<FieldOrigin> = {}): FieldOrigin {
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

describe('la captura, como el formulario la pide', () => {
  it('muestra los bloques en su orden con sus etiquetas', () => {
    render(
      <FormView
        schema={SCHEMA}
        uiSchema={UI}
        answers={{ material: 'concrete', measured_ohms: 18.4, final_state: 'resuelto' }}
      />,
    );
    const headings = screen.getAllByRole('heading', { level: 4 }).map((h) => h.textContent ?? '');
    expect(headings[0]).toContain('Estado encontrado');
    expect(headings[1]).toContain('Mediciones');
    expect(headings[2]).toContain('Cierre');
  });

  it('un booleano se lee Sí o No, no true', () => {
    // La UI está en español del Ecuador (regla 11): `true` bajo «¿Quedó señalizado?» es el formato
    // de almacenamiento, no la respuesta.
    render(<FormView schema={SCHEMA} uiSchema={UI} answers={{ signposted: false }} />);
    const cierre = screen.getByLabelText('Cierre');
    expect(within(cierre).getByText('No')).not.toBeNull();
  });

  it('una tabla repetible no se imprime como [object Object]', () => {
    // El defecto por el que `displayValue` existe, aquí también.
    render(
      <FormView
        schema={SCHEMA}
        uiSchema={{ 'ui:groups': [{ block: 'B06', title: 'Actividades', fields: ['activities'] }] }}
        answers={{ activities: [{ uc: 'E1', cantidad: 2 }] }}
      />,
    );
    expect(screen.getByText(/uc: E1; cantidad: 2/)).not.toBeNull();
    expect(screen.queryByText(/object Object/)).toBeNull();
  });

  it('un campo sin responder sale con raya y no se omite', () => {
    // Omitirlo haría que la captura pareciera más completa de lo que está.
    render(<FormView schema={SCHEMA} uiSchema={UI} answers={{}} />);
    expect(screen.getByText('Resistencia medida')).not.toBeNull();
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });
});

describe('lo que el supervisor no debería tener que inferir', () => {
  it('un valor propuesto por un modelo se marca con su procedencia (regla 8)', () => {
    render(
      <FormView
        schema={SCHEMA}
        uiSchema={UI}
        answers={{ material: 'concrete' }}
        provenance={[aiEntry()]}
      />,
    );
    expect(screen.getByText(/mobilenetv3-pole 2026.09/)).not.toBeNull();
    expect(screen.getByText(/aceptado sin cambios por tecnico.7/)).not.toBeNull();
  });

  it('un valor que la persona escribió no lleva nota', () => {
    // Marcarlos todos significaría nada.
    render(
      <FormView
        schema={SCHEMA}
        uiSchema={UI}
        answers={{ material: 'concrete', measured_ohms: 18.4 }}
        provenance={[aiEntry()]}
      />,
    );
    const mediciones = screen.getByLabelText('Mediciones');
    expect(within(mediciones).queryByText(/propuesto por/)).toBeNull();
  });

  it('una procedencia que no es de IA no marca el campo', () => {
    render(
      <FormView
        schema={SCHEMA}
        uiSchema={UI}
        answers={{ material: 'concrete' }}
        provenance={[aiEntry({ is_ai: false })]}
      />,
    );
    expect(screen.queryByText(/propuesto por/)).toBeNull();
  });

  it('un requisito condicional sin cumplir se marca con el mensaje de la regla', () => {
    render(
      <FormView
        schema={SCHEMA}
        uiSchema={UI}
        answers={{ final_state: 'no_resuelto' }}
        rules={RULES}
      />,
    );
    expect(
      screen.getByText('Indique la causa cuando el trabajo no quedó resuelto'),
    ).not.toBeNull();
  });

  it('y no se marca cuando la regla no aplica', () => {
    render(
      <FormView schema={SCHEMA} uiSchema={UI} answers={{ final_state: 'resuelto' }} rules={RULES} />,
    );
    expect(screen.queryByText(/Indique la causa/)).toBeNull();
  });

  it('un campo huérfano se muestra en vez de desaparecer', () => {
    render(
      <FormView
        schema={SCHEMA}
        uiSchema={{ 'ui:groups': [{ block: 'B12', title: 'Cierre', fields: ['final_state'] }] }}
        answers={{ final_state: 'resuelto', measured_ohms: 18.4 }}
      />,
    );
    const orphans = screen.getByLabelText('Campos sin bloque');
    expect(within(orphans).getByText('Resistencia medida')).not.toBeNull();
  });

  it('los avisos del compositor se muestran', () => {
    render(
      <FormView
        schema={SCHEMA}
        uiSchema={UI}
        answers={{}}
        warnings={["el bloque 'B07' no existe y se omitió"]}
      />,
    );
    expect(screen.getByText(/B07/)).not.toBeNull();
  });

  it('un formulario sin bloques lo dice en vez de quedar en blanco', () => {
    render(<FormView schema={{}} uiSchema={{}} answers={{}} />);
    expect(screen.getByText(/no declara bloques que mostrar/)).not.toBeNull();
  });
});
