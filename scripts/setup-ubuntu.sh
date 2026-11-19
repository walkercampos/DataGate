#!/usr/bin/env bash
# Configura o Studio Pilates num Ubuntu (22.04 ou 24.04) e sobe tudo com Docker.
#
#   ./scripts/setup-ubuntu.sh          -> instala Docker, gera .env com senhas aleatórias e sobe o sistema
#   ./scripts/setup-ubuntu.sh --dev    -> além disso, instala Python 3.12 + Node 22 + Playwright e roda TODOS os testes
#
# Pode rodar quantas vezes quiser: o que já estiver pronto é mantido (inclusive o .env).
set -euo pipefail

DEV=false
[ "${1:-}" = "--dev" ] && DEV=true
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

passo() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
aviso() { printf '\033[1;33m[!] %s\033[0m\n' "$*"; }

# ---------------------------------------------------------------- verificações
. /etc/os-release
if [ "${ID:-}" != "ubuntu" ]; then aviso "Feito para Ubuntu; detectado: ${PRETTY_NAME:-desconhecido}. Continuando mesmo assim."; fi

passo "Pacotes básicos (curl, git, openssl)"
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq ca-certificates curl git openssl gnupg >/dev/null

# ---------------------------------------------------------------- Docker
if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
  passo "Instalando Docker Engine + Compose (repositório oficial)"
  $SUDO install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  $SUDO chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
else
  passo "Docker já instalado: $(docker --version)"
fi
$SUDO systemctl enable --now docker >/dev/null 2>&1 || true

# Usuário no grupo docker (vale a partir do próximo login; nesta execução usamos sudo se preciso).
if [ -n "$SUDO" ] && ! id -nG "$USER" | grep -qw docker; then
  $SUDO usermod -aG docker "$USER"
  aviso "Seu usuário entrou no grupo 'docker'. Faça logout/login para usar 'docker' sem sudo."
fi
DOCKER="docker"; docker info >/dev/null 2>&1 || DOCKER="$SUDO docker"

# ---------------------------------------------------------------- portas
for porta in 5432 6379 8000 8080; do
  if ss -ltnH "sport = :$porta" 2>/dev/null | grep -q . && ! $DOCKER ps --format '{{.Ports}}' | grep -q ":$porta->"; then
    aviso "A porta $porta já está em uso por outro programa (ex.: um PostgreSQL/Redis instalado no Ubuntu)."
    aviso "Pare-o (ex.: sudo systemctl stop postgresql) e rode este script de novo."
    exit 1
  fi
done

# ---------------------------------------------------------------- .env com segredos aleatórios
ENV="$RAIZ/backend/.env"
if [ -f "$ENV" ]; then
  passo ".env já existe: mantido ($ENV)"
else
  passo "Gerando backend/.env com senhas aleatórias"
  aleatorio() { openssl rand -hex 24; }
  sed -e "s/troque-superusuario/$(aleatorio)/g" \
      -e "s/troque-owner/$(aleatorio)/g" \
      -e "s/troque-app/$(aleatorio)/g" \
      -e "s/troque-waha/$(aleatorio)/g" \
      -e "s/^JWT_SECRET=.*/JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n=+\/')/" \
      "$RAIZ/backend/.env.example" > "$ENV"
  chmod 600 "$ENV"
fi

# ---------------------------------------------------------------- sobe o sistema
passo "Construindo e subindo: PostgreSQL, Redis, API e interface web (pode levar alguns minutos)"
cd "$RAIZ/backend"
$DOCKER compose up -d --build

passo "Aguardando a API ficar saudável"
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/health >/dev/null; then break; fi
  [ "$i" -eq 60 ] && { aviso "A API não respondeu. Veja os logs: cd backend && docker compose logs api"; exit 1; }
  sleep 2
done
curl -s http://localhost:8000/health; echo

# ---------------------------------------------------------------- ambiente de desenvolvimento + testes
if $DEV; then
  passo "Python 3.12 (backend)"
  if ! command -v python3.12 >/dev/null; then
    $SUDO apt-get install -y -qq software-properties-common >/dev/null
    $SUDO add-apt-repository -y ppa:deadsnakes/ppa >/dev/null
    $SUDO apt-get update -qq
  fi
  $SUDO apt-get install -y -qq python3.12 python3.12-venv >/dev/null
  [ -d "$RAIZ/backend/.venv" ] || python3.12 -m venv "$RAIZ/backend/.venv"
  "$RAIZ/backend/.venv/bin/pip" install -q --upgrade pip
  "$RAIZ/backend/.venv/bin/pip" install -q -r "$RAIZ/backend/requirements-dev.txt"

  passo "Node.js 22 (frontend)"
  if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 22 ]; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | $SUDO -E bash - >/dev/null
    $SUDO apt-get install -y -qq nodejs >/dev/null
  fi
  cd "$RAIZ/frontend"
  npm ci --no-audit --no-fund
  passo "Navegador para os testes de ponta a ponta (Playwright/Chromium)"
  npx playwright install --with-deps chromium

  passo "Rodando TODOS os testes: pytest -> npm test -> build -> navegador"
  "$RAIZ/scripts/testar-tudo.sh"
fi

passo "Pronto!"
cat <<EOF
  Interface:  http://localhost:8080
  API/Swagger: http://localhost:8000/docs
  Parar:       cd backend && docker compose down
  Subir de novo: cd backend && docker compose up -d
  Testes:      ./scripts/setup-ubuntu.sh --dev   (instala as ferramentas)  ou  ./scripts/testar-tudo.sh
EOF
