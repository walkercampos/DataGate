#!/usr/bin/env bash
# Roda TODOS os testes, na ordem: backend (pytest) -> frontend (npm test + build) -> navegador (e2e).
# Uso: ./scripts/testar-tudo.sh          (com Postgres e Redis rodando, ex.: docker compose up -d postgres redis)
#      ./scripts/testar-tudo.sh --sem-e2e
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> 1/3 Backend: pytest (banco saas_pilates_test)"
cd "$RAIZ/backend"
PY="${PYTHON:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}"
"$PY" -m pytest -q

echo "==> 2/3 Frontend: npm test (tipos + testes) e build"
cd "$RAIZ/frontend"
[ -d node_modules ] || npm ci --no-audit --no-fund
npm test
npm run build

if [ "${1:-}" != "--sem-e2e" ]; then
  echo "==> 3/3 Navegador: npm run test:e2e (API precisa estar em http://localhost:8000)"
  curl -sf http://localhost:8000/health >/dev/null || { echo "API fora do ar: rode 'docker compose up -d' em backend/ ou uvicorn"; exit 1; }
  npm run test:e2e
fi
echo "✅ Tudo verde."
