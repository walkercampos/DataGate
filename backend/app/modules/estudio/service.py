from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UsuarioAtual
from app.core.errors import NaoEncontrado, Proibido
from app.modules.estudio import repository
from app.modules.estudio.schemas import EstudioOut, EstudioUpdate


async def obter(session: AsyncSession, tenant_id: UUID) -> EstudioOut:
    row = await repository.buscar(session, tenant_id)
    if not row:
        raise NaoEncontrado("Estúdio não encontrado.")
    return EstudioOut(**row)


async def atualizar(session: AsyncSession, usuario: UsuarioAtual, dados: EstudioUpdate) -> EstudioOut:
    if usuario.papel != "admin":
        raise Proibido("Apenas administradores podem alterar as configurações do estúdio.")
    campos = dados.model_dump(exclude_unset=True, exclude_none=True)
    if not campos:
        return await obter(session, usuario.tenant_id)
    row = await repository.atualizar(session, usuario.tenant_id, campos)
    if not row:
        raise NaoEncontrado("Estúdio não encontrado.")
    return EstudioOut(**row)
