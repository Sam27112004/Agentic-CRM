import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/rag': 'http://localhost:8000',
      '/agent': 'http://localhost:8000',
      '/dashboard': 'http://localhost:8000',
      '/threads': 'http://localhost:8000',
      '/analytics': 'http://localhost:8000',
      '/contacts': 'http://localhost:8000',
      '/drafts': 'http://localhost:8000',
      '/respond': 'http://localhost:8000',
      '/intelligence': 'http://localhost:8000',
      '/audit': 'http://localhost:8000',
    },
  },
})
