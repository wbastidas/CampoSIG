/**
 * The session: acquire a token, keep it fresh, and hand the app the person behind it (RF-001).
 *
 * Wraps the whole app so no screen has to think about authentication. Three behaviours are
 * deliberate and each one comes from a way this goes wrong in the field:
 *
 * * **The redirect remembers where the person was.** A supervisor who opens a deep link to a
 *   work order and gets bounced through the identity provider should land back on that work
 *   order, not on a dashboard.
 * * **Renewal is silent and early.** Losing a half-typed observation because a token expired is
 *   the kind of thing people stop using a tool over.
 * * **A failed renewal does not blank the screen.** It offers a re-login, and what is on screen
 *   stays on screen while the person decides.
 */

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';

import { notifyExpired, onTokenExpired, setAccessToken } from '../api/session';
import {
  authorizeUrl,
  createChallenge,
  exchangeBody,
  logoutUrl,
  type OidcConfig,
  OidcError,
  readCallback,
  readTokenResponse,
  refreshBody,
  rememberChallenge,
  renewIn,
  takeReturnTo,
  takeVerifier,
  type TokenSet,
  tokenEndpoint,
} from './oidc';

export interface SessionUser {
  subject: string;
  username: string | null;
  roles: string[];
  businessUnits: string[];
}

export interface SessionState {
  status: 'cargando' | 'anonimo' | 'autenticado' | 'error';
  user: SessionUser | null;
  error: string | null;
  signIn: () => void;
  signOut: () => void;
}

const SessionContext = createContext<SessionState | null>(null);

export function useSession(): SessionState {
  const state = useContext(SessionContext);
  if (state === null) {
    throw new Error('useSession requiere un <SessionProvider> por encima');
  }
  return state;
}

/**
 * Read the roles and units out of the access token for the UI's own use.
 *
 * Presentational only: the backend verifies the signature and decides what anybody may do. The
 * browser reading its own token is how a screen knows to hide a button, never how access is
 * granted — a claim the client trusted for authorisation would be a claim the client could edit.
 */
export function describeToken(accessToken: string): SessionUser | null {
  const [, payload] = accessToken.split('.');
  if (!payload) return null;
  try {
    const decoded = JSON.parse(
      atob(payload.replace(/-/g, '+').replace(/_/g, '/')),
    ) as Record<string, unknown>;
    const realm = (decoded.realm_access as { roles?: string[] } | undefined)?.roles ?? [];
    const units = decoded.business_units;
    return {
      subject: String(decoded.sub ?? ''),
      username: typeof decoded.preferred_username === 'string' ? decoded.preferred_username : null,
      roles: realm.map(String),
      businessUnits: Array.isArray(units) ? units.map(String) : [],
    };
  } catch {
    // An unreadable payload is not fatal: the backend is the one that has to understand the
    // token. The UI simply shows less.
    return null;
  }
}

export interface SessionProviderProps {
  config: OidcConfig;
  children: ReactNode;
  /** Injected in tests so no real network or redirect happens. */
  fetchImpl?: typeof fetch;
  redirect?: (url: string) => void;
  location?: { search: string; pathname: string };
}

export function SessionProvider({
  config,
  children,
  fetchImpl,
  redirect,
  location,
}: SessionProviderProps) {
  const [status, setStatus] = useState<SessionState['status']>('cargando');
  const [user, setUser] = useState<SessionUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const tokensRef = useRef<TokenSet | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doFetch = fetchImpl ?? globalThis.fetch.bind(globalThis);
  const go = redirect ?? ((url: string) => { globalThis.location.assign(url); });
  const here = location ?? { search: globalThis.location?.search ?? '', pathname: globalThis.location?.pathname ?? '/' };

  const adopt = useCallback((tokens: TokenSet) => {
    tokensRef.current = tokens;
    setAccessToken(tokens.accessToken);
    setUser(describeToken(tokens.accessToken));
    setStatus('autenticado');
    setError(null);
  }, []);

  const signIn = useCallback(() => {
    void (async () => {
      try {
        const challenge = await createChallenge();
        rememberChallenge(challenge, `${here.pathname}${here.search}`);
        go(authorizeUrl(config, challenge));
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : String(cause));
        setStatus('error');
      }
    })();
  }, [config, go, here.pathname, here.search]);

  const signOut = useCallback(() => {
    tokensRef.current = null;
    setAccessToken(null);
    setUser(null);
    setStatus('anonimo');
    go(logoutUrl(config));
  }, [config, go]);

  const renew = useCallback(async () => {
    const current = tokensRef.current;
    if (!current?.refreshToken) {
      // Nothing to renew with. Not an error yet: the token may still be valid, and the person
      // will be asked to sign in again when it is not.
      notifyExpired();
      setStatus('anonimo');
      return;
    }
    try {
      const answer = await doFetch(tokenEndpoint(config), {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: refreshBody(config, current.refreshToken).toString(),
      });
      if (!answer.ok) throw new OidcError(`la renovación falló con ${answer.status}`);
      adopt(readTokenResponse(await answer.json()));
    } catch (cause) {
      // The screen is not blanked. What is on it stays while the person decides to sign in.
      setError(cause instanceof Error ? cause.message : String(cause));
      setStatus('anonimo');
      notifyExpired();
    }
  }, [adopt, config, doFetch]);

  // Complete the callback, or start out anonymous.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      if (!here.search.includes('code=')) {
        setStatus('anonimo');
        return;
      }
      try {
        const { code } = readCallback(here.search);
        const verifier = takeVerifier();
        const answer = await doFetch(tokenEndpoint(config), {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: exchangeBody(config, code, verifier).toString(),
        });
        if (!answer.ok) throw new OidcError(`el intercambio del código falló con ${answer.status}`);
        if (cancelled) return;
        adopt(readTokenResponse(await answer.json()));
        const returnTo = takeReturnTo();
        if (returnTo && globalThis.history?.replaceState) {
          // The code must not stay in the address bar: it is single-use, and a bookmarked URL
          // carrying it produces a confusing failure on the next visit.
          globalThis.history.replaceState(null, '', returnTo);
        }
      } catch (cause) {
        if (cancelled) return;
        setError(cause instanceof Error ? cause.message : String(cause));
        setStatus('error');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [adopt, config, doFetch, here.search]);

  // Schedule the silent renewal.
  useEffect(() => {
    if (status !== 'autenticado' || !tokensRef.current) return;
    const delay = renewIn(tokensRef.current);
    timerRef.current = setTimeout(() => void renew(), delay);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [status, renew]);

  // A 401 from any API call means the token stopped working before its stated expiry.
  useEffect(() => {
    onTokenExpired(() => {
      setStatus('anonimo');
      setUser(null);
    });
    return () => onTokenExpired(null);
  }, []);

  return (
    <SessionContext.Provider value={{ status, user, error, signIn, signOut }}>
      {children}
    </SessionContext.Provider>
  );
}

/** Shows its children only to an authenticated person; otherwise offers the sign-in. */
export function RequireSession({ children }: { children: ReactNode }) {
  const session = useSession();

  if (session.status === 'cargando') return <p>Verificando la sesión…</p>;

  if (session.status === 'autenticado') return <>{children}</>;

  return (
    <section className="login-gate">
      <h1>SIGEC-Campo</h1>
      <p>Esta plataforma requiere su cuenta corporativa.</p>
      {session.error && <p role="alert">{session.error}</p>}
      <button type="button" onClick={session.signIn}>
        Iniciar sesión
      </button>
    </section>
  );
}
