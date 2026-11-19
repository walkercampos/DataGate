from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioAtual, get_tenant_session, get_usuario_atual
from app.modules.prontuario import service
from app.modules.prontuario.schemas import RegistroCreate, RegistroOut, RegistroUpdate, VerificacaoOut

router = APIRouter(tags=["prontuario"])


@router.post("/alunos/{aluno_id}/prontuario", response_model=RegistroOut, status_code=status.HTTP_201_CREATED)
async def criar(
    aluno_id: UUID,
    dados: RegistroCreate,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> RegistroOut:
    """Cria uma avaliação ou evolução como RASCUNHO."""
    return await service.criar(session, usuario, aluno_id, dados)


@router.get("/alunos/{aluno_id}/prontuario", response_model=list[RegistroOut])
async def listar(
    aluno_id: UUID,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[RegistroOut]:
    return await service.listar_do_aluno(session, usuario.tenant_id, aluno_id)


@router.get("/prontuario/{registro_id}", response_model=RegistroOut)
async def obter(
    registro_id: UUID,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> RegistroOut:
    return await service.obter(session, usuario.tenant_id, registro_id)


@router.patch("/prontuario/{registro_id}", response_model=RegistroOut)
async def atualizar(
    registro_id: UUID,
    dados: RegistroUpdate,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> RegistroOut:
    return await service.atualizar(session, usuario.tenant_id, registro_id, dados)


@router.delete("/prontuario/{registro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir(
    registro_id: UUID,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> Response:
    await service.excluir(session, usuario.tenant_id, registro_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/prontuario/{registro_id}/assinar", response_model=RegistroOut)
async def assinar(
    registro_id: UUID,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> RegistroOut:
    """Assina o registro: o banco grava data, hash SHA-256 e bloqueia alterações para sempre."""
    return await service.assinar(session, usuario, registro_id)


@router.get("/prontuario/{registro_id}/verificar", response_model=VerificacaoOut)
async def verificar(
    registro_id: UUID,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> VerificacaoOut:
    """Recalcula o hash e compara com o gravado na assinatura."""
    return await service.verificar(session, usuario.tenant_id, registro_id)
