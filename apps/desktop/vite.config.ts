import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Tauri serves the built app; in dev it loads this server.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: { port: 1431, strictPort: true },
  build: { target: 'safari16', outDir: 'dist' },
})
