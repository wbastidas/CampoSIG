/**
 * El catálogo de formularios, renderizado (RF-032).
 *
 * Lo que se comprueba: que el borrador sin publicar se vea y diga qué implica, que publicar explique
 * qué le pasa a las OT que ya existen, y que quien no administra no vea los botones.
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { CatalogueRow, FormVersion } from '../../api/forms';
import { FormCatalogueScreen } from './FormCatalogueScreen';

function row(overrides: Partial<CatalogueRow> = {}): CatalogueRow {
  return {
    code: 'F-MT-01',
    title: 'Inspección preventiva',
    area: 'mantenimiento',
    file_version: '1.0.0',
    published_version: '1.0.0',
    has_unpublished_draft: false,
    never_published: false,
    ...overrides,
  };
}

function version(overrides: Partial<FormVersion> = {}): FormVersion {
  return {
    code: 'F-MT-01',
    version: '1.0.0',
    state: 'publicado',
    content_hash: 'a'.repeat(64),
    published_by: 'admin.funcional',
    published_at: '2026-09-20T10:00:00+00:00',
    obsoleted_at: null,
    obsoleted_by: null,
    note: null,
    blocks: ['B01', 'B02'],
    ...overrides,
  };
}

function mockApi(stub: { forms?: CatalogueRow[]; versions?: FormVersion[] } = {}) {
  const calls: { url: string; method: string; body: unknown }[] = [];
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    calls.push({
      url,
      method,
      body: typeof init?.body === 'string' ? JSON.parse(init.body) : null,
    });
    if (url.endsWith('/catalogue')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ forms: stub.forms ?? [row()] }),
      } as unknown as Response;
    }
    if (url.includes('/publish') || url.includes('/obsolete')) {
      return { ok: true, status: 201, json: async () => version() } as unknown as Response;
    }
    return {
      ok: true,
      status: 200,
      json: async () => stub.versions ?? [version()],
    } as unknown as Response;
  });
  return { fetcher, calls };
}

afterEach(() => vi.unstubAllGlobals());

describe('el catálogo', () => {
  it('muestra el borrador sin publicar y qué implica', async () => {
    const { fetcher } = mockApi({
      forms: [row({ has_unpublished_draft: true, file_version: '2.0.0' })],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen />);

    const panel = await screen.findByRole('region', { name: 'Catálogo' });
    expect(within(panel).getByText('Borrador sin publicar')).toBeTruthy();
    expect(within(panel).getByText(/Nadie en campo ha visto este cambio/)).toBeTruthy();
  });

  it('distingue nunca publicado de borrador sin publicar', async () => {
    const { fetcher } = mockApi({
      forms: [
        row({ code: 'F-AP-01', never_published: true, published_version: null }),
        row({ code: 'F-MT-01', has_unpublished_draft: true, file_version: '2.0.0' }),
      ],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen />);

    const panel = await screen.findByRole('region', { name: 'Catálogo' });
    expect(within(panel).getByText('Nunca publicado')).toBeTruthy();
    expect(within(panel).getByText('Borrador sin publicar')).toBeTruthy();
    // Lo peor primero.
    const headers = within(panel).getAllByRole('rowheader');
    expect(headers[0]?.textContent).toBe('F-AP-01');
  });

  it('no ofrece publicar lo que ya está al día', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen />);
    await screen.findByRole('region', { name: 'Catálogo' });
    expect(screen.queryByText(/^Publicar v/)).toBeNull();
  });

  it('publicar explica qué le pasa a las OT que ya existen', async () => {
    const { fetcher, calls } = mockApi({
      forms: [row({ has_unpublished_draft: true, file_version: '2.0.0' })],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen />);

    fireEvent.click(await screen.findByText('Publicar v2.0.0'));
    await waitFor(() => {
      expect(calls.some((call) => call.url.includes('/publish'))).toBe(true);
    });
    expect(await screen.findByText(/conservan la suya/)).toBeTruthy();
  });

  it('un fallo del servidor se ve', async () => {
    const fetcher = vi.fn(
      async () =>
        ({
          ok: false,
          status: 500,
          statusText: 'Server Error',
          json: async () => ({ detail: 'la base no responde' }),
        }) as unknown as Response,
    );
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen />);
    expect(await screen.findByRole('alert')).toBeTruthy();
  });
});

describe('las versiones', () => {
  it('no pide nada hasta que se elige un formulario', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen />);
    await screen.findByLabelText('Formulario');
    expect(calls.some((call) => call.url.includes('/versions'))).toBe(false);
  });

  it('muestra quién congeló cada versión y de qué bloques está hecha', async () => {
    const { fetcher } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen />);

    fireEvent.change(await screen.findByLabelText('Formulario'), {
      target: { value: 'F-MT-01' },
    });
    expect(await screen.findByText(/publicada por admin.funcional/)).toBeTruthy();
    expect(screen.getByText(/Bloques: B01, B02/)).toBeTruthy();
  });

  it('un formulario sin versiones lo dice y explica contra qué se compone', async () => {
    const { fetcher } = mockApi({
      forms: [row({ never_published: true, published_version: null })],
      versions: [],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen />);

    fireEvent.change(await screen.findByLabelText('Formulario'), {
      target: { value: 'F-MT-01' },
    });
    expect(await screen.findByText(/se componen contra el archivo actual/)).toBeTruthy();
  });

  it('retirar una versión explica que las OT que la llevan siguen usándola', async () => {
    const { fetcher, calls } = mockApi();
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen />);

    fireEvent.change(await screen.findByLabelText('Formulario'), {
      target: { value: 'F-MT-01' },
    });
    fireEvent.click(await screen.findByText('Retirar'));
    await waitFor(() => {
      expect(calls.some((call) => call.url.includes('/obsolete'))).toBe(true);
    });
    expect(await screen.findByText(/siguen componiéndose contra ella/)).toBeTruthy();
  });

  it('una versión obsoleta no ofrece retirarse otra vez', async () => {
    const { fetcher } = mockApi({ versions: [version({ state: 'obsoleto' })] });
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen />);

    fireEvent.change(await screen.findByLabelText('Formulario'), {
      target: { value: 'F-MT-01' },
    });
    await screen.findByText(/Obsoleta/);
    expect(screen.queryByText('Retirar')).toBeNull();
  });
});

describe('quien no administra', () => {
  it('ve el catálogo y no ve con qué publicar ni retirar', async () => {
    const { fetcher } = mockApi({
      forms: [row({ has_unpublished_draft: true, file_version: '2.0.0' })],
    });
    vi.stubGlobal('fetch', fetcher);
    render(<FormCatalogueScreen mayPublish={false} />);

    await screen.findByRole('region', { name: 'Catálogo' });
    expect(screen.queryByText(/^Publicar v/)).toBeNull();

    fireEvent.change(screen.getByLabelText('Formulario'), { target: { value: 'F-MT-01' } });
    await screen.findByText(/publicada por admin.funcional/);
    expect(screen.queryByText('Retirar')).toBeNull();
  });
});
