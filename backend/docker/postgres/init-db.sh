#!/usr/bin/env bash
# Executado UMA vez pelo container do Postgres na criação do volume.
# Cria os papéis (dono das migrações x API sem privilégios) e os bancos principal, de teste e do WAHA.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v owner_pw="$DB_OWNER_PASSWORD" -v app_pw="$DB_APP_PASSWORD" <<'SQL'
CREATE ROLE saas_owner LOGIN PASSWORD :'owner_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
-- A API conecta com este papel: sem SUPERUSER e sem BYPASSRLS, então o RLS sempre vale.
CREATE ROLE saas_app   LOGIN PASSWORD :'app_pw'   NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

CREATE DATABASE saas_pilates      OWNER saas_owner;
CREATE DATABASE saas_pilates_test OWNER saas_owner;
CREATE DATABASE waha              OWNER saas_owner;
SQL

for db in saas_pilates saas_pilates_test; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<'SQL'
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO saas_owner;
GRANT USAGE ON SCHEMA public TO saas_app;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SQL
done
