from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

TipoRegistro = Literal["avaliacao", "evolucao"]


class RegistroCreate(BaseModel):
    tipo: TipoRegistro
    titulo: str = Field(min_length=2, max_length=150, examples=["Avaliação física inicial"])
    conteudo: str = Field(min_length=1, max_length=20000)
    dor_eva: int | None = Field(default=None, ge=0, le=10, description="Escala Visual Analógica de dor (0-10)")
    agendamento_id: UUID | None = None


class RegistroUpdate(BaseModel):
    """Só rascunhos podem ser editados."""

    titulo: str | None = Field(default=None, min_length=2, max_length=150)
    conteudo: str | None = Field(default=None, min_length=1, max_length=20000)
    dor_eva: int | None = Field(default=None, ge=0, le=10)


class RegistroOut(BaseModel):
    id: UUID
    aluno_id: UUID
    agendamento_id: UUID | None
    tipo: TipoRegistro
    titulo: str
    conteudo: str
    dor_eva: int | None
    autor_id: UUID
    autor_nome: str
    status: Literal["rascunho", "assinado"]
    assinado_por: UUID | None
    assinado_por_nome: str | None
    assinado_em: datetime | None
    hash_sha256: str | None
    criado_em: datetime
    atualizado_em: datetime | None


class VerificacaoOut(BaseModel):
    id: UUID
    hash_registrado: str
    hash_recalculado: str
    integro: bool
