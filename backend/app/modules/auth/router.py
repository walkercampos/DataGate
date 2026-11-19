from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import UsuarioAtual, get_tenant_session, get_usuario_atual
from app.modules.auth import service
from app.modules.auth.schemas import LoginIn, RegistrarIn, TokenOut, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registrar", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def registrar(dados: RegistrarIn, request: Request, session: AsyncSession = Depends(get_session)) -> TokenOut:
    """Cria um novo estúdio (tenant) e o usuário administrador dele."""
    return await service.registrar_estudio(session, request.app.state.settings, dados)


@router.post("/login", response_model=TokenOut)
async def login(dados: LoginIn, request: Request, session: AsyncSession = Depends(get_session)) -> TokenOut:
    return await service.login(session, request.app.state.settings, dados)


@router.get("/me", response_model=UsuarioOut)
async def me(
    usuario: UsuarioAtual = Depends(get_usuario_atual), session: AsyncSession = Depends(get_tenant_session)
) -> UsuarioOut:
    return await service.obter_usuario(session, usuario.tenant_id, usuario.usuario_id)
