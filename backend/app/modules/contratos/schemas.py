from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class HorarioFixo(BaseModel):
    dia_semana: int = Field(ge=0, le=6, description="0=segunda ... 6=domingo")
    hora: time = Field(description="Horário local do estúdio, ex.: 07:00")


class ContratoCreate(BaseModel):
    """Preço e frequência NÃO vêm do cliente: são copiados do plano no banco."""

    aluno_id: UUID
    plano_id: UUID
    data_inicio: date
    horarios: list[HorarioFixo] = Field(min_length=1, max_length=7)

    @field_validator("horarios")
    @classmethod
    def _sem_repetidos(cls, v: list[HorarioFixo]) -> list[HorarioFixo]:
        if len({(h.dia_semana, h.hora) for h in v}) != len(v):
            raise ValueError("Há horários repetidos.")
        return v


class ContratoOut(BaseModel):
    id: UUID
    aluno_id: UUID
    aluno_nome: str
    plano_id: UUID
    plano_nome: str
    aulas_por_semana: int
    valor_mensal: Decimal
    data_inicio: date
    data_fim: date | None
    status: str
    horarios: list[HorarioFixo]
    criado_em: datetime


class MesIn(BaseModel):
    ano: int = Field(ge=2020, le=2100)
    mes: int = Field(ge=1, le=12)


class GradeOut(BaseModel):
    contrato_id: UUID
    ano: int
    mes: int
    agendadas: int = 0
    ja_existentes: int = 0
    aulas_criadas: int = 0
    lotadas: list[datetime] = []


class ContratoCriadoOut(BaseModel):
    contrato: ContratoOut
    grade: GradeOut


class EncerrarIn(BaseModel):
    data_fim: date | None = Field(default=None, description="Padrão: hoje")


class EncerrarOut(BaseModel):
    contrato: ContratoOut
    agendamentos_cancelados: int
