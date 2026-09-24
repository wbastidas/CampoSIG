/**
 * Entry point.
 *
 * `RequireSession` wraps everything: there is no screen in this application that a person
 * without a corporate identity should see, and putting the gate here means no screen has to
 * remember that.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { RequireSession, SessionProvider } from './auth/SessionProvider';
import { App } from './App';
import { oidcConfig } from './config';
import './styles.css';

const container = document.getElementById('root');
if (!container) {
  // A missing mount point is a broken build, not a runtime condition to handle gracefully.
  throw new Error('no existe el elemento #root en el documento');
}

createRoot(container).render(
  <StrictMode>
    <SessionProvider config={oidcConfig}>
      <RequireSession>
        <App />
      </RequireSession>
    </SessionProvider>
  </StrictMode>,
);
