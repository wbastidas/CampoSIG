import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // jsdom para los tests que tocan APIs del navegador —`Storage.prototype`, por ejemplo—.
    // La lógica pura no lo necesita, pero un entorno por archivo sería una configuración que
    // alguien tiene que recordar mantener.
    environment: 'jsdom',
  },
});
