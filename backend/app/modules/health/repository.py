"""Apenas acesso a infraestrutura (banco e Redis). Sem regra de negócio."""

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def ping_database(session: AsyncSession) -> bool:
    result = await session.execute(text("SELECT 1"))
    return result.scalar_one() == 1


async def ping_redis(redis: Redis) -> bool:
    return bool(await redis.ping())
