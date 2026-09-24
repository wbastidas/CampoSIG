/**
 * Authorization code flow with PKCE against the corporate identity provider (RF-001, ADR-013).
 *
 * PKCE and not an implicit flow, and no client secret: this is a browser, so anything the code
 * knows the user knows. The proof-of-possession is the point — an intercepted authorization code
 * is useless without the verifier that never left the tab.
 *
 * Three decisions worth knowing:
 *
 * * **The verifier lives in `sessionStorage`, the token in memory.** The verifier has to survive
 *   a full-page redirect, which memory does not; it must not survive a closed browser, which
 *   `localStorage` would. `sessionStorage` is exactly tab-scoped, which is exactly the lifetime
 *   the verifier needs. The access token has no such requirement and stays in memory.
 * * **A callback whose `state` does not match is refused.** That check is the whole defence
 *   against a CSRF on the login flow, and it is the one people skip because the flow works
 *   without it.
 * * **Renewal happens early, not on failure.** A supervisor mid-observation should not discover
 *   the session expired by losing what they typed.
 */

/** Where the PKCE verifier and state wait out the redirect. Tab-scoped by design. */
const VERIFIER_KEY = 'sigec.pkce.verifier';
const STATE_KEY = 'sigec.pkce.state';
const RETURN_KEY = 'sigec.pkce.return';

export interface OidcConfig {
  /** e.g. `https://keycloak.example/realms/sigec` */
  issuer: string;
  clientId: string;
  redirectUri: string;
  /** `openid` is required; the rest is what the backend reads from the token. */
  scope?: string;
}

export interface PkceChallenge {
  verifier: string;
  challenge: string;
  state: string;
}

export interface TokenSet {
  accessToken: string;
  refreshToken: string | null;
  /** Epoch milliseconds. */
  expiresAt: number;
}

export class OidcError extends Error {
  constructor(message: string, readonly cause?: unknown) {
    super(message);
    this.name = 'OidcError';
  }
}

function base64Url(bytes: Uint8Array): string {
  let text = '';
  for (const byte of bytes) text += String.fromCharCode(byte);
  return btoa(text).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function randomString(byteLength = 32): string {
  const bytes = new Uint8Array(byteLength);
  globalThis.crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

/** A fresh verifier, its S256 challenge, and a state value. */
export async function createChallenge(): Promise<PkceChallenge> {
  const verifier = randomString(32);
  const digest = await globalThis.crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(verifier),
  );
  return {
    verifier,
    challenge: base64Url(new Uint8Array(digest)),
    state: randomString(16),
  };
}

export function authorizeUrl(config: OidcConfig, challenge: PkceChallenge): string {
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    scope: config.scope ?? 'openid profile email',
    state: challenge.state,
    code_challenge: challenge.challenge,
    // S256 and never `plain`: a plain challenge is the verifier, which defeats the point.
    code_challenge_method: 'S256',
  });
  return `${config.issuer.replace(/\/$/, '')}/protocol/openid-connect/auth?${params}`;
}

export function tokenEndpoint(config: OidcConfig): string {
  return `${config.issuer.replace(/\/$/, '')}/protocol/openid-connect/token`;
}

export function logoutUrl(config: OidcConfig, idTokenHint?: string): string {
  const params = new URLSearchParams({ post_logout_redirect_uri: config.redirectUri });
  if (idTokenHint) params.set('id_token_hint', idTokenHint);
  return `${config.issuer.replace(/\/$/, '')}/protocol/openid-connect/logout?${params}`;
}

/** Stash what has to survive the redirect. */
export function rememberChallenge(challenge: PkceChallenge, returnTo?: string): void {
  try {
    sessionStorage.setItem(VERIFIER_KEY, challenge.verifier);
    sessionStorage.setItem(STATE_KEY, challenge.state);
    if (returnTo) sessionStorage.setItem(RETURN_KEY, returnTo);
  } catch (cause) {
    // Private browsing, or storage disabled by policy. Worth a clear message: without this the
    // login cannot complete, and "nothing happens when I sign in" is a bad bug report.
    throw new OidcError(
      'el navegador no permite almacenamiento de sesión, necesario para iniciar sesión',
      cause,
    );
  }
}

