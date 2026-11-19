"""Regras de contratos: frequência do plano, horários fixos e geração da grade mensal."""

import calendar
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Conflito, NaoEncontrado
from app.modules.agenda import repository as agenda_repo
from app.modules.agenda import service as agenda_service
from app.modules.contratos import repository
from app.modules.contratos.schemas import (
    ContratoCreate,
    ContratoCriadoOut,
    ContratoOut,
    EncerrarIn,
    EncerrarOut,
    GradeOut,
    HorarioFixo,
)

TITULO_PADRAO = "Pilates"
DURACAO_PADRAO = 50
MESES_A_FRENTE = 3


def _agora() -> datetime:
    return datetime.now(UTC)


async def criar(session: AsyncSession, tenant_id: UUID, dados: ContratoCreate) -> ContratoCriadoOut:
    aluno = await repository.buscar_aluno(session, tenant_id, dados.aluno_id)
    if not aluno:
        raise NaoEncontrado("Aluno não encontrado.")
    if not aluno["ativo"]:
        raise Conflito("Aluno inativo não pode contratar plano.")
    plano = await repository.buscar_plano(session, tenant_id, dados.plano_id)
    if not plano:
        raise NaoEncontrado("Plano não encontrado.")
    if not plano["ativo"]:
        raise Conflito("Este plano está inativo.")
    if len(dados.horarios) != plano["aulas_por_semana"]:
        raise AppError(
            f"O plano '{plano['nome']}' tem {plano['aulas_por_semana']} aula(s) por semana: "
            f"escolha exatamente {plano['aulas_por_semana']} horário(s)."
        )
    if await repository.aluno_tem_contrato_ativo(session, tenant_id, dados.aluno_id):
        raise Conflito("Este aluno já tem um contrato ativo. Encerre-o antes de contratar outro.")

    try:
        contrato_id = await repository.inserir(
            session, tenant_id, dados.aluno_id, dados.plano_id,
            plano["aulas_por_semana"], plano["valor_mensal"], dados.data_inicio,
        )
    except IntegrityError:  # corrida: dois contratos simultâneos para o mesmo aluno
        raise Conflito("Este aluno já tem um contrato ativo.") from None
    for h in dados.horarios:
        await repository.inserir_horario(session, tenant_id, contrato_id, h.dia_semana, h.hora)

    # Geração automática da grade do mês de início (ou do mês atual, se o início já passou).
    cfg = await agenda_repo.config_estudio(session, tenant_id)
    hoje = _agora().astimezone(ZoneInfo(cfg["fuso_horario"])).date()
    ref = max(dados.data_inicio, hoje)
    grade = await gerar_grade(session, tenant_id, contrato_id, ref.year, ref.month)
    return ContratoCriadoOut(contrato=await obter(session, tenant_id, contrato_id), grade=grade)


async def obter(session: AsyncSession, tenant_id: UUID, contrato_id: UUID) -> ContratoOut:
    row = await repository.buscar(session, tenant_id, contrato_id)
    if not row:
        raise NaoEncontrado("Contrato não encontrado.")
    hs = await repository.horarios(session, tenant_id, [contrato_id])
    return ContratoOut(**row, horarios=[HorarioFixo(dia_semana=h["dia_semana"], hora=h["hora"]) for h in hs])


async def listar(session: AsyncSession, tenant_id: UUID, aluno_id: UUID | None, status: str | None) -> list[ContratoOut]:
    rows = await repository.listar(session, tenant_id, aluno_id, status)
    hs = await repository.horarios(session, tenant_id, [r["id"] for r in rows])
    return [
        ContratoOut(
            **r,
            horarios=[HorarioFixo(dia_semana=h["dia_semana"], hora=h["hora"]) for h in hs if h["contrato_id"] == r["id"]],
        )
        for r in rows
    ]


