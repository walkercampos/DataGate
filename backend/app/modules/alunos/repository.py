"""Apenas SQL. Sem regra de negócio."""

from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

_COLUNAS = "id, nome, telefone, email, observacoes, ativo, creditos_reposicao, creditos_validade_ate, criado_em"
_EDITAVEIS = ("nome", "telefone", "email", "observacoes", "ativo")


async def inserir(session: AsyncSession, tenant_id: UUID, dados: dict[str, Any]) -> RowMapping:
    result = await session.execute(
        text(
            f"""
            INSERT INTO alunos (tenant_id, nome, telefone, email, observacoes)
            VALUES (:tid, :nome, :telefone, :email, :observacoes)
            RETURNING {_COLUNAS}
            """
        ),
        {"tid": tenant_id, **dados},
    )
    return result.mappings().one()


async def listar(session: AsyncSession, tenant_id: UUID, busca: str | None, apenas_ativos: bool) -> list[RowMapping]:
    result = await session.execute(
        text(
            f"""
            SELECT {_COLUNAS} FROM alunos
             WHERE tenant_id = :tid
               AND (CAST(:busca AS text) IS NULL
                    OR nome ILIKE '%' || CAST(:busca AS text) || '%'
                    OR telefone ILIKE '%' || CAST(:busca AS text) || '%')
               AND (NOT CAST(:apenas_ativos AS boolean) OR ativo)
             ORDER BY nome
            """
        ),
        {"tid": tenant_id, "busca": busca, "apenas_ativos": apenas_ativos},
    )
    return list(result.mappings().all())


async def buscar(session: AsyncSession, tenant_id: UUID, aluno_id: UUID) -> RowMapping | None:
    result = await session.execute(
        text(f"SELECT {_COLUNAS} FROM alunos WHERE id = :id AND tenant_id = :tid"), {"id": aluno_id, "tid": tenant_id}
    )
    return result.mappings().first()


async def atualizar(session: AsyncSession, tenant_id: UUID, aluno_id: UUID, campos: dict[str, Any]) -> RowMapping | None:
    sets = ", ".join(f"{c} = :{c}" for c in _EDITAVEIS if c in campos)
    params = {c: campos[c] for c in _EDITAVEIS if c in campos}
    result = await session.execute(
        text(f"UPDATE alunos SET {sets} WHERE id = :id AND tenant_id = :tid RETURNING {_COLUNAS}"),
        {**params, "id": aluno_id, "tid": tenant_id},
    )
    return result.mappings().first()
