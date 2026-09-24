/**
 * El tablero de consignaciones, renderizado (RF-024).
 *
 * Lo que se prueba es que las decisiones lleguen al servidor como el procedimiento las exige: una
 * otorgada con su número, una negada con su motivo, y ninguna de las dos desde quien la pidió. Y que
 * la pantalla diga las dos cosas que los estados solos no dicen: la otorgada que nadie usó y la
 * ventana que ya cerró con el descargo vigente.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { OutageList, OutageRequestRow } from '../../api/outages';
import { OutagesScreen } from './OutagesScreen';

const NOW = new Date('2026-09-26T18:00:00Z');
const PLANNER = 'kc|planificador.demo';
const CONTROL = 'kc|centro.control';

function request(overrides: Partial<OutageRequestRow> = {}): OutageRequestRow {
  return {
    id: 'c1',
    number: null,
    state: 'solicitada',
    equipment: 'Alimentador 04BH070T11, tramo sur',
    feeder_code: '04BH070T11',
    substation_code: null,
    window_start: '2026-09-26T11:00:00Z',
    window_end: '2026-09-26T23:00:00Z',
    requested_by: PLANNER,
    decided_by: null,
    decided_at: null,
    returned_at: null,
    returned_by: null,
    note: null,
    grants_permit: false,
    orders: 0,
    unused: false,
    ...overrides,
  };
}

function list(...requests: OutageRequestRow[]): OutageList {
  const counts: Record<string, number> = {};
  for (const row of requests) counts[row.state] = (counts[row.state] ?? 0) + 1;
  return { counts, requests };
}

function mockApi(body: OutageList, onPost?: (url: string, payload: unknown) => void) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === 'POST') {
      onPost?.(url, init.body ? JSON.parse(String(init.body)) : null);
      return {
        ok: true,
        status: 200,
        json: async () => request({ state: 'aprobada', number: 'DESC-2026-0771' }),
      } as unknown as Response;
    }
    return { ok: true, status: 200, json: async () => body } as unknown as Response;
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('decidir una consignación', () => {
  it('otorga con el número, que es lo que llega al servidor', async () => {
    const calls: { url: string; payload: unknown }[] = [];
    vi.stubGlobal(
      'fetch',
      mockApi(list(request()), (url, payload) => calls.push({ url, payload })),
    );
    render(<OutagesScreen businessUnit="GYE" subject={CONTROL} now={() => NOW} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Decidir' }));
    fireEvent.change(screen.getByLabelText('Decisión'), { target: { value: 'otorgar' } });
    fireEvent.change(screen.getByLabelText('N.º de consignación'), {
      target: { value: 'DESC-2026-0771' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar la decisión' }));

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]?.url).toContain('/c1/approve');
    expect(calls[0]?.payload).toEqual({ number: 'DESC-2026-0771', note: undefined });
  });

  it('no otorga sin número: el número es la autoridad', async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      'fetch',
      mockApi(list(request()), (url) => calls.push(url)),
    );
    render(<OutagesScreen businessUnit="GYE" subject={CONTROL} now={() => NOW} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Decidir' }));
    fireEvent.change(screen.getByLabelText('Decisión'), { target: { value: 'otorgar' } });

    const confirm = screen.getByRole('button', { name: 'Confirmar la decisión' });
    expect((confirm as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(confirm);
    expect(calls).toHaveLength(0);
  });

  it('niega con el motivo, y no sin él', async () => {
    const calls: { url: string; payload: unknown }[] = [];
    vi.stubGlobal(
      'fetch',
      mockApi(list(request()), (url, payload) => calls.push({ url, payload })),
    );
    render(<OutagesScreen businessUnit="GYE" subject={CONTROL} now={() => NOW} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Decidir' }));
    fireEvent.change(screen.getByLabelText('Decisión'), { target: { value: 'negar' } });
    expect(
      screen.getByRole<HTMLButtonElement>('button', { name: 'Confirmar la decisión' }).disabled,
    ).toBe(true);

    fireEvent.change(screen.getByLabelText('Motivo'), {
      target: { value: 'hay carga que no se puede transferir' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar la decisión' }));

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]?.url).toContain('/c1/reject');
    expect(calls[0]?.payload).toEqual({ note: 'hay carga que no se puede transferir' });
  });

  it('quien la pidió no la otorga, y la pantalla dice por qué', async () => {
    vi.stubGlobal('fetch', mockApi(list(request())));
    render(<OutagesScreen businessUnit="GYE" subject={PLANNER} now={() => NOW} />);

    await waitFor(() => expect(screen.getByText(/la otorga otra persona/)).toBeTruthy());
    expect(screen.queryByRole('button', { name: 'Decidir' })).toBeNull();
  });

  it('una ya decidida no se vuelve a decidir', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(list(request({ state: 'aprobada', number: 'DESC-1', grants_permit: true }))),
    );
    render(<OutagesScreen businessUnit="GYE" subject={CONTROL} now={() => NOW} />);

    await waitFor(() => expect(screen.getByText(/DESC-1/)).toBeTruthy());
    expect(screen.queryByRole('button', { name: 'Decidir' })).toBeNull();
  });

  it('quien no es del Centro de Control no ve el botón; el servidor lo niega igual', async () => {
    vi.stubGlobal('fetch', mockApi(list(request())));
    render(
      <OutagesScreen businessUnit="GYE" subject={CONTROL} mayDecide={false} now={() => NOW} />,
    );

    await waitFor(() => expect(screen.getByText(/tramo sur/)).toBeTruthy());
    expect(screen.queryByRole('button', { name: 'Decidir' })).toBeNull();
  });
});

describe('lo que la pantalla avisa', () => {
  it('una otorgada sin ninguna OT es una línea desenergizada para nada', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        list(request({ state: 'aprobada', number: 'DESC-1', grants_permit: true, unused: true })),
      ),
    );
    render(<OutagesScreen businessUnit="GYE" subject={CONTROL} now={() => NOW} />);

    await waitFor(() => expect(screen.getByText(/desenergizada para nada/)).toBeTruthy());
  });

  it('una ventana cerrada con el descargo vigente se dice y se puede devolver', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        list(
          request({
            state: 'aprobada',
            number: 'DESC-1',
            grants_permit: true,
            window_end: '2026-09-26T12:00:00Z',
          }),
        ),
      ),
    );
    render(<OutagesScreen businessUnit="GYE" subject={CONTROL} now={() => NOW} />);

    await waitFor(() => expect(screen.getByText(/ventana ya cerró/)).toBeTruthy());
    expect(screen.getByRole('button', { name: 'Devolver al Centro de Control' })).toBeTruthy();
  });

  it('una otorgada sin número no se presenta como habilitada', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(list(request({ state: 'aprobada', number: null, grants_permit: false }))),
    );
    render(<OutagesScreen businessUnit="GYE" subject={CONTROL} now={() => NOW} />);

    await waitFor(() => expect(screen.getByText(/no habilita el F-TR-02/)).toBeTruthy());
  });

  it('sin consignaciones lo dice, en lugar de una lista vacía', async () => {
    vi.stubGlobal('fetch', mockApi(list()));
    render(<OutagesScreen businessUnit="GYE" subject={CONTROL} now={() => NOW} />);

    await waitFor(() => expect(screen.getByText(/No hay consignaciones/)).toBeTruthy());
  });

  it('el error del servidor se muestra tal cual', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 403,
            statusText: 'Forbidden',
            json: async () => ({ detail: 'quien solicita una consignación no la otorga' }),
          }) as unknown as Response,
      ),
    );
    render(<OutagesScreen businessUnit="GYE" subject={CONTROL} now={() => NOW} />);

    await waitFor(() =>
      expect(screen.getByText('quien solicita una consignación no la otorga')).toBeTruthy(),
    );
  });
});

describe('solicitar una consignación', () => {
  it('manda la ventana en UTC y el equipo, sin autor en el cuerpo', async () => {
    const calls: { url: string; payload: unknown }[] = [];
    vi.stubGlobal(
      'fetch',
      mockApi(list(), (url, payload) => calls.push({ url, payload })),
    );
    render(<OutagesScreen businessUnit="GYE" subject={PLANNER} now={() => NOW} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Solicitar consignación' }));
    fireEvent.change(screen.getByLabelText('Equipo o tramo'), {
      target: { value: 'Alimentador sur, tramo 3' },
    });
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-09-27T06:00' } });
    fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-09-27T12:00' } });
    fireEvent.click(screen.getByRole('button', { name: 'Enviar la solicitud' }));

    await waitFor(() => expect(calls).toHaveLength(1));
    const payload = calls[0]?.payload as Record<string, unknown>;
    expect(payload.equipment).toBe('Alimentador sur, tramo 3');
    expect(payload).not.toHaveProperty('requested_by');
    expect(String(payload.window_start)).toContain('2026-09-27');
  });

  it('una ventana invertida no se envía, y lo dice', async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      'fetch',
      mockApi(list(), (url) => calls.push(url)),
    );
    render(<OutagesScreen businessUnit="GYE" subject={PLANNER} now={() => NOW} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Solicitar consignación' }));
    fireEvent.change(screen.getByLabelText('Equipo o tramo'), { target: { value: 'Tramo sur' } });
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-09-27T12:00' } });
    fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-09-27T06:00' } });

    expect(screen.getByText('La ventana termina antes de empezar.')).toBeTruthy();
    const send = screen.getByRole('button', { name: 'Enviar la solicitud' });
    expect((send as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(send);
    expect(calls).toHaveLength(0);
  });

  it('quien no puede pedir no ve el formulario', async () => {
    vi.stubGlobal('fetch', mockApi(list()));
    render(
      <OutagesScreen businessUnit="GYE" subject={CONTROL} mayRequest={false} now={() => NOW} />,
    );

    await waitFor(() => expect(screen.getByText(/No hay consignaciones/)).toBeTruthy());
    expect(screen.queryByRole('button', { name: 'Solicitar consignación' })).toBeNull();
  });
});
