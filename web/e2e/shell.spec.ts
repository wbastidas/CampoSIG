/**
 * The built application, in a real browser.
 *
 * This is the verification that neither the unit tests nor the render tests can give: that the
 * artifact which gets deployed actually loads, mounts, and puts the login gate in front of
 * everything. A bundle that fails to load shows up nowhere else — `tsc` compiles it, `vitest`
 * imports the modules directly, and both are happy.
 *
 * No identity provider runs here, so the flow stops at the gate. That is the point: the gate is
 * what must hold when there is no way in.
 */

import { expect, test } from '@playwright/test';

test('la aplicación carga y exige iniciar sesión', async ({ page }) => {
  const problems: string[] = [];
  page.on('pageerror', (error) => problems.push(`error de página: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error') problems.push(`consola: ${message.text()}`);
  });

  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'SIGEC-Campo' })).toBeVisible();
  await expect(page.getByRole('button', { name: /iniciar sesión/i })).toBeVisible();
  // Ninguna pantalla debe estar detrás de la puerta cuando no hay sesión.
  await expect(page.getByRole('navigation', { name: 'Pantallas' })).toHaveCount(0);

  // Un bundle que carga con errores en consola "funciona" hasta que no.
  expect(problems).toEqual([]);
});

test('el botón de iniciar sesión lleva al proveedor de identidad con PKCE', async ({ page }) => {
  // Se intercepta la navegación en vez de redefinir `window.location`: en un navegador real esa
  // propiedad no se puede reemplazar, y un test que dependiera de ello solo pasaría en jsdom.
  let authorizeUrl: string | null = null;
  await page.route('**/protocol/openid-connect/auth*', async (route) => {
    authorizeUrl = route.request().url();
    // Se aborta en vez de responder: si la navegación se completa, la página queda en el origen
    // del proveedor y su `sessionStorage` es otro — el verificador que se comprueba abajo vive
    // en el de la aplicación.
    await route.abort();
  });

  await page.goto('/');
  await page.getByRole('button', { name: /iniciar sesión/i }).click();

  await expect.poll(() => authorizeUrl).not.toBeNull();
  const url = new URL(authorizeUrl!);
  expect(url.pathname).toContain('/protocol/openid-connect/auth');
  expect(url.searchParams.get('code_challenge_method')).toBe('S256');
  expect(url.searchParams.get('response_type')).toBe('code');
  expect(url.searchParams.get('code_challenge')).toBeTruthy();
  // El verificador nunca viaja en la petición de autorización; se queda en la pestaña.
  expect(url.search).not.toContain('code_verifier');

  // Que el verificador se guarde y sobreviva a la redirección se comprueba donde se puede
  // comprobar con precisión: en `oidc.test.ts` y en `SessionProvider.test.tsx`. Aquí, tras
  // abortar la navegación, el documento ya no concede acceso a su almacenamiento, y un test que
  // lo intentara estaría midiendo el estado del navegador y no el de la aplicación.
});

test('el documento declara español de Ecuador', async ({ page }) => {
  // La regla 11 de CLAUDE.md: textos de UI en es-EC. Si el documento no lo declara, los
  // lectores de pantalla y la corrección ortográfica del navegador usan otro idioma.
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('lang', 'es-EC');
});
