"""Fatia 3 — Agenda: aulas (turmas com capacidade) e agendamentos.

Revision ID: 0004_agenda
Revises: 0003_alunos
Create Date: 2026-11-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_agenda"
down_revision: str | None = "0003_alunos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "saas_app"


def _rls(tabela: str) -> None:
    op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {tabela} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {tabela}
            USING (tenant_id = app_current_tenant())
            WITH CHECK (tenant_id = app_current_tenant())
        """
    )


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE aulas (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id         UUID NOT NULL REFERENCES tenants(id),
            titulo            VARCHAR(100) NOT NULL DEFAULT 'Pilates',
            inicio            TIMESTAMPTZ NOT NULL,
            duracao_minutos   INT NOT NULL CHECK (duracao_minutos BETWEEN 10 AND 240),
            capacidade        INT NOT NULL CHECK (capacidade BETWEEN 1 AND 50),
            criado_em         TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, id)
        )
        """
    )
    op.execute("CREATE INDEX ix_aulas_tenant_inicio ON aulas (tenant_id, inicio)")
    _rls("aulas")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON aulas TO {APP_ROLE}")

    op.execute(
        """
        CREATE TABLE agendamentos (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     UUID NOT NULL REFERENCES tenants(id),
            aula_id       UUID NOT NULL,
            aluno_id      UUID NOT NULL,
            tipo          VARCHAR(20) NOT NULL DEFAULT 'regular' CHECK (tipo IN ('regular', 'reposicao')),
            status        VARCHAR(30) NOT NULL DEFAULT 'agendado' CHECK (status IN (
                              'agendado', 'cancelado_com_credito', 'cancelado_sem_credito', 'presente', 'falta')),
            criado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ,
            -- FKs compostas: aula e aluno precisam ser do MESMO tenant do agendamento.
            FOREIGN KEY (tenant_id, aula_id)  REFERENCES aulas  (tenant_id, id),
            FOREIGN KEY (tenant_id, aluno_id) REFERENCES alunos (tenant_id, id)
        )
        """
    )
    # Um aluno não pode ocupar duas vagas na mesma aula.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_agendamento_ativo ON agendamentos (aula_id, aluno_id)
            WHERE status IN ('agendado', 'presente', 'falta')
        """
    )
    op.execute("CREATE INDEX ix_agendamentos_aula ON agendamentos (tenant_id, aula_id)")
    op.execute("CREATE INDEX ix_agendamentos_aluno ON agendamentos (tenant_id, aluno_id)")
    _rls("agendamentos")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON agendamentos TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agendamentos")
    op.execute("DROP TABLE IF EXISTS aulas")
