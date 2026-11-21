"""Apenas SQL. Hash e bloqueio de alteração ficam no banco (função + trigger)."""

from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

_SELECT = """
    SELECT r.id, r.aluno_id, r.agendamento_id, r.tipo, r.titulo, r.conteudo, r.dor_eva,
           r.autor_id, ua.nome AS autor_nome, r.status, r.assinado_por, us.nome AS assinado_por_nome,
           r.assinado_em, r.hash_sha256, r.criado_em, r.atualizado_em
      FROM prontuario_registros r
      JOIN usuarios ua ON ua.id = r.autor_id AND ua.tenant_id = r.tenant_id
      LEFT JOIN usuarios us ON us.id = r.assinado_por AND us.tenant_id = r.tenant_id
"""
_EDITAVEIS = ("titulo", "conteudo", "dor_eva")


async def aluno_existe(session: AsyncSession, tenant_id: UUID, aluno_id: UUID) -> bool:
    result = await session.execute(
        text("SELECT EXISTS (SELECT 1 FROM alunos WHERE id = :id AND tenant_id = :tid)"), {"id": aluno_id, "tid": tenant_id}
    )
    return bool(result.scalar_one())


async def agendamento_do_aluno(session: AsyncSession, tenant_id: UUID, agendamento_id: UUID, aluno_id: UUID) -> bool:
    result = await session.execute(
        text("SELECT EXISTS (SELECT 1 FROM agendamentos WHERE id = :id AND tenant_id = :tid AND aluno_id = :aluno)"),
        {"id": agendamento_id, "tid": tenant_id, "aluno": aluno_id},
    )
    return bool(result.scalar_one())


async def inserir(session: AsyncSession, tenant_id: UUID, aluno_id: UUID, autor_id: UUID, dados: dict[str, Any]) -> UUID:
    result = await session.execute(
        text(
            """
            INSERT INTO prontuario_registros (tenant_id, aluno_id, autor_id, tipo, titulo, conteudo, dor_eva, agendamento_id)
            VALUES (:tid, :aluno, :autor, :tipo, :titulo, :conteudo, :dor_eva, :agendamento_id) RETURNING id
            """
        ),
        {"tid": tenant_id, "aluno": aluno_id, "autor": autor_id, **dados},
    )
    return result.scalar_one()


async def buscar(session: AsyncSession, tenant_id: UUID, registro_id: UUID) -> RowMapping | None:
    result = await session.execute(text(_SELECT + " WHERE r.id = :id AND r.tenant_id = :tid"), {"id": registro_id, "tid": tenant_id})
    return result.mappings().first()


async def listar_do_aluno(session: AsyncSession, tenant_id: UUID, aluno_id: UUID) -> list[RowMapping]:
    result = await session.execute(
        text(_SELECT + " WHERE r.aluno_id = :aluno AND r.tenant_id = :tid ORDER BY r.criado_em DESC"),
        {"aluno": aluno_id, "tid": tenant_id},
    )
    return list(result.mappings().all())


async def travar_status(session: AsyncSession, tenant_id: UUID, registro_id: UUID) -> str | None:
    result = await session.execute(
        text("SELECT status FROM prontuario_registros WHERE id = :id AND tenant_id = :tid FOR UPDATE"),
        {"id": registro_id, "tid": tenant_id},
    )
    return result.scalar_one_or_none()


async def atualizar(session: AsyncSession, tenant_id: UUID, registro_id: UUID, campos: dict[str, Any]) -> None:
    sets = ", ".join(f"{c} = :{c}" for c in _EDITAVEIS if c in campos)
    params = {c: campos[c] for c in _EDITAVEIS if c in campos}
    await session.execute(
        text(f"UPDATE prontuario_registros SET {sets} WHERE id = :id AND tenant_id = :tid"),
        {**params, "id": registro_id, "tid": tenant_id},
    )


async def assinar(session: AsyncSession, tenant_id: UUID, registro_id: UUID, usuario_id: UUID) -> None:
    # assinado_em e hash_sha256 são preenchidos pelo trigger, não pela aplicação.
    await session.execute(
        text(
            """
            UPDATE prontuario_registros SET status = 'assinado', assinado_por = :uid
             WHERE id = :id AND tenant_id = :tid
            """
        ),
        {"uid": usuario_id, "id": registro_id, "tid": tenant_id},
    )


async def excluir(session: AsyncSession, tenant_id: UUID, registro_id: UUID) -> None:
    await session.execute(
        text("DELETE FROM prontuario_registros WHERE id = :id AND tenant_id = :tid"), {"id": registro_id, "tid": tenant_id}
    )


async def verificar_hash(session: AsyncSession, tenant_id: UUID, registro_id: UUID) -> RowMapping | None:
    result = await session.execute(
        text(
            """
            SELECT r.id, r.status, r.hash_sha256 AS hash_registrado, prontuario_calcular_hash(r) AS hash_recalculado
              FROM prontuario_registros r WHERE r.id = :id AND r.tenant_id = :tid
            """
        ),
        {"id": registro_id, "tid": tenant_id},
    )
    return result.mappings().first()
