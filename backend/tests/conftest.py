"""Infra de testes: SEMPRE contra o banco saas_pilates_test, com o papel sem privilégios da API."""

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


class _TestEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    test_database_url: SecretStr
    test_migration_database_url: SecretStr
    test_redis_url: SecretStr = SecretStr("redis://localhost:6379/15")


_env = _TestEnv()  # type: ignore[call-arg]
TEST_DB_URL = _env.test_database_url.get_secret_value()
TEST_MIGRATION_URL = _env.test_migration_database_url.get_secret_value()

for _url in (TEST_DB_URL, TEST_MIGRATION_URL):
    if make_url(_url).database != "saas_pilates_test":
        raise RuntimeError("Testes só podem rodar no banco 'saas_pilates_test'. Confira TEST_*_DATABASE_URL.")

# Precisa acontecer ANTES de importar app.main (que instancia a app no import).
os.environ.update(
    ENVIRONMENT="test",
    DATABASE_URL=TEST_DB_URL,
    MIGRATION_DATABASE_URL=TEST_MIGRATION_URL,
    REDIS_URL=_env.test_redis_url.get_secret_value(),
)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.core.database import create_engine, create_session_factory  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    """Recria o schema do zero via Alembic (downgrade base -> upgrade head) a cada execução."""
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = TEST_MIGRATION_URL
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    yield
    # Limpeza com o papel dono (a API não tem permissão de TRUNCATE).
    engine = create_async_engine(TEST_MIGRATION_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE tenants, eventos_processados"))
    await engine.dispose()


@pytest.fixture
def settings() -> Settings:
    return Settings(environment="test")  # type: ignore[call-arg]


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    # raise_app_exceptions=False: queremos ver a resposta 500 que o cliente real recebe.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await app.state.redis.aclose()
    await app.state.engine.dispose()


@pytest.fixture
async def app_engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    """Engine com o MESMO papel da API (saas_app) para testar RLS direto no banco."""
    engine = create_engine(settings)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(app_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(app_engine)
