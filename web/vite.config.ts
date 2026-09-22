import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    // The web app talks to the backend on the same origin in development, so the screens need
    // no CORS configuration and no absolute URLs in the client.
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
  test: {
    // jsdom for the whole suite: some tests touch browser APIs (`sessionStorage`,
    // `crypto.subtle`) and others render React. One environment per file would be a
    // configuration somebody has to remember to maintain.
    environment: 'jsdom',
    setupFiles: ['./src/test-support/setup.ts'],
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
});
