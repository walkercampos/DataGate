from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioAtual, get_tenant_session, get_usuario_atual
from app.modules.alunos import service
from app.modules.alunos.schemas import AlunoCreate, AlunoOut, AlunoUpdate

router = APIRouter(prefix="/alunos", tags=["alunos"])


@router.post("", response_model=AlunoOut, status_code=status.HTTP_201_CREATED)
async def criar(
    dados: AlunoCreate,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> AlunoOut:
    return await service.criar(session, usuario.tenant_id, dados)


@router.get("", response_model=list[AlunoOut])
async def listar(
    busca: str | None = Query(default=None, max_length=100),
    apenas_ativos: bool = True,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[AlunoOut]:
    return await service.listar(session, usuario.tenant_id, busca, apenas_ativos)


@router.get("/{aluno_id}", response_model=AlunoOut)
async def obter(
    aluno_id: UUID,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> AlunoOut:
    return await service.obter(session, usuario.tenant_id, aluno_id)


@router.patch("/{aluno_id}", response_model=AlunoOut)
async def atualizar(
    aluno_id: UUID,
    dados: AlunoUpdate,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> AlunoOut:
    return await service.atualizar(session, usuario.tenant_id, aluno_id, dados)
