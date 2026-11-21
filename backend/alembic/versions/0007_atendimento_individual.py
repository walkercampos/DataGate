"""Fatia 7 — Atendimentos individuais (1:1) ao lado das turmas.

Revision ID: 0007_atendimento_individual
Revises: 0006_prontuario
Create Date: 2026-11-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_atendimento_individual"
down_revision: str | None = "0006_prontuario"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE aulas
            ADD COLUMN tipo VARCHAR(20) NOT NULL DEFAULT 'grupo' CHECK (tipo IN ('grupo', 'individual'))
        """
    )
    # Garantia no banco: atendimento individual comporta exatamente 1 pessoa.
    op.execute("ALTER TABLE aulas ADD CONSTRAINT ck_individual_capacidade CHECK (tipo <> 'individual' OR capacidade = 1)")


def downgrade() -> None:
    op.execute("ALTER TABLE aulas DROP CONSTRAINT IF EXISTS ck_individual_capacidade")
    op.execute("ALTER TABLE aulas DROP COLUMN IF EXISTS tipo")
