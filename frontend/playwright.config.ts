import { defineConfig } from "@playwright/test";

// Teste de ponta a ponta: navegador real -> frontend -> API real -> PostgreSQL.
// Pré-requisito: API rodando (docker compose up -d, ou uvicorn na porta 8000).
export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  retries: 0,
  use: { baseURL: process.env.E2E_URL ?? "http://localhost:4173", viewport: { width: 1360, height: 900 } },
  webServer: process.env.E2E_URL ? undefined : {
    command: "npm run build && npx vite preview --port 4173 --strictPort",
    url: "http://localhost:4173",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
