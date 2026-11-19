"""Hash de senha (Argon2id) e emissão/validação de JWT."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings

_hasher = PasswordHasher()
_ALGORITHM = "HS256"

# Hash fixo usado quando o e-mail não existe: o tempo de resposta fica igual (evita enumerar e-mails).
HASH_FALSO = _hasher.hash("senha-inexistente-para-tempo-constante")


def hash_senha(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return _hasher.verify(senha_hash, senha)
    except (VerificationError, InvalidHashError):
        return False


def criar_token(settings: Settings, usuario_id: UUID, tenant_id: UUID, papel: str) -> str:
    agora = datetime.now(UTC)
    payload = {
        "sub": str(usuario_id),
        "tid": str(tenant_id),
        "papel": papel,
        "iat": agora,
        "exp": agora + timedelta(minutes=settings.jwt_expira_minutos),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=_ALGORITHM)


def decodificar_token(settings: Settings, token: str) -> dict:
    """Levanta jwt.PyJWTError se o token for inválido, expirado ou adulterado."""
    return jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[_ALGORITHM],
        options={"require": ["sub", "tid", "exp"]},
    )
