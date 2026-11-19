from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, field_validator

StatusAgendamento = Literal["agendado", "cancelado_com_credito", "cancelado_sem_credito", "presente", "falta"]


class AulaCreate(BaseModel):
    """A capacidade NÃO vem do cliente: é a configuração do estúdio no banco."""

    inicio: AwareDatetime = Field(description="Data/hora com fuso, ex.: 2026-12-01T07:00:00-03:00")
    duracao_minutos: int = Field(default=50, ge=10, le=240)
    titulo: str = Field(default="Pilates", min_length=2, max_length=100)


class AulasRecorrentesCreate(BaseModel):
    data_inicio: date
    semanas: int = Field(ge=1, le=12)
    dias_semana: list[int] = Field(min_length=1, max_length=7, description="0=segunda ... 6=domingo")
    hora: time = Field(description="Horário local do estúdio, ex.: 07:00")
    duracao_minutos: int = Field(default=50, ge=10, le=240)
    titulo: str = Field(default="Pilates", min_length=2, max_length=100)

    @field_validator("dias_semana")
    @classmethod
    def _dias_validos(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("dias_semana deve conter valores de 0 (segunda) a 6 (domingo).")
        return sorted(set(v))


class ParticipanteOut(BaseModel):
    agendamento_id: UUID
    aluno_id: UUID
    aluno_nome: str
    tipo: str
    status: StatusAgendamento


class AulaOut(BaseModel):
    id: UUID
    titulo: str
    inicio: datetime
    duracao_minutos: int
    capacidade: int
    ocupadas: int
    vagas: int
    participantes: list[ParticipanteOut] = []


class AgendarIn(BaseModel):
    aluno_id: UUID
    usar_reposicao: bool = Field(default=False, description="Consome 1 crédito de reposição do aluno")


class AgendamentoOut(BaseModel):
    id: UUID
    aula_id: UUID
    aluno_id: UUID
    tipo: str
    status: StatusAgendamento
    criado_em: datetime


class CancelamentoOut(BaseModel):
    agendamento: AgendamentoOut
    credito_gerado: bool
    mensagem: str


class PresencaIn(BaseModel):
    status: Literal["presente", "falta"]
