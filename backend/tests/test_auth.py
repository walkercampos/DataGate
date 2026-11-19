import jwt
from httpx import AsyncClient

from app.core.config import Settings
from app.core.security import criar_token


async def test_registrar_cria_estudio_e_devolve_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/registrar",
        json={"nome_estudio": "Studio Equilíbrio", "nome": "Ana", "email": "Ana@Equilibrio.com.br", "senha": "senha-forte-123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["usuario"]["email"] == "ana@equilibrio.com.br"
    assert body["usuario"]["papel"] == "admin"
    assert body["usuario"]["estudio_nome"] == "Studio Equilíbrio"
    assert "senha" not in resp.text and "senha_hash" not in resp.text

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == body["usuario"]["id"]


async def test_tenant_id_enviado_pelo_cliente_e_ignorado(client: AsyncClient) -> None:
    falso = "00000000-0000-0000-0000-000000000001"
    resp = await client.post(
        "/auth/registrar",
        json={"nome_estudio": "Studio X", "nome": "Ana", "email": "x@estudio.com.br", "senha": "senha-forte-123", "tenant_id": falso},
    )
    assert resp.status_code == 201
    assert resp.json()["usuario"]["tenant_id"] != falso


async def test_email_duplicado_retorna_409(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    est = await registrar()
    resp = await client.post(
        "/auth/registrar",
        json={"nome_estudio": "Outro", "nome": "Bia", "email": est["email"].upper(), "senha": "senha-forte-123"},
    )
    assert resp.status_code == 409


async def test_login_ok_e_erros_com_mesma_mensagem(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    est = await registrar()

    ok = await client.post("/auth/login", json={"email": est["email"], "senha": "senha-forte-123"})
    assert ok.status_code == 200
    assert ok.json()["usuario"]["tenant_id"] == est["usuario"]["tenant_id"]

    senha_errada = await client.post("/auth/login", json={"email": est["email"], "senha": "errada-123"})
    inexistente = await client.post("/auth/login", json={"email": "ninguem@estudio.com.br", "senha": "errada-123"})
    assert senha_errada.status_code == inexistente.status_code == 401
    assert senha_errada.json() == inexistente.json()  # não revela se o e-mail existe


async def test_rotas_protegidas_exigem_token_valido(client: AsyncClient, settings: Settings, registrar) -> None:  # type: ignore[no-untyped-def]
    est = await registrar()
    u = est["usuario"]

    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.get("/alunos", headers={"Authorization": "Bearer lixo"})).status_code == 401

    outro_segredo = jwt.encode({"sub": u["id"], "tid": u["tenant_id"], "exp": 9999999999}, "segredo-do-atacante", algorithm="HS256")
    assert (await client.get("/alunos", headers={"Authorization": f"Bearer {outro_segredo}"})).status_code == 401

    expirado = criar_token(settings.model_copy(update={"jwt_expira_minutos": -1}), u["id"], u["tenant_id"], "admin")
    assert (await client.get("/alunos", headers={"Authorization": f"Bearer {expirado}"})).status_code == 401

    sem_alg = jwt.encode({"sub": u["id"], "tid": u["tenant_id"], "exp": 9999999999}, None, algorithm="none")
    assert (await client.get("/alunos", headers={"Authorization": f"Bearer {sem_alg}"})).status_code == 401
