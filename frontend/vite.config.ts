import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The board calls the FastAPI backend directly at http://localhost:9000 (see src/api.ts);
// the backend's CORS list allows this page's origin, http://localhost:5173.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 }, // if 5173 is taken, Vite moves to 5174 (also allowed by the backend)
})
