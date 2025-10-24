import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    tailwindcss()
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  // Dev server proxy so that frontend (e.g. running on :5173) forwards API/static requests
  // to the FastAPI backend on :8000. This fixes the issue where the app was calling
  // http://localhost:5173/api/... (served by Vite and returning index.html) instead of
  // the FastAPI JSON endpoints, causing "Unexpected token '<'" JSON parse errors.
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Serve backend static assets (fonts, etc.) through the dev server too.
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
