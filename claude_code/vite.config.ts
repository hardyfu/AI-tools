import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    environmentOptions: {
      url: 'http://localhost:3000',
    },
    setupFiles: './src/test/setup.ts',
  },
})
