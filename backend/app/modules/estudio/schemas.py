from uuid import UUID
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, field_validator


class EstudioOut(BaseModel):
    id: UUID
    nome: str
    capacidade_padrao_turma: int
    antecedencia_cancelamento_horas: int
    validade_credito_dias: int
    fuso_horario: str


class EstudioUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    capacidade_padrao_turma: int | None = Field(default=None, ge=1, le=50)
    antecedencia_cancelamento_horas: int | None = Field(default=None, ge=0, le=168)
    validade_credito_dias: int | None = Field(default=None, ge=1, le=365)
    fuso_horario: str | None = None

    @field_validator("fuso_horario")
    @classmethod
    def _fuso_valido(cls, v: str | None) -> str | None:
        if v is not None and v not in available_timezones():
            raise ValueError("Fuso horário inválido (ex.: America/Sao_Paulo).")
        return v
