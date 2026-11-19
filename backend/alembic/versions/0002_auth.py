"""Fatia 1 — Auth: configurações do estúdio, usuários e função de login.

Revision ID: 0002_auth
Revises: 0001_fundacao
Create Date: 2026-11-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_auth"
down_revision: str | None = "0001_fundacao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "saas_app"
OWNER_ROLE = "saas_owner"


def upgrade() -> None:
    # Configurações do estúdio: SEMPRE lidas do banco pelo backend, nunca do cliente.
    op.execute(
        """
        ALTER TABLE tenants
            ADD COLUMN capacidade_padrao_turma         INT NOT NULL DEFAULT 4
                CHECK (capacidade_padrao_turma BETWEEN 1 AND 50),
            ADD COLUMN antecedencia_cancelamento_horas INT NOT NULL DEFAULT 3
                CHECK (antecedencia_cancelamento_horas BETWEEN 0 AND 168),
            ADD COLUMN validade_credito_dias           INT NOT NULL DEFAULT 30
                CHECK (validade_credito_dias BETWEEN 1 AND 365),
            ADD COLUMN fuso_horario                    VARCHAR(64) NOT NULL DEFAULT 'America/Sao_Paulo'
        """
    )

    op.execute(
        """
        CREATE TABLE usuarios (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL REFERENCES tenants(id),
            nome        VARCHAR(150) NOT NULL,
            email       VARCHAR(254) NOT NULL,
            senha_hash  TEXT NOT NULL,
            papel       VARCHAR(20) NOT NULL DEFAULT 'admin' CHECK (papel IN ('admin', 'instrutor')),
            ativo       BOOLEAN NOT NULL DEFAULT true,
            criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    # E-mail único no sistema todo: o login acontece ANTES de sabermos o tenant.
    op.execute("CREATE UNIQUE INDEX uq_usuarios_email ON usuarios (lower(email))")
    op.execute("CREATE INDEX ix_usuarios_tenant ON usuarios (tenant_id)")
    op.execute("ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE usuarios FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON usuarios
            USING (tenant_id = app_current_tenant())
            WITH CHECK (tenant_id = app_current_tenant())
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON usuarios TO {APP_ROLE}")

    # Login: única leitura sem tenant. Função SECURITY DEFINER (roda como saas_owner),
    # só leitura, devolve apenas o necessário para validar a senha. As políticas abaixo
    # valem SOMENTE para o papel dono — a API (saas_app) continua 100% isolada.
    op.execute(f"CREATE POLICY auth_lookup ON usuarios FOR SELECT TO {OWNER_ROLE} USING (true)")
    op.execute(f"CREATE POLICY auth_lookup ON tenants FOR SELECT TO {OWNER_ROLE} USING (true)")
    op.execute(
        """
        CREATE FUNCTION auth_buscar_credenciais(p_email TEXT)
        RETURNS TABLE (usuario_id UUID, tenant_id UUID, senha_hash TEXT, papel VARCHAR)
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT u.id, u.tenant_id, u.senha_hash, u.papel
              FROM usuarios u
              JOIN tenants t ON t.id = u.tenant_id
             WHERE lower(u.email) = lower(p_email)
               AND u.ativo AND t.ativo
        $$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION auth_buscar_credenciais(TEXT) FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION auth_buscar_credenciais(TEXT) TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS auth_buscar_credenciais(TEXT)")
    op.execute("DROP POLICY IF EXISTS auth_lookup ON tenants")
    op.execute("DROP TABLE IF EXISTS usuarios")
    op.execute(
        """
        ALTER TABLE tenants
            DROP COLUMN capacidade_padrao_turma,
            DROP COLUMN antecedencia_cancelamento_horas,
            DROP COLUMN validade_credito_dias,
            DROP COLUMN fuso_horario
        """
    )
