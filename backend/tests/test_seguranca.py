"""Blindagem de produção: Swagger desligado e erros sem vazamento de detalhes internos."""

import uuid

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import get_session
from app.main import create_app


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
async def test_swagger_desligado_em_producao(settings: Settings, path: str) -> None:
    app = create_app(settings.model_copy(update={"environment": "production"}))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(path)

    assert resp.status_code == 404
    await app.state.engine.dispose()


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
async def test_swagger_ligado_fora_de_producao(client: AsyncClient, path: str) -> None:
    resp = await client.get(path)
    assert resp.status_code == 200


async def test_erro_interno_retorna_apenas_trace_id(app: FastAPI, client: AsyncClient) -> None:
    # Rota que provoca um erro de banco real citando uma tabela e uma coluna.
    async def rota_com_bug(session: AsyncSession = Depends(get_session)) -> dict:
        await session.execute(text("SELECT coluna_secreta FROM tabela_secreta_pacientes"))
        return {}

    app.add_api_route("/_bug", rota_com_bug)

    resp = await client.get("/_bug")

    assert resp.status_code == 500
    body = resp.json()
    assert set(body) == {"detail", "trace_id"}
    uuid.UUID(body["trace_id"])  # trace_id é um UUID válido
    for vazamento in ("tabela_secreta_pacientes", "coluna_secreta", "Traceback", "sqlalchemy", "asyncpg"):
        assert vazamento not in resp.text


async def test_erro_python_generico_tambem_e_mascarado(app: FastAPI, client: AsyncClient) -> None:
    async def rota_que_explode() -> dict:
        raise ValueError("segredo interno: /etc/app/config")

    app.add_api_route("/_explode", rota_que_explode)

    resp = await client.get("/_explode")

    assert resp.status_code == 500
    assert "segredo interno" not in resp.text
    assert "ValueError" not in resp.text
    assert set(resp.json()) == {"detail", "trace_id"}
