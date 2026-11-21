"""Apenas SQL. Sem regra de negócio."""

from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession


async def buscar_credenciais(session: AsyncSession, email: str) -> RowMapping | None:
    result = await session.execute(text("SELECT * FROM auth_buscar_credenciais(:email)"), {"email": email})
    return result.mappings().first()


async def inserir_tenant(session: AsyncSession, tenant_id: UUID, nome: str) -> None:
    await session.execute(text("INSERT INTO tenants (id, nome) VALUES (:id, :nome)"), {"id": tenant_id, "nome": nome})


async def inserir_usuario(
    session: AsyncSession, tenant_id: UUID, nome: str, email: str, senha_hash: str, papel: str
) -> UUID:
    result = await session.execute(
        text(
            """
            INSERT INTO usuarios (tenant_id, nome, email, senha_hash, papel)
            VALUES (:tid, :nome, :email, :senha_hash, :papel)
            RETURNING id
            """
        ),
        {"tid": tenant_id, "nome": nome, "email": email, "senha_hash": senha_hash, "papel": papel},
    )
    return result.scalar_one()


async def buscar_usuario(session: AsyncSession, tenant_id: UUID, usuario_id: UUID) -> RowMapping | None:
    result = await session.execute(
        text(
            """
            SELECT u.id, u.nome, u.email, u.papel, u.tenant_id, t.nome AS estudio_nome
              FROM usuarios u
              JOIN tenants t ON t.id = u.tenant_id AND t.id = :tid
             WHERE u.id = :uid AND u.tenant_id = :tid AND u.ativo
            """
        ),
        {"tid": tenant_id, "uid": usuario_id},
    )
    return result.mappings().first()
