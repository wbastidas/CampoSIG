/**
 * La sesión, renderizada de verdad (RF-001, ADR-013).
 *
 * Estos tests montan el componente en jsdom: es la primera vez que el render de React se ejecuta
 * en este proyecto, y por eso empiezan por lo que un test de lógica pura no puede ver — que la
 * puerta de login no deja pasar a nadie, que el código del intercambio no se queda en la barra de
 * direcciones, y que una renovación fallida no borra lo que había en pantalla.
 */

import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { currentToken, setAccessToken } from '../api/session';
import { createChallenge, rememberChallenge } from './oidc';
import { describeToken, RequireSession, SessionProvider, useSession } from './SessionProvider';

const CONFIG = {
  issuer: 'https://keycloak.example/realms/sigec',
  clientId: 'sigec-web',
  redirectUri: 'https://sigec.example/callback',
};

/** A token whose payload is readable, unsigned — the UI never verifies, the backend does. */
function fakeToken(claims: Record<string, unknown>): string {
  const encode = (value: unknown) =>
    btoa(JSON.stringify(value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  return `${encode({ alg: 'RS256' })}.${encode(claims)}.firma-que-nadie-verifica-aqui`;
}

const CLAIMS = {
  sub: 'kc|supervisor.demo',
  preferred_username: 'supervisor.demo',
  realm_access: { roles: ['supervisor'] },
  business_units: ['GYE'],
};

function tokenResponse(token: string, expiresIn = 900) {
  return {
    ok: true,
    status: 200,
    json: async () => ({ access_token: token, refresh_token: 'r3fr3sh', expires_in: expiresIn }),
  } as unknown as Response;
}

beforeEach(() => {
  sessionStorage.clear();
  setAccessToken(null);
});

afterEach(() => {
  // Explícito y no por `globals: true`: testing-library solo limpia solo si encuentra el
  // `afterEach` global del framework, y un DOM que sobrevive al test anterior produce
  // "found multiple elements" en el siguiente — un fallo que no habla de lo que se está probando.
  cleanup();
  vi.useRealTimers();
  setAccessToken(null);
});

function Whoami() {
  const session = useSession();
  return (
    <p>
      estado: {session.status}; usuario: {session.user?.username ?? 'ninguno'}
    </p>
  );
}

describe('la puerta de login', () => {
  it('no deja pasar a nadie sin sesión, y ofrece iniciarla', async () => {
    render(
      <SessionProvider
        config={CONFIG}
        fetchImpl={vi.fn()}
        redirect={vi.fn()}
        location={{ search: '', pathname: '/planificacion' }}
      >
        <RequireSession>
          <p>contenido reservado</p>
        </RequireSession>
      </SessionProvider>,
    );

    await waitFor(() => expect(screen.getByRole('button', { name: /iniciar sesión/i })).toBeTruthy());
    expect(screen.queryByText('contenido reservado')).toBeNull();
  });

  it('el botón lleva al proveedor con S256 y recuerda dónde estaba la persona', async () => {
    const redirect = vi.fn();
    render(
      <SessionProvider
        config={CONFIG}
        fetchImpl={vi.fn()}
        redirect={redirect}
        location={{ search: '', pathname: '/revision' }}
      >
        <RequireSession>
          <p>contenido reservado</p>
        </RequireSession>
      </SessionProvider>,
    );

    const button = await screen.findByRole('button', { name: /iniciar sesión/i });
    button.click();

    await waitFor(() => expect(redirect).toHaveBeenCalledTimes(1));
    const url = new URL(redirect.mock.calls[0]![0] as string);
    expect(url.searchParams.get('code_challenge_method')).toBe('S256');
    // Volver al sitio donde estaba, no a un tablero genérico.
    expect(sessionStorage.getItem('sigec.pkce.return')).toBe('/revision');
  });
});

describe('el regreso del proveedor', () => {
  it('intercambia el código y deja la sesión autenticada', async () => {
    const challenge = await createChallenge();
    rememberChallenge(challenge, '/revision');
    const token = fakeToken(CLAIMS);
    const doFetch = vi.fn().mockResolvedValue(tokenResponse(token));

    render(
      <SessionProvider
        config={CONFIG}
        fetchImpl={doFetch}
        redirect={vi.fn()}
        location={{ search: `?code=abc&state=${challenge.state}`, pathname: '/callback' }}
      >
        <RequireSession>
          <Whoami />
        </RequireSession>
      </SessionProvider>,
    );

    await waitFor(() => expect(screen.getByText(/supervisor\.demo/)).toBeTruthy());
    expect(currentToken()).toBe(token);

    const body = String((doFetch.mock.calls[0]![1] as RequestInit).body);
    expect(body).toContain('grant_type=authorization_code');
    expect(body).toContain(`code_verifier=${challenge.verifier}`);
  });

  it('el código no se queda en la barra de direcciones', async () => {
    const challenge = await createChallenge();
    rememberChallenge(challenge, '/revision');
    const replaceState = vi.spyOn(globalThis.history, 'replaceState');

    render(
      <SessionProvider
        config={CONFIG}
        fetchImpl={vi.fn().mockResolvedValue(tokenResponse(fakeToken(CLAIMS)))}
        redirect={vi.fn()}
        location={{ search: `?code=abc&state=${challenge.state}`, pathname: '/callback' }}
      >
        <Whoami />
      </SessionProvider>,
    );

    // Es de un solo uso: un marcador con el código dentro falla de forma confusa la próxima vez.
    await waitFor(() => expect(replaceState).toHaveBeenCalledWith(null, '', '/revision'));
    replaceState.mockRestore();
  });

  it('un estado que no coincide deja la sesión en error y no autentica', async () => {
    rememberChallenge(await createChallenge());
    render(
      <SessionProvider
        config={CONFIG}
        fetchImpl={vi.fn()}
        redirect={vi.fn()}
        location={{ search: '?code=abc&state=falsificado', pathname: '/callback' }}
      >
        <Whoami />
      </SessionProvider>,
    );

    await waitFor(() => expect(screen.getByText(/estado: error/)).toBeTruthy());
    expect(currentToken()).toBeNull();
  });

  it('un intercambio rechazado por el proveedor no autentica a nadie', async () => {
    const challenge = await createChallenge();
    rememberChallenge(challenge);
    const doFetch = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 400, json: async () => ({}) } as unknown as Response);

    render(
      <SessionProvider
        config={CONFIG}
        fetchImpl={doFetch}
        redirect={vi.fn()}
        location={{ search: `?code=abc&state=${challenge.state}`, pathname: '/callback' }}
      >
        <Whoami />
      </SessionProvider>,
    );

    await waitFor(() => expect(screen.getByText(/estado: error/)).toBeTruthy());
    expect(currentToken()).toBeNull();
  });
});

