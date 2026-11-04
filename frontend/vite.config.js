import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Forward API calls to the Flask backend during local development,
    // so the frontend can always use relative URLs like /api/chat.
    proxy: {
      '/api': 'http://127.0.0.1:5001',
    },
  },
})
