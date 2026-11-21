"""Regras do prontuário: rascunho editável; assinado é imutável (garantido também por trigger)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioAtual
from app.core.errors import AppError, Conflito, NaoEncontrado
from app.modules.prontuario import repository
from app.modules.prontuario.schemas import RegistroCreate, RegistroOut, RegistroUpdate, VerificacaoOut

MSG_IMUTAVEL = "Registro assinado é imutável: não pode ser alterado nem excluído."


async def criar(session: AsyncSession, usuario: UsuarioAtual, aluno_id: UUID, dados: RegistroCreate) -> RegistroOut:
    tid = usuario.tenant_id
    if not await repository.aluno_existe(session, tid, aluno_id):
        raise NaoEncontrado("Aluno não encontrado.")
    if dados.agendamento_id and not await repository.agendamento_do_aluno(session, tid, dados.agendamento_id, aluno_id):
        raise NaoEncontrado("Agendamento não encontrado para este aluno.")
    payload = dados.model_dump()
    payload["titulo"] = payload["titulo"].strip()
    # O autor é SEMPRE o usuário do token.
    registro_id = await repository.inserir(session, tid, aluno_id, usuario.usuario_id, payload)
    return await obter(session, tid, registro_id)


async def listar_do_aluno(session: AsyncSession, tenant_id: UUID, aluno_id: UUID) -> list[RegistroOut]:
    if not await repository.aluno_existe(session, tenant_id, aluno_id):
        raise NaoEncontrado("Aluno não encontrado.")
    return [RegistroOut(**r) for r in await repository.listar_do_aluno(session, tenant_id, aluno_id)]


async def obter(session: AsyncSession, tenant_id: UUID, registro_id: UUID) -> RegistroOut:
    row = await repository.buscar(session, tenant_id, registro_id)
    if not row:
        raise NaoEncontrado("Registro de prontuário não encontrado.")
    return RegistroOut(**row)


async def atualizar(session: AsyncSession, tenant_id: UUID, registro_id: UUID, dados: RegistroUpdate) -> RegistroOut:
    await _exigir_rascunho(session, tenant_id, registro_id)
    campos = dados.model_dump(exclude_unset=True)
    for obrigatorio in ("titulo", "conteudo"):
        if campos.get(obrigatorio, "") is None:
            campos.pop(obrigatorio)
    if campos:
        await repository.atualizar(session, tenant_id, registro_id, campos)
    return await obter(session, tenant_id, registro_id)


async def assinar(session: AsyncSession, usuario: UsuarioAtual, registro_id: UUID) -> RegistroOut:
    await _exigir_rascunho(session, usuario.tenant_id, registro_id)
    await repository.assinar(session, usuario.tenant_id, registro_id, usuario.usuario_id)
    return await obter(session, usuario.tenant_id, registro_id)


async def excluir(session: AsyncSession, tenant_id: UUID, registro_id: UUID) -> None:
    await _exigir_rascunho(session, tenant_id, registro_id)
    await repository.excluir(session, tenant_id, registro_id)


async def verificar(session: AsyncSession, tenant_id: UUID, registro_id: UUID) -> VerificacaoOut:
    row = await repository.verificar_hash(session, tenant_id, registro_id)
    if not row:
        raise NaoEncontrado("Registro de prontuário não encontrado.")
    if row["status"] != "assinado":
        raise AppError("Só registros assinados têm hash para verificar.")
    return VerificacaoOut(
        id=row["id"],
        hash_registrado=row["hash_registrado"],
        hash_recalculado=row["hash_recalculado"],
        integro=row["hash_registrado"] == row["hash_recalculado"],
    )


async def _exigir_rascunho(session: AsyncSession, tenant_id: UUID, registro_id: UUID) -> None:
    status = await repository.travar_status(session, tenant_id, registro_id)
    if status is None:
        raise NaoEncontrado("Registro de prontuário não encontrado.")
    if status != "rascunho":
        raise Conflito(MSG_IMUTAVEL)
