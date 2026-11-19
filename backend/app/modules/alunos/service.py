from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NaoEncontrado
from app.modules.alunos import repository
from app.modules.alunos.schemas import AlunoCreate, AlunoOut, AlunoUpdate


def _para_saida(row: Any) -> AlunoOut:
    """Créditos vencidos não contam: o aluno vê 0 disponível."""
    dados = dict(row)
    validade = dados["creditos_validade_ate"]
    if dados["creditos_reposicao"] and (validade is None or validade < datetime.now(UTC)):
        dados["creditos_reposicao"] = 0
    return AlunoOut(**dados)


async def criar(session: AsyncSession, tenant_id: UUID, dados: AlunoCreate) -> AlunoOut:
    payload = dados.model_dump()
    payload["nome"] = payload["nome"].strip()
    payload["email"] = payload["email"].lower() if payload["email"] else None
    return _para_saida(await repository.inserir(session, tenant_id, payload))


async def listar(session: AsyncSession, tenant_id: UUID, busca: str | None, apenas_ativos: bool) -> list[AlunoOut]:
    busca = busca.strip() if busca and busca.strip() else None
    return [_para_saida(r) for r in await repository.listar(session, tenant_id, busca, apenas_ativos)]


async def obter(session: AsyncSession, tenant_id: UUID, aluno_id: UUID) -> AlunoOut:
    row = await repository.buscar(session, tenant_id, aluno_id)
    if not row:
        raise NaoEncontrado("Aluno não encontrado.")
    return _para_saida(row)


async def atualizar(session: AsyncSession, tenant_id: UUID, aluno_id: UUID, dados: AlunoUpdate) -> AlunoOut:
    campos = dados.model_dump(exclude_unset=True)
    # nome/telefone/ativo são obrigatórios no banco: null explícito é ignorado.
    for obrigatorio in ("nome", "telefone", "ativo"):
        if campos.get(obrigatorio, "") is None:
            campos.pop(obrigatorio)
    if "email" in campos and campos["email"]:
        campos["email"] = campos["email"].lower()
    if not campos:
        return await obter(session, tenant_id, aluno_id)
    row = await repository.atualizar(session, tenant_id, aluno_id, campos)
    if not row:
        raise NaoEncontrado("Aluno não encontrado.")
    return _para_saida(row)
