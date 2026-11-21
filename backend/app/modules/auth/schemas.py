from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegistrarIn(BaseModel):
    nome_estudio: str = Field(min_length=2, max_length=150)
    nome: str = Field(min_length=2, max_length=150, description="Nome do(a) responsável")
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class UsuarioOut(BaseModel):
    id: UUID
    nome: str
    email: str
    papel: str
    tenant_id: UUID
    estudio_nome: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
