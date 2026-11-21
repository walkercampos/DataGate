import asyncio
from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _futuro(horas: float = 48) -> datetime:
    return datetime.now(UTC) + timedelta(hours=horas)


async def _aluno(client: AsyncClient, h: dict, nome: str = "Aluno") -> str:
    resp = await client.post("/alunos", headers=h, json={"nome": nome, "telefone": "11987654321"})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _aula(client: AsyncClient, h: dict, horas: float = 48) -> dict:
    resp = await client.post("/agenda/aulas", headers=h, json={"inicio": _iso(_futuro(horas))})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _creditos(client: AsyncClient, h: dict, aluno_id: str) -> int:
    return (await client.get(f"/alunos/{aluno_id}", headers=h)).json()["creditos_reposicao"]


async def test_capacidade_vem_do_estudio_e_nao_do_cliente(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    await client.patch("/estudio", headers=h, json={"capacidade_padrao_turma": 3})

    resp = await client.post("/agenda/aulas", headers=h, json={"inicio": _iso(_futuro()), "capacidade": 100})
    assert resp.status_code == 201
    assert resp.json()["capacidade"] == 3
    assert resp.json()["vagas"] == 3


async def test_nao_cria_aula_no_passado(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    resp = await client.post("/agenda/aulas", headers=h, json={"inicio": _iso(_futuro(-1))})
    assert resp.status_code == 400


async def test_grade_recorrente_sem_duplicar(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    hoje = date.today()
    proxima_segunda = hoje + timedelta(days=(7 - hoje.weekday()) or 7)
    payload = {"data_inicio": proxima_segunda.isoformat(), "semanas": 2, "dias_semana": [0, 2], "hora": "07:00"}

    resp = await client.post("/agenda/aulas/recorrentes", headers=h, json=payload)
    assert resp.status_code == 201
    aulas = resp.json()
    assert len(aulas) == 4  # 2 semanas x (segunda + quarta)
    assert all(a["inicio"].endswith("10:00:00Z") for a in aulas)  # 07:00 em São Paulo = 10:00 UTC

    repetido = await client.post("/agenda/aulas/recorrentes", headers=h, json=payload)
    assert repetido.json() == []

    de, ate = proxima_segunda.isoformat() + "T00:00:00-03:00", (proxima_segunda + timedelta(days=14)).isoformat() + "T00:00:00-03:00"
    assert len((await client.get("/agenda/aulas", headers=h, params={"de": de, "ate": ate})).json()) == 4


async def test_lotacao_da_turma(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aula = await _aula(client, h)
    alunos = [await _aluno(client, h, f"Aluno {i}") for i in range(5)]

    for aluno_id in alunos[:4]:
        resp = await client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": aluno_id})
        assert resp.status_code == 201

    lotada = await client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": alunos[4]})
    assert lotada.status_code == 409
    assert "lotada" in lotada.json()["detail"]

    detalhe = (await client.get(f"/agenda/aulas/{aula['id']}", headers=h)).json()
    assert detalhe["ocupadas"] == 4 and detalhe["vagas"] == 0
    assert len(detalhe["participantes"]) == 4


async def test_race_condition_nao_estoura_lotacao(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aula = await _aula(client, h)
    alunos = [await _aluno(client, h, f"Aluno {i}") for i in range(10)]

    respostas = await asyncio.gather(
        *[client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": a}) for a in alunos]
    )

    codigos = sorted(r.status_code for r in respostas)
    assert codigos.count(201) == 4
    assert codigos.count(409) == 6
    assert (await client.get(f"/agenda/aulas/{aula['id']}", headers=h)).json()["ocupadas"] == 4


async def test_aluno_nao_ocupa_duas_vagas_na_mesma_aula(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aula = await _aula(client, h)
    aluno = await _aluno(client, h)

    url = f"/agenda/aulas/{aula['id']}/agendamentos"
    respostas = await asyncio.gather(*[client.post(url, headers=h, json={"aluno_id": aluno}) for _ in range(3)])
    assert sorted(r.status_code for r in respostas) == [201, 409, 409]


async def test_cancelamento_no_prazo_gera_credito_e_libera_vaga(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aula = await _aula(client, h, horas=48)
    aluno = await _aluno(client, h)
    ag = (await client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": aluno})).json()

    resp = await client.post(f"/agenda/agendamentos/{ag['id']}/cancelar", headers=h)
    assert resp.status_code == 200
    assert resp.json()["credito_gerado"] is True
    assert resp.json()["agendamento"]["status"] == "cancelado_com_credito"
    assert await _creditos(client, h, aluno) == 1
    assert (await client.get(f"/agenda/aulas/{aula['id']}", headers=h)).json()["vagas"] == 4

    de_novo = await client.post(f"/agenda/agendamentos/{ag['id']}/cancelar", headers=h)
    assert de_novo.status_code == 409
    assert await _creditos(client, h, aluno) == 1


async def test_cancelamento_fora_do_prazo_perde_a_aula(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aula = await _aula(client, h, horas=1)  # antecedência padrão: 3h
    aluno = await _aluno(client, h)
    ag = (await client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": aluno})).json()

    resp = await client.post(f"/agenda/agendamentos/{ag['id']}/cancelar", headers=h)
    assert resp.json()["credito_gerado"] is False
    assert resp.json()["agendamento"]["status"] == "cancelado_sem_credito"
    assert await _creditos(client, h, aluno) == 0


async def test_cancelamentos_simultaneos_geram_um_unico_credito(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aula = await _aula(client, h)
    aluno = await _aluno(client, h)
    ag = (await client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": aluno})).json()

    respostas = await asyncio.gather(
        *[client.post(f"/agenda/agendamentos/{ag['id']}/cancelar", headers=h) for _ in range(5)]
    )
    assert sorted(r.status_code for r in respostas) == [200, 409, 409, 409, 409]
    assert await _creditos(client, h, aluno) == 1


async def test_reposicao_consome_credito(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno = await _aluno(client, h)
    aula1, aula2 = await _aula(client, h, 48), await _aula(client, h, 72)

    sem_credito = await client.post(
        f"/agenda/aulas/{aula2['id']}/agendamentos", headers=h, json={"aluno_id": aluno, "usar_reposicao": True}
    )
    assert sem_credito.status_code == 409

    ag = (await client.post(f"/agenda/aulas/{aula1['id']}/agendamentos", headers=h, json={"aluno_id": aluno})).json()
    await client.post(f"/agenda/agendamentos/{ag['id']}/cancelar", headers=h)
    assert await _creditos(client, h, aluno) == 1

    repo = await client.post(
        f"/agenda/aulas/{aula2['id']}/agendamentos", headers=h, json={"aluno_id": aluno, "usar_reposicao": True}
    )
    assert repo.status_code == 201
    assert repo.json()["tipo"] == "reposicao"
    assert await _creditos(client, h, aluno) == 0


async def test_um_credito_nao_paga_duas_reposicoes_simultaneas(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno = await _aluno(client, h)
    origem = await _aula(client, h, 24)
    ag = (await client.post(f"/agenda/aulas/{origem['id']}/agendamentos", headers=h, json={"aluno_id": aluno})).json()
    await client.post(f"/agenda/agendamentos/{ag['id']}/cancelar", headers=h)

    destinos = [await _aula(client, h, 48 + i) for i in range(4)]
    respostas = await asyncio.gather(
        *[
            client.post(f"/agenda/aulas/{d['id']}/agendamentos", headers=h, json={"aluno_id": aluno, "usar_reposicao": True})
            for d in destinos
        ]
    )
    assert sorted(r.status_code for r in respostas) == [201, 409, 409, 409]
    assert await _creditos(client, h, aluno) == 0


async def test_credito_vencido_nao_pode_ser_usado(client: AsyncClient, registrar, owner_url: str) -> None:  # type: ignore[no-untyped-def]
    est = await registrar()
    h = est["headers"]
    aluno = await _aluno(client, h)
    origem = await _aula(client, h)
    ag = (await client.post(f"/agenda/aulas/{origem['id']}/agendamentos", headers=h, json={"aluno_id": aluno})).json()
    await client.post(f"/agenda/agendamentos/{ag['id']}/cancelar", headers=h)
    assert await _creditos(client, h, aluno) == 1

    # Simula a passagem do tempo. Até o papel dono está sujeito ao RLS (FORCE): define o tenant.
    engine = create_async_engine(owner_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": est["usuario"]["tenant_id"]})
        result = await conn.execute(
            text("UPDATE alunos SET creditos_validade_ate = now() - interval '1 day' WHERE id = :id"), {"id": aluno}
        )
        assert result.rowcount == 1
    await engine.dispose()

    assert await _creditos(client, h, aluno) == 0
    destino = await _aula(client, h, 72)
    resp = await client.post(
        f"/agenda/aulas/{destino['id']}/agendamentos", headers=h, json={"aluno_id": aluno, "usar_reposicao": True}
    )
    assert resp.status_code == 409


async def test_presenca_e_falta(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aula = await _aula(client, h)
    aluno = await _aluno(client, h)
    ag = (await client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": aluno})).json()

    resp = await client.post(f"/agenda/agendamentos/{ag['id']}/presenca", headers=h, json={"status": "falta"})
    assert resp.status_code == 200 and resp.json()["status"] == "falta"
    # Falta não pode virar cancelamento com crédito.
    assert (await client.post(f"/agenda/agendamentos/{ag['id']}/cancelar", headers=h)).status_code == 409
    assert await _creditos(client, h, aluno) == 0


async def test_aluno_inativo_nao_agenda(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aula = await _aula(client, h)
    aluno = await _aluno(client, h)
    await client.patch(f"/alunos/{aluno}", headers=h, json={"ativo": False})

    resp = await client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": aluno})
    assert resp.status_code == 409


async def test_excluir_aula_somente_sem_agendamentos(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    vazia, ocupada = await _aula(client, h), await _aula(client, h, 50)
    aluno = await _aluno(client, h)
    await client.post(f"/agenda/aulas/{ocupada['id']}/agendamentos", headers=h, json={"aluno_id": aluno})

    assert (await client.delete(f"/agenda/aulas/{vazia['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/agenda/aulas/{vazia['id']}", headers=h)).status_code == 404
    assert (await client.delete(f"/agenda/aulas/{ocupada['id']}", headers=h)).status_code == 409


async def test_isolamento_da_agenda_entre_estudios(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    a = (await registrar("Studio A"))["headers"]
    b = (await registrar("Studio B"))["headers"]
    aula_a, aula_b = await _aula(client, a), await _aula(client, b)
    aluno_a, aluno_b = await _aluno(client, a), await _aluno(client, b)
    ag_a = (await client.post(f"/agenda/aulas/{aula_a['id']}/agendamentos", headers=a, json={"aluno_id": aluno_a})).json()

    # B não vê, não agenda e não cancela nada de A — nem misturando IDs.
    assert (await client.get(f"/agenda/aulas/{aula_a['id']}", headers=b)).status_code == 404
    assert (await client.post(f"/agenda/aulas/{aula_a['id']}/agendamentos", headers=b, json={"aluno_id": aluno_b})).status_code == 404
    assert (await client.post(f"/agenda/aulas/{aula_b['id']}/agendamentos", headers=b, json={"aluno_id": aluno_a})).status_code == 404
    assert (await client.post(f"/agenda/agendamentos/{ag_a['id']}/cancelar", headers=b)).status_code == 404
    assert (await client.delete(f"/agenda/aulas/{aula_a['id']}", headers=b)).status_code == 404

    de, ate = _iso(datetime.now(UTC)), _iso(_futuro(24 * 30))
    lista_b = (await client.get("/agenda/aulas", headers=b, params={"de": de, "ate": ate})).json()
    assert [x["id"] for x in lista_b] == [aula_b["id"]]


async def test_cors_libera_frontend_e_bloqueia_origem_desconhecida(client: AsyncClient) -> None:
    preflight = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"}
    ok = await client.options("/auth/login", headers={"Origin": "http://localhost:5173", **preflight})
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"

    for origem in ("https://site-malicioso.com", "https://meu-app.lovable.app", "http://localhost.evil.com"):
        ruim = await client.options("/auth/login", headers={"Origin": origem, **preflight})
        assert "access-control-allow-origin" not in ruim.headers, origem
