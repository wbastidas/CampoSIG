import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end configuration.
 *
 * Runs against the **production build**, not the dev server. What the tests should exercise is
 * the artifact that gets deployed: a dev server transforms modules on the fly and papers over
 * mistakes a real build would surface — a missing entry point, a broken import, a chunk that
 * never loads.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  reporter: process.env.CI ? 'list' : 'html',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          // El entorno de CI y el de desarrollo pueden traer un Chromium ya instalado con una
          // revisión distinta de la que este @playwright/test espera. Si PLAYWRIGHT_CHROMIUM
          // apunta a un binario, se usa ese en vez de descargar otro: la alternativa es que la
          // suite e2e solo corra donde alguien acertó con la versión.
          executablePath: process.env.PLAYWRIGHT_CHROMIUM || undefined,
        },
      },
    },
  ],
  webServer: {
    // `--host 127.0.0.1` explícito: sin él, `vite preview` escucha en `localhost`, que en un
    // runner de CI resuelve primero a ::1, mientras Playwright sondea 127.0.0.1 — y espera dos
    // minutos a un servidor que sí estaba arriba, en la otra pila.
    command: 'npm run build && npm run preview -- --host 127.0.0.1 --port 4173 --strictPort',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
    // El tiempo incluye la compilación de producción, que en un runner frío no es inmediata.
    timeout: 180_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
