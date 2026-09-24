/**
 * El panel de adjuntos, renderizado (RF-017).
 *
 * El botón de retirar es la razón por la que este panel existe además de la lista: un plano
 * equivocado que no se puede retirar se sigue descargando al teléfono. Así que lo que se prueba es
 * que el retiro llegue al servidor con su motivo, que no salga sin motivo, y que el panel diga lo
 * que la lista sola no dice: cuánto pesa la descarga y qué no está viajando.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Attachment, AttachmentList } from '../../api/attachments';
import { AttachmentsPanel } from './AttachmentsPanel';

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

function mockApi(body: AttachmentList, onWithdraw?: (url: string, payload: unknown) => void) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/withdraw')) {
      onWithdraw?.(url, init?.body ? JSON.parse(String(init.body)) : null);
      return {
        ok: true,
        status: 200,
        json: async () => attachment({ is_active: false }),
      } as unknown as Response;
    }
    return { ok: true, status: 200, json: async () => body } as unknown as Response;
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('lo que el panel dice', () => {
  it('dice cuánto pesa la descarga de la cuadrilla, con su techo', async () => {
    vi.stubGlobal('fetch', mockApi(list({ offline_bytes: 12 * MB })));
    render(<AttachmentsPanel businessUnit="GYE" workOrderId="ot-1" />);

    await waitFor(() => expect(screen.getByText('12,0 de 60,0 MB')).toBeTruthy());
  });

  it('distingue el adjunto que no baja al teléfono del que sí', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        list({
          offline_bytes: 0,
          attachments: [attachment({ id: 'a2', title: 'Estudio de cargabilidad', offline: false })],
        }),
      ),
    );
    render(<AttachmentsPanel businessUnit="GYE" workOrderId="ot-1" />);

    await waitFor(() => expect(screen.getByText(/No baja al teléfono/)).toBeTruthy());
    // Y no ofrece retirar lo que ya no viaja: no hay nada que retirar.
    expect(screen.queryByRole('button', { name: 'Retirar' })).toBeNull();
  });

  it('avisa cuando la OT se acerca al límite, antes de que el servidor la rechace', async () => {
    vi.stubGlobal('fetch', mockApi(list({ offline_bytes: 55 * MB })));
    render(<AttachmentsPanel businessUnit="GYE" workOrderId="ot-1" />);

    await waitFor(() => expect(screen.getByText(/55,0 MB de adjuntos offline/)).toBeTruthy());
  });

  it('sin adjuntos lo dice, en lugar de mostrar una lista vacía', async () => {
    vi.stubGlobal('fetch', mockApi(list({ offline_bytes: 0, attachments: [] })));
    render(<AttachmentsPanel businessUnit="GYE" workOrderId="ot-1" />);

    await waitFor(() => expect(screen.getByText(/no tiene adjuntos de oficina/)).toBeTruthy());
  });

  it('marca el plano que es de la obra y no del frente', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(
        list({
          work_order_id: 'frente-3',
          attachments: [attachment({ work_order_id: 'obra-1' })],
        }),
      ),
    );
    render(<AttachmentsPanel businessUnit="GYE" workOrderId="frente-3" />);

    await waitFor(() => expect(screen.getByText('De la obra, compartido')).toBeTruthy());
  });
});

describe('retirar un adjunto', () => {
  it('llega al servidor con su motivo', async () => {
    const calls: { url: string; payload: unknown }[] = [];
    vi.stubGlobal(
      'fetch',
      mockApi(list(), (url, payload) => calls.push({ url, payload })),
    );
    render(<AttachmentsPanel businessUnit="GYE" workOrderId="ot-1" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Retirar' }));
    fireEvent.change(await screen.findByLabelText('Motivo'), {
      target: { value: 'lo reemplaza el diseño final' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar retiro' }));

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]?.url).toContain('/units/GYE/a1/withdraw');
    expect(calls[0]?.payload).toEqual({ reason: 'lo reemplaza el diseño final' });
  });

  it('no sale sin motivo, y lo dice', async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      'fetch',
      mockApi(list(), (url) => calls.push(url)),
    );
    render(<AttachmentsPanel businessUnit="GYE" workOrderId="ot-1" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Retirar' }));

    const confirm = await screen.findByRole('button', { name: 'Confirmar retiro' });
    expect((confirm as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Escriba el motivo/)).toBeTruthy();
    fireEvent.click(confirm);
    expect(calls).toHaveLength(0);
  });

  it('dice que no se borra antes de que alguien pulse', async () => {
    vi.stubGlobal('fetch', mockApi(list()));
    render(<AttachmentsPanel businessUnit="GYE" workOrderId="ot-1" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Retirar' }));

    await waitFor(() => expect(screen.getByText(/No se borra/)).toBeTruthy());
  });

  it('quien no puede escribir no ve el botón; el servidor lo niega igual', async () => {
    vi.stubGlobal('fetch', mockApi(list()));
    render(<AttachmentsPanel businessUnit="GYE" workOrderId="ot-1" mayWithdraw={false} />);

    await waitFor(() => expect(screen.getByText(/Plano estructural/)).toBeTruthy());
    expect(screen.queryByRole('button', { name: 'Retirar' })).toBeNull();
  });
});

describe('cuando el servidor falla', () => {
  it('lo dice con el detalle del servidor y no con una lista vacía silenciosa', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 404,
            statusText: 'Not Found',
            json: async () => ({ detail: 'la OT no existe en esta unidad de negocio' }),
          }) as unknown as Response,
      ),
    );
    render(<AttachmentsPanel businessUnit="GYE" workOrderId="ot-1" />);

    await waitFor(() =>
      expect(screen.getByText('la OT no existe en esta unidad de negocio')).toBeTruthy(),
    );
  });
});
