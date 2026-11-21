"""Engine assíncrono, sessões por requisição e ativação do RLS por tenant."""

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    # Em testes não reaproveitamos conexões entre event loops.
    pool_kwargs = {"poolclass": NullPool} if settings.environment == "test" else {"pool_pre_ping": True}
    return create_async_engine(settings.database_url.get_secret_value(), **pool_kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Uma transação por requisição: commit no sucesso, rollback em qualquer erro."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        async with session.begin():
            yield session


async def set_tenant(session: AsyncSession, tenant_id: UUID) -> None:
    """Equivalente a `SET LOCAL app.current_tenant_id = :tid`.

    `SET LOCAL` não aceita parâmetros bind; `set_config(..., true)` tem o mesmo efeito
    (vale só até o fim da transação atual) e é seguro contra SQL injection.
    O `tenant_id` passado aqui deve vir SEMPRE do JWT autenticado (Fatia 1).
    """
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(UUID(str(tenant_id)))},
    )
