"""Isolamento multi-tenant no PostgreSQL: o RLS precisa barrar mesmo sem o WHERE da aplicação."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import set_tenant

SessionFactory = async_sessionmaker[AsyncSession]


async def _criar_tenant(factory: SessionFactory, nome: str) -> uuid.UUID:
    tid = uuid.uuid4()
    async with factory() as s, s.begin():
        await set_tenant(s, tid)
        await s.execute(text("INSERT INTO tenants (id, nome) VALUES (:id, :nome)"), {"id": tid, "nome": nome})
    return tid


async def test_papel_da_api_nao_ignora_rls(session_factory: SessionFactory) -> None:
    async with session_factory() as s:
        row = (
            await s.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"))
        ).one()
    assert row.rolsuper is False
    assert row.rolbypassrls is False


async def test_tenant_so_enxerga_os_proprios_dados(session_factory: SessionFactory) -> None:
    tenant_a = await _criar_tenant(session_factory, "Estúdio A")
    tenant_b = await _criar_tenant(session_factory, "Estúdio B")

    async with session_factory() as s, s.begin():
        await set_tenant(s, tenant_a)
        # Query propositalmente SEM WHERE tenant: só o RLS está protegendo aqui.
        ids = (await s.execute(text("SELECT id FROM tenants"))).scalars().all()
        alvo_b = (await s.execute(text("SELECT id FROM tenants WHERE id = :id"), {"id": tenant_b})).all()

    assert ids == [tenant_a]
    assert alvo_b == []


async def test_sem_tenant_definido_nada_e_visivel(session_factory: SessionFactory) -> None:
    await _criar_tenant(session_factory, "Estúdio A")

    async with session_factory() as s, s.begin():
        total = (await s.execute(text("SELECT count(*) FROM tenants"))).scalar_one()

    assert total == 0


async def test_tenant_nao_altera_dados_de_outro(session_factory: SessionFactory) -> None:
    tenant_a = await _criar_tenant(session_factory, "Estúdio A")
    tenant_b = await _criar_tenant(session_factory, "Estúdio B")

    async with session_factory() as s, s.begin():
        await set_tenant(s, tenant_a)
        result = await s.execute(text("UPDATE tenants SET nome = 'hackeado' WHERE id = :id"), {"id": tenant_b})
    assert result.rowcount == 0

    async with session_factory() as s, s.begin():
        await set_tenant(s, tenant_b)
        nome = (await s.execute(text("SELECT nome FROM tenants"))).scalar_one()
    assert nome == "Estúdio B"


async def test_tenant_nao_insere_linha_em_nome_de_outro(session_factory: SessionFactory) -> None:
    tenant_a = await _criar_tenant(session_factory, "Estúdio A")

    with pytest.raises(DBAPIError, match="row-level security"):
        async with session_factory() as s, s.begin():
            await set_tenant(s, tenant_a)
            await s.execute(text("INSERT INTO tenants (id, nome) VALUES (:id, 'intruso')"), {"id": uuid.uuid4()})


async def test_tenant_vale_somente_dentro_da_transacao(session_factory: SessionFactory) -> None:
    tenant_a = await _criar_tenant(session_factory, "Estúdio A")

    async with session_factory() as s:
        async with s.begin():
            await set_tenant(s, tenant_a)
            assert (await s.execute(text("SELECT count(*) FROM tenants"))).scalar_one() == 1
        # Nova transação na MESMA conexão: o SET LOCAL já expirou.
        async with s.begin():
            assert (await s.execute(text("SELECT count(*) FROM tenants"))).scalar_one() == 0


async def test_evento_processado_nao_pode_ser_carimbado_duas_vezes(session_factory: SessionFactory) -> None:
    async with session_factory() as s, s.begin():
        await s.execute(text("INSERT INTO eventos_processados (evento_id) VALUES ('waha:msg:123')"))

    with pytest.raises(IntegrityError):
        async with session_factory() as s, s.begin():
            await s.execute(text("INSERT INTO eventos_processados (evento_id) VALUES ('waha:msg:123')"))


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM eventos_processados",
        "UPDATE eventos_processados SET processado_em = now()",
        "DELETE FROM tenants",
    ],
)
async def test_api_nao_tem_permissao_para_apagar_ou_reescrever(session_factory: SessionFactory, sql: str) -> None:
    with pytest.raises(DBAPIError, match="permission denied"):
        async with session_factory() as s, s.begin():
            await s.execute(text(sql))
