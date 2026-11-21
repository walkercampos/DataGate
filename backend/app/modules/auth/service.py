"""Regras de cadastro e login."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import set_tenant
from app.core.errors import Conflito, NaoAutorizado, NaoEncontrado
from app.core.security import HASH_FALSO, criar_token, hash_senha, verificar_senha
from app.modules.auth import repository
from app.modules.auth.schemas import LoginIn, RegistrarIn, TokenOut, UsuarioOut

MSG_CREDENCIAIS = "E-mail ou senha incorretos."


async def registrar_estudio(session: AsyncSession, settings: Settings, dados: RegistrarIn) -> TokenOut:
    email = dados.email.lower()
    if await repository.buscar_credenciais(session, email):
        raise Conflito("Este e-mail já está cadastrado.")

    tenant_id = uuid.uuid4()  # gerado no backend, nunca pelo cliente
    await set_tenant(session, tenant_id)
    await repository.inserir_tenant(session, tenant_id, dados.nome_estudio.strip())
    try:
        usuario_id = await repository.inserir_usuario(
            session, tenant_id, dados.nome.strip(), email, hash_senha(dados.senha), "admin"
        )
    except IntegrityError:  # corrida: mesmo e-mail cadastrado em paralelo
        raise Conflito("Este e-mail já está cadastrado.") from None

    return await _emitir_token(session, settings, tenant_id, usuario_id)


async def login(session: AsyncSession, settings: Settings, dados: LoginIn) -> TokenOut:
    cred = await repository.buscar_credenciais(session, dados.email.lower())
    # Sempre verifica um hash (mesmo inexistente) para não revelar quais e-mails existem.
    senha_ok = verificar_senha(dados.senha, cred["senha_hash"] if cred else HASH_FALSO)
    if not cred or not senha_ok:
        raise NaoAutorizado(MSG_CREDENCIAIS)

    await set_tenant(session, cred["tenant_id"])
    return await _emitir_token(session, settings, cred["tenant_id"], cred["usuario_id"])


async def obter_usuario(session: AsyncSession, tenant_id: uuid.UUID, usuario_id: uuid.UUID) -> UsuarioOut:
    row = await repository.buscar_usuario(session, tenant_id, usuario_id)
    if not row:
        raise NaoEncontrado("Usuário não encontrado.")
    return UsuarioOut(**row)


async def _emitir_token(
    session: AsyncSession, settings: Settings, tenant_id: uuid.UUID, usuario_id: uuid.UUID
) -> TokenOut:
    usuario = await obter_usuario(session, tenant_id, usuario_id)
    token = criar_token(settings, usuario.id, usuario.tenant_id, usuario.papel)
    return TokenOut(access_token=token, usuario=usuario)
