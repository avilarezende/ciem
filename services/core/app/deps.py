"""Dependências FastAPI compartilhadas (autenticação por token assinado)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ciem_common.auth import User
from ciem_common.config_loader import load_auth_config
from ciem_common.interfaces import UserRole

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Sessão por token assinado (HMAC-SHA256) com expiração e revogação por
# usuário inativo. Substitui o antigo "ciem-{username}" que era forjável.
# ---------------------------------------------------------------------------

_SESSION_TTL_SECONDS = int(os.environ.get("CIEM_SESSION_TTL", "28800"))  # 8h


def _session_secret() -> bytes:
    secret = os.environ.get(
        "CIEM_SECRET_KEY",
        os.environ.get("CIEM_SESSION_SECRET", ""),
    )
    if not secret or secret in ("change-me-in-production", "change-me", "change_me"):
        raise RuntimeError(
            "CIEM_SECRET_KEY não configurada (ou valor padrão). "
            "Defina uma chave forte via variável de ambiente antes de iniciar o core."
        )
    return secret.encode()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode())


def create_session_token(user: User) -> str:
    """Gera token de sessão assinado para a API do core."""
    expires = int(time.time()) + _SESSION_TTL_SECONDS
    payload: dict[str, Any] = {
        "user": user.username,
        "role": user.role.value,
        "exp": expires,
    }
    data = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_session_secret(), data, hashlib.sha256).digest()
    return f"{_b64encode(data)}.{_b64encode(sig)}"


def verify_session_token(token: str) -> dict[str, Any] | None:
    """Valida assinatura e expiração; retorna payload ou None (sem exceção)."""
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        data = _b64decode(payload_b64)
        sig = _b64decode(sig_b64)
        expected = hmac.new(_session_secret(), data, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(data.decode())
        if int(payload.get("exp", 0)) < time.time():
            return None
        return payload
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def _user_from_payload(payload: dict[str, Any]) -> User | None:
    """Constrói User a partir do token, validando que a conta ainda existe/ativa."""
    username = str(payload.get("user", ""))
    if not username:
        return None

    auth_cfg = load_auth_config()
    for entry in auth_cfg.local_users:
        if entry.username == username and entry.enabled:
            return User(
                username=entry.username,
                role=UserRole.ADMIN if entry.role == "admin" else UserRole.OBSERVER,
                auth_source="local",
                display_name=entry.username,
            )
    return None


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    payload = verify_session_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

    user = _user_from_payload(payload)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou desativado",
        )
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return user