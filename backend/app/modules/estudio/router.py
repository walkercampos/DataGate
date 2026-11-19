from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioAtual, get_tenant_session, get_usuario_atual
from app.modules.estudio import service
from app.modules.estudio.schemas import EstudioOut, EstudioUpdate

router = APIRouter(prefix="/estudio", tags=["estudio"])


@router.get("", response_model=EstudioOut)
async def obter(
    usuario: UsuarioAtual = Depends(get_usuario_atual), session: AsyncSession = Depends(get_tenant_session)
) -> EstudioOut:
    return await service.obter(session, usuario.tenant_id)


@router.patch("", response_model=EstudioOut)
async def atualizar(
    dados: EstudioUpdate,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> EstudioOut:
    return await service.atualizar(session, usuario, dados)
