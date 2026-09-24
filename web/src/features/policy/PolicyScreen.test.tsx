/**
 * La pantalla de política, renderizada (RF-151).
 *
 * Lo que se comprueba: que el valor heredado se distinga del decidido, que guardar mande solo lo
 * cambiado —un PUT con los diez campos convertiría «no toqué esto» en «ponlo en nulo»—, y que un
 * supervisor no vea con qué escribir.
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { EffectivePolicy, PolicyList } from '../../api/policy';
import { PolicyScreen } from './PolicyScreen';

function rows(): PolicyList {
  return {
    fields: ['store_audio', 'min_photos'],
    defaults: { store_audio: false, min_photos: 1 },
    rows: [
      {
        zone_code: null,
        values: {
          store_audio: true,
          require_audio_consent: null,
          audio_retention_days: null,
          min_photos: 3,
          photo_max_edge_px: null,
          photo_quality: null,
          evidence_retention_days: null,
          upload_on_metered: null,
          metered_upload_limit_mb: null,
          downscale_on_metered: null,
        },
        note: null,
        updated_by: 'admin.funcional',
        updated_at: '2026-09-20T10:00:00+00:00',
      },
      {
        zone_code: 'NORTE',
        values: {
          store_audio: null,
          require_audio_consent: null,
          audio_retention_days: null,
          min_photos: 5,
          photo_max_edge_px: null,
          photo_quality: null,
          evidence_retention_days: null,
          upload_on_metered: null,
          metered_upload_limit_mb: null,
          downscale_on_metered: null,
        },
        note: null,
        updated_by: 'admin.funcional',
        updated_at: '2026-09-21T10:00:00+00:00',
      },
    ],
  };
}

function effective(): EffectivePolicy {
  return {
    business_unit: 'GYE',
    zone_code: null,
    values: {
      store_audio: { value: true, source: 'unidad' },
      require_audio_consent: { value: true, source: 'por omisión de la plataforma' },
      audio_retention_days: { value: 90, source: 'por omisión de la plataforma' },
      min_photos: { value: 3, source: 'unidad' },
      photo_max_edge_px: { value: 1600, source: 'por omisión de la plataforma' },
      photo_quality: { value: 80, source: 'por omisión de la plataforma' },
      evidence_retention_days: { value: 1825, source: 'por omisión de la plataforma' },
      upload_on_metered: { value: false, source: 'por omisión de la plataforma' },
      metered_upload_limit_mb: { value: null, source: 'por omisión de la plataforma' },
      downscale_on_metered: { value: true, source: 'por omisión de la plataforma' },
    },
  };
}

function mockApi(overrides: { effective?: EffectivePolicy; list?: PolicyList } = {}) {
  const calls: { url: string; method: string; body: unknown }[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    calls.push({
      url,
      method,
      body: typeof init?.body === 'string' ? JSON.parse(init.body) : null,
    });
    if (url.includes('/effective')) {
      return {
        ok: true,
        status: 200,
        json: async () => overrides.effective ?? effective(),
      } as unknown as Response;
    }
    if (method !== 'GET') {
      return { ok: true, status: 200, json: async () => ({}) } as unknown as Response;
    }
    return {
      ok: true,
      status: 200,
      json: async () => overrides.list ?? rows(),
    } as unknown as Response;
  });
  return { fetcher, calls };
}

afterEach(() => vi.unstubAllGlobals());

describe('lo que obedece el teléfono', () => {
  it('nombra quién decidió cada valor', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);

    const panel = await screen.findByRole('region', { name: 'Lo que obedece el teléfono' });
    const row = within(panel).getByText('Fotos mínimas por OT').closest('tr');
    expect(row?.textContent).toContain('unidad');
  });

  it('un valor heredado se marca, para que no se lea como una decisión', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);

    const panel = await screen.findByRole('region', { name: 'Lo que obedece el teléfono' });
    const inherited = panel.querySelectorAll('tr.pol-inherited');
    expect(inherited.length).toBeGreaterThan(0);
  });

  it('un booleano se lee en español y no como true', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);

    const panel = await screen.findByRole('region', { name: 'Lo que obedece el teléfono' });
    const row = within(panel).getByText('Guardar el audio original').closest('tr');
    expect(row?.textContent).toContain('Sí');
    expect(row?.textContent).not.toContain('true');
  });

  it('un tope sin definir lo dice en vez de mostrar cero', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);

    const panel = await screen.findByRole('region', { name: 'Lo que obedece el teléfono' });
    const row = within(panel).getByText(/Tope diario/).closest('tr');
    expect(row?.textContent).toContain('sin definir');
  });
});

describe('el editor', () => {
  it('guarda solo el campo que se cambió', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Editar la política' });

    fireEvent.change(screen.getByLabelText('Fotos mínimas por OT'), { target: { value: '6' } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => {
      const put = calls.find((call) => call.method === 'PUT');
      expect(put?.body).toEqual({ min_photos: 6 });
    });
  });

  it('vaciar un campo manda un nulo, que es lo que hace que se herede otra vez', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Editar la política' });

    fireEvent.change(screen.getByLabelText('Fotos mínimas por OT'), { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => {
      const put = calls.find((call) => call.method === 'PUT');
      expect(put?.body).toEqual({ min_photos: null });
    });
  });

  it('el botón está apagado mientras no haya nada cambiado', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Editar la política' });

    expect(screen.getByRole('button', { name: 'Guardar' }).getAttribute('disabled')).not.toBeNull();
    expect(screen.getByText('No hay nada cambiado que guardar.')).toBeTruthy();
  });

  it('un valor imposible se avisa antes de mandarlo', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Editar la política' });

    fireEvent.change(screen.getByLabelText(/Calidad JPEG/), { target: { value: '140' } });
    expect(screen.getByRole('alert').textContent).toContain('1 a 100');
    expect(screen.getByRole('button', { name: 'Guardar' }).getAttribute('disabled')).not.toBeNull();
    expect(calls.some((call) => call.method === 'PUT')).toBe(false);
  });

  it('un booleano ofrece heredar además de sí y no', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);
    await screen.findByRole('region', { name: 'Editar la política' });

    const select = screen.getByLabelText('Subir por datos móviles');
    expect(within(select).getByText('Heredar')).toBeTruthy();
  });
});

describe('el ámbito', () => {
  it('ofrece las zonas que ya tienen política propia', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);

    const select = await screen.findByLabelText('Editar');
    expect(within(select).getByText('Zona NORTE')).toBeTruthy();
  });

  it('al cambiar a una zona pide su política efectiva al servidor', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);
    await screen.findByLabelText('Editar');

    fireEvent.change(screen.getByLabelText('Editar'), { target: { value: 'NORTE' } });
    await waitFor(() => {
      expect(calls.some((call) => call.url.includes('effective?zone=NORTE'))).toBe(true);
    });
  });

  it('dice que una zona hereda lo que no declara', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);
    await screen.findByLabelText('Editar');

    fireEvent.change(screen.getByLabelText('Editar'), { target: { value: 'NORTE' } });
    expect(await screen.findByText(/hereda de la unidad/)).toBeTruthy();
  });

  it('quitar la política de una zona la borra en el servidor', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);
    await screen.findByLabelText('Editar');

    fireEvent.change(screen.getByLabelText('Editar'), { target: { value: 'NORTE' } });
    fireEvent.click(await screen.findByText(/Quitar la política de NORTE/));

    await waitFor(() => {
      expect(calls.some((call) => call.method === 'DELETE' && call.url.includes('NORTE'))).toBe(
        true,
      );
    });
  });

  it('no ofrece quitar la política de la unidad', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" />);
    await screen.findByLabelText('Editar');
    expect(screen.queryByText(/Quitar la política/)).toBeNull();
  });
});

describe('el supervisor', () => {
  it('ve lo que obedece el teléfono y no ve con qué cambiarlo', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<PolicyScreen businessUnit="GYE" mayEdit={false} />);

    await screen.findByRole('region', { name: 'Lo que obedece el teléfono' });
    expect(screen.queryByRole('region', { name: 'Editar la política' })).toBeNull();
    expect(screen.queryByText('Añadir una zona')).toBeNull();
  });
});
