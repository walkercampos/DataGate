from httpx import AsyncClient

ALUNO = {"nome": "Maria Souza", "telefone": "(11) 98765-4321", "email": "Maria@Email.com"}


async def test_crud_de_alunos(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]

    criado = await client.post("/alunos", headers=h, json=ALUNO)
    assert criado.status_code == 201
    aluno = criado.json()
    assert aluno["email"] == "maria@email.com"
    assert aluno["creditos_reposicao"] == 0
    assert aluno["ativo"] is True

    await client.post("/alunos", headers=h, json={"nome": "João Lima", "telefone": "11912345678"})
    assert [a["nome"] for a in (await client.get("/alunos", headers=h)).json()] == ["João Lima", "Maria Souza"]
    assert [a["nome"] for a in (await client.get("/alunos?busca=mar", headers=h)).json()] == ["Maria Souza"]

    assert (await client.get(f"/alunos/{aluno['id']}", headers=h)).json()["nome"] == "Maria Souza"

    editado = await client.patch(f"/alunos/{aluno['id']}", headers=h, json={"telefone": "11900000000", "ativo": False})
    assert editado.status_code == 200
    assert editado.json()["telefone"] == "11900000000"
    assert [a["nome"] for a in (await client.get("/alunos", headers=h)).json()] == ["João Lima"]
    assert len((await client.get("/alunos?apenas_ativos=false", headers=h)).json()) == 2


async def test_cliente_nao_consegue_alterar_creditos(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno = (await client.post("/alunos", headers=h, json={**ALUNO, "creditos_reposicao": 50})).json()
    assert aluno["creditos_reposicao"] == 0

    resp = await client.patch(f"/alunos/{aluno['id']}", headers=h, json={"creditos_reposicao": 99})
    assert resp.json()["creditos_reposicao"] == 0


async def test_validacao_de_entrada(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    assert (await client.post("/alunos", headers=h, json={"nome": "A", "telefone": "123"})).status_code == 422
    assert (await client.post("/alunos", headers=h, json={**ALUNO, "email": "nao-e-email"})).status_code == 422
    assert (await client.get("/alunos/nao-e-uuid", headers=h)).status_code == 422


async def test_estudio_nao_acessa_alunos_de_outro(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    a = await registrar("Studio A")
    b = await registrar("Studio B")
    aluno_a = (await client.post("/alunos", headers=a["headers"], json=ALUNO)).json()

    assert (await client.get("/alunos", headers=b["headers"])).json() == []
    assert (await client.get(f"/alunos/{aluno_a['id']}", headers=b["headers"])).status_code == 404
    patch = await client.patch(f"/alunos/{aluno_a['id']}", headers=b["headers"], json={"nome": "Invadido"})
    assert patch.status_code == 404
    assert (await client.get(f"/alunos/{aluno_a['id']}", headers=a["headers"])).json()["nome"] == "Maria Souza"
