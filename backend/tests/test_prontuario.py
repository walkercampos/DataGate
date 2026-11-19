import re

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import set_tenant

AVALIACAO = {
    "tipo": "avaliacao",
    "titulo": "Avaliação física inicial",
    "conteudo": "Queixa: lombalgia há 6 meses. Encurtamento de isquiotibiais. Objetivo: fortalecer core.",
    "dor_eva": 6,
}


async def _aluno(client: AsyncClient, h: dict) -> str:
    return (await client.post("/alunos", headers=h, json={"nome": "Paciente", "telefone": "11987654321"})).json()["id"]


async def _registro_assinado(client: AsyncClient, h: dict) -> tuple[str, dict]:
    aluno = await _aluno(client, h)
    reg = (await client.post(f"/alunos/{aluno}/prontuario", headers=h, json=AVALIACAO)).json()
    assinado = (await client.post(f"/prontuario/{reg['id']}/assinar", headers=h)).json()
    return aluno, assinado


async def test_fluxo_rascunho_edicao_assinatura(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    est = await registrar()
    h = est["headers"]
    aluno = await _aluno(client, h)

    criado = await client.post(f"/alunos/{aluno}/prontuario", headers=h, json=AVALIACAO)
    assert criado.status_code == 201
    reg = criado.json()
    assert reg["status"] == "rascunho"
    assert reg["hash_sha256"] is None
    assert reg["autor_id"] == est["usuario"]["id"]

    editado = await client.patch(f"/prontuario/{reg['id']}", headers=h, json={"dor_eva": 4})
    assert editado.status_code == 200 and editado.json()["dor_eva"] == 4

    assinado = await client.post(f"/prontuario/{reg['id']}/assinar", headers=h)
    assert assinado.status_code == 200
    body = assinado.json()
    assert body["status"] == "assinado"
    assert re.fullmatch(r"[0-9a-f]{64}", body["hash_sha256"])
    assert body["assinado_por"] == est["usuario"]["id"]
    assert body["assinado_em"] is not None

    verif = (await client.get(f"/prontuario/{reg['id']}/verificar", headers=h)).json()
    assert verif["integro"] is True
    assert verif["hash_registrado"] == verif["hash_recalculado"] == body["hash_sha256"]

    lista = (await client.get(f"/alunos/{aluno}/prontuario", headers=h)).json()
    assert [r["id"] for r in lista] == [reg["id"]]


async def test_registro_assinado_nao_pode_ser_alterado_nem_excluido_pela_api(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    _, reg = await _registro_assinado(client, h)

    assert (await client.patch(f"/prontuario/{reg['id']}", headers=h, json={"conteudo": "adulterado"})).status_code == 409
    assert (await client.delete(f"/prontuario/{reg['id']}", headers=h)).status_code == 409
    assert (await client.post(f"/prontuario/{reg['id']}/assinar", headers=h)).status_code == 409
    assert (await client.get(f"/prontuario/{reg['id']}", headers=h)).json()["conteudo"] == AVALIACAO["conteudo"]


async def test_rascunho_pode_ser_excluido(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno = await _aluno(client, h)
    reg = (await client.post(f"/alunos/{aluno}/prontuario", headers=h, json=AVALIACAO)).json()
    assert (await client.delete(f"/prontuario/{reg['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/prontuario/{reg['id']}", headers=h)).status_code == 404


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE prontuario_registros SET conteudo = 'adulterado' WHERE id = :id",
        "UPDATE prontuario_registros SET status = 'rascunho' WHERE id = :id",
        "UPDATE prontuario_registros SET hash_sha256 = repeat('0', 64) WHERE id = :id",
        "DELETE FROM prontuario_registros WHERE id = :id",
    ],
)
async def test_trigger_bloqueia_sql_direto_mesmo_do_papel_da_api(
    client: AsyncClient, registrar, session_factory: async_sessionmaker[AsyncSession], sql: str  # type: ignore[no-untyped-def]
) -> None:
    est = await registrar()
    _, reg = await _registro_assinado(client, est["headers"])

    with pytest.raises(DBAPIError, match="prontuario_imutavel"):
        async with session_factory() as s, s.begin():
            await set_tenant(s, est["usuario"]["tenant_id"])
            await s.execute(text(sql), {"id": reg["id"]})


async def test_trigger_bloqueia_ate_o_dono_das_tabelas(client: AsyncClient, registrar, owner_url: str) -> None:  # type: ignore[no-untyped-def]
    est = await registrar()
    _, reg = await _registro_assinado(client, est["headers"])

    engine = create_async_engine(owner_url, poolclass=NullPool)
    try:
        with pytest.raises(DBAPIError, match="prontuario_imutavel"):
            async with engine.begin() as conn:
                await conn.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": est["usuario"]["tenant_id"]})
                await conn.execute(text("UPDATE prontuario_registros SET conteudo = 'x' WHERE id = :id"), {"id": reg["id"]})
    finally:
        await engine.dispose()


async def test_nao_e_possivel_inserir_registro_ja_assinado(
    client: AsyncClient, registrar, session_factory: async_sessionmaker[AsyncSession]  # type: ignore[no-untyped-def]
) -> None:
    est = await registrar()
    u = est["usuario"]
    aluno = await _aluno(client, est["headers"])

    with pytest.raises(DBAPIError, match="prontuario_imutavel"):
        async with session_factory() as s, s.begin():
            await set_tenant(s, u["tenant_id"])
            await s.execute(
                text(
                    """
                    INSERT INTO prontuario_registros
                        (tenant_id, aluno_id, autor_id, tipo, titulo, conteudo, status, assinado_por, assinado_em, hash_sha256)
                    VALUES (:t, :a, :u, 'evolucao', 'falso', 'x', 'assinado', :u, now(), repeat('0', 64))
                    """
                ),
                {"t": u["tenant_id"], "a": aluno, "u": u["id"]},
            )


async def test_verificacao_detecta_adulteracao_com_trigger_desligado(client: AsyncClient, registrar, owner_url: str) -> None:  # type: ignore[no-untyped-def]
    """Mesmo quem tem poder de DDL e desliga o trigger é pego pela verificação do hash."""
    est = await registrar()
    h = est["headers"]
    _, reg = await _registro_assinado(client, h)

    engine = create_async_engine(owner_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE prontuario_registros DISABLE TRIGGER trg_prontuario_protecao"))
        await conn.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": est["usuario"]["tenant_id"]})
        result = await conn.execute(text("UPDATE prontuario_registros SET conteudo = 'adulterado' WHERE id = :id"), {"id": reg["id"]})
        assert result.rowcount == 1
        await conn.execute(text("ALTER TABLE prontuario_registros ENABLE TRIGGER trg_prontuario_protecao"))
    await engine.dispose()

    verif = (await client.get(f"/prontuario/{reg['id']}/verificar", headers=h)).json()
    assert verif["integro"] is False
    assert verif["hash_registrado"] == reg["hash_sha256"]


async def test_validacoes_e_vinculo_com_agendamento(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    h = (await registrar())["headers"]
    aluno = await _aluno(client, h)
    outro = await _aluno(client, h)
    assert (await client.post(f"/alunos/{aluno}/prontuario", headers=h, json={**AVALIACAO, "dor_eva": 11})).status_code == 422
    assert (await client.post(f"/alunos/{aluno}/prontuario", headers=h, json={**AVALIACAO, "tipo": "receita"})).status_code == 422

    from datetime import UTC, datetime, timedelta

    aula = (await client.post("/agenda/aulas", headers=h, json={"inicio": (datetime.now(UTC) + timedelta(days=1)).isoformat()})).json()
    ag = (await client.post(f"/agenda/aulas/{aula['id']}/agendamentos", headers=h, json={"aluno_id": aluno})).json()

    evolucao = {"tipo": "evolucao", "titulo": "Sessão 1", "conteudo": "Boa execução do hundred.", "agendamento_id": ag["id"]}
    assert (await client.post(f"/alunos/{aluno}/prontuario", headers=h, json=evolucao)).status_code == 201
    # Agendamento de outro aluno não pode ser vinculado.
    assert (await client.post(f"/alunos/{outro}/prontuario", headers=h, json=evolucao)).status_code == 404


async def test_isolamento_do_prontuario(client: AsyncClient, registrar) -> None:  # type: ignore[no-untyped-def]
    a = (await registrar("Studio A"))["headers"]
    b = (await registrar("Studio B"))["headers"]
    aluno_a, reg = await _registro_assinado(client, a)

    assert (await client.get(f"/prontuario/{reg['id']}", headers=b)).status_code == 404
    assert (await client.get(f"/prontuario/{reg['id']}/verificar", headers=b)).status_code == 404
    assert (await client.get(f"/alunos/{aluno_a}/prontuario", headers=b)).status_code == 404
    assert (await client.post(f"/alunos/{aluno_a}/prontuario", headers=b, json=AVALIACAO)).status_code == 404
