/**
 * El tablero operativo, renderizado (RF-130).
 *
 * Dos propiedades se prueban con cuidado. La primera es el criterio de aceptación: los datos se
 * actualizan cada cinco minutos, y el tablero dice cuándo se calcularon —un tablero que se refresca
 * en silencio parece igual de fresco cuando el refresco lleva una hora fallando.
 *
 * La segunda es qué pasa cuando el servidor falla: el tablero anterior se queda en pantalla con el
 * aviso encima. Borrarlo dejaría al supervisor sin nada, y unos datos de hace cinco minutos con su
 * advertencia valen más que una pantalla vacía.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { OperationalBoard } from '../../api/analytics';
import { OperationsBoard } from './OperationsBoard';

const NOW = new Date('2026-09-20T12:00:00Z');

function board(overrides: Partial<OperationalBoard> = {}): OperationalBoard {
  return {
    computed_at: '2026-09-20T12:00:00+00:00',
    since: '2026-08-21T12:00:00+00:00',
    by_state: { en_ejecucion: 3, planificada: 7, cerrada: 20 },
    sla: { overdue: 2, due_soon: 4, due_soon_hours: 8, without_sla: 5 },
    legs: [
      {
        key: 'despacho_llegada',
        label: 'Despacho → llegada',
        measured: 12,
        in_progress: 3,
        unrecorded: 8,
        median_minutes: 52,
        p90_minutes: 140,
        worst_minutes: 300,
        min_sample: 5,
      },
    ],
    crews: [
      {
        crew_id: 'c-1',
        crew_name: 'Cuadrilla Norte',
        closed_in_field: 9,
        approved: 7,
        open_now: 2,
      },
    ],
    ...overrides,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('lo que muestra', () => {
  it('el SLA vencido se anuncia como alerta, no como un dato más', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, status: 200, json: async () => board() }) as unknown as Response),
    );
    render(<OperationsBoard businessUnit="GYE" now={() => NOW} />);

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('2 OT vencida');
  });

  it('las OT sin SLA se dicen, porque «0 vencidas» sobre ellas no informa de nada', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, status: 200, json: async () => board() }) as unknown as Response),
    );
    render(<OperationsBoard businessUnit="GYE" now={() => NOW} />);
    expect(await screen.findByText(/5 OT abiertas sin compromiso/)).toBeTruthy();
  });

  it('el tramo muestra la mediana, la cola y las salvedades', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, status: 200, json: async () => board() }) as unknown as Response),
    );
    render(<OperationsBoard businessUnit="GYE" now={() => NOW} />);

    expect(await screen.findByText(/Mediana 52 min sobre 12/)).toBeTruthy();
    expect(screen.getByText(/la peor, 5,0 h/)).toBeTruthy();
    expect(screen.getByText(/3 en curso/)).toBeTruthy();
    expect(screen.getByText(/8 sin registro/)).toBeTruthy();
  });

  it('las OT abiertas del encabezado no cuentan lo cerrado', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, status: 200, json: async () => board() }) as unknown as Response),
    );
    render(<OperationsBoard businessUnit="GYE" now={() => NOW} />);
    expect(await screen.findByText(/10 OT abiertas/)).toBeTruthy();
  });
});

describe('la frescura y el refresco', () => {
  it('dice cuándo se calculó', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, status: 200, json: async () => board() }) as unknown as Response),
    );
    render(
      <OperationsBoard businessUnit="GYE" now={() => new Date('2026-09-20T12:06:00Z')} />,
    );
    expect(await screen.findByText(/Calculado hace 6 minuto/)).toBeTruthy();
  });

  it('vuelve a pedir los datos al pasar el intervalo (RF-130)', async () => {
    const fetcher = vi.fn(
      async () => ({ ok: true, status: 200, json: async () => board() }) as unknown as Response,
    );
    vi.stubGlobal('fetch', fetcher);
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<OperationsBoard businessUnit="GYE" refreshMs={1000} now={() => NOW} />);
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));

    await vi.advanceTimersByTimeAsync(2100);
    // El criterio de aceptación es que los datos se actualicen solos: sin esto, el tablero se queda
    // en lo que se cargó al abrir la pestaña y nadie lo nota.
    expect(fetcher.mock.calls.length).toBeGreaterThanOrEqual(3);
  });
});

describe('cuando el servidor falla', () => {
  it('avisa y no borra lo que ya había', async () => {
    let calls = 0;
    const fetcher = vi.fn(async () => {
      calls += 1;
      if (calls === 1) {
        return { ok: true, status: 200, json: async () => board() } as unknown as Response;
      }
      return {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'la consulta falló' }),
      } as unknown as Response;
    });
    vi.stubGlobal('fetch', fetcher);
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<OperationsBoard businessUnit="GYE" refreshMs={1000} now={() => NOW} />);
    await screen.findByText(/Mediana 52 min/);

    await vi.advanceTimersByTimeAsync(1100);
    await waitFor(() =>
      expect(
        screen.getAllByRole('alert').some((node) => node.textContent?.includes('la consulta falló')),
      ).toBe(true),
    );
    // Unos datos de hace cinco minutos con su advertencia valen más que una pantalla vacía.
    expect(screen.getByText(/Mediana 52 min/)).toBeTruthy();
  });

  it('si falla la primera carga no se queda diciendo «cargando»', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 503,
            statusText: 'Service Unavailable',
            json: async () => ({ detail: 'sin base de datos' }),
          }) as unknown as Response,
      ),
    );
    render(<OperationsBoard businessUnit="GYE" now={() => NOW} />);

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.queryByText(/Cargando el tablero/)).toBeNull();
  });
});

/**
 * La base de interrupciones dentro del tablero (RF-132).
 *
 * El fallo que este panel podría causar es que alguien copie un numerador a un informe regulatorio
 * como si fuera FMIK. Así que lo que se comprueba es que los numeradores se llamen numeradores, que
 * la explicación del servidor esté a la vista, y que un payload con otra forma deje el panel fuera en
 * vez de tumbar el tablero con el que se persigue el SLA.
 */
