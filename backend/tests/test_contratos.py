import asyncio
import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from httpx import AsyncClient

SP = ZoneInfo("America/Sao_Paulo")


def _proximo_mes(hoje: date) -> tuple[int, int]:
    return (hoje.year + 1, 1) if hoje.month == 12 else (hoje.year, hoje.month + 1)


def _dias_do_mes(ano: int, mes: int, dias_semana: set[int]) -> list[date]:
    return [
        date(ano, mes, d)
        for d in range(1, calendar.monthrange(ano, mes)[1] + 1)
        if date(ano, mes, d).weekday() in dias_semana
    ]


async def _setup(client: AsyncClient, h: dict, aulas_por_semana: int = 2, valor: str = "350.00") -> tuple[str, str]:
    aluno = (await client.post("/alunos", headers=h, json={"nome": "Carla", "telefone": "11987654321"})).json()["id"]
    plano = (
        await client.post("/planos", headers=h, json={"nome": f"{aulas_por_semana}x", "aulas_por_semana": aulas_por_semana, "valor_mensal": valor})
    ).json()["id"]
    return aluno, plano


async def test_crud_de_planos(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    resp = await client.post("/planos", headers=h, json={"nome": "2x por semana", "aulas_por_semana": 2, "valor_mensal": "320.50"})
    assert resp.status_code == 201
    plano = resp.json()
    assert plano["valor_mensal"] == "320.50"

    await client.patch(f"/planos/{plano['id']}", headers=h, json={"ativo": False})
    assert (await client.get("/planos", headers=h)).json() == []
    assert len((await client.get("/planos?apenas_ativos=false", headers=h)).json()) == 1
    assert (await client.post("/planos", headers=h, json={"nome": "8x", "aulas_por_semana": 8, "valor_mensal": "1"})).status_code == 422


async def test_contrato_copia_preco_do_plano_e_ignora_cliente(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno, plano = await _setup(client, h, 2, "350.00")
    ano, mes = _proximo_mes(date.today())

    resp = await client.post(
        "/contratos",
        headers=h,
        json={
            "aluno_id": aluno, "plano_id": plano, "data_inicio": date(ano, mes, 1).isoformat(),
            "horarios": [{"dia_semana": 0, "hora": "07:00"}, {"dia_semana": 2, "hora": "07:00"}],
            "valor_mensal": "1.00", "aulas_por_semana": 7,
        },
    )
    assert resp.status_code == 201, resp.text
    contrato = resp.json()["contrato"]
    assert contrato["valor_mensal"] == "350.00"
    assert contrato["aulas_por_semana"] == 2

    # Mudar o preço do plano depois não altera o contrato já fechado.
    await client.patch(f"/planos/{plano}", headers=h, json={"valor_mensal": "999.00"})
    assert (await client.get(f"/contratos/{contrato['id']}", headers=h)).json()["valor_mensal"] == "350.00"


async def test_quantidade_de_horarios_precisa_bater_com_o_plano(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno, plano = await _setup(client, h, 2)
    resp = await client.post(
        "/contratos", headers=h,
        json={"aluno_id": aluno, "plano_id": plano, "data_inicio": date.today().isoformat(), "horarios": [{"dia_semana": 0, "hora": "07:00"}]},
    )
    assert resp.status_code == 400
    assert "2 horário" in resp.json()["detail"]


async def test_contrato_gera_grade_mensal_automaticamente(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno, plano = await _setup(client, h, 2)
    ano, mes = _proximo_mes(date.today())

    resp = await client.post(
        "/contratos", headers=h,
        json={"aluno_id": aluno, "plano_id": plano, "data_inicio": date(ano, mes, 1).isoformat(),
              "horarios": [{"dia_semana": 0, "hora": "07:00"}, {"dia_semana": 3, "hora": "18:30"}]},
    )
    grade = resp.json()["grade"]
    esperadas = len(_dias_do_mes(ano, mes, {0, 3}))
    assert grade["agendadas"] == esperadas
    assert grade["aulas_criadas"] == esperadas
    assert grade["lotadas"] == []

    de = datetime(ano, mes, 1, tzinfo=SP)
    ate = de + timedelta(days=calendar.monthrange(ano, mes)[1])
    aulas = (await client.get("/agenda/aulas", headers=h, params={"de": de.isoformat(), "ate": ate.isoformat()})).json()
    assert len(aulas) == esperadas
    for a in aulas:
        local = datetime.fromisoformat(a["inicio"]).astimezone(SP)
        assert (local.weekday(), local.strftime("%H:%M")) in {(0, "07:00"), (3, "18:30")}
        assert [p["aluno_id"] for p in a["participantes"]] == [aluno]

    # Idempotente: gerar de novo não duplica nada.
    de_novo = (await client.post(f"/contratos/{resp.json()['contrato']['id']}/gerar-grade", headers=h, json={"ano": ano, "mes": mes})).json()
    assert de_novo["agendadas"] == 0
    assert de_novo["ja_existentes"] == esperadas


async def test_grade_reaproveita_aula_existente_e_respeita_lotacao(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    await client.patch("/estudio", headers=h, json={"capacidade_padrao_turma": 1})
    ano, mes = _proximo_mes(date.today())
    plano = (await client.post("/planos", headers=h, json={"nome": "1x", "aulas_por_semana": 1, "valor_mensal": "200"})).json()["id"]
    a1 = (await client.post("/alunos", headers=h, json={"nome": "Ana", "telefone": "11987654321"})).json()["id"]
    a2 = (await client.post("/alunos", headers=h, json={"nome": "Bia", "telefone": "11987654322"})).json()["id"]
    corpo = {"plano_id": plano, "data_inicio": date(ano, mes, 1).isoformat(), "horarios": [{"dia_semana": 1, "hora": "08:00"}]}

    g1 = (await client.post("/contratos", headers=h, json={**corpo, "aluno_id": a1})).json()["grade"]
    g2 = (await client.post("/contratos", headers=h, json={**corpo, "aluno_id": a2})).json()["grade"]

    terças = len(_dias_do_mes(ano, mes, {1}))
    assert g1["agendadas"] == terças
    assert g2["aulas_criadas"] == 0  # reaproveitou as aulas do mesmo horário
    assert g2["agendadas"] == 0
    assert len(g2["lotadas"]) == terças


async def test_aluno_so_tem_um_contrato_ativo(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno, plano = await _setup(client, h, 1)
    ano, mes = _proximo_mes(date.today())
    corpo = {"aluno_id": aluno, "plano_id": plano, "data_inicio": date(ano, mes, 1).isoformat(), "horarios": [{"dia_semana": 4, "hora": "09:00"}]}

    respostas = await asyncio.gather(*[client.post("/contratos", headers=h, json=corpo) for _ in range(3)])
    assert sorted(r.status_code for r in respostas) == [201, 409, 409]


async def test_encerrar_contrato_libera_vagas_futuras_sem_credito(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno, plano = await _setup(client, h, 1)
    ano, mes = _proximo_mes(date.today())
    criado = (
        await client.post(
            "/contratos", headers=h,
            json={"aluno_id": aluno, "plano_id": plano, "data_inicio": date(ano, mes, 1).isoformat(),
                  "horarios": [{"dia_semana": 2, "hora": "10:00"}]},
        )
    ).json()
    agendadas = criado["grade"]["agendadas"]

    resp = await client.post(f"/contratos/{criado['contrato']['id']}/encerrar", headers=h, json={"data_fim": date(ano, mes, 1).isoformat()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["contrato"]["status"] == "encerrado"
    quartas_apos_dia_1 = len([d for d in _dias_do_mes(ano, mes, {2}) if d > date(ano, mes, 1)])
    assert body["agendamentos_cancelados"] == quartas_apos_dia_1 <= agendadas

    aluno_out = (await client.get(f"/alunos/{aluno}", headers=h)).json()
    assert aluno_out["creditos_reposicao"] == 0
    assert (await client.post(f"/contratos/{criado['contrato']['id']}/encerrar", headers=h, json={})).status_code == 409
    # Agora pode contratar de novo.
    novo = await client.post(
        "/contratos", headers=h,
        json={"aluno_id": aluno, "plano_id": plano, "data_inicio": date(ano, mes, 2).isoformat(), "horarios": [{"dia_semana": 4, "hora": "10:00"}]},
    )
    assert novo.status_code == 201


async def test_gerar_grade_mensal_para_todos_e_limites_de_mes(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno, plano = await _setup(client, h, 1)
    hoje = date.today()
    await client.post(
        "/contratos", headers=h,
        json={"aluno_id": aluno, "plano_id": plano, "data_inicio": hoje.isoformat(), "horarios": [{"dia_semana": 5, "hora": "09:00"}]},
    )
    ano, mes = _proximo_mes(hoje)
    resp = await client.post("/contratos/gerar-grade-mensal", headers=h, json={"ano": ano, "mes": mes})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["agendadas"] == len(_dias_do_mes(ano, mes, {5}))

    passado = await client.post("/contratos/gerar-grade-mensal", headers=h, json={"ano": hoje.year - 1, "mes": 1})
    assert passado.status_code == 400


async def test_isolamento_de_planos_e_contratos(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    a = (await registrar("Studio A"))["headers"]
    b = (await registrar("Studio B"))["headers"]
    aluno_a, plano_a = await _setup(client, a, 1)
    aluno_b, _ = await _setup(client, b, 1)
    ano, mes = _proximo_mes(date.today())
    contrato_a = (
        await client.post(
            "/contratos", headers=a,
            json={"aluno_id": aluno_a, "plano_id": plano_a, "data_inicio": date(ano, mes, 1).isoformat(), "horarios": [{"dia_semana": 0, "hora": "07:00"}]},
        )
    ).json()["contrato"]["id"]

    assert (await client.get("/planos", headers=b)).json()[0]["id"] != plano_a
    usar_plano_alheio = await client.post(
        "/contratos", headers=b,
        json={"aluno_id": aluno_b, "plano_id": plano_a, "data_inicio": date(ano, mes, 1).isoformat(), "horarios": [{"dia_semana": 0, "hora": "07:00"}]},
    )
    assert usar_plano_alheio.status_code == 404
    assert (await client.get(f"/contratos/{contrato_a}", headers=b)).status_code == 404
    assert (await client.post(f"/contratos/{contrato_a}/encerrar", headers=b, json={})).status_code == 404
    assert (await client.patch(f"/planos/{plano_a}", headers=b, json={"valor_mensal": "1"})).status_code == 404
