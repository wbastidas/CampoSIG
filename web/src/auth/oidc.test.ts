/**
 * El flujo de autorización con PKCE (RF-001, ADR-013).
 *
 * Casi todo lo que sigue es un rechazo. El flujo "funciona" sin comprobar el `state`, sin usar
 * S256 y sin consumir el verificador una sola vez — y cada una de esas tres omisiones es la que
 * la gente deja pasar porque nada se rompe al dejarla pasar.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  authorizeUrl,
  createChallenge,
  exchangeBody,
  isExpired,
  logoutUrl,
  OidcError,
  readCallback,
  readTokenResponse,
  refreshBody,
  RENEW_MARGIN_MS,
  renewIn,
  rememberChallenge,
  takeReturnTo,
  takeVerifier,
  tokenEndpoint,
  type OidcConfig,
} from './oidc';

const CONFIG: OidcConfig = {
  issuer: 'https://keycloak.example/realms/sigec/',
  clientId: 'sigec-web',
  redirectUri: 'https://sigec.example/callback',
};

beforeEach(() => sessionStorage.clear());
afterEach(() => sessionStorage.clear());

describe('el desafío', () => {
  it('genera un verificador y su desafío S256, distintos cada vez', async () => {
    const first = await createChallenge();
    const second = await createChallenge();
    expect(first.verifier).not.toBe(second.verifier);
    expect(first.state).not.toBe(second.state);
    // El desafío no es el verificador: si lo fuera, PKCE no probaría nada.
    expect(first.challenge).not.toBe(first.verifier);
    expect(first.challenge).toHaveLength(43); // SHA-256 en base64url, sin relleno
  });

  it('el verificador y el desafío son base64url, sin caracteres que haya que escapar', async () => {
    const { verifier, challenge } = await createChallenge();
    expect(verifier).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(challenge).toMatch(/^[A-Za-z0-9_-]+$/);
  });
});

describe('la URL de autorización', () => {
  it('pide un código con S256 y nunca plain', async () => {
    const challenge = await createChallenge();
    const url = new URL(authorizeUrl(CONFIG, challenge));
    expect(url.pathname).toBe('/realms/sigec/protocol/openid-connect/auth');
    expect(url.searchParams.get('response_type')).toBe('code');
    expect(url.searchParams.get('code_challenge_method')).toBe('S256');
    expect(url.searchParams.get('code_challenge')).toBe(challenge.challenge);
    expect(url.searchParams.get('state')).toBe(challenge.state);
    // El verificador no viaja nunca en la petición de autorización.
    expect(url.search).not.toContain(challenge.verifier);
  });

  it('no manda un secreto de cliente, porque un navegador no puede guardarlo', async () => {
    const url = authorizeUrl(CONFIG, await createChallenge());
    expect(url).not.toContain('client_secret');
  });

  it('la barra final del emisor no duplica la ruta', async () => {
    expect(authorizeUrl(CONFIG, await createChallenge())).not.toContain('//protocol');
    expect(tokenEndpoint(CONFIG)).toBe(
      'https://keycloak.example/realms/sigec/protocol/openid-connect/token',
    );
    expect(logoutUrl(CONFIG)).toContain('/protocol/openid-connect/logout?');
  });
});

describe('el regreso del proveedor', () => {
  it('acepta un código con el estado que esta pestaña envió', async () => {
    const challenge = await createChallenge();
    rememberChallenge(challenge);
    const params = readCallback(`?code=abc123&state=${challenge.state}`);
    expect(params.code).toBe('abc123');
  });

  it('rechaza un estado que no coincide', async () => {
    const challenge = await createChallenge();
    rememberChallenge(challenge);
    // Es la única defensa contra un CSRF en el inicio de sesión.
    expect(() => readCallback('?code=abc123&state=otro')).toThrow(OidcError);
  });

  it('rechaza un regreso en una pestaña que no inició nada', () => {
    expect(() => readCallback('?code=abc123&state=cualquiera')).toThrow(/no inició/);
  });

  it('propaga el error que reportó el proveedor, con su descripción', async () => {
    rememberChallenge(await createChallenge());
    expect(() =>
      readCallback('?error=access_denied&error_description=El+usuario+cancel%C3%B3'),
    ).toThrow(/cancel/);
  });

  it('rechaza un regreso sin código', async () => {
    const challenge = await createChallenge();
    rememberChallenge(challenge);
    expect(() => readCallback(`?state=${challenge.state}`)).toThrow(/código/);
  });

  it('acepta la cadena con o sin el signo de interrogación', async () => {
    const challenge = await createChallenge();
    rememberChallenge(challenge);
    expect(readCallback(`code=x&state=${challenge.state}`).code).toBe('x');
  });
});

describe('el verificador', () => {
  it('se usa una sola vez', async () => {
    const challenge = await createChallenge();
    rememberChallenge(challenge);
    expect(takeVerifier()).toBe(challenge.verifier);
    // Un verificador que se queda es uno que se puede reutilizar.
    expect(() => takeVerifier()).toThrow(OidcError);
  });

  it('sin verificador guardado, el intercambio no se intenta', () => {
    expect(() => takeVerifier()).toThrow(/verificador/);
  });

  it('vive en sessionStorage y no en localStorage', async () => {
    // Tiene que sobrevivir a una redirección completa, y no a un navegador cerrado.
    const challenge = await createChallenge();
    rememberChallenge(challenge, '/planificacion');
    expect(sessionStorage.getItem('sigec.pkce.verifier')).toBe(challenge.verifier);
    expect(localStorage.getItem('sigec.pkce.verifier')).toBeNull();
  });

  it('recuerda a dónde volver, una sola vez', async () => {
    rememberChallenge(await createChallenge(), '/revision');
    expect(takeReturnTo()).toBe('/revision');
    expect(takeReturnTo()).toBeNull();
  });
});

describe('el intercambio', () => {
  it('manda el verificador y ningún secreto', () => {
    const body = exchangeBody(CONFIG, 'codigo', 'verificador');
    expect(body.get('grant_type')).toBe('authorization_code');
    expect(body.get('code_verifier')).toBe('verificador');
    expect(body.get('client_secret')).toBeNull();
  });

  it('la renovación manda el refresh token', () => {
    expect(refreshBody(CONFIG, 'r3fr3sh').get('refresh_token')).toBe('r3fr3sh');
  });
});

describe('la respuesta del token', () => {
  it('calcula la caducidad desde expires_in', () => {
    const tokens = readTokenResponse(
      { access_token: 'a', refresh_token: 'r', expires_in: 900 },
      1_000_000,
    );
    expect(tokens.accessToken).toBe('a');
    expect(tokens.refreshToken).toBe('r');
    expect(tokens.expiresAt).toBe(1_000_000 + 900_000);
  });

  it('un expires_in ausente o absurdo no produce un token ya caducado', () => {
    // Si no, la renovación entraría en bucle desde el primer momento.
    const sinDato = readTokenResponse({ access_token: 'a' }, 0);
    const negativo = readTokenResponse({ access_token: 'a', expires_in: -50 }, 0);
    expect(sinDato.expiresAt).toBeGreaterThan(0);
    expect(negativo.expiresAt).toBeGreaterThan(0);
  });

  it('una respuesta sin access_token se rechaza', () => {
    expect(() => readTokenResponse({ token_type: 'Bearer' })).toThrow(/access_token/);
    expect(() => readTokenResponse(null)).toThrow(OidcError);
  });

  it('sin refresh token, el campo es nulo y no una cadena vacía', () => {
    expect(readTokenResponse({ access_token: 'a', expires_in: 60 }).refreshToken).toBeNull();
  });
});

describe('la renovación', () => {
  const tokens = { accessToken: 'a', refreshToken: 'r', expiresAt: 1_000_000 };

  it('se programa con margen, antes de que caduque', () => {
    expect(renewIn(tokens, 1_000_000 - 5 * 60_000)).toBe(5 * 60_000 - RENEW_MARGIN_MS);
  });

  it('nunca es negativa', () => {
    expect(renewIn(tokens, 2_000_000)).toBe(0);
  });

  it('un token ya caducado se reconoce como tal', () => {
    expect(isExpired(tokens, 1_000_001)).toBe(true);
    expect(isExpired(tokens, 999_999)).toBe(false);
  });
});