export interface CallbackParams {
  code: string;
  state: string;
}

/**
 * Read the provider's redirect.
 *
 * @throws OidcError when the provider reported an error, when required parameters are missing,
 *   or when `state` does not match what this tab sent — which is a CSRF attempt or a stale tab,
 *   and either way not something to continue from.
 */
export function readCallback(search: string): CallbackParams {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);

  const error = params.get('error');
  if (error) {
    throw new OidcError(
      `el proveedor de identidad rechazó el inicio de sesión: ${params.get('error_description') ?? error}`,
    );
  }

  const code = params.get('code');
  const state = params.get('state');
  if (!code || !state) {
    throw new OidcError('la respuesta del proveedor de identidad no trae código ni estado');
  }

  const expected = sessionStorage.getItem(STATE_KEY);
  if (!expected) {
    throw new OidcError('esta pestaña no inició ninguna sesión; vuelva a intentarlo');
  }
  if (state !== expected) {
    throw new OidcError('el estado devuelto no coincide con el que envió esta pestaña');
  }
  return { code, state };
}

export function takeVerifier(): string {
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  if (!verifier) {
    throw new OidcError('no hay verificador PKCE guardado para completar el inicio de sesión');
  }
  // Single use: a verifier that stays behind is one that can be replayed.
  sessionStorage.removeItem(VERIFIER_KEY);
  sessionStorage.removeItem(STATE_KEY);
  return verifier;
}

export function takeReturnTo(): string | null {
  const target = sessionStorage.getItem(RETURN_KEY);
  sessionStorage.removeItem(RETURN_KEY);
  return target;
}

/** Body for the code-for-token exchange. No secret: a browser cannot keep one. */
export function exchangeBody(
  config: OidcConfig,
  code: string,
  verifier: string,
): URLSearchParams {
  return new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    code,
    code_verifier: verifier,
  });
}

export function refreshBody(config: OidcConfig, refreshToken: string): URLSearchParams {
  return new URLSearchParams({
    grant_type: 'refresh_token',
    client_id: config.clientId,
    refresh_token: refreshToken,
  });
}

/**
 * Turn a token endpoint response into a token set.
 *
 * `expires_in` is trusted but floored: a provider that reports zero or a negative lifetime would
 * otherwise produce a token treated as already expired, and an endless renewal loop.
 */
export function readTokenResponse(body: unknown, now: number = Date.now()): TokenSet {
  if (typeof body !== 'object' || body === null) {
    throw new OidcError('la respuesta del token no es un objeto');
  }
  const payload = body as Record<string, unknown>;
  const accessToken = payload.access_token;
  if (typeof accessToken !== 'string' || !accessToken) {
    throw new OidcError('la respuesta del token no trae access_token');
  }
  const lifetime = typeof payload.expires_in === 'number' ? payload.expires_in : 0;
  return {
    accessToken,
    refreshToken: typeof payload.refresh_token === 'string' ? payload.refresh_token : null,
    expiresAt: now + Math.max(lifetime, 30) * 1000,
  };
}

/** How long before expiry renewal should fire. */
export const RENEW_MARGIN_MS = 60_000;

/**
 * Milliseconds until this token set should be renewed, never negative.
 *
 * Early rather than on failure: a supervisor halfway through typing an observation should not
 * find out the session expired by losing what they typed.
 */
export function renewIn(tokens: TokenSet, now: number = Date.now()): number {
  return Math.max(tokens.expiresAt - now - RENEW_MARGIN_MS, 0);
}

export function isExpired(tokens: TokenSet, now: number = Date.now()): boolean {
  return tokens.expiresAt <= now;
}
