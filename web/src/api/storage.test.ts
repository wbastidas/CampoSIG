/**
 * El cliente de subida al almacenamiento (RF-076, RF-017).
 *
 * Lo que se prueba: que pedir una firma llegue al endpoint correcto, y que subir con la URL
 * firmada mande las cabeceras exactas que el servidor dijo — una firma de S3 no valida con
 * cabeceras distintas a las que se usaron para calcularla.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { type PresignedUpload, presignUpload, uploadFile } from './storage';

afterEach(() => vi.unstubAllGlobals());

describe('presignUpload', () => {
  it('pide la firma con la unidad y el propósito en el cuerpo', async () => {
    const calls: { url: string; payload: unknown }[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        calls.push({
          url: String(input),
          payload: init?.body ? JSON.parse(String(init.body)) : null,
        });
        return {
          ok: true,
          status: 200,
          json: async () => ({
            url: 'http://localhost:8333/sigec-evidence/GYE/x',
            storage_key: 'GYE/evidencia/foto/x.jpg',
            method: 'PUT',
            expires_in: 300,
            headers: { 'Content-Type': 'image/jpeg' },
          }),
        } as unknown as Response;
      }),
    );

    const upload = await presignUpload('GYE', {
      purpose: 'evidencia',
      kind: 'foto',
      filename: 'antes.jpg',
      content_type: 'image/jpeg',
      size_bytes: 1024,
    });

    expect(calls[0]?.url).toContain('/api/v1/storage/units/GYE/presign');
    expect(calls[0]?.payload).toEqual({
      purpose: 'evidencia',
      kind: 'foto',
      filename: 'antes.jpg',
      content_type: 'image/jpeg',
      size_bytes: 1024,
    });
    expect(upload.storage_key).toBe('GYE/evidencia/foto/x.jpg');
  });

  it('el error del servidor se propaga tal cual', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 422,
            statusText: 'Unprocessable',
            json: async () => ({ detail: 'el archivo pesa demasiado' }),
          }) as unknown as Response,
      ),
    );

    await expect(
      presignUpload('GYE', {
        purpose: 'adjunto',
        kind: 'plano',
        filename: 'a.pdf',
        content_type: 'application/pdf',
        size_bytes: 1,
      }),
    ).rejects.toThrow('el archivo pesa demasiado');
  });
});

describe('uploadFile', () => {
  function upload(overrides: Partial<PresignedUpload> = {}): PresignedUpload {
    return {
      url: 'http://localhost:8333/sigec-evidence/GYE/x.jpg?signature=abc',
      storage_key: 'GYE/evidencia/foto/x.jpg',
      method: 'PUT',
      expires_in: 300,
      headers: { 'Content-Type': 'image/jpeg' },
      ...overrides,
    };
  }

  it('sube con el método y las cabeceras exactas que dijo la firma', async () => {
    const calls: { url: string; init: RequestInit }[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        calls.push({ url: String(input), init: init ?? {} });
        return { ok: true, status: 200 } as unknown as Response;
      }),
    );
    const file = new Blob(['contenido'], { type: 'image/jpeg' });

    await uploadFile(upload(), file);

    expect(calls[0]?.url).toBe(upload().url);
    expect(calls[0]?.init.method).toBe('PUT');
    expect(calls[0]?.init.headers).toEqual({ 'Content-Type': 'image/jpeg' });
    expect(calls[0]?.init.body).toBe(file);
  });

  it('una subida rechazada por el almacenamiento se informa con su código', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 403 }) as unknown as Response),
    );

    await expect(uploadFile(upload(), new Blob(['x']))).rejects.toThrow('403');
  });
});
