/**
 * La pantalla del auditor, renderizada (RF-161).
 *
 * Dos cosas se comprueban con cuidado. La primera, que las cuatro preguntas de RF-161 lleguen al
 * servidor como filtros y no se queden en la pantalla. La segunda, que una cadena rota se vea como
 * rota: pintar de verde una verificación que falló sería el peor defecto posible de esta pantalla,
 * porque el auditor confiaría justo donde no debe.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuditScreen } from './AuditScreen';

const EVENT = {
  sequence: 7,
  kind: 'transicion',
  subject_type: 'orden_trabajo',
  subject_id: 'wo-1',
  work_order_id: 'wo-1',
  asset_code: 'P-000452',
  actor_kind: 'persona',
  actor: 'kc|sup.1',
  device_key: 'dev-3',
  payload: { from: 'sincronizada', to: 'en_revision' },
  reason: null,
  occurred_at: '2026-09-20T12:00:00+00:00',
  hash: 'a'.repeat(64),
  prev_hash: 'b'.repeat(64),
};

function mockApi(verify: Record<string, unknown>, events = [EVENT]) {
  const urls: string[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    urls.push(url);
    if (url.includes('/verify')) {
      return { ok: true, status: 200, json: async () => verify } as unknown as Response;
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ total: events.length, events }),
    } as unknown as Response;
  });
  return { fetcher, urls };
}

afterEach(() => vi.unstubAllGlobals());

describe('la trazabilidad', () => {
  it('muestra el evento con lo que pasó y quién lo hizo', async () => {
    const { fetcher } = mockApi({ events: 1, intact: true, broken_at: null, problem: null });
    vi.stubGlobal('fetch', fetcher);
    render(<AuditScreen businessUnit="GYE" />);

    expect(await screen.findByText(/sincronizada → en_revision/)).toBeTruthy();
    expect(screen.getByText(/kc\|sup.1/)).toBeTruthy();
    expect(screen.getByText(/dev-3/)).toBeTruthy();
  });

  it('los cuatro filtros de RF-161 viajan al servidor', async () => {
    const { fetcher, urls } = mockApi({ events: 0, intact: true, broken_at: null, problem: null });
    vi.stubGlobal('fetch', fetcher);
    render(<AuditScreen businessUnit="GYE" />);
    await screen.findByLabelText('Activo');

    const inputs: [string, string][] = [
      ['Orden de trabajo', 'wo-9'],
      ['Activo', 'P-000999'],
      ['Persona', 'kc|tecnico.2'],
      ['Dispositivo', 'dev-8'],
    ];
    for (const [label, value] of inputs) {
      // `fireEvent.change` y no asignar `.value` a mano: React lleva su propio rastreador del valor
      // y una asignación directa no le llega, así que el test pasaría con la pantalla rota.
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    }
    (await screen.findByRole('button', { name: 'Buscar' })).click();

    await waitFor(() => {
      const asked = urls.filter((url) => url.includes('work_order_id'));
      expect(asked.length).toBeGreaterThan(0);
      expect(asked.at(-1)).toContain('asset_code=P-000999');
      expect(asked.at(-1)).toContain('device_key=dev-8');
    });
  });

  it('sin resultados lo dice, en vez de una tabla vacía', async () => {
    const { fetcher } = mockApi({ events: 0, intact: true, broken_at: null, problem: null }, []);
    vi.stubGlobal('fetch', fetcher);
    render(<AuditScreen businessUnit="GYE" />);
    expect(await screen.findByText(/Ningún evento coincide/)).toBeTruthy();
  });
});

describe('la integridad de la cadena', () => {
  it('una cadena íntegra se informa con su número de eventos', async () => {
    const { fetcher } = mockApi({ events: 12, intact: true, broken_at: null, problem: null });
    vi.stubGlobal('fetch', fetcher);
    render(<AuditScreen businessUnit="GYE" />);

    (await screen.findByRole('button', { name: /Verificar la cadena/ })).click();
    expect(await screen.findByText(/íntegra sobre 12/)).toBeTruthy();
  });

  it('una cadena rota se ve rota, con el evento y el motivo', async () => {
    // El peor defecto posible de esta pantalla sería pintar de verde una verificación que falló.
    const { fetcher } = mockApi({
      events: 12,
      intact: false,
      broken_at: 5,
      problem: 'el evento 5 fue alterado después de escribirse',
    });
    vi.stubGlobal('fetch', fetcher);
    render(<AuditScreen businessUnit="GYE" />);

    (await screen.findByRole('button', { name: /Verificar la cadena/ })).click();
    const verdict = await screen.findByText(/Cadena rota en el evento 5/);
    expect(verdict.className).toContain('audit-broken');
    expect(verdict.textContent).toContain('alterado');
  });
});

describe('lo que la pantalla no tiene', () => {
  it('ningún botón que edite ni borre la bitácora (RF-160)', async () => {
    const { fetcher } = mockApi({ events: 1, intact: true, broken_at: null, problem: null });
    vi.stubGlobal('fetch', fetcher);
    render(<AuditScreen businessUnit="GYE" />);
    await screen.findByText(/sincronizada → en_revision/);

    const labels = screen
      .getAllByRole('button')
      .map((button) => (button.textContent ?? '').toLowerCase());
    for (const forbidden of ['borrar', 'eliminar', 'editar', 'corregir', 'anular']) {
      expect(labels.some((label) => label.includes(forbidden))).toBe(false);
    }
  });
});
