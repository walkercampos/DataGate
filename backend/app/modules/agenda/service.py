"""Regras da agenda: lotação, reposição, cancelamento com/sem crédito e presença."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Conflito, NaoEncontrado
from app.modules.agenda import repository
from app.modules.agenda.schemas import (
    AgendamentoOut,
    AgendarIn,
    AulaCreate,
    AulaOut,
    AulasRecorrentesCreate,
    CancelamentoOut,
    ParticipanteOut,
    PresencaIn,
)

MAX_JANELA_DIAS = 62


class TurmaLotada(Conflito):
    pass


class JaAgendado(Conflito):
    pass


def _agora() -> datetime:
    return datetime.now(UTC)


def _capacidade(tipo: str, cfg) -> int:  # type: ignore[no-untyped-def]
    """Regra: atendimento individual = 1 pessoa; turma = capacidade configurada no estúdio."""
    return 1 if tipo == "individual" else cfg["capacidade_padrao_turma"]


async def criar_aula(session: AsyncSession, tenant_id: UUID, dados: AulaCreate) -> AulaOut:
    if dados.inicio <= _agora():
        raise AppError("A aula precisa começar no futuro.")
    cfg = await repository.config_estudio(session, tenant_id)
    aula_id = await repository.inserir_aula(
        session, tenant_id, dados.titulo.strip(), dados.inicio, dados.duracao_minutos,
        _capacidade(dados.tipo, cfg), dados.tipo,
    )
    if dados.aluno_id:
        # Mesma transação: se o aluno não puder ser agendado, a aula também não é criada.
        await agendar(session, tenant_id, aula_id, AgendarIn(aluno_id=dados.aluno_id))
    return await obter_aula(session, tenant_id, aula_id)


async def criar_aulas_recorrentes(session: AsyncSession, tenant_id: UUID, dados: AulasRecorrentesCreate) -> list[AulaOut]:
    cfg = await repository.config_estudio(session, tenant_id)
    fuso = ZoneInfo(cfg["fuso_horario"])
    agora = _agora()
    titulo = dados.titulo.strip()

    inicios: list[datetime] = []
    for i in range(dados.semanas * 7):
        dia: date = dados.data_inicio + timedelta(days=i)
        if dia.weekday() in dados.dias_semana:
            inicio = datetime.combine(dia, dados.hora, tzinfo=fuso)
            if inicio > agora:
                inicios.append(inicio)

    # Não duplica aulas já existentes no mesmo horário/título.
    existentes = await repository.inicios_existentes(session, tenant_id, titulo, inicios, dados.tipo)
    novos = [i for i in inicios if i not in existentes]
    for inicio in novos:
        await repository.inserir_aula(
            session, tenant_id, titulo, inicio, dados.duracao_minutos, _capacidade(dados.tipo, cfg), dados.tipo
        )
    if not novos:
        return []
    return await listar_aulas(session, tenant_id, min(novos), max(novos) + timedelta(seconds=1), titulo=titulo)


async def listar_aulas(
    session: AsyncSession, tenant_id: UUID, de: datetime, ate: datetime, titulo: str | None = None
) -> list[AulaOut]:
    if ate <= de:
        raise AppError("O fim do período deve ser depois do início.")
    if ate - de > timedelta(days=MAX_JANELA_DIAS):
        raise AppError(f"Consulte no máximo {MAX_JANELA_DIAS} dias por vez.")
    aulas = await repository.listar_aulas(session, tenant_id, de, ate)
    if titulo:
        aulas = [a for a in aulas if a["titulo"] == titulo]
    parts = await repository.participantes(session, tenant_id, [a["id"] for a in aulas])
    return [_montar_aula(a, [p for p in parts if p["aula_id"] == a["id"]]) for a in aulas]


async def obter_aula(session: AsyncSession, tenant_id: UUID, aula_id: UUID) -> AulaOut:
    aula = await repository.buscar_aula(session, tenant_id, aula_id)
    if not aula:
        raise NaoEncontrado("Aula não encontrada.")
    return _montar_aula(aula, await repository.participantes(session, tenant_id, [aula_id]))


async def excluir_aula(session: AsyncSession, tenant_id: UUID, aula_id: UUID) -> None:
    aula = await repository.travar_aula(session, tenant_id, aula_id)
    if not aula:
        raise NaoEncontrado("Aula não encontrada.")
    if await repository.contar_agendamentos(session, tenant_id, aula_id):
        raise Conflito("Esta aula já teve agendamentos e não pode ser excluída.")
    await repository.excluir_aula(session, tenant_id, aula_id)


async def agendar(session: AsyncSession, tenant_id: UUID, aula_id: UUID, dados: AgendarIn) -> AgendamentoOut:
    aluno = await repository.buscar_aluno(session, tenant_id, dados.aluno_id)
    if not aluno:
        raise NaoEncontrado("Aluno não encontrado.")
    if not aluno["ativo"]:
        raise Conflito("Aluno inativo não pode ser agendado.")
    return await reservar_vaga(session, tenant_id, aula_id, dados.aluno_id, usar_reposicao=dados.usar_reposicao)


async def reservar_vaga(
    session: AsyncSession,
    tenant_id: UUID,
    aula_id: UUID,
    aluno_id: UUID,
    *,
    usar_reposicao: bool = False,
    contrato_id: UUID | None = None,
) -> AgendamentoOut:
    """Núcleo do agendamento (usado pela agenda e pela grade fixa dos contratos)."""
    # 1) Trava a aula: requisições concorrentes para a mesma turma esperam aqui.
    aula = await repository.travar_aula(session, tenant_id, aula_id)
    if not aula:
        raise NaoEncontrado("Aula não encontrada.")
    if aula["inicio"] <= _agora():
        raise Conflito("Esta aula já começou ou já passou.")

    # 2) Com a trava, a contagem é confiável: ninguém insere nesta aula até o commit.
    if await repository.aluno_ja_na_aula(session, tenant_id, aula_id, aluno_id):
        raise JaAgendado("Este aluno já está agendado nesta aula.")
    if await repository.contar_ocupadas(session, tenant_id, aula_id) >= aula["capacidade"]:
        raise TurmaLotada("Turma lotada: não há vagas neste horário.")

    # 3) Reposição: débito atômico. Se a transação falhar depois, o crédito volta (rollback).
    tipo = "regular"
    if usar_reposicao:
        if not await repository.consumir_credito(session, tenant_id, aluno_id):
            raise Conflito("O aluno não tem créditos de reposição válidos.")
        tipo = "reposicao"

    try:
        row = await repository.inserir_agendamento(session, tenant_id, aula_id, aluno_id, tipo, contrato_id)
    except IntegrityError:
        raise JaAgendado("Este aluno já está agendado nesta aula.") from None
    return AgendamentoOut(**row)


async def cancelar(session: AsyncSession, tenant_id: UUID, agendamento_id: UUID) -> CancelamentoOut:
    ag = await repository.travar_agendamento(session, tenant_id, agendamento_id)
    if not ag:
        raise NaoEncontrado("Agendamento não encontrado.")
    if ag["status"] != "agendado":
        raise Conflito("Este agendamento não pode mais ser cancelado.")

    cfg = await repository.config_estudio(session, tenant_id)
    horas = cfg["antecedencia_cancelamento_horas"]
    limite = ag["inicio"] - timedelta(hours=horas)

    if _agora() <= limite:
        row = await repository.atualizar_status(session, tenant_id, agendamento_id, "cancelado_com_credito")
        await repository.conceder_credito(session, tenant_id, ag["aluno_id"], cfg["validade_credito_dias"])
        mensagem = (
            f"Cancelado com {horas}h ou mais de antecedência: +1 crédito de reposição "
            f"válido por {cfg['validade_credito_dias']} dias."
        )
        return CancelamentoOut(agendamento=AgendamentoOut(**row), credito_gerado=True, mensagem=mensagem)

    row = await repository.atualizar_status(session, tenant_id, agendamento_id, "cancelado_sem_credito")
    mensagem = f"Cancelado com menos de {horas}h de antecedência: a aula foi perdida (sem crédito)."
    return CancelamentoOut(agendamento=AgendamentoOut(**row), credito_gerado=False, mensagem=mensagem)


async def registrar_presenca(
    session: AsyncSession, tenant_id: UUID, agendamento_id: UUID, dados: PresencaIn
) -> AgendamentoOut:
    ag = await repository.travar_agendamento(session, tenant_id, agendamento_id)
    if not ag:
        raise NaoEncontrado("Agendamento não encontrado.")
    if ag["status"] not in ("agendado", "presente", "falta"):
        raise Conflito("Agendamento cancelado não recebe presença.")
    return AgendamentoOut(**await repository.atualizar_status(session, tenant_id, agendamento_id, dados.status))


def _montar_aula(aula, participantes) -> AulaOut:  # type: ignore[no-untyped-def]
    return AulaOut(
        id=aula["id"],
        titulo=aula["titulo"],
        tipo=aula["tipo"],
        inicio=aula["inicio"],
        duracao_minutos=aula["duracao_minutos"],
        capacidade=aula["capacidade"],
        ocupadas=aula["ocupadas"],
        vagas=max(aula["capacidade"] - aula["ocupadas"], 0),
        participantes=[ParticipanteOut(**{k: p[k] for k in ParticipanteOut.model_fields}) for p in participantes],
    )
