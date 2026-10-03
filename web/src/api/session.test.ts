/**
 * La sesión del navegador (RF-001).
 *
 * El token vive en memoria y no se persiste, a propósito: `localStorage` sobreviviría a un
 * portátil cerrado en una sala de control de subestación, que es justo donde no debería
 * sobrevivir. Eso tiene su test, porque es el tipo de decisión que alguien "arregla" para que
 * no haya que volver a entrar tras recargar.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { authHeaders, currentToken, notifyExpired, onTokenExpired, setAccessToken } from './session';

afterEach(() => {
  setAccessToken(null);
  onTokenExpired(null);
});

describe('encabezados', () => {
  it('sin token, no se inventa uno', () => {
    const headers = authHeaders() as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
    expect(headers['Content-Type']).toBe('application/json');
  });

  it('con token, va como Bearer', () => {
    setAccessToken('t0k3n');
    expect((authHeaders() as Record<string, string>).Authorization).toBe('Bearer t0k3n');
  });

  it('los encabezados propios de la llamada se conservan', () => {
    setAccessToken('t0k3n');
    const headers = authHeaders({ 'X-Algo': 'sí' }) as Record<string, string>;
    expect(headers['X-Algo']).toBe('sí');
    expect(headers.Authorization).toBe('Bearer t0k3n');
  });
});

describe('caducidad', () => {
  it('un 401 descarta el token y avisa una vez', () => {
    const handler = vi.fn();
    setAccessToken('t0k3n');
    onTokenExpired(handler);

    notifyExpired();

    expect(currentToken()).toBeNull();
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('sin manejador registrado, no revienta', () => {
    setAccessToken('t0k3n');
    expect(() => notifyExpired()).not.toThrow();
    expect(currentToken()).toBeNull();
  });
});

describe('el token no se persiste', () => {
  it('no toca localStorage ni sessionStorage', () => {
    // Un token en almacenamiento del navegador sobrevive a la sesión, y ese es el problema.
    const local = vi.spyOn(Storage.prototype, 'setItem');
    setAccessToken('t0k3n');
    authHeaders();
    notifyExpired();
    expect(local).not.toHaveBeenCalled();
    local.mockRestore();
  });
});