describe('las interrupciones', () => {
  const BASE = {
    since: '2026-08-21T12:00:00+00:00',
    until: '2026-09-20T12:00:00+00:00',
    interruptions: 12,
    computable: 9,
    not_computable: 2,
    unclassified: 1,
    numerators: {
      kva_affected: 12500,
      kva_hours: 31250.5,
      missing_kva: 2,
      note: 'la plataforma no calcula los índices: el denominador es el kVA instalado de la unidad',
    },
    formats: ['arcernnr-002-20'],
  };

  function mockWith(interruptions: unknown) {
    const urls: string[] = [];
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      urls.push(url);
      if (url.includes('/interruptions.csv')) {
        return {
          ok: true,
          status: 200,
          blob: async () => new Blob(['﻿a;b\r\n'], { type: 'text/csv' }),
        } as unknown as Response;
      }
      if (url.includes('/interruptions')) {
        return { ok: true, status: 200, json: async () => interruptions } as unknown as Response;
      }
      return { ok: true, status: 200, json: async () => board() } as unknown as Response;
    });
    return { fetcher, urls };
  }

  it('muestra los numeradores nombrados como tales, con la nota del servidor', async () => {
    const { fetcher } = mockWith(BASE);
    vi.stubGlobal('fetch', fetcher);
    render(<OperationsBoard businessUnit="GYE" now={() => NOW} />);

    expect(await screen.findByText(/Numeradores de FMIK y TTIK/)).toBeTruthy();
    expect(screen.getByText(/12\.500,00/)).toBeTruthy();
    expect(screen.getByText(/no calcula los índices/)).toBeTruthy();
    // Y avisa de que dos interrupciones sin kVA dejan los numeradores cortos.
    expect(screen.getByText(/por debajo de la realidad/)).toBeTruthy();
  });

  it('las que no se pudieron clasificar se dicen', async () => {
    const { fetcher } = mockWith(BASE);
    vi.stubGlobal('fetch', fetcher);
    render(<OperationsBoard businessUnit="GYE" now={() => NOW} />);
    expect(await screen.findByText(/1 sin clasificar/)).toBeTruthy();
  });

  it('exporta en el formato que el servidor declara', async () => {
    const { fetcher, urls } = mockWith(BASE);
    vi.stubGlobal('fetch', fetcher);
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() });
    render(<OperationsBoard businessUnit="GYE" now={() => NOW} />);

    (await screen.findByRole('button', { name: /Exportar arcernnr-002-20/ })).click();
    await waitFor(() =>
      expect(urls.some((url) => url.includes('/interruptions.csv?format=arcernnr-002-20'))).toBe(
        true,
      ),
    );
  });

  it('un payload con otra forma deja el panel fuera y no tumba el tablero', async () => {
    // Es la lección del panel de concordancia: el fallo de un panel secundario no puede dejar sin
    // tablero a quien responde por el SLA.
    const { fetcher } = mockWith({ interruptions: 'doce' });
    vi.stubGlobal('fetch', fetcher);
    render(<OperationsBoard businessUnit="GYE" now={() => NOW} />);

    expect(await screen.findByText(/Mediana 52 min/)).toBeTruthy();
    expect(screen.queryByText(/Numeradores de FMIK y TTIK/)).toBeNull();
  });
});
