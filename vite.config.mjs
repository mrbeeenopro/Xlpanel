import { defineConfig } from 'vite';
import { resolve } from 'node:path';

export default defineConfig({
  root: resolve(process.cwd(), 'frontend'),
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/afk/ws': {
        target: 'ws://127.0.0.1:5000',
        ws: true,
      },
    },
  },
  build: {
    outDir: resolve(process.cwd(), 'frontend', 'dist'),
    emptyOutDir: true,
  },
});