async def gerar_grade(session: AsyncSession, tenant_id: UUID, contrato_id: UUID, ano: int, mes: int) -> GradeOut:
    """Agenda o aluno em todos os horários fixos do mês. Idempotente: rodar de novo não duplica."""
    contrato = await repository.buscar(session, tenant_id, contrato_id)
    if not contrato:
        raise NaoEncontrado("Contrato não encontrado.")
    if contrato["status"] != "ativo":
        raise Conflito("Contrato encerrado não gera grade.")

    cfg = await agenda_repo.config_estudio(session, tenant_id)
    fuso = ZoneInfo(cfg["fuso_horario"])
    agora = _agora()
    hoje = agora.astimezone(fuso).date()
    _validar_mes(hoje, ano, mes)

    resultado = GradeOut(contrato_id=contrato_id, ano=ano, mes=mes)
    aluno = await repository.buscar_aluno(session, tenant_id, contrato["aluno_id"])
    if not aluno or not aluno["ativo"]:
        return resultado

    horarios = await repository.horarios(session, tenant_id, [contrato_id])
    primeiro = max(date(ano, mes, 1), contrato["data_inicio"])
    ultimo = date(ano, mes, calendar.monthrange(ano, mes)[1])
    if contrato["data_fim"]:
        ultimo = min(ultimo, contrato["data_fim"])

    dia = primeiro
    while dia <= ultimo:
        for h in horarios:
            if h["dia_semana"] != dia.weekday():
                continue
            inicio = datetime.combine(dia, h["hora"], tzinfo=fuso)
            if inicio <= agora:
                continue
            aula_id = await agenda_repo.buscar_aula_por_inicio(session, tenant_id, inicio)
            if aula_id is None:
                aula_id = await agenda_repo.inserir_aula(
                    session, tenant_id, TITULO_PADRAO, inicio, DURACAO_PADRAO, cfg["capacidade_padrao_turma"]
                )
                resultado.aulas_criadas += 1
            # SAVEPOINT por aula: um conflito não derruba a grade inteira.
            try:
                async with session.begin_nested():
                    await agenda_service.reservar_vaga(
                        session, tenant_id, aula_id, contrato["aluno_id"], contrato_id=contrato_id
                    )
                resultado.agendadas += 1
            except agenda_service.JaAgendado:
                resultado.ja_existentes += 1
            except agenda_service.TurmaLotada:
                resultado.lotadas.append(inicio)
        dia += timedelta(days=1)
    return resultado


async def gerar_grade_mensal(session: AsyncSession, tenant_id: UUID, ano: int, mes: int) -> list[GradeOut]:
    """Gera a grade do mês para TODOS os contratos ativos (será disparado também pelo job mensal)."""
    return [await gerar_grade(session, tenant_id, cid, ano, mes) for cid in await repository.ids_ativos(session, tenant_id)]


async def encerrar(session: AsyncSession, tenant_id: UUID, contrato_id: UUID, dados: EncerrarIn) -> EncerrarOut:
    contrato = await repository.travar(session, tenant_id, contrato_id)
    if not contrato:
        raise NaoEncontrado("Contrato não encontrado.")
    if contrato["status"] != "ativo":
        raise Conflito("Este contrato já está encerrado.")

    cfg = await agenda_repo.config_estudio(session, tenant_id)
    fuso = ZoneInfo(cfg["fuso_horario"])
    hoje = _agora().astimezone(fuso).date()
    data_fim = dados.data_fim or hoje
    if data_fim < contrato["data_inicio"]:
        raise AppError("A data de encerramento não pode ser anterior ao início do contrato.")

    await repository.encerrar(session, tenant_id, contrato_id, data_fim)
    # Libera as vagas futuras (após o último dia do contrato) sem gerar crédito.
    desde = max(_agora(), datetime.combine(data_fim + timedelta(days=1), time(0), tzinfo=fuso))
    cancelados = await agenda_repo.cancelar_futuros_do_contrato(session, tenant_id, contrato_id, desde)
    return EncerrarOut(contrato=await obter(session, tenant_id, contrato_id), agendamentos_cancelados=cancelados)


def _validar_mes(hoje: date, ano: int, mes: int) -> None:
    alvo = ano * 12 + (mes - 1)
    atual = hoje.year * 12 + (hoje.month - 1)
    if alvo < atual:
        raise AppError("Não é possível gerar grade de um mês que já passou.")
    if alvo > atual + MESES_A_FRENTE:
        raise AppError(f"Gere a grade com no máximo {MESES_A_FRENTE} meses de antecedência.")
