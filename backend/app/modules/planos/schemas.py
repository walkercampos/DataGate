from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PlanoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=100, examples=["2x por semana"])
    aulas_por_semana: int = Field(ge=1, le=7)
    valor_mensal: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class PlanoUpdate(BaseModel):
    """Mudanças valem para novos contratos: contratos existentes guardam a cópia do plano."""

    nome: str | None = Field(default=None, min_length=2, max_length=100)
    aulas_por_semana: int | None = Field(default=None, ge=1, le=7)
    valor_mensal: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    ativo: bool | None = None


class PlanoOut(BaseModel):
    id: UUID
    nome: str
    aulas_por_semana: int
    valor_mensal: Decimal
    ativo: bool
    criado_em: datetime
