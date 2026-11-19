"""Apenas SQL. Sem regra de negócio."""

from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

_COLUNAS = "id, nome, capacidade_padrao_turma, antecedencia_cancelamento_horas, validade_credito_dias, fuso_horario"
# Lista fechada de colunas editáveis: o nome da coluna NUNCA vem do cliente.
_EDITAVEIS = ("nome", "capacidade_padrao_turma", "antecedencia_cancelamento_horas", "validade_credito_dias", "fuso_horario")


async def buscar(session: AsyncSession, tenant_id: UUID) -> RowMapping | None:
    result = await session.execute(text(f"SELECT {_COLUNAS} FROM tenants WHERE id = :tid"), {"tid": tenant_id})
    return result.mappings().first()


async def atualizar(session: AsyncSession, tenant_id: UUID, campos: dict[str, Any]) -> RowMapping | None:
    sets = ", ".join(f"{c} = :{c}" for c in _EDITAVEIS if c in campos)
    params = {c: campos[c] for c in _EDITAVEIS if c in campos}
    result = await session.execute(
        text(f"UPDATE tenants SET {sets} WHERE id = :tid RETURNING {_COLUNAS}"), {**params, "tid": tenant_id}
    )
    return result.mappings().first()
