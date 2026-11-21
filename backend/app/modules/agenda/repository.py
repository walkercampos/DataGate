"""Apenas SQL. Travas (FOR UPDATE) e atualizações atômicas ficam aqui; as regras, no service."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

_AG = "id, aula_id, aluno_id, tipo, status, criado_em"
ATIVOS = "('agendado', 'presente', 'falta')"  # status que ocupam vaga


async def config_estudio(session: AsyncSession, tenant_id: UUID) -> RowMapping:
    result = await session.execute(
        text(
            """
            SELECT capacidade_padrao_turma, antecedencia_cancelamento_horas, validade_credito_dias, fuso_horario
              FROM tenants WHERE id = :tid
            """
        ),
        {"tid": tenant_id},
    )
    return result.mappings().one()


async def inserir_aula(
    session: AsyncSession,
    tenant_id: UUID,
    titulo: str,
    inicio: datetime,
    duracao: int,
    capacidade: int,
    tipo: str = "grupo",
) -> UUID:
    result = await session.execute(
        text(
            """
            INSERT INTO aulas (tenant_id, titulo, inicio, duracao_minutos, capacidade, tipo)
            VALUES (:tid, :titulo, :inicio, :duracao, :capacidade, :tipo) RETURNING id
            """
        ),
        {"tid": tenant_id, "titulo": titulo, "inicio": inicio, "duracao": duracao, "capacidade": capacidade, "tipo": tipo},
    )
    return result.scalar_one()


async def inicios_existentes(
    session: AsyncSession, tenant_id: UUID, titulo: str, inicios: list[datetime], tipo: str = "grupo"
) -> set[datetime]:
    result = await session.execute(
        text(
            "SELECT inicio FROM aulas WHERE tenant_id = :tid AND titulo = :titulo AND tipo = :tipo"
            " AND inicio = ANY(:inicios)"
        ),
        {"tid": tenant_id, "titulo": titulo, "tipo": tipo, "inicios": inicios},
    )
    return set(result.scalars().all())


async def listar_aulas(session: AsyncSession, tenant_id: UUID, de: datetime, ate: datetime) -> list[RowMapping]:
    result = await session.execute(
        text(
            f"""
            SELECT a.id, a.titulo, a.tipo, a.inicio, a.duracao_minutos, a.capacidade,
                   count(ag.id) FILTER (WHERE ag.status IN {ATIVOS}) AS ocupadas
              FROM aulas a
              LEFT JOIN agendamentos ag ON ag.aula_id = a.id AND ag.tenant_id = a.tenant_id
             WHERE a.tenant_id = :tid AND a.inicio >= :de AND a.inicio < :ate
             GROUP BY a.id
             ORDER BY a.inicio
            """
        ),
        {"tid": tenant_id, "de": de, "ate": ate},
    )
    return list(result.mappings().all())


async def buscar_aula(session: AsyncSession, tenant_id: UUID, aula_id: UUID) -> RowMapping | None:
    result = await session.execute(
        text(
            f"""
            SELECT a.id, a.titulo, a.tipo, a.inicio, a.duracao_minutos, a.capacidade,
                   (SELECT count(*) FROM agendamentos ag
                     WHERE ag.aula_id = a.id AND ag.tenant_id = a.tenant_id AND ag.status IN {ATIVOS}) AS ocupadas
              FROM aulas a WHERE a.id = :id AND a.tenant_id = :tid
            """
        ),
        {"id": aula_id, "tid": tenant_id},
    )
    return result.mappings().first()


async def participantes(session: AsyncSession, tenant_id: UUID, aula_ids: list[UUID]) -> list[RowMapping]:
    if not aula_ids:
        return []
    result = await session.execute(
        text(
            """
            SELECT ag.aula_id, ag.id AS agendamento_id, ag.aluno_id, al.nome AS aluno_nome, ag.tipo, ag.status
              FROM agendamentos ag
              JOIN alunos al ON al.id = ag.aluno_id AND al.tenant_id = ag.tenant_id
             WHERE ag.tenant_id = :tid AND ag.aula_id = ANY(:ids)
             ORDER BY ag.criado_em
            """
        ),
        {"tid": tenant_id, "ids": aula_ids},
    )
    return list(result.mappings().all())


async def travar_aula(session: AsyncSession, tenant_id: UUID, aula_id: UUID) -> RowMapping | None:
    """SELECT ... FOR UPDATE: agendamentos simultâneos na MESMA aula entram em fila aqui."""
    result = await session.execute(
        text("SELECT id, inicio, capacidade FROM aulas WHERE id = :id AND tenant_id = :tid FOR UPDATE"),
        {"id": aula_id, "tid": tenant_id},
    )
    return result.mappings().first()


async def contar_ocupadas(session: AsyncSession, tenant_id: UUID, aula_id: UUID) -> int:
    result = await session.execute(
        text(f"SELECT count(*) FROM agendamentos WHERE tenant_id = :tid AND aula_id = :id AND status IN {ATIVOS}"),
        {"tid": tenant_id, "id": aula_id},
    )
    return result.scalar_one()


async def contar_agendamentos(session: AsyncSession, tenant_id: UUID, aula_id: UUID) -> int:
    result = await session.execute(
        text("SELECT count(*) FROM agendamentos WHERE tenant_id = :tid AND aula_id = :id"),
        {"tid": tenant_id, "id": aula_id},
    )
    return result.scalar_one()


async def excluir_aula(session: AsyncSession, tenant_id: UUID, aula_id: UUID) -> int:
    result = await session.execute(
        text("DELETE FROM aulas WHERE id = :id AND tenant_id = :tid"), {"id": aula_id, "tid": tenant_id}
    )
    return result.rowcount


async def aluno_ja_na_aula(session: AsyncSession, tenant_id: UUID, aula_id: UUID, aluno_id: UUID) -> bool:
    result = await session.execute(
        text(
            f"""
            SELECT EXISTS (SELECT 1 FROM agendamentos
                            WHERE tenant_id = :tid AND aula_id = :aula AND aluno_id = :aluno AND status IN {ATIVOS})
            """
        ),
        {"tid": tenant_id, "aula": aula_id, "aluno": aluno_id},
    )
    return bool(result.scalar_one())


async def buscar_aluno(session: AsyncSession, tenant_id: UUID, aluno_id: UUID) -> RowMapping | None:
    result = await session.execute(
        text("SELECT id, ativo FROM alunos WHERE id = :id AND tenant_id = :tid"), {"id": aluno_id, "tid": tenant_id}
    )
    return result.mappings().first()


async def consumir_credito(session: AsyncSession, tenant_id: UUID, aluno_id: UUID) -> bool:
    """Débito atômico: só desconta se houver saldo válido. Nunca fica negativo."""
    result = await session.execute(
        text(
            """
            UPDATE alunos SET creditos_reposicao = creditos_reposicao - 1
             WHERE id = :id AND tenant_id = :tid
               AND creditos_reposicao > 0 AND creditos_validade_ate >= now()
            RETURNING id
            """
        ),
        {"id": aluno_id, "tid": tenant_id},
    )
    return result.first() is not None


async def conceder_credito(session: AsyncSession, tenant_id: UUID, aluno_id: UUID, validade_dias: int) -> None:
    """Crédito atômico. Créditos já vencidos são zerados antes de somar o novo."""
    await session.execute(
        text(
            """
            UPDATE alunos
               SET creditos_reposicao = CASE WHEN creditos_validade_ate >= now()
                                             THEN creditos_reposicao ELSE 0 END + 1,
                   creditos_validade_ate = now() + make_interval(days => :dias)
             WHERE id = :id AND tenant_id = :tid
            """
        ),
        {"id": aluno_id, "tid": tenant_id, "dias": validade_dias},
    )


async def inserir_agendamento(
    session: AsyncSession, tenant_id: UUID, aula_id: UUID, aluno_id: UUID, tipo: str, contrato_id: UUID | None = None
) -> RowMapping:
    result = await session.execute(
        text(
            f"""
            INSERT INTO agendamentos (tenant_id, aula_id, aluno_id, tipo, contrato_id)
            VALUES (:tid, :aula, :aluno, :tipo, :contrato) RETURNING {_AG}
            """
        ),
        {"tid": tenant_id, "aula": aula_id, "aluno": aluno_id, "tipo": tipo, "contrato": contrato_id},
    )
    return result.mappings().one()


async def travar_agendamento(session: AsyncSession, tenant_id: UUID, agendamento_id: UUID) -> RowMapping | None:
    """FOR UPDATE: dois cancelamentos simultâneos não geram crédito duplicado."""
    result = await session.execute(
        text(
            """
            SELECT ag.id, ag.aula_id, ag.aluno_id, ag.status, a.inicio
              FROM agendamentos ag
              JOIN aulas a ON a.id = ag.aula_id AND a.tenant_id = ag.tenant_id
             WHERE ag.id = :id AND ag.tenant_id = :tid
               FOR UPDATE OF ag
            """
        ),
        {"id": agendamento_id, "tid": tenant_id},
    )
    return result.mappings().first()


async def atualizar_status(session: AsyncSession, tenant_id: UUID, agendamento_id: UUID, status: str) -> RowMapping:
    result = await session.execute(
        text(
            f"""
            UPDATE agendamentos SET status = :status, atualizado_em = now()
             WHERE id = :id AND tenant_id = :tid RETURNING {_AG}
            """
        ),
        {"status": status, "id": agendamento_id, "tid": tenant_id},
    )
    return result.mappings().one()


async def buscar_aula_por_inicio(
    session: AsyncSession, tenant_id: UUID, inicio: datetime, tipo: str = "grupo"
) -> UUID | None:
    result = await session.execute(
        text(
            "SELECT id FROM aulas WHERE tenant_id = :tid AND inicio = :inicio AND tipo = :tipo"
            " ORDER BY criado_em LIMIT 1"
        ),
        {"tid": tenant_id, "inicio": inicio, "tipo": tipo},
    )
    return result.scalar_one_or_none()


async def cancelar_futuros_do_contrato(
    session: AsyncSession, tenant_id: UUID, contrato_id: UUID, a_partir_de: datetime
) -> int:
    result = await session.execute(
        text(
            """
            UPDATE agendamentos ag SET status = 'cancelado_contrato', atualizado_em = now()
              FROM aulas a
             WHERE a.id = ag.aula_id AND a.tenant_id = ag.tenant_id
               AND ag.tenant_id = :tid AND ag.contrato_id = :contrato
               AND ag.status = 'agendado' AND a.inicio >= :desde
            """
        ),
        {"tid": tenant_id, "contrato": contrato_id, "desde": a_partir_de},
    )
    return result.rowcount
