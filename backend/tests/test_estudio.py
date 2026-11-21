from httpx import AsyncClient


async def test_configuracao_padrao_e_atualizacao(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    est = await registrar("Studio Config")
    h = est["headers"]

    cfg = (await client.get("/estudio", headers=h)).json()
    assert cfg["nome"] == "Studio Config"
    assert cfg["capacidade_padrao_turma"] == 4
    assert cfg["antecedencia_cancelamento_horas"] == 3
    assert cfg["validade_credito_dias"] == 30
    assert cfg["fuso_horario"] == "America/Sao_Paulo"

    resp = await client.patch("/estudio", headers=h, json={"capacidade_padrao_turma": 3, "antecedencia_cancelamento_horas": 6})
    assert resp.status_code == 200
    assert resp.json()["capacidade_padrao_turma"] == 3
    assert resp.json()["antecedencia_cancelamento_horas"] == 6


async def test_configuracao_invalida_retorna_422(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    assert (await client.patch("/estudio", headers=h, json={"capacidade_padrao_turma": 0})).status_code == 422
    assert (await client.patch("/estudio", headers=h, json={"fuso_horario": "Marte/Base"})).status_code == 422


async def test_cada_estudio_ve_apenas_a_propria_configuracao(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    a = await registrar("Studio A")
    b = await registrar("Studio B")
    await client.patch("/estudio", headers=a["headers"], json={"nome": "Studio A Renomeado"})

    assert (await client.get("/estudio", headers=b["headers"])).json()["nome"] == "Studio B"
