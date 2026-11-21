from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


async def test_health_ok_com_banco_e_redis(client: AsyncClient) -> None:
    resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "ok", "redis": "ok"}


async def test_health_retorna_503_quando_redis_cai(settings: Settings) -> None:
    quebrado = settings.model_copy(update={"redis_url": SecretStr("redis://localhost:1/0")})
    app = create_app(quebrado)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/health")

    assert resp.status_code == 503
    assert resp.json() == {"status": "erro", "database": "ok", "redis": "erro"}
    await app.state.engine.dispose()
