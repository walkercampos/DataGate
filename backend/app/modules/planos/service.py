from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NaoEncontrado
from app.modules.planos import repository
from app.modules.planos.schemas import PlanoCreate, PlanoOut, PlanoUpdate


async def criar(session: AsyncSession, tenant_id: UUID, dados: PlanoCreate) -> PlanoOut:
    payload = dados.model_dump()
    payload["nome"] = payload["nome"].strip()
    return PlanoOut(**await repository.inserir(session, tenant_id, payload))


async def listar(session: AsyncSession, tenant_id: UUID, apenas_ativos: bool) -> list[PlanoOut]:
    return [PlanoOut(**r) for r in await repository.listar(session, tenant_id, apenas_ativos)]


async def obter(session: AsyncSession, tenant_id: UUID, plano_id: UUID) -> PlanoOut:
    row = await repository.buscar(session, tenant_id, plano_id)
    if not row:
        raise NaoEncontrado("Plano não encontrado.")
    return PlanoOut(**row)


async def atualizar(session: AsyncSession, tenant_id: UUID, plano_id: UUID, dados: PlanoUpdate) -> PlanoOut:
    campos = dados.model_dump(exclude_unset=True, exclude_none=True)
    if not campos:
        return await obter(session, tenant_id, plano_id)
    row = await repository.atualizar(session, tenant_id, plano_id, campos)
    if not row:
        raise NaoEncontrado("Plano não encontrado.")
    return PlanoOut(**row)
