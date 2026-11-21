import asyncio
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from httpx import AsyncClient

SP = ZoneInfo("America/Sao_Paulo")


def _futuro(horas: float = 48) -> str:
    return (datetime.now(UTC) + timedelta(hours=horas)).isoformat()


async def _aluno(client: AsyncClient, h: dict, nome: str = "Paciente") -> str:
    return (await client.post("/alunos", headers=h, json={"nome": nome, "telefone": "11987654321"})).json()["id"]


async def test_individual_tem_capacidade_1_mesmo_com_turma_de_4(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    resp = await client.post("/agenda/aulas", headers=h, json={"inicio": _futuro(), "tipo": "individual", "titulo": "Fisio", "capacidade": 4})
    assert resp.status_code == 201
    assert resp.json()["tipo"] == "individual"
    assert resp.json()["capacidade"] == 1
    # Turma continua usando a configuração do estúdio.
    turma = (await client.post("/agenda/aulas", headers=h, json={"inicio": _futuro(50)})).json()
    assert (turma["tipo"], turma["capacidade"]) == ("grupo", 4)


async def test_criar_individual_ja_agendando_o_paciente(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    maria = await _aluno(client, h, "Maria")
    resp = await client.post("/agenda/aulas", headers=h, json={"inicio": _futuro(), "tipo": "individual", "titulo": "Avaliação física", "aluno_id": maria})
    assert resp.status_code == 201
    aula = resp.json()
    assert (aula["ocupadas"], aula["vagas"]) == (1, 0)
    assert [p["aluno_id"] for p in aula["participantes"]] == [maria]

    outro = await _aluno(client, h, "João")
    lotada = await client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": outro})
    assert lotada.status_code == 409


async def test_dois_pacientes_simultaneos_no_mesmo_individual(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aula = (await client.post("/agenda/aulas", headers=h, json={"inicio": _futuro(), "tipo": "individual", "titulo": "Fisio"})).json()
    a, b = await _aluno(client, h, "Ana"), await _aluno(client, h, "Bia")
    rs = await asyncio.gather(*[client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": x}) for x in (a, b)])
    assert sorted(r.status_code for r in rs) == [201, 409]


async def test_paciente_invalido_nao_deixa_aula_orfa(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    inicio = datetime.now(UTC) + timedelta(days=2)
    falso = "00000000-0000-0000-0000-000000000001"
    resp = await client.post("/agenda/aulas", headers=h, json={"inicio": inicio.isoformat(), "tipo": "individual", "titulo": "Fisio", "aluno_id": falso})
    assert resp.status_code == 404
    de, ate = (inicio - timedelta(hours=1)).isoformat(), (inicio + timedelta(hours=1)).isoformat()
    assert (await client.get("/agenda/aulas", headers=h, params={"de": de, "ate": ate})).json() == []


async def test_paciente_de_outro_estudio_e_recusado(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    a = (await registrar("Studio A"))["headers"]
    b = (await registrar("Studio B"))["headers"]
    aluno_a = await _aluno(client, a)
    resp = await client.post("/agenda/aulas", headers=b, json={"inicio": _futuro(), "tipo": "individual", "titulo": "Fisio", "aluno_id": aluno_a})
    assert resp.status_code == 404


async def test_individual_aceita_reposicao_presenca_e_cancelamento(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    pac = await _aluno(client, h)
    aula = (await client.post("/agenda/aulas", headers=h, json={"inicio": _futuro(), "tipo": "individual", "titulo": "Fisio", "aluno_id": pac})).json()
    ag = aula["participantes"][0]["agendamento_id"]
    r = (await client.post(f"/agenda/agendamentos/{ag}/cancelar", headers=h)).json()
    assert r["credito_gerado"] is True
    outra = (await client.post("/agenda/aulas", headers=h, json={"inicio": _futuro(72), "tipo": "individual", "titulo": "Fisio"})).json()
    repo = await client.post(f"/agenda/aulas/{outra['id']}/agendamentos", headers=h, json={"aluno_id": pac, "usar_reposicao": True})
    assert repo.status_code == 201 and repo.json()["tipo"] == "reposicao"
    pres = await client.post(f"/agenda/agendamentos/{repo.json()['id']}/presenca", headers=h, json={"status": "presente"})
    assert pres.json()["status"] == "presente"


async def test_grade_recorrente_individual(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    hoje = date.today()
    seg = hoje + timedelta(days=(7 - hoje.weekday()) or 7)
    corpo = {"data_inicio": seg.isoformat(), "semanas": 2, "dias_semana": [1], "hora": "10:00", "titulo": "Fisio", "tipo": "individual"}
    aulas = (await client.post("/agenda/aulas/recorrentes", headers=h, json=corpo)).json()
    assert len(aulas) == 2 and all(a["tipo"] == "individual" and a["capacidade"] == 1 for a in aulas)


async def test_grade_do_contrato_nunca_usa_horario_individual(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    """Um atendimento individual às 07:00 não pode receber alunos da turma fixa das 07:00."""
    h = (await registrar())["headers"]
    hoje = date.today()
    ano, mes = (hoje.year + 1, 1) if hoje.month == 12 else (hoje.year, hoje.month + 1)
    primeira_seg = next(date(ano, mes, d) for d in range(1, 8) if date(ano, mes, d).weekday() == 0)
    pac, aluno = await _aluno(client, h, "Paciente"), await _aluno(client, h, "Aluno da turma")
    inicio = datetime.combine(primeira_seg, time(7, 0), tzinfo=SP).isoformat()
    ind = (await client.post("/agenda/aulas", headers=h, json={"inicio": inicio, "tipo": "individual", "titulo": "Fisio", "aluno_id": pac})).json()

    plano = (await client.post("/planos", headers=h, json={"nome": "1x", "aulas_por_semana": 1, "valor_mensal": "200"})).json()["id"]
    grade = (
        await client.post("/contratos", headers=h, json={"aluno_id": aluno, "plano_id": plano, "data_inicio": date(ano, mes, 1).isoformat(), "horarios": [{"dia_semana": 0, "hora": "07:00"}]})
    ).json()["grade"]
    assert grade["lotadas"] == []  # não tentou entrar no individual
    assert grade["aulas_criadas"] == grade["agendadas"]  # criou turmas próprias
    assert [p["aluno_id"] for p in (await client.get(f"/agenda/aulas/{ind['id']}", headers=h)).json()["participantes"]] == [pac]
