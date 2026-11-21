"""Apenas SQL. Sem regra de negócio."""

from datetime import date, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

_SELECT = """
    SELECT c.id, c.aluno_id, al.nome AS aluno_nome, c.plano_id, p.nome AS plano_nome,
           c.aulas_por_semana, c.valor_mensal, c.data_inicio, c.data_fim, c.status, c.criado_em
      FROM contratos c
      JOIN alunos al ON al.id = c.aluno_id AND al.tenant_id = c.tenant_id
      JOIN planos p  ON p.id = c.plano_id  AND p.tenant_id = c.tenant_id
"""


async def buscar_aluno(session: AsyncSession, tenant_id: UUID, aluno_id: UUID) -> RowMapping | None:
    result = await session.execute(
        text("SELECT id, nome, ativo FROM alunos WHERE id = :id AND tenant_id = :tid"), {"id": aluno_id, "tid": tenant_id}
    )
    return result.mappings().first()


async def buscar_plano(session: AsyncSession, tenant_id: UUID, plano_id: UUID) -> RowMapping | None:
    result = await session.execute(
        text("SELECT id, nome, aulas_por_semana, valor_mensal, ativo FROM planos WHERE id = :id AND tenant_id = :tid"),
        {"id": plano_id, "tid": tenant_id},
    )
    return result.mappings().first()


async def aluno_tem_contrato_ativo(session: AsyncSession, tenant_id: UUID, aluno_id: UUID) -> bool:
    result = await session.execute(
        text("SELECT EXISTS (SELECT 1 FROM contratos WHERE tenant_id = :tid AND aluno_id = :id AND status = 'ativo')"),
        {"tid": tenant_id, "id": aluno_id},
    )
    return bool(result.scalar_one())


async def inserir(
    session: AsyncSession,
    tenant_id: UUID,
    aluno_id: UUID,
    plano_id: UUID,
    aulas_por_semana: int,
    valor_mensal: Decimal,
    data_inicio: date,
) -> UUID:
    result = await session.execute(
        text(
            """
            INSERT INTO contratos (tenant_id, aluno_id, plano_id, aulas_por_semana, valor_mensal, data_inicio)
            VALUES (:tid, :aluno, :plano, :aps, :valor, :inicio) RETURNING id
            """
        ),
        {"tid": tenant_id, "aluno": aluno_id, "plano": plano_id, "aps": aulas_por_semana, "valor": valor_mensal, "inicio": data_inicio},
    )
    return result.scalar_one()


async def inserir_horario(session: AsyncSession, tenant_id: UUID, contrato_id: UUID, dia_semana: int, hora: time) -> None:
    await session.execute(
        text("INSERT INTO contrato_horarios (tenant_id, contrato_id, dia_semana, hora) VALUES (:tid, :c, :d, :h)"),
        {"tid": tenant_id, "c": contrato_id, "d": dia_semana, "h": hora},
    )


async def buscar(session: AsyncSession, tenant_id: UUID, contrato_id: UUID) -> RowMapping | None:
    result = await session.execute(
        text(_SELECT + " WHERE c.id = :id AND c.tenant_id = :tid"), {"id": contrato_id, "tid": tenant_id}
    )
    return result.mappings().first()


async def listar(
    session: AsyncSession, tenant_id: UUID, aluno_id: UUID | None, status: str | None
) -> list[RowMapping]:
    result = await session.execute(
        text(
            _SELECT
            + """
             WHERE c.tenant_id = :tid
               AND (CAST(:aluno AS uuid) IS NULL OR c.aluno_id = CAST(:aluno AS uuid))
               AND (CAST(:status AS text) IS NULL OR c.status = CAST(:status AS text))
             ORDER BY c.status, al.nome
            """
        ),
        {"tid": tenant_id, "aluno": aluno_id, "status": status},
    )
    return list(result.mappings().all())


async def horarios(session: AsyncSession, tenant_id: UUID, contrato_ids: list[UUID]) -> list[RowMapping]:
    if not contrato_ids:
        return []
    result = await session.execute(
        text(
            """
            SELECT contrato_id, dia_semana, hora FROM contrato_horarios
             WHERE tenant_id = :tid AND contrato_id = ANY(:ids) ORDER BY dia_semana, hora
            """
        ),
        {"tid": tenant_id, "ids": contrato_ids},
    )
    return list(result.mappings().all())


async def travar(session: AsyncSession, tenant_id: UUID, contrato_id: UUID) -> RowMapping | None:
    result = await session.execute(
        text("SELECT id, status, data_inicio FROM contratos WHERE id = :id AND tenant_id = :tid FOR UPDATE"),
        {"id": contrato_id, "tid": tenant_id},
    )
    return result.mappings().first()


async def encerrar(session: AsyncSession, tenant_id: UUID, contrato_id: UUID, data_fim: date) -> None:
    await session.execute(
        text("UPDATE contratos SET status = 'encerrado', data_fim = :fim WHERE id = :id AND tenant_id = :tid"),
        {"fim": data_fim, "id": contrato_id, "tid": tenant_id},
    )


async def ids_ativos(session: AsyncSession, tenant_id: UUID) -> list[UUID]:
    result = await session.execute(
        text("SELECT id FROM contratos WHERE tenant_id = :tid AND status = 'ativo' ORDER BY criado_em"),
        {"tid": tenant_id},
    )
    return list(result.scalars().all())
