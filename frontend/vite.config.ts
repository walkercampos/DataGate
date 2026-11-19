import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Em dev, /api é repassado para a API FastAPI (sem CORS). Em produção, o nginx faz o mesmo.
const API = process.env.API_URL ?? "http://localhost:8000";
const proxy = { "/api": { target: API, changeOrigin: true, rewrite: (p: string) => p.replace(/^\/api/, "") } };

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
});
