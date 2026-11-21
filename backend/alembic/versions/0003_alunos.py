"""Fatia 2 — Alunos.

Revision ID: 0003_alunos
Revises: 0002_auth
Create Date: 2026-11-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_alunos"
down_revision: str | None = "0002_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "saas_app"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE alunos (
            id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id              UUID NOT NULL REFERENCES tenants(id),
            nome                   VARCHAR(150) NOT NULL,
            telefone               VARCHAR(20) NOT NULL,
            email                  VARCHAR(254),
            observacoes            TEXT,
            ativo                  BOOLEAN NOT NULL DEFAULT true,
            -- Créditos só mudam por regra do backend (UPDATE atômico), nunca pelo cliente.
            creditos_reposicao     INT NOT NULL DEFAULT 0 CHECK (creditos_reposicao >= 0),
            creditos_validade_ate  TIMESTAMPTZ,
            criado_em              TIMESTAMPTZ NOT NULL DEFAULT now(),
            -- Permite FKs compostas (tenant_id, id): impossível ligar dados de tenants diferentes.
            UNIQUE (tenant_id, id)
        )
        """
    )
    op.execute("CREATE INDEX ix_alunos_tenant_nome ON alunos (tenant_id, nome)")
    op.execute("ALTER TABLE alunos ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alunos FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON alunos
            USING (tenant_id = app_current_tenant())
            WITH CHECK (tenant_id = app_current_tenant())
        """
    )
    # Sem DELETE: aluno é inativado (histórico clínico precisa ser preservado).
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON alunos TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS alunos")
