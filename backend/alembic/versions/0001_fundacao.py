"""Fundação: função de tenant atual, tabela tenants (com RLS) e eventos_processados.

Revision ID: 0001_fundacao
Revises:
Create Date: 2026-11-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_fundacao"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Papel usado pela API em runtime (sem SUPERUSER, sem BYPASSRLS). Criado pelo init do Postgres.
APP_ROLE = "saas_app"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Tenant atual da transação. Se não foi definido, retorna NULL e as políticas
    # RLS não casam com nenhuma linha (fail-closed).
    op.execute(
        """
        CREATE FUNCTION app_current_tenant() RETURNS uuid
        LANGUAGE sql STABLE
        AS $$ SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::uuid $$
        """
    )

    op.execute(
        """
        CREATE TABLE tenants (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            nome       VARCHAR(150) NOT NULL,
            ativo      BOOLEAN      NOT NULL DEFAULT true,
            criado_em  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )
    # Padrão RLS que toda tabela de tenant vai repetir: ENABLE + FORCE + política única.
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON tenants
            USING (id = app_current_tenant())
            WITH CHECK (id = app_current_tenant())
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON tenants TO {APP_ROLE}")

    # Idempotência ("carimbou, tá pago"): o INSERT do evento_id acontece ANTES da ação.
    # Somente SELECT/INSERT para a API: um carimbo nunca é alterado nem apagado.
    op.execute(
        """
        CREATE TABLE eventos_processados (
            evento_id      VARCHAR(255) PRIMARY KEY,
            processado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(f"GRANT SELECT, INSERT ON eventos_processados TO {APP_ROLE}")
    op.execute(f"GRANT EXECUTE ON FUNCTION app_current_tenant() TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS eventos_processados")
    op.execute("DROP TABLE IF EXISTS tenants")
    op.execute("DROP FUNCTION IF EXISTS app_current_tenant()")
