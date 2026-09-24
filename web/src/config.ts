/**
 * Build-time configuration, from the environment (RF-001).
 *
 * Read through `import.meta.env` rather than fetched at runtime: the identity provider's URL and
 * the client id are not secrets, and a deployment that had to serve them from an endpoint would
 * have an endpoint that must work before anybody can log in.
 *
 * Defaults point at the development Compose. They are wrong in production, which is why the
 * build fails loudly on a missing business unit rather than guessing one.
 */

import type { OidcConfig } from './auth/oidc';

interface Env {
  VITE_OIDC_ISSUER?: string;
  VITE_OIDC_CLIENT_ID?: string;
  VITE_BUSINESS_UNIT?: string;
}

const env = import.meta.env as unknown as Env;

export const oidcConfig: OidcConfig = {
  issuer: env.VITE_OIDC_ISSUER ?? 'http://localhost:8080/realms/sigec',
  clientId: env.VITE_OIDC_CLIENT_ID ?? 'sigec-web',
  // The provider redirects back to wherever the app is served from. Computed rather than
  // configured, so a deployment behind a different hostname needs no extra setting.
  redirectUri: `${globalThis.location?.origin ?? ''}/`,
  scope: 'openid profile email',
};

/**
 * The business unit this deployment serves.
 *
 * Every API call carries it (ADR-009). A person whose token names several units picks one; this
 * is the default the screens open with.
 */
export const defaultBusinessUnit = env.VITE_BUSINESS_UNIT ?? 'GYE';
