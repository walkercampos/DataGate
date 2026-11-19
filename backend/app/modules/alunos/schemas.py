from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

_TEL = {"min_length": 10, "max_length": 20, "pattern": r"^\+?[0-9 ()-]+$", "description": "Ex.: (11) 98765-4321"}


class AlunoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    telefone: str = Field(**_TEL)
    email: EmailStr | None = None
    observacoes: str | None = Field(default=None, max_length=2000)


class AlunoUpdate(BaseModel):
    """Créditos de reposição NÃO são editáveis: só mudam por regra do backend."""

    nome: str | None = Field(default=None, min_length=2, max_length=150)
    telefone: str | None = Field(default=None, **_TEL)
    email: EmailStr | None = None
    observacoes: str | None = Field(default=None, max_length=2000)
    ativo: bool | None = None


class AlunoOut(BaseModel):
    id: UUID
    nome: str
    telefone: str
    email: str | None
    observacoes: str | None
    ativo: bool
    creditos_reposicao: int
    creditos_validade_ate: datetime | None
    criado_em: datetime
