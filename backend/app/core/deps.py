"""Dependências de autenticação: o tenant_id sai EXCLUSIVAMENTE do JWT."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import NaoAutorizado
from app.core.database import set_tenant
from app.core.security import decodificar_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UsuarioAtual:
    usuario_id: UUID
    tenant_id: UUID
    papel: str


def get_usuario_atual(
    request: Request, cred: HTTPAuthorizationCredentials | None = Depends(_bearer)
) -> UsuarioAtual:
    if cred is None or cred.scheme.lower() != "bearer":
        raise NaoAutorizado("Faça login para continuar.")
    try:
        payload = decodificar_token(request.app.state.settings, cred.credentials)
        return UsuarioAtual(UUID(payload["sub"]), UUID(payload["tid"]), str(payload.get("papel", "")))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise NaoAutorizado("Sessão inválida ou expirada. Faça login novamente.") from None


async def get_tenant_session(
    request: Request, usuario: UsuarioAtual = Depends(get_usuario_atual)
) -> AsyncIterator[AsyncSession]:
    """Transação por requisição com RLS já ativado para o tenant do token."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        async with session.begin():
            await set_tenant(session, usuario.tenant_id)
            yield session
