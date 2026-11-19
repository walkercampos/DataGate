"""Fábrica da aplicação FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.exceptions import register_exception_handlers
from app.modules.agenda.router import router as agenda_router
from app.modules.alunos.router import router as alunos_router
from app.modules.auth.router import router as auth_router
from app.modules.contratos.router import router as contratos_router
from app.modules.estudio.router import router as estudio_router
from app.modules.health.router import router as health_router
from app.modules.planos.router import router as planos_router
from app.modules.prontuario.router import router as prontuario_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await app.state.redis.aclose()
        await app.state.engine.dispose()

    # Blindagem: sem Swagger/ReDoc/OpenAPI em produção.
    docs_kwargs = (
        {"docs_url": None, "redoc_url": None, "openapi_url": None}
        if settings.is_production
        else {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}
    )
    app = FastAPI(title=settings.app_name, lifespan=lifespan, **docs_kwargs)

    app.state.settings = settings
    app.state.engine = create_engine(settings)
    app.state.session_factory = create_session_factory(app.state.engine)
    app.state.redis = Redis.from_url(settings.redis_url.get_secret_value())

    # Frontend (Lovable/localhost) chama a API pelo navegador: CORS restrito por regex.
    # allow_private_network: permite que uma página pública acesse a API rodando em localhost.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=settings.cors_origin_regex,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        allow_private_network=True,
    )

    register_exception_handlers(app)
    for router in (
        health_router, auth_router, estudio_router, alunos_router, planos_router, contratos_router, agenda_router,
        prontuario_router,
    ):
        app.include_router(router)
    return app


app = create_app()
