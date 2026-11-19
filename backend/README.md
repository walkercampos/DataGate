# SaaS Pilates & Fisio — Backend (API-First)

FastAPI + PostgreSQL 16 (SQLAlchemy 2.0 async/asyncpg) + Redis. Multi-tenant com RLS.

## Status das fatias

| Fatia | Escopo | Status |
|---|---|---|
| 0 | Fundação: Docker, config, RLS, `trace_id`, Swagger off em produção, `/health` | ✅ |
| 1 | Auth/JWT multi-tenant: cadastro de estúdio, login, `/auth/me`, configurações do estúdio | ✅ |
| 2 | Alunos: cadastro, busca, edição, inativação (créditos não editáveis pelo cliente) | ✅ |
| 3 | Agenda: aulas avulsas e grade recorrente, lotação com `FOR UPDATE`, cancelamento com/sem crédito, reposição com débito atômico, presença/falta | ✅ |
| 4 | Planos e contratos com horários fixos; grade mensal automática e idempotente | ✅ |
| 5 | Prontuário: avaliação/evolução, assinatura, hash SHA-256 e trigger de imutabilidade | ✅ |
| Web | Interface própria em `../frontend` (React + Vite + Tailwind) | ✅ |
| 6 | WhatsApp (WAHA + ARQ): lembrete 24h, cancelamento por "2", webhooks idempotentes | ⏳ |

## Endpoints

| Método | Rota | O que faz |
|---|---|---|
| POST | `/auth/registrar` | Cria estúdio + admin, devolve token |
| POST | `/auth/login` | Login, devolve token |
| GET | `/auth/me` | Usuário logado |
| GET/PATCH | `/estudio` | Configurações (capacidade, antecedência, validade do crédito, fuso) |
| POST/GET | `/alunos` | Cadastrar / listar (`?busca=`, `?apenas_ativos=`) |
| GET/PATCH | `/alunos/{id}` | Detalhe / editar / inativar |
| POST | `/agenda/aulas` | Criar aula avulsa (capacidade vem do estúdio) |
| POST | `/agenda/aulas/recorrentes` | Gerar grade (dias da semana × semanas) |
| GET | `/agenda/aulas?de=&ate=` | Aulas do período com vagas e participantes |
| GET/DELETE | `/agenda/aulas/{id}` | Detalhe / excluir (só sem agendamentos) |
| POST | `/agenda/aulas/{id}/agendamentos` | Agendar aluno (`usar_reposicao` consome crédito) |
| POST | `/agenda/agendamentos/{id}/cancelar` | Cancela; no prazo gera +1 crédito |
| POST | `/agenda/agendamentos/{id}/presenca` | Marca `presente` ou `falta` |
| POST/GET | `/planos` | Criar / listar planos |
| PATCH | `/planos/{id}` | Editar / inativar plano |
| POST | `/contratos` | Contratar plano com horários fixos (gera a grade do mês) |
| GET | `/contratos?aluno_id=` | Contratos |
| POST | `/contratos/{id}/gerar-grade` | Gerar grade de um mês para o contrato |
| POST | `/contratos/gerar-grade-mensal` | Gerar grade do mês para todos os contratos ativos |
| POST | `/contratos/{id}/encerrar` | Encerrar e liberar aulas futuras |
| POST/GET | `/alunos/{id}/prontuario` | Novo registro (rascunho) / histórico |
| GET/PATCH/DELETE | `/prontuario/{id}` | Ver / editar / excluir (só rascunho) |
| POST | `/prontuario/{id}/assinar` | Assina: o banco grava hash SHA-256 e bloqueia |
| GET | `/prontuario/{id}/verificar` | Recalcula o hash e confere a integridade |

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

## Ubuntu: instalação em um comando

```bash
git clone https://github.com/walkercampos/DataGate.git && cd DataGate
git checkout claude/pilates-physio-saas-backend-lv5qr2
./scripts/setup-ubuntu.sh          # instala Docker, gera .env com senhas aleatórias e sobe tudo
./scripts/setup-ubuntu.sh --dev    # + Python 3.12, Node 22, Playwright e roda TODOS os testes
```
Interface em http://localhost:8080 · Swagger em http://localhost:8000/docs.

## Rodando com Docker

```bash
cd backend
cp .env.example .env          # edite as senhas e o JWT_SECRET
docker compose up -d --build  # postgres + redis + api + web (aplica migrações ao subir)
# Interface: http://localhost:8080
curl http://localhost:8000/health
# Swagger: http://localhost:8000/docs   (desativado se ENVIRONMENT=production)

# Testes dentro do container (banco saas_pilates_test):
docker compose exec api pytest -v

# WAHA (fatia de WhatsApp):
docker compose --profile whatsapp up -d waha
```

> O script `docker/postgres/init-db.sh` roda só na **criação** do volume. Se mudar senhas depois: `docker compose down -v` (apaga os dados locais).

## Todos os testes de uma vez

```bash
./scripts/testar-tudo.sh   # na raiz: pytest -> npm test -> build -> e2e (Playwright)
```
O GitHub Actions roda os mesmos três níveis a cada push.

## Rodando local (sem Docker para a API)

```bash
cd backend
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
docker compose up -d postgres redis
pytest -v
alembic upgrade head && uvicorn app.main:app --reload
```
