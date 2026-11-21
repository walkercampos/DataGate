"""Apenas SQL. Sem regra de negócio."""

from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

_COLUNAS = "id, nome, aulas_por_semana, valor_mensal, ativo, criado_em"
_EDITAVEIS = ("nome", "aulas_por_semana", "valor_mensal", "ativo")


async def inserir(session: AsyncSession, tenant_id: UUID, dados: dict[str, Any]) -> RowMapping:
    result = await session.execute(
        text(
            f"""
            INSERT INTO planos (tenant_id, nome, aulas_por_semana, valor_mensal)
            VALUES (:tid, :nome, :aulas_por_semana, :valor_mensal) RETURNING {_COLUNAS}
            """
        ),
        {"tid": tenant_id, **dados},
    )
    return result.mappings().one()


async def listar(session: AsyncSession, tenant_id: UUID, apenas_ativos: bool) -> list[RowMapping]:
    result = await session.execute(
        text(
            f"""
            SELECT {_COLUNAS} FROM planos
             WHERE tenant_id = :tid AND (NOT CAST(:apenas_ativos AS boolean) OR ativo)
             ORDER BY aulas_por_semana, nome
            """
        ),
        {"tid": tenant_id, "apenas_ativos": apenas_ativos},
    )
    return list(result.mappings().all())


async def buscar(session: AsyncSession, tenant_id: UUID, plano_id: UUID) -> RowMapping | None:
    result = await session.execute(
        text(f"SELECT {_COLUNAS} FROM planos WHERE id = :id AND tenant_id = :tid"), {"id": plano_id, "tid": tenant_id}
    )
    return result.mappings().first()


async def atualizar(session: AsyncSession, tenant_id: UUID, plano_id: UUID, campos: dict[str, Any]) -> RowMapping | None:
    sets = ", ".join(f"{c} = :{c}" for c in _EDITAVEIS if c in campos)
    params = {c: campos[c] for c in _EDITAVEIS if c in campos}
    result = await session.execute(
        text(f"UPDATE planos SET {sets} WHERE id = :id AND tenant_id = :tid RETURNING {_COLUNAS}"),
        {**params, "id": plano_id, "tid": tenant_id},
    )
    return result.mappings().first()
