"""Configurações da aplicação, lidas exclusivamente do ambiente / arquivo .env."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "SaaS Pilates & Fisio API"

    # Conexão da API: papel SEM superusuário e SEM BYPASSRLS (RLS sempre ativo).
    database_url: SecretStr
    # Conexão das migrações: papel dono das tabelas (DDL). Nunca usado pela API.
    migration_database_url: SecretStr

    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")

    # JWT: segredo SEMPRE no .env (gere com: python -c "import secrets;print(secrets.token_urlsafe(48))")
    jwt_secret: SecretStr
    jwt_expira_minutos: int = 480

    # Origens liberadas no CORS (regex). O frontend oficial usa o mesmo domínio (/api via nginx),
    # então só o desenvolvimento local precisa de CORS.
    cors_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
