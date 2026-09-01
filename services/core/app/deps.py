"""Dependências FastAPI compartilhadas (autenticação)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ciem_common.auth import User
from ciem_common.config_loader import load_auth_config
from ciem_common.interfaces import UserRole

security = HTTPBearer(auto_error=False)


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> User:
    if not credentials or not credentials.credentials.startswith("ciem-"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    username = credentials.credentials.removeprefix("ciem-")
    auth_cfg = load_auth_config()
    for entry in auth_cfg.local_users:
        if entry.username == username and entry.enabled:
            return User(
                username=entry.username,
                role=UserRole.ADMIN if entry.role == "admin" else UserRole.OBSERVER,
                auth_source="local",
            )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return user
