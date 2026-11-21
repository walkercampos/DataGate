"""Regra: o serviço só está saudável se banco E Redis responderem."""

import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.health import repository
from app.modules.health.schemas import HealthOut

logger = logging.getLogger("app.health")


async def check_health(session: AsyncSession, redis: Redis) -> HealthOut:
    try:
        db_ok = await repository.ping_database(session)
    except Exception:
        logger.exception("Health: banco indisponível")
        db_ok = False
    try:
        redis_ok = await repository.ping_redis(redis)
    except Exception:
        logger.exception("Health: Redis indisponível")
        redis_ok = False

    return HealthOut(
        status="ok" if db_ok and redis_ok else "erro",
        database="ok" if db_ok else "erro",
        redis="ok" if redis_ok else "erro",
    )
