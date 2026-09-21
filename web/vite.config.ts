import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    // The web app talks to the backend on the same origin in development, so the planner
    // screens need no CORS configuration and no absolute URLs in the client.
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
});
