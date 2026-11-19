# SaaS Pilates & Fisio — Backend (API-First)

FastAPI + PostgreSQL 16 (SQLAlchemy 2.0 async/asyncpg) + Redis. Multi-tenant com RLS.

## Status das fatias

| Fatia | Escopo | Status |
|---|---|---|
| 0 | Fundação: Docker, config, RLS, `trace_id`, Swagger off em produção, `/health` | ✅ |
| 1 | Auth/JWT multi-tenant | ⏳ |

## Estrutura

```
app/
  core/            config (.env), database (sessão + set_tenant/RLS), exceptions (trace_id)
  modules/<nome>/  schemas.py · repository.py · service.py · router.py   ("gavetas")
alembic/versions/  migrações em SQL explícito (RLS, grants, triggers)
docker/postgres/   init: papéis saas_owner / saas_app e bancos saas_pilates, saas_pilates_test, waha
tests/             integração real contra saas_pilates_test
```

## Segurança do banco

- **Dois papéis:** `saas_owner` é dono das tabelas e só roda migrações. `saas_app` é usado pela API: `NOSUPERUSER NOBYPASSRLS`, só DML liberado tabela a tabela.
- **RLS em toda tabela de tenant:** `ENABLE` + `FORCE ROW LEVEL SECURITY` + política `tenant_isolation` usando `app_current_tenant()`. Sem tenant definido na transação, nenhuma linha é visível (fail-closed).
- **`set_tenant(session, tenant_id)`** executa `set_config('app.current_tenant_id', :tid, true)`, equivalente parametrizado de `SET LOCAL`, válido só na transação. O `tenant_id` virá do JWT (Fatia 1).
- **`eventos_processados`:** a API só tem `SELECT/INSERT` — um carimbo nunca é apagado ou reescrito.

## Rodando com Docker

```bash
cd backend
cp .env.example .env          # edite as senhas
docker compose up -d --build  # postgres + redis + api (aplica migrações ao subir)
curl http://localhost:8000/health
# Swagger: http://localhost:8000/docs   (desativado se ENVIRONMENT=production)

# Testes dentro do container (banco saas_pilates_test):
docker compose exec api pytest -v

# WAHA (fatia de WhatsApp):
docker compose --profile whatsapp up -d waha
```

> O script `docker/postgres/init-db.sh` roda só na **criação** do volume. Se mudar senhas depois: `docker compose down -v` (apaga os dados locais).

## Rodando local (sem Docker para a API)

```bash
cd backend
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
docker compose up -d postgres redis
pytest -v
alembic upgrade head && uvicorn app.main:app --reload
```
