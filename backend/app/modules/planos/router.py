from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioAtual, get_tenant_session, get_usuario_atual
from app.modules.planos import service
from app.modules.planos.schemas import PlanoCreate, PlanoOut, PlanoUpdate

router = APIRouter(prefix="/planos", tags=["planos"])


@router.post("", response_model=PlanoOut, status_code=status.HTTP_201_CREATED)
async def criar(
    dados: PlanoCreate,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> PlanoOut:
    return await service.criar(session, usuario.tenant_id, dados)


@router.get("", response_model=list[PlanoOut])
async def listar(
    apenas_ativos: bool = True,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[PlanoOut]:
    return await service.listar(session, usuario.tenant_id, apenas_ativos)


@router.patch("/{plano_id}", response_model=PlanoOut)
async def atualizar(
    plano_id: UUID,
    dados: PlanoUpdate,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> PlanoOut:
    return await service.atualizar(session, usuario.tenant_id, plano_id, dados)
