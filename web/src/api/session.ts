/**
 * The bearer token every API call carries (RF-001).
 *
 * One place, for one reason: a `fetch` somewhere that forgets the header is a call that fails
 * with 401 in production and works on the developer's machine, where the escape hatch is on.
 *
 * The token is **not** persisted. It lives in memory for the tab's lifetime and is re-acquired
 * from the identity provider on reload. `localStorage` would survive a closed laptop in a
 * substation control room, which is exactly the place it should not survive.
 */

let accessToken: string | null = null;
let onExpired: (() => void) | null = null;

/** Called by the login flow once the identity provider returns a token. */
export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function currentToken(): string | null {
  return accessToken;
}

/**
 * Register what to do when the server says the token is no longer good.
 *
 * Kept as a callback rather than hard-coded to a redirect: a supervisor halfway through typing
 * an observation should be offered a re-login, not have the page replaced under them.
 */
export function onTokenExpired(handler: (() => void) | null): void {
  onExpired = handler;
}

/** Headers for an API call: the content type, and the token when there is one. */
export function authHeaders(extra: HeadersInit = {}): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(extra as Record<string, string>),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  return headers;
}

/** Called by the API clients on a 401, so the session can be renewed once. */
export function notifyExpired(): void {
  accessToken = null;
  onExpired?.();
}
