"""Fatia 5 — Prontuário: avaliações e evoluções com assinatura, hash SHA-256 e imutabilidade via trigger.

Revision ID: 0006_prontuario
Revises: 0005_planos_contratos
Create Date: 2026-11-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_prontuario"
down_revision: str | None = "0005_planos_contratos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "saas_app"


def upgrade() -> None:
    op.execute("ALTER TABLE usuarios ADD CONSTRAINT uq_usuarios_tenant_id UNIQUE (tenant_id, id)")
    op.execute("ALTER TABLE agendamentos ADD CONSTRAINT uq_agendamentos_tenant_id UNIQUE (tenant_id, id)")

    op.execute(
        """
        CREATE TABLE prontuario_registros (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            aluno_id        UUID NOT NULL,
            agendamento_id  UUID,
            tipo            VARCHAR(20) NOT NULL CHECK (tipo IN ('avaliacao', 'evolucao')),
            titulo          VARCHAR(150) NOT NULL,
            conteudo        TEXT NOT NULL,
            dor_eva         INT CHECK (dor_eva BETWEEN 0 AND 10),
            autor_id        UUID NOT NULL,
            status          VARCHAR(20) NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'assinado')),
            assinado_por    UUID,
            assinado_em     TIMESTAMPTZ,
            hash_sha256     CHAR(64),
            criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em   TIMESTAMPTZ,
            FOREIGN KEY (tenant_id, aluno_id)       REFERENCES alunos (tenant_id, id),
            FOREIGN KEY (tenant_id, agendamento_id) REFERENCES agendamentos (tenant_id, id),
            FOREIGN KEY (tenant_id, autor_id)       REFERENCES usuarios (tenant_id, id),
            FOREIGN KEY (tenant_id, assinado_por)   REFERENCES usuarios (tenant_id, id),
            CHECK (status = 'rascunho' OR (assinado_por IS NOT NULL AND assinado_em IS NOT NULL AND hash_sha256 IS NOT NULL))
        )
        """
    )
    op.execute("CREATE INDEX ix_prontuario_aluno ON prontuario_registros (tenant_id, aluno_id, criado_em DESC)")
    op.execute("ALTER TABLE prontuario_registros ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE prontuario_registros FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON prontuario_registros
            USING (tenant_id = app_current_tenant())
            WITH CHECK (tenant_id = app_current_tenant())
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON prontuario_registros TO {APP_ROLE}")

    # Hash canônico: jsonb ordena as chaves; datas sempre em UTC com microssegundos.
    op.execute(
        """
        CREATE FUNCTION prontuario_calcular_hash(r prontuario_registros) RETURNS TEXT
        LANGUAGE sql STABLE
        SET search_path = public, pg_temp
        AS $$
            SELECT encode(digest(jsonb_build_object(
                'id', r.id, 'tenant_id', r.tenant_id, 'aluno_id', r.aluno_id,
                'agendamento_id', r.agendamento_id, 'tipo', r.tipo, 'titulo', r.titulo,
                'conteudo', r.conteudo, 'dor_eva', r.dor_eva, 'autor_id', r.autor_id,
                'assinado_por', r.assinado_por,
                'assinado_em', to_char(r.assinado_em AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
            )::text, 'sha256'), 'hex')
        $$
        """
    )
    op.execute(f"GRANT EXECUTE ON FUNCTION prontuario_calcular_hash(prontuario_registros) TO {APP_ROLE}")

    # Trigger de imutabilidade (CFM/CREFITO/LGPD): vale para QUALQUER papel, inclusive o dono.
    op.execute(
        """
        CREATE FUNCTION prontuario_protecao() RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = public, pg_temp
        AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.status = 'assinado' THEN
                    RAISE EXCEPTION 'prontuario_imutavel: registro assinado não pode ser excluído'
                        USING ERRCODE = 'P0001';
                END IF;
                RETURN OLD;
            END IF;

            IF TG_OP = 'INSERT' THEN
                IF NEW.status <> 'rascunho' THEN
                    RAISE EXCEPTION 'prontuario_imutavel: registro deve nascer como rascunho'
                        USING ERRCODE = 'P0001';
                END IF;
                NEW.assinado_por := NULL;
                NEW.assinado_em := NULL;
                NEW.hash_sha256 := NULL;
                RETURN NEW;
            END IF;

            -- UPDATE
            IF OLD.status = 'assinado' THEN
                RAISE EXCEPTION 'prontuario_imutavel: registro assinado não pode ser alterado'
                    USING ERRCODE = 'P0001';
            END IF;
            IF NEW.id <> OLD.id OR NEW.tenant_id <> OLD.tenant_id OR NEW.aluno_id <> OLD.aluno_id
               OR NEW.autor_id <> OLD.autor_id OR NEW.criado_em <> OLD.criado_em THEN
                RAISE EXCEPTION 'prontuario_imutavel: campos de identificação não podem mudar'
                    USING ERRCODE = 'P0001';
            END IF;

            IF NEW.status = 'assinado' THEN
                IF NEW.assinado_por IS NULL THEN
                    RAISE EXCEPTION 'prontuario_imutavel: assinatura exige o usuário que assina'
                        USING ERRCODE = 'P0001';
                END IF;
                NEW.assinado_em := now();
                NEW.hash_sha256 := prontuario_calcular_hash(NEW);
            ELSE
                NEW.assinado_por := NULL;
                NEW.assinado_em := NULL;
                NEW.hash_sha256 := NULL;
            END IF;
            NEW.atualizado_em := now();
            RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_prontuario_protecao
            BEFORE INSERT OR UPDATE OR DELETE ON prontuario_registros
            FOR EACH ROW EXECUTE FUNCTION prontuario_protecao()
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS prontuario_calcular_hash(prontuario_registros)")
    op.execute("DROP TABLE IF EXISTS prontuario_registros")
    op.execute("DROP FUNCTION IF EXISTS prontuario_protecao()")
    op.execute("ALTER TABLE agendamentos DROP CONSTRAINT IF EXISTS uq_agendamentos_tenant_id")
    op.execute("ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS uq_usuarios_tenant_id")
