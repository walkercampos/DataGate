from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioAtual, get_tenant_session, get_usuario_atual
from app.modules.agenda import service
from app.modules.agenda.schemas import (
    AgendamentoOut,
    AgendarIn,
    AulaCreate,
    AulaOut,
    AulasRecorrentesCreate,
    CancelamentoOut,
    PresencaIn,
)

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.post("/aulas", response_model=AulaOut, status_code=status.HTTP_201_CREATED)
async def criar_aula(
    dados: AulaCreate,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> AulaOut:
    return await service.criar_aula(session, usuario.tenant_id, dados)


@router.post("/aulas/recorrentes", response_model=list[AulaOut], status_code=status.HTTP_201_CREATED)
async def criar_aulas_recorrentes(
    dados: AulasRecorrentesCreate,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[AulaOut]:
    """Gera a grade: ex. seg/qua/sex às 07:00 pelas próximas 4 semanas."""
    return await service.criar_aulas_recorrentes(session, usuario.tenant_id, dados)


@router.get("/aulas", response_model=list[AulaOut])
async def listar_aulas(
    de: AwareDatetime = Query(description="Início do período, com fuso"),
    ate: AwareDatetime = Query(description="Fim do período, com fuso"),
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[AulaOut]:
    return await service.listar_aulas(session, usuario.tenant_id, de, ate)


@router.get("/aulas/{aula_id}", response_model=AulaOut)
async def obter_aula(
    aula_id: UUID,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> AulaOut:
    return await service.obter_aula(session, usuario.tenant_id, aula_id)


@router.delete("/aulas/{aula_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_aula(
    aula_id: UUID,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> Response:
    await service.excluir_aula(session, usuario.tenant_id, aula_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/aulas/{aula_id}/agendamentos", response_model=AgendamentoOut, status_code=status.HTTP_201_CREATED)
async def agendar(
    aula_id: UUID,
    dados: AgendarIn,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> AgendamentoOut:
    return await service.agendar(session, usuario.tenant_id, aula_id, dados)


@router.post("/agendamentos/{agendamento_id}/cancelar", response_model=CancelamentoOut)
async def cancelar(
    agendamento_id: UUID,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> CancelamentoOut:
    return await service.cancelar(session, usuario.tenant_id, agendamento_id)


@router.post("/agendamentos/{agendamento_id}/presenca", response_model=AgendamentoOut)
async def registrar_presenca(
    agendamento_id: UUID,
    dados: PresencaIn,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> AgendamentoOut:
    return await service.registrar_presenca(session, usuario.tenant_id, agendamento_id, dados)
