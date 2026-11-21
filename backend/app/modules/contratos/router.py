from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioAtual, get_tenant_session, get_usuario_atual
from app.modules.contratos import service
from app.modules.contratos.schemas import (
    ContratoCreate,
    ContratoCriadoOut,
    ContratoOut,
    EncerrarIn,
    EncerrarOut,
    GradeOut,
    MesIn,
)

router = APIRouter(prefix="/contratos", tags=["contratos"])


@router.post("", response_model=ContratoCriadoOut, status_code=status.HTTP_201_CREATED)
async def criar(
    dados: ContratoCreate,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> ContratoCriadoOut:
    """Contrata um plano com horários fixos e já gera a grade do mês."""
    return await service.criar(session, usuario.tenant_id, dados)


@router.get("", response_model=list[ContratoOut])
async def listar(
    aluno_id: UUID | None = None,
    status_contrato: Literal["ativo", "encerrado"] | None = None,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[ContratoOut]:
    return await service.listar(session, usuario.tenant_id, aluno_id, status_contrato)


@router.post("/gerar-grade-mensal", response_model=list[GradeOut])
async def gerar_grade_mensal(
    dados: MesIn,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[GradeOut]:
    """Gera a grade do mês para todos os contratos ativos (idempotente)."""
    return await service.gerar_grade_mensal(session, usuario.tenant_id, dados.ano, dados.mes)


@router.get("/{contrato_id}", response_model=ContratoOut)
async def obter(
    contrato_id: UUID,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> ContratoOut:
    return await service.obter(session, usuario.tenant_id, contrato_id)


@router.post("/{contrato_id}/gerar-grade", response_model=GradeOut)
async def gerar_grade(
    contrato_id: UUID,
    dados: MesIn,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> GradeOut:
    return await service.gerar_grade(session, usuario.tenant_id, contrato_id, dados.ano, dados.mes)


@router.post("/{contrato_id}/encerrar", response_model=EncerrarOut)
async def encerrar(
    contrato_id: UUID,
    dados: EncerrarIn,
    usuario: UsuarioAtual = Depends(get_usuario_atual),
    session: AsyncSession = Depends(get_tenant_session),
) -> EncerrarOut:
    return await service.encerrar(session, usuario.tenant_id, contrato_id, dados)