describe('la renovación silenciosa', () => {
  it('se dispara antes de que el token caduque', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const challenge = await createChallenge();
    rememberChallenge(challenge);

    const first = fakeToken(CLAIMS);
    const second = fakeToken({ ...CLAIMS, preferred_username: 'supervisor.renovado' });
    const doFetch = vi
      .fn()
      .mockResolvedValueOnce(tokenResponse(first, 120))
      .mockResolvedValueOnce(tokenResponse(second, 900));

    render(
      <SessionProvider
        config={CONFIG}
        fetchImpl={doFetch}
        redirect={vi.fn()}
        location={{ search: `?code=abc&state=${challenge.state}`, pathname: '/callback' }}
      >
        <Whoami />
      </SessionProvider>,
    );

    await waitFor(() => expect(screen.getByText(/supervisor\.demo/)).toBeTruthy());

    // 120 s de vida y 60 s de margen: la renovación toca al minuto.
    await vi.advanceTimersByTimeAsync(61_000);
    await waitFor(() => expect(screen.getByText(/supervisor\.renovado/)).toBeTruthy());

    const renewalBody = String((doFetch.mock.calls[1]![1] as RequestInit).body);
    expect(renewalBody).toContain('grant_type=refresh_token');
  });

  it('una renovación fallida no borra lo que había en pantalla', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const challenge = await createChallenge();
    rememberChallenge(challenge);

    const doFetch = vi
      .fn()
      .mockResolvedValueOnce(tokenResponse(fakeToken(CLAIMS), 120))
      .mockResolvedValueOnce({ ok: false, status: 400, json: async () => ({}) } as unknown as Response);

    render(
      <SessionProvider
        config={CONFIG}
        fetchImpl={doFetch}
        redirect={vi.fn()}
        location={{ search: `?code=abc&state=${challenge.state}`, pathname: '/callback' }}
      >
        <>
          <p>una observación a medio escribir</p>
          <Whoami />
        </>
      </SessionProvider>,
    );

    await waitFor(() => expect(screen.getByText(/supervisor\.demo/)).toBeTruthy());
    await vi.advanceTimersByTimeAsync(61_000);

    await waitFor(() => expect(screen.getByText(/estado: anonimo/)).toBeTruthy());
    // Perder una observación a medio escribir es de las cosas por las que se deja de usar algo.
    expect(screen.getByText('una observación a medio escribir')).toBeTruthy();
  });
});

describe('lo que la interfaz lee del token', () => {
  it('saca usuario, roles y unidades', () => {
    const described = describeToken(fakeToken(CLAIMS));
    expect(described?.username).toBe('supervisor.demo');
    expect(described?.roles).toEqual(['supervisor']);
    expect(described?.businessUnits).toEqual(['GYE']);
  });

  it('un token ilegible no revienta la interfaz', () => {
    // El backend es quien tiene que entender el token; aquí solo se muestra menos.
    expect(describeToken('no-es-un-jwt')).toBeNull();
    expect(describeToken('a.b.c')).toBeNull();
  });

  it('un token sin roles no inventa ninguno', () => {
    expect(describeToken(fakeToken({ sub: 'x' }))?.roles).toEqual([]);
  });
});

describe('useSession fuera de su proveedor', () => {
  it('falla con un mensaje que dice qué falta', () => {
    // Un contexto nulo produciría un `cannot read property of null` treinta líneas más abajo.
    expect(() => render(<Whoami />)).toThrow(/SessionProvider/);
  });
});
