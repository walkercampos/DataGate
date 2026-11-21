"""Fatia 4 — Planos, contratos (matrículas) com horários fixos e vínculo agendamento↔contrato.

Revision ID: 0005_planos_contratos
Revises: 0004_agenda
Create Date: 2026-11-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_planos_contratos"
down_revision: str | None = "0004_agenda"
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
        CREATE TABLE planos (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id         UUID NOT NULL REFERENCES tenants(id),
            nome              VARCHAR(100) NOT NULL,
            aulas_por_semana  INT NOT NULL CHECK (aulas_por_semana BETWEEN 1 AND 7),
            valor_mensal      NUMERIC(10, 2) NOT NULL CHECK (valor_mensal >= 0),
            ativo             BOOLEAN NOT NULL DEFAULT true,
            criado_em         TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, id)
        )
        """
    )
    _rls("planos")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON planos TO {APP_ROLE}")

    op.execute(
        """
        CREATE TABLE contratos (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id         UUID NOT NULL REFERENCES tenants(id),
            aluno_id          UUID NOT NULL,
            plano_id          UUID NOT NULL,
            -- Cópia do plano no momento da contratação (preço/frequência vêm do banco, nunca do cliente).
            aulas_por_semana  INT NOT NULL,
            valor_mensal      NUMERIC(10, 2) NOT NULL,
            data_inicio       DATE NOT NULL,
            data_fim          DATE,
            status            VARCHAR(20) NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'encerrado')),
            criado_em         TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, id),
            FOREIGN KEY (tenant_id, aluno_id) REFERENCES alunos (tenant_id, id),
            FOREIGN KEY (tenant_id, plano_id) REFERENCES planos (tenant_id, id)
        )
        """
    )
    # Um aluno tem no máximo um contrato ativo.
    op.execute("CREATE UNIQUE INDEX uq_contrato_ativo ON contratos (tenant_id, aluno_id) WHERE status = 'ativo'")
    _rls("contratos")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON contratos TO {APP_ROLE}")

    op.execute(
        """
        CREATE TABLE contrato_horarios (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id    UUID NOT NULL REFERENCES tenants(id),
            contrato_id  UUID NOT NULL,
            dia_semana   INT NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
            hora         TIME NOT NULL,
            UNIQUE (contrato_id, dia_semana, hora),
            FOREIGN KEY (tenant_id, contrato_id) REFERENCES contratos (tenant_id, id)
        )
        """
    )
    _rls("contrato_horarios")
    op.execute(f"GRANT SELECT, INSERT ON contrato_horarios TO {APP_ROLE}")

    op.execute("ALTER TABLE agendamentos ADD COLUMN contrato_id UUID")
    op.execute(
        """
        ALTER TABLE agendamentos ADD CONSTRAINT fk_agendamento_contrato
            FOREIGN KEY (tenant_id, contrato_id) REFERENCES contratos (tenant_id, id)
        """
    )
    op.execute("ALTER TABLE agendamentos DROP CONSTRAINT agendamentos_status_check")
    op.execute(
        """
        ALTER TABLE agendamentos ADD CONSTRAINT agendamentos_status_check CHECK (status IN (
            'agendado', 'cancelado_com_credito', 'cancelado_sem_credito', 'cancelado_contrato', 'presente', 'falta'))
        """
    )


def downgrade() -> None:
    op.execute("UPDATE agendamentos SET status = 'cancelado_sem_credito' WHERE status = 'cancelado_contrato'")
    op.execute("ALTER TABLE agendamentos DROP CONSTRAINT agendamentos_status_check")
    op.execute(
        """
        ALTER TABLE agendamentos ADD CONSTRAINT agendamentos_status_check CHECK (status IN (
            'agendado', 'cancelado_com_credito', 'cancelado_sem_credito', 'presente', 'falta'))
        """
    )
    op.execute("ALTER TABLE agendamentos DROP CONSTRAINT fk_agendamento_contrato")
    op.execute("ALTER TABLE agendamentos DROP COLUMN contrato_id")
    op.execute("DROP TABLE IF EXISTS contrato_horarios")
    op.execute("DROP TABLE IF EXISTS contratos")
    op.execute("DROP TABLE IF EXISTS planos")
